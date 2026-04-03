ssize_t f2fs_partial_write_offload(struct inode *inode,
				   struct iov_iter *iter,
				   loff_t offset)
{
	size_t count = iov_iter_count(iter);
	size_t copied = 0;
	ssize_t ret = 0;

	/*
	 * F2FS is a log-structured (copy-on-write) filesystem.
	 * Direct device RMW via NVMe vendor command cannot work because
	 * F2FS always allocates new blocks on write, so reading back
	 * through the filesystem will never see the patched old block.
	 *
	 * Instead, perform host-side RMW through the page cache:
	 *   1. For each page touched by [offset, offset+count),
	 *      read it into the page cache (if not already present),
	 *      copy the new bytes in, mark it dirty.
	 *   2. F2FS writeback will allocate a new block and flush it
	 *      to the device, making the data visible on the next read.
	 *
	 * This is functionally identical to what the generic buffered
	 * write path does for sub-page writes, but we drive it
	 * explicitly so we can log the offload event.
	 */

	pr_info("f2fs_pw: page-cache RMW offset=%lld len=%zu\n", offset, count);

	while (count) {
		struct page *page;
		unsigned int pg_off  = offset_in_page(offset);
		unsigned int pg_len  = min_t(unsigned int,
					 PAGE_SIZE - pg_off, count);
		void *fsdata;

		ret = f2fs_write_begin(NULL, inode->i_mapping, offset,
				       pg_len, 0, &page, &fsdata);
		if (ret) {
			pr_err("f2fs_pw: write_begin failed: %zd\n", ret);
			break;
		}

		if (copy_from_iter(page_address(page) + pg_off,
				   pg_len, iter) != pg_len) {
			f2fs_write_end(NULL, inode->i_mapping, offset,
				       pg_len, 0, page, fsdata);
			ret = -EFAULT;
			break;
		}

		ret = f2fs_write_end(NULL, inode->i_mapping, offset,
				     pg_len, pg_len, page, fsdata);
		if (ret < 0) {
			pr_err("f2fs_pw: write_end failed: %zd\n", ret);
			break;
		}

		copied += pg_len;
		offset += pg_len;
		count  -= pg_len;
		ret = 0;
	}

	if (copied) {
		f2fs_update_iostat(F2FS_I_SB(inode), APP_BUFFERED_IO, copied);
		pr_info("f2fs_pw: page-cache RMW ok copied=%zu\n", copied);
		return (ssize_t)copied;
	}

	return ret;
}
