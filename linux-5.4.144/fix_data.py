#!/usr/bin/env python3
"""
替换 f2fs_partial_write_offload 的函数体�? NVMe vendor 命令实现�?
策略：找到注释块开头到函数结束�? '}'，整段替�?�?
"""
import sys

INFILE = '/home/femu/io-pass-in-iouring/linux-5.4.144/fs/f2fs/data.c'

with open(INFILE, 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

# 1. 找注释块开头（包含 f2fs_partial_write_offload �? /* 注释�?
comment_start = None
func_sig_line = None
func_end = None

for i, line in enumerate(lines):
    if 'f2fs_partial_write_offload - offload' in line and comment_start is None:
        # 往前找 /*
        for j in range(i, max(i-5, -1), -1):
            if lines[j].strip().startswith('/*'):
                comment_start = j
                break
    if 'ssize_t f2fs_partial_write_offload' in line and func_sig_line is None:
        func_sig_line = i

if comment_start is None or func_sig_line is None:
    print('ERROR: cannot find function markers')
    sys.exit(1)

# 2. 找函数结束的 } (brace matching from func_sig_line)
depth = 0
started = False
for i in range(func_sig_line, len(lines)):
    for ch in lines[i]:
        if ch == '{':
            depth += 1
            started = True
        elif ch == '}':
            depth -= 1
    if started and depth == 0:
        func_end = i
        break

if func_end is None:
    print('ERROR: cannot find function end')
    sys.exit(1)

print('comment_start=%d func_sig=%d func_end=%d' % (comment_start, func_sig_line, func_end))

# 3. 新函数文�?
NEW_FUNC = '''\
/*
 * f2fs_partial_write_offload - offload a non-block-aligned write to FEMU.
 *
 * For non-page-aligned DIO writes, instead of doing host-side RMW via bio,
 * we send a vendor NVMe command (opcode 0xC1, NVME_CMD_WRITE_PARTIAL) to
 * FEMU so the controller performs Read-Modify-Write internally.
 *
 * Command layout (matches FEMU nvme-pw.h):
 *   nsid  = 1
 *   cdw10 = low  32 bits of byte offset within the NVMe namespace
 *   cdw11 = high 32 bits of byte offset within the NVMe namespace
 *   cdw12 = byte length of the partial payload
 *   buffer = partial data (DMA-mapped by nvme_submit_sync_cmd)
 *
 * Returns bytes written on success, -errno on error,
 * or 0 if the block is not yet allocated (caller falls back to buffered I/O).
 */
ssize_t f2fs_partial_write_offload(struct inode *inode,
				   struct iov_iter *iter,
				   loff_t offset)
{
	struct f2fs_sb_info *sbi = F2FS_I_SB(inode);
	struct block_device *bdev = inode->i_sb->s_bdev;
	size_t count = iov_iter_count(iter);
	sector_t file_blk = (sector_t)(offset >> F2FS_BLKSIZE_BITS);
	u32 intra_blk = (u32)(offset & (F2FS_BLKSIZE - 1));
	sector_t phys_blk;
	u64 ns_byte_off;
	void *kbuf;
	struct nvme_command cmd;
	int ret;

	/*
	 * Use bmap() to translate the file logical block to a physical block
	 * on the NVMe namespace.  If the block is not yet allocated we cannot
	 * do RMW; return 0 so the caller falls back to buffered I/O.
	 */
	phys_blk = bmap(inode, file_blk);
	if (phys_blk == 0)
		return 0;

	/*
	 * Byte offset within the NVMe namespace:
	 *   physical block number * F2FS_BLKSIZE + intra-block byte offset.
	 * F2FS always uses 4 KiB blocks (F2FS_BLKSIZE_BITS = 12).
	 */
	ns_byte_off = ((u64)phys_blk << F2FS_BLKSIZE_BITS) + intra_blk;

	/* Copy user data into a kernel bounce buffer. */
	kbuf = kmalloc(count, GFP_KERNEL);
	if (!kbuf)
		return -ENOMEM;

	if (copy_from_iter(kbuf, count, iter) != count) {
		kfree(kbuf);
		return -EFAULT;
	}

	/*
	 * Build vendor NVMe command 0xC1 (NVME_CMD_WRITE_PARTIAL).
	 * nvme_submit_sync_cmd() maps kbuf via blk_rq_map_kern() and waits
	 * synchronously for FEMU to complete the controller-side RMW.
	 */
	memset(&cmd, 0, sizeof(cmd));
	cmd.common.opcode = 0xC1;
	cmd.common.nsid   = cpu_to_le32(1);
	cmd.common.cdw10  = cpu_to_le32((u32)(ns_byte_off & 0xFFFFFFFFULL));
	cmd.common.cdw11  = cpu_to_le32((u32)(ns_byte_off >> 32));
	cmd.common.cdw12  = cpu_to_le32((u32)count);

	pr_info("f2fs_pw: FEMU RMW: file_blk=%llu phys_blk=%llu "
		"ns_byte_off=%llu len=%zu\n",
		(u64)file_blk, (u64)phys_blk, ns_byte_off, count);

	ret = nvme_submit_sync_cmd(bdev_get_queue(bdev), &cmd,
				   kbuf, (unsigned int)count);
	kfree(kbuf);

	if (ret) {
		pr_err("f2fs_pw: FEMU RMW failed: ns_byte_off=%llu len=%zu ret=%d\n",
		       ns_byte_off, count, ret);
		return -EIO;
	}

	/* Update file size if the write extended the file. */
	if (offset + (loff_t)count > i_size_read(inode)) {
		i_size_write(inode, offset + count);
		mark_inode_dirty(inode);
	}

	/*
	 * Invalidate the page cache over the written range so subsequent
	 * reads fetch fresh data from the device.
	 */
	invalidate_inode_pages2_range(inode->i_mapping,
				      offset >> PAGE_SHIFT,
				      (offset + count - 1) >> PAGE_SHIFT);

	f2fs_update_iostat(sbi, APP_DIRECT_IO, count);

	pr_info("f2fs_pw: FEMU RMW success: offset=%lld len=%zu ns_byte_off=%llu\n",
		offset, count, ns_byte_off);

	return (ssize_t)count;
}
'''

# 4. 重建文件：[0..comment_start-1] + NEW_FUNC + [func_end+1..end]
out = []
out.extend(lines[:comment_start])
out.append(NEW_FUNC)
out.extend(lines[func_end + 1:])

with open(INFILE, 'w', encoding='utf-8') as f:
    f.writelines(out)

print('Done. Total lines: %d' % len(out))
