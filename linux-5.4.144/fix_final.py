#!/usr/bin/env python3
# 按精�?行号替换 f2fs_partial_write_offload，并�? nvme_pw.h 后插�? include

INFILE = '/home/femu/io-pass-in-iouring/linux-5.4.144/fs/f2fs/data.c'

# 已知精确行号�?1-based�?
NVME_PW_LINE   = 27    # #include <linux/nvme_pw.h>
FUNC_START     = 2828  # ssize_t f2fs_partial_write_offload(
NEXT_FUNC_LINE = 2879  # static ssize_t f2fs_direct_IO( -- 旧函数结束后的下一�?函数
# 旧函数范�?: [FUNC_START, NEXT_FUNC_LINE-1] (1-based), i.e. lines[2827:2878] (0-based)

with open(INFILE, 'rb') as f:
    raw = f.read()

# �? splitlines(True) 保留行尾
lines = raw.decode('utf-8', errors='replace').splitlines(True)

print('Total lines before:', len(lines))
print('Line %d: %r' % (FUNC_START, lines[FUNC_START-1][:60]))
print('Line %d: %r' % (NEXT_FUNC_LINE, lines[NEXT_FUNC_LINE-1][:60]))

# 新的 include 行（插入�? nvme_pw.h 之后�?
NEW_INCLUDE = (
    '#include <linux/nvme.h>\n'
    'extern int nvme_submit_sync_cmd(struct request_queue *q, struct nvme_command *cmd, void *buffer, unsigned bufflen);\n'
)

# 新函数（替换�? lines[FUNC_START-1 : NEXT_FUNC_LINE-1]，即 lines[2827:2878]�?
NEW_FUNC = (
    '/*\n'
    ' * f2fs_partial_write_offload - offload a non-block-aligned write to FEMU.\n'
    ' *\n'
    ' * Sends vendor NVMe command 0xC1 (NVME_CMD_WRITE_PARTIAL) to FEMU so the\n'
    ' * controller performs Read-Modify-Write internally, instead of the host.\n'
    ' *\n'
    ' * cdw10 = low32(ns_byte_offset)  cdw11 = high32(ns_byte_offset)\n'
    ' * cdw12 = byte_length            buffer = partial payload\n'
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
    '\t/* bmap(): translate file logical block -> NVMe namespace physical block */\n'
    '\tphys_blk = bmap(inode, file_blk);\n'
    '\tif (phys_blk == 0)\n'
    '\t\treturn 0; /* block not allocated yet; caller uses buffered I/O */\n'
    '\n'
    '\t/* Byte offset in the NVMe namespace (4 KiB blocks, F2FS_BLKSIZE_BITS=12) */\n'
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
    '\t/* Fill vendor NVMe command 0xC1 */\n'
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

# Build output using exact 0-based indices
# Insert NEW_INCLUDE after line index NVME_PW_LINE-1 (0-based: 26)
out = []
out.extend(lines[:NVME_PW_LINE])           # lines[0..26] inclusive
out.append(NEW_INCLUDE)
out.extend(lines[NVME_PW_LINE:FUNC_START-1])  # lines[27..2826]
out.append(NEW_FUNC)
out.extend(lines[NEXT_FUNC_LINE-1:])       # lines[2878..end] (f2fs_direct_IO onwards)

with open(INFILE, 'w', encoding='utf-8') as f:
    f.writelines(out)

print('Done. Total lines:', len(out))
print('New func at line ~%d' % (NVME_PW_LINE + 1 + (FUNC_START - NVME_PW_LINE - 1)))
