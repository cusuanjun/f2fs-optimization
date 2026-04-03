#!/usr/bin/env python3
"""
高效替换 f2fs_partial_write_offload 函数�?
�?读取文件一次，找到注释块开头和函数结尾，然后替�?�?
"""
INFILE = '/home/femu/io-pass-in-iouring/linux-5.4.144/fs/f2fs/data.c'

# 新函数内容（所有字符串�?�? \n 都是真实的换行�?�，不是�?义）
NEW_FUNC = (
'/*\n'
' * f2fs_partial_write_offload - offload a non-block-aligned write to FEMU.\n'
' *\n'
' * For non-page-aligned DIO writes, instead of doing host-side RMW via bio,\n'
' * we send a vendor NVMe command (opcode 0xC1, NVME_CMD_WRITE_PARTIAL) to\n'
' * FEMU so the controller performs Read-Modify-Write internally.\n'
' *\n'
' * Command layout (matches FEMU nvme-pw.h):\n'
' *   nsid  = 1\n'
' *   cdw10 = low  32 bits of byte offset within the NVMe namespace\n'
' *   cdw11 = high 32 bits of byte offset within the NVMe namespace\n'
' *   cdw12 = byte length of the partial payload\n'
' *   buffer = partial data (DMA-mapped by nvme_submit_sync_cmd)\n'
' *\n'
' * Returns bytes written on success, -errno on error,\n'
' * or 0 if the block is not yet allocated (caller falls back to buffered I/O).\n'
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
'\tpr_info("f2fs_pw: FEMU RMW: phys_blk=%llu ns_byte_off=%llu len=%zu\\n",\n'
'\t\t(u64)phys_blk, ns_byte_off, count);\n'
'\n'
'\tret = nvme_submit_sync_cmd(bdev_get_queue(bdev), &cmd,\n'
'\t\t\t\t   kbuf, (unsigned int)count);\n'
'\tkfree(kbuf);\n'
'\n'
'\tif (ret) {\n'
'\t\tpr_err("f2fs_pw: FEMU RMW failed: ns_byte_off=%llu len=%zu ret=%d\\n",\n'
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
'\tpr_info("f2fs_pw: FEMU RMW ok: offset=%lld len=%zu ns_off=%llu\\n",\n'
'\t\toffset, count, ns_byte_off);\n'
'\n'
'\treturn (ssize_t)count;\n'
'}\n'
)

# 新�?�的 include �? extern 声明
NEW_INCLUDES = (
'#include <linux/nvme.h>\n'
'\n'
'/* nvme_submit_sync_cmd is exported by drivers/nvme/host/nvme-core */\n'
'extern int nvme_submit_sync_cmd(struct request_queue *q,\n'
'\t\t\t\tstruct nvme_command *cmd,\n'
'\t\t\t\tvoid *buffer, unsigned bufflen);\n'
)

with open(INFILE, 'r', errors='replace') as f:
    lines = f.readlines()

# --- Step 1: insert includes after nvme_pw.h ---
for i, line in enumerate(lines):
    if 'nvme_pw.h' in line:
        lines = lines[:i+1] + [NEW_INCLUDES] + lines[i+1:]
        break

# re-find line numbers after insertion
comment_start = None
func_end = None
for i, line in enumerate(lines):
    if 'f2fs_partial_write_offload - offload' in line and comment_start is None:
        for j in range(i, max(i-5,-1), -1):
            if lines[j].strip().startswith('/*'):
                comment_start = j
                break

if comment_start is None:
    print('ERROR: comment not found'); exit(1)

# find end of function via brace matching
depth = 0
started = False
for i in range(comment_start, len(lines)):
    line = lines[i] if isinstance(lines[i], str) else ''
    for ch in line:
        if ch == '{': depth += 1; started = True
        elif ch == '}': depth -= 1
    if started and depth == 0:
        func_end = i
        break

if func_end is None:
    print('ERROR: func end not found'); exit(1)

print('comment_start=%d func_end=%d' % (comment_start, func_end))

# --- Step 2: replace old function with new ---
out = lines[:comment_start] + [NEW_FUNC] + lines[func_end+1:]

with open(INFILE, 'w') as f:
    f.writelines(out)

print('Done. Total lines:', len(out))
