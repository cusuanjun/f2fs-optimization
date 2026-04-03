#!/usr/bin/env python3
"""
按动态�?�号替换 f2fs_partial_write_offload，并插入必�?�的 include�?
使用逐�?��?�取避免一次性加载整�?文件�?
"""
INFILE  = '/home/femu/io-pass-in-iouring/linux-5.4.144/fs/f2fs/data.c'
OUTFILE = '/home/femu/io-pass-in-iouring/linux-5.4.144/fs/f2fs/data.c'

NEW_INCLUDE = (
    '#include <linux/nvme.h>\n'
    'extern int nvme_submit_sync_cmd(struct request_queue *q,'
    ' struct nvme_command *cmd, void *buffer, unsigned bufflen);\n'
)

NEW_FUNC = (
    '/*\n'
    ' * f2fs_partial_write_offload - offload a non-block-aligned write to FEMU.\n'
    ' *\n'
    ' * Sends vendor NVMe command 0xC1 (NVME_CMD_WRITE_PARTIAL) to FEMU so\n'
    ' * the controller performs Read-Modify-Write internally.\n'
    ' *\n'
    ' * cdw10/11 = 64-bit byte offset in namespace, cdw12 = byte length\n'
    ' */\n'
    'ssize_t f2fs_partial_write_offload(struct inode *inode,\n'
    '\t\t\t\t   struct iov_iter *iter,\n'
    '\t\t\t\t   loff_t offset)\n'
    '{\n'
    '\tstruct f2fs_sb_info *sbi = F2FS_I_SB(inode);\n'
    '\tstruct block_device *bdev = inode->i_sb->s_bdev;\n'
    '\tsize_t count = iov_iter_count(iter);\n'
    '\tsector_t file_blk = (sector_t)(offset >> F2FS_BLKSIZE_BITS);\n'
    '\tu32 intra_blk = (u32)(offset & (F2FS_BLKSIZE - 1));\n'
    '\tsector_t phys_blk;\n'
    '\tu64 ns_byte_off;\n'
    '\tvoid *kbuf;\n'
    '\tstruct nvme_command cmd;\n'
    '\tint ret;\n'
    '\n'
    '\tphys_blk = bmap(inode, file_blk);\n'
    '\tif (phys_blk == 0)\n'
    '\t\treturn 0;\n'
    '\n'
    '\tns_byte_off = ((u64)phys_blk << F2FS_BLKSIZE_BITS) + intra_blk;\n'
    '\n'
    '\tkbuf = kmalloc(count, GFP_KERNEL);\n'
    '\tif (!kbuf)\n'
    '\t\treturn -ENOMEM;\n'
    '\n'
    '\tif (copy_from_iter(kbuf, count, iter) != count) {\n'
    '\t\tkfree(kbuf);\n'
    '\t\treturn -EFAULT;\n'
    '\t}\n'
    '\n'
    '\tmemset(&cmd, 0, sizeof(cmd));\n'
    '\tcmd.common.opcode = 0xC1;\n'
    '\tcmd.common.nsid   = cpu_to_le32(1);\n'
    '\tcmd.common.cdw10  = cpu_to_le32((u32)(ns_byte_off & 0xFFFFFFFFULL));\n'
    '\tcmd.common.cdw11  = cpu_to_le32((u32)(ns_byte_off >> 32));\n'
    '\tcmd.common.cdw12  = cpu_to_le32((u32)count);\n'
    '\n'
    '\tpr_info("f2fs_pw: FEMU RMW phys_blk=%llu off=%llu len=%zu\\n",\n'
    '\t\t(u64)phys_blk, ns_byte_off, count);\n'
    '\n'
    '\tret = nvme_submit_sync_cmd(bdev_get_queue(bdev), &cmd,\n'
    '\t\t\t\t   kbuf, (unsigned int)count);\n'
    '\tkfree(kbuf);\n'
    '\n'
    '\tif (ret) {\n'
    '\t\tpr_err("f2fs_pw: FEMU RMW failed off=%llu len=%zu ret=%d\\n",\n'
    '\t\t       ns_byte_off, count, ret);\n'
    '\t\treturn -EIO;\n'
    '\t}\n'
    '\n'
    '\tif (offset + (loff_t)count > i_size_read(inode)) {\n'
    '\t\ti_size_write(inode, offset + count);\n'
    '\t\tmark_inode_dirty(inode);\n'
    '\t}\n'
    '\n'
    '\tinvalidate_inode_pages2_range(inode->i_mapping,\n'
    '\t\t\t\t      offset >> PAGE_SHIFT,\n'
    '\t\t\t\t      (offset + count - 1) >> PAGE_SHIFT);\n'
    '\n'
    '\tf2fs_update_iostat(sbi, APP_DIRECT_IO, count);\n'
    '\n'
    '\tpr_info("f2fs_pw: FEMU RMW ok offset=%lld len=%zu\\n", offset, count);\n'
    '\n'
    '\treturn (ssize_t)count;\n'
    '}\n'
    '\n'
)

# --- Phase 1: scan to find line numbers ---
include_insert_after = None  # line index (0-based) of nvme_pw.h
func_sig_line = None         # line index of 'ssize_t f2fs_partial_write_offload'
next_func_line = None        # line index of 'static ssize_t f2fs_direct_IO'

print('Scanning...')
with open(INFILE, 'r', errors='replace') as f:
    for idx, line in enumerate(f):
        if include_insert_after is None and 'nvme_pw.h' in line:
            include_insert_after = idx
        if func_sig_line is None and 'ssize_t f2fs_partial_write_offload' in line:
            func_sig_line = idx
        if next_func_line is None and 'static ssize_t f2fs_direct_IO' in line:
            next_func_line = idx
        if include_insert_after and func_sig_line and next_func_line:
            break

print('include_after=%s func_sig=%s next_func=%s' % (
    include_insert_after, func_sig_line, next_func_line))

if None in (include_insert_after, func_sig_line, next_func_line):
    print('ERROR: markers not found'); exit(1)

# --- Phase 2: stream-write the new file ---
print('Writing...')
tmp = OUTFILE + '.tmp'
with open(INFILE, 'r', errors='replace') as fin, open(tmp, 'w') as fout:
    for idx, line in enumerate(fin):
        if idx == include_insert_after:
            fout.write(line)          # write the nvme_pw.h line itself
            fout.write(NEW_INCLUDE)   # then the new include
        elif idx == func_sig_line:
            fout.write(NEW_FUNC)      # replace old function with new
        elif func_sig_line < idx < next_func_line:
            pass                      # skip old function body
        else:
            fout.write(line)

import os
os.replace(tmp, OUTFILE)
print('Done.')
