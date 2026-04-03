/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/linux/nvme_pw.h
 *
 * NVMe Partial Write vendor command definitions.
 * Used by the NVMe host driver (core.c) and F2FS.
 *
 * Opcode: nvme_cmd_write_partial (0xC1)
 *
 *   nsid      : namespace id
 *   cdw10     : lower 32 bits of byte offset within the namespace
 *   cdw11     : upper 32 bits of byte offset within the namespace
 *   cdw12     : byte length of the partial payload
 *   prp1/prp2 : PRP pointer(s) to the data buffer
 */
#ifndef _LINUX_NVME_PW_H
#define _LINUX_NVME_PW_H

#include <linux/types.h>

/**
 * nvme_submit_partial_write() - submit a sub-sector write to an NVMe namespace.
 * @bdev:        block device of the target NVMe namespace
 * @byte_offset: byte offset within the namespace (need not be sector-aligned)
 * @buf:         kernel virtual address of the data to write
 * @byte_len:    number of bytes to write (need not be sector-aligned)
 *
 * Builds a vendor command (opcode 0xC1) and submits it synchronously.
 * The device controller (FEMU) performs the RMW operation internally.
 *
 * Returns 0 on success, negative errno on failure.
 */
int nvme_submit_partial_write(struct block_device *bdev, u64 byte_offset,
			      const void *buf, u32 byte_len);

#endif /* _LINUX_NVME_PW_H */
