# F2FS RMW Offload Configuration Guide

## Quick Start

### 1. Build the Modified Kernel

```bash
cd /home/femu/io-pass-in-iouring
./build-rmw-kernel.sh
```

Expected output:
```
====> Building Linux kernel with F2FS RMW offload support ...
...
===> Success! Kernel with RMW offload support built successfully!
Compiled kernel binary:
  - /home/femu/io-pass-in-iouring/linux-5.4.144/arch/x86/boot/bzImage
```

### 2. Build the Modified FEMU

```bash
cd /home/femu/workspace/femu-src
./build-rmw-femu.sh
```

Expected output:
```
====> Building FEMU with RMW offload support ...
...
===> Success! FEMU with RMW offload support built successfully!
Compiled FEMU binary:
  - /home/femu/workspace/femu-src/src/iodaFEMU-b13b482/build/qemu-system-x86_64
```

### 3. Install in VM

In the virtual machine:

```bash
# Mount shared directory
sudo mount -t 9p -o trans=virtio hostshare /mnt/share/ -oversion=9p2000.L

# Install kernel
cd /mnt/share/linux-5.4.144
sudo make INSTALL_MOD_STRIP=1 modules_install
sudo make install

# Reboot
sudo reboot
```

### 4. Mount F2FS with RMW Offload

```bash
# Format device
sudo mkfs.f2fs /dev/nvme0n1

# Mount with RMW offload
sudo mount -t f2fs -o rmw_offload /dev/nvme0n1 /mnt
```

## Kernel Configuration

### Enable RMW Offload in Kernel Config

The build script automatically enables this, but you can also do it manually:

```bash
cd /home/femu/io-pass-in-iouring/linux-5.4.144

# Edit .config
echo "CONFIG_F2FS_MOUNT_RMW_OFFLOAD=y" >> .config

# Or use menuconfig
make menuconfig
# Navigate to: File systems -> F2FS -> Enable RMW offload
```

### Verify Configuration

```bash
grep CONFIG_F2FS_MOUNT_RMW_OFFLOAD /boot/config-$(uname -r)
# Should output: CONFIG_F2FS_MOUNT_RMW_OFFLOAD=y
```

## F2FS Mount Options

### Basic Mount

```bash
sudo mount -t f2fs /dev/nvme0n1 /mnt
```

### Mount with RMW Offload

```bash
sudo mount -t f2fs -o rmw_offload /dev/nvme0n1 /mnt
```

### Mount with Multiple Options

```bash
sudo mount -t f2fs -o rmw_offload,active_logs=6,gc_merge /dev/nvme0n1 /mnt
```

### Verify Mount Options

```bash
mount | grep f2fs
# Output should include: rmw_offload
```

## FEMU Configuration

### Launch FEMU with RMW Support

Use the new FEMU binary in your VM launch script:

```bash
/home/femu/workspace/femu-src/src/iodaFEMU-b13b482/build/qemu-system-x86_64 \
    -m 8G \
    -smp 4 \
    -drive file=vm.img,if=none,id=drive0,format=qcow2 \
    -device virtio-blk-pci,drive=drive0 \
    -device femu,devsz_mb=16384,femu_mode=1 \
    -net user,hostfwd=tcp::2222-:22 \
    -net nic \
    -nographic
```

### Enable RMW Offload Logging

In FEMU, RMW offload operations are logged with `[RMW-OFFLOAD]` prefix:

```bash
# Check FEMU logs
grep "RMW-OFFLOAD" femu.log

# Expected output:
# [RMW-OFFLOAD] partial write: byte_offset=..., byte_len=...
# [RMW-OFFLOAD] RMW operation: ns_start=..., first_sector=..., last_sector=...
# [RMW-OFFLOAD] Write complete: slba=..., nlb=...
```

## Verification Steps

### 1. Check Kernel Support

```bash
# In VM
uname -r
# Should show: 5.4.144

# Check RMW_OFFLOAD config
grep CONFIG_F2FS_MOUNT_RMW_OFFLOAD /boot/config-$(uname -r)
# Should output: CONFIG_F2FS_MOUNT_RMW_OFFLOAD=y
```

### 2. Check F2FS Mount

```bash
# In VM
mount | grep f2fs
# Should show: rmw_offload in options
```

### 3. Test RMW Offload

