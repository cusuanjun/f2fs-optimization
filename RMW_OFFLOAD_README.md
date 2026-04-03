# F2FS RMW Offload Implementation

## Overview

This implementation enables F2FS to offload Read-Modify-Write (RMW) operations for non-page-aligned writes to the FEMU NVMe controller. This avoids the need to perform RMW in the filesystem layer, improving performance and reducing CPU overhead.

## Architecture

### Components Modified

#### 1. Linux Kernel (F2FS)
- **File**: `/home/femu/io-pass-in-iouring/linux-5.4.144/fs/f2fs/`
  - `data.c`: Added `f2fs_submit_rmw_offload()` function and RMW offload logic in `f2fs_do_write_data_page()`
  - `segment.c`: Added `f2fs_rmw_offload_write_data()` function for RMW offload submission
  - `f2fs.h`: Added function declarations and `F2FS_MOUNT_RMW_OFFLOAD` mount option

#### 2. FEMU NVMe Controller
- **File**: `/home/femu/workspace/femu-src/src/iodaFEMU-b13b482/hw/femu/`
  - `nvme-io.c`: Enhanced `nvme_write_partial()` with improved RMW logic and logging
  - `nvme-pw.h`: Extended with helper macros for setting partial write command fields

### RMW Offload Flow

```
F2FS Write Path
    â†?
f2fs_do_write_data_page()
    â†?
Check if RMW_OFFLOAD enabled
    â†?
f2fs_rmw_offload_write_data()
    â†?
Submit NVME_CMD_WRITE_PARTIAL (0xC1)
    â†?
FEMU Controller
    â†?
nvme_write_partial()
    â†?
1. DMA-read partial data from guest
2. Perform RMW in DRAM backend
3. Return success
    â†?
F2FS completes write
```

## Building

### Build Modified Kernel

```bash
cd /home/femu/io-pass-in-iouring
chmod +x build-rmw-kernel.sh
./build-rmw-kernel.sh
```

This will:
1. Clean previous builds
2. Enable `CONFIG_F2FS_MOUNT_RMW_OFFLOAD` in kernel config
3. Compile the kernel with RMW offload support
4. Output: `linux-5.4.144/arch/x86/boot/bzImage`

### Build Modified FEMU

```bash
cd /home/femu/workspace/femu-src
chmod +x build-rmw-femu.sh
./build-rmw-femu.sh
```

This will:
1. Configure FEMU with meson
2. Build FEMU with enhanced RMW offload support
3. Output: `src/iodaFEMU-b13b482/build/qemu-system-x86_64`

## Installation

### In the VM

1. Mount the kernel source directory:
```bash
sudo mount -t 9p -o trans=virtio hostshare /mnt/share/ -oversion=9p2000.L
```

2. Install the kernel:
```bash
cd /mnt/share/linux-5.4.144
sudo make INSTALL_MOD_STRIP=1 modules_install
sudo make install
sudo reboot
```

### Mount F2FS with RMW Offload

```bash
# Format the device with F2FS
sudo mkfs.f2fs /dev/nvme0n1

# Mount with RMW offload enabled
sudo mount -t f2fs -o rmw_offload /dev/nvme0n1 /mnt
```

## Testing

### Run Test Suite

```bash
cd /home/femu/io-pass-in-iouring
chmod +x test-rmw-offload.sh
./test-rmw-offload.sh
```

This will:
1. Verify F2FS is mounted with rmw_offload option
2. Test non-page-aligned writes
3. Verify data integrity
4. Check kernel logs for RMW offload operations

### Manual Testing

```bash
# Create a test file with non-page-aligned writes
dd if=/dev/urandom of=/mnt/test.bin bs=512 count=1 seek=2

# Check kernel logs for RMW offload messages
dmesg | grep "RMW-OFFLOAD"

# Expected output:
# [RMW-OFFLOAD] partial write: byte_offset=..., byte_len=...
# [RMW-OFFLOAD] RMW operation: ns_start=..., first_sector=..., last_sector=...
# [RMW-OFFLOAD] Write complete: slba=..., nlb=...
```

## Key Features

### 1. Arbitrary Length Writes
- Supports non-page-aligned writes of any length
- Automatically calculates affected sectors
- Handles partial sector updates

### 2. Controller-Side RMW
- RMW operations performed in FEMU controller
- No RMW overhead in F2FS layer
- Reduced CPU usage for write operations

### 3. Transparent Operation
- Works seamlessly with existing F2FS code
- Falls back to regular writes if RMW offload fails
- No changes required to user applications

### 4. Enhanced Logging
- Detailed RMW operation logging in FEMU
- Kernel-side logging for debugging
- Performance monitoring support

## Performance Considerations

### Benefits
- Eliminates RMW overhead in F2FS
- Reduces CPU usage for non-page-aligned writes
- Improves write throughput for small writes

### Trade-offs
- Requires NVMe controller support (FEMU)
- Adds latency for DMA operations
- Requires kernel with RMW_OFFLOAD enabled

## Troubleshooting

### RMW Offload Not Working

1. Check if kernel has RMW_OFFLOAD enabled:
```bash
grep CONFIG_F2FS_MOUNT_RMW_OFFLOAD /boot/config-$(uname -r)
```

2. Check if F2FS is mounted with rmw_offload:
```bash
mount | grep f2fs
```

3. Check kernel logs:
```bash
dmesg | grep -i "rmw\|offload"
```

### Performance Issues

1. Check FEMU logs for RMW operation details
2. Monitor system CPU usage during writes
3. Verify DRAM backend is properly configured

## Implementation Details

### F2FS Changes

#### Mount Option
```c
#define F2FS_MOUNT_RMW_OFFLOAD  0x08000000
```

#### RMW Offload Function
```c
int f2fs_rmw_offload_write_data(struct f2fs_io_info *fio)
```

This function:
1. Checks if RMW_OFFLOAD is enabled
2. Calculates byte offset and length
3. Creates a bio with RMW offload flag
4. Submits the bio to the device

### FEMU Changes

#### Enhanced RMW Logic
```c
static uint16_t nvme_write_partial(FemuCtrl *n, NvmeNamespace *ns,
                                   NvmeCmd *cmd, NvmeRequest *req)
```

This function:
1. Validates byte offset and length
2. DMA-reads partial data from guest
3. Performs sector-by-sector RMW in DRAM backend
4. Returns success status

#### Command Format
```
NVME_CMD_WRITE_PARTIAL (0xC1)
  cdw10/cdw11: 64-bit byte offset
  cdw12: byte length
  prp1/prp2: data buffer pointer
```

## Future Enhancements

1. **Performance Optimization**
   - Batch multiple RMW operations
   - Optimize sector-by-sector patching
   - Add caching for frequently accessed sectors

2. **Extended Features**
   - Support for multiple namespaces
   - Atomic RMW operations
   - RMW with verification

3. **Monitoring and Debugging**
   - RMW operation statistics
   - Performance profiling
   - Detailed error reporting

## References

- F2FS Documentation: https://www.kernel.org/doc/html/latest/filesystems/f2fs.html
- NVMe Specification: https://nvmexpress.org/
- FEMU Project: https://github.com/ucare-uchicago/FEMU

## License

This implementation follows the same license as the Linux kernel (GPL-2.0) and FEMU (GPL-2.0+).
