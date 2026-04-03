#!/usr/bin/env python3
INFILE = '/home/femu/io-pass-in-iouring/linux-5.4.144/fs/f2fs/data.c'

NEW_FUNC = (
'/*\n'
' * f2fs_partial_write_offload - offload a non-block-aligned write to FEMU.\n'
' *\n'
' * For non-page-aligned DIO writes, send vendor NVMe command 0xC1\n'
' * (NVME_CMD_WRITE_PARTIAL) to FEMU so the controller performs RMW internally.\n'
' *\n'
' * cdw10 = low32(byte_offset_in_ns), cdw11 = high32(byte_offset_in_ns)\n'
' * cdw12 = byte_length, buffer = partial payload\n'
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
)

NEW_INCLUDE = (
'#include <linux/nvme.h>\n'
'extern int nvme_submit_sync_cmd(struct request_queue *q, struct nvme_command *cmd, void *buffer, unsigned bufflen);\n'
)

with open(INFILE, 'r', errors='replace') as f:
    lines = f.readlines()

# Step 1: add nvme.h include after nvme_pw.h
nvme_pw_idx = next(i for i,l in enumerate(lines) if 'nvme_pw.h' in l)
lines.insert(nvme_pw_idx + 1, NEW_INCLUDE)

# Step 2: find function signature line (ssize_t f2fs_partial_write_offload)
func_start = next(i for i,l in enumerate(lines) if 'ssize_t f2fs_partial_write_offload' in l)

# Step 3: find function end by brace matching
depth = 0
started = False
func_end = None
for i in range(func_start, len(lines)):
    for ch in lines[i]:
        if ch == '{': depth += 1; started = True
        elif ch == '}': depth -= 1
    if started and depth == 0:
        func_end = i
        break

print('func_start=%d func_end=%d' % (func_start, func_end))

# Step 4: replace
out = lines[:func_start] + [NEW_FUNC] + lines[func_end+1:]

with open(INFILE, 'w') as f:
    f.writelines(out)

print('Done. lines=%d' % len(out))