```bash
# In VM
cd /mnt

# Create test file with non-page-aligned write
dd if=/dev/urandom of=test.bin bs=512 count=1 seek=2

# Check kernel logs
dmesg | tail -20
# Should show RMW-related messages if available
```

### 4. Monitor Performance

```bash
# In VM
# Monitor write performance
time dd if=/dev/zero of=/mnt/test.bin bs=4K count=10000

# Check I/O statistics
iostat -x 1 5
```

## Troubleshooting

### Issue: RMW Offload Not Enabled

**Symptom**: Mount succeeds but rmw_offload option not shown

**Solution**:
1. Verify kernel config: `grep CONFIG_F2FS_MOUNT_RMW_OFFLOAD /boot/config-$(uname -r)`
2. Rebuild kernel if needed: `./build-rmw-kernel.sh`
3. Reinstall kernel in VM

### Issue: Mount Fails with rmw_offload Option

**Symptom**: `mount: unknown option 'rmw_offload'`

**Solution**:
1. Check kernel version: `uname -r` (should be 5.4.144)
2. Verify F2FS module is loaded: `lsmod | grep f2fs`
3. Rebuild and reinstall kernel

### Issue: No RMW Offload Messages in Logs

**Symptom**: Writes work but no `[RMW-OFFLOAD]` messages in dmesg

**Solution**:
1. Verify F2FS is mounted with rmw_offload: `mount | grep f2fs`
2. Check if writes are actually non-page-aligned
3. Enable debug logging in FEMU if needed

### Issue: Performance Not Improved

**Symptom**: Write performance similar to without RMW offload

**Solution**:
1. Verify RMW offload is being used: `dmesg | grep RMW-OFFLOAD`
2. Check if workload has many non-page-aligned writes
3. Monitor CPU usage: `top` or `htop`
4. Check FEMU logs for RMW operation details

## Performance Tuning

### Optimize for RMW Workloads

```bash
# Mount with optimized options
sudo mount -t f2fs -o rmw_offload,active_logs=6,gc_merge,extent_cache /dev/nvme0n1 /mnt
```

### Monitor RMW Operations

```bash
# In VM, watch RMW operations in real-time
watch -n 1 'dmesg | grep RMW-OFFLOAD | tail -10'
```

### Benchmark RMW Performance

```bash
# Create test script
cat > /tmp/rmw_bench.sh << 'EOF'
#!/bin/bash
echo "RMW Offload Benchmark"
echo "====================="

# Test 1: Sequential non-page-aligned writes
echo "Test 1: Sequential non-page-aligned writes"
time dd if=/dev/zero of=/mnt/test1.bin bs=512 count=10000 seek=1

# Test 2: Random non-page-aligned writes
echo "Test 2: Random non-page-aligned writes"
time dd if=/dev/urandom of=/mnt/test2.bin bs=512 count=10000 seek=1

# Test 3: Mixed page-aligned and non-page-aligned writes
echo "Test 3: Mixed writes"
time dd if=/dev/zero of=/mnt/test3.bin bs=4K count=5000
time dd if=/dev/zero of=/mnt/test3.bin bs=512 count=5000 seek=1

echo "Benchmark complete"
EOF

chmod +x /tmp/rmw_bench.sh
/tmp/rmw_bench.sh
```

## Advanced Configuration

### Custom Kernel Build

If you need to customize the kernel build:

```bash
cd /home/femu/io-pass-in-iouring/linux-5.4.144

# Use menuconfig for interactive configuration
make menuconfig

# Build with custom config
make -j$(nproc)
```

### Custom FEMU Build

For custom FEMU configuration:

```bash
cd /home/femu/workspace/femu-src/src/iodaFEMU-b13b482/build

# Reconfigure with custom options
meson configure -Dprefix=/usr/local

# Rebuild
ninja
```

## References

- Kernel Build: `/home/femu/io-pass-in-iouring/build-rmw-kernel.sh`
- FEMU Build: `/home/femu/workspace/femu-src/build-rmw-femu.sh`
- Test Suite: `/home/femu/io-pass-in-iouring/test-rmw-offload.sh`
- Documentation: `/home/femu/io-pass-in-iouring/RMW_OFFLOAD_README.md`

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review kernel logs: `dmesg`
3. Check FEMU logs for RMW operation details
4. Verify all components are properly built and installed
