# F2FS RMW Offload - �?速故障排除指�?

## 🔧 常�?�问题和解决方�??

### 编译�?�?

#### �? 脚本无法执�??

**错�??信息**:
```
sudo: ./build-rmw-kernel.sh: command not found
```

**解决方�??**:
```bash
# 添加执�?�权�?
chmod +x /home/femu/io-pass-in-iouring/build-rmw-kernel.sh
chmod +x /home/femu/workspace/femu-src/build-rmw-femu.sh
chmod +x /home/femu/io-pass-in-iouring/test-rmw-offload.sh

# 验证权限
ls -la /home/femu/io-pass-in-iouring/build-rmw-kernel.sh
# 应�?�显�?: -rwxrwxr-x
```

---

#### �? 编译失败

**错�??信息**:
```
make: *** [all] Error 2
```

**解决方�??**:
```bash
# 1. 检查编译日�?
cat /home/femu/io-pass-in-iouring/rmw-kernel-build.log | tail -50

# 2. 清理并重新编�?
cd /home/femu/io-pass-in-iouring/linux-5.4.144
make clean
./build-rmw-kernel.sh

# 3. 检查依�?
sudo apt-get install build-essential libncurses-dev bison flex libssl-dev libelf-dev
```

---

### 安�?�问�?

#### �? 挂载点不存在

**错�??信息**:
```
mount: /mnt/share/: mount point does not exist.
```

**解决方�??**:
```bash
# 创建挂载�?
sudo mkdir -p /mnt/share

# 验证
ls -la /mnt/ | grep share
```

---

#### �? 无法挂载9p

**错�??信息**:
```
mount: unknown filesystem type '9p'
```

**解决方�??**:
```bash
# 加载9p模块
sudo modprobe 9p
sudo modprobe 9pnet_virtio

# 验证模块已加�?
lsmod | grep 9p
```

---

#### �? 权限�?拒绝

**错�??信息**:
```
Permission denied
```

**解决方�??**:
```bash
# 使用sudo
sudo mount -t 9p -o trans=virtio hostshare /mnt/share/ -oversion=9p2000.L

# 或者修改权�?
sudo chmod 777 /mnt/share
```

---

### 内核安�?�问�?

#### �? 内核安�?�失�?

**错�??信息**:
```
make: *** [install] Error 1
```

**解决方�??**:
```bash
# 1. 检查�?�盘空间
df -h /boot

# 2. 使用sudo
sudo make install

# 3. 查看详细错�??
sudo make install 2>&1 | tail -20
```

---

#### �? 重启后仍然是旧内�?

**错�??信息**:
```
uname -r
# 输出: 5.4.121 (而不�? 5.4.144)
```

**解决方�??**:
```bash
# 1. 更新GRUB
sudo update-grub

# 2. 检�?GRUB配置
sudo grub-mkconfig -o /boot/grub/grub.cfg

# 3. 重启
sudo reboot

# 4. 重启后验�?
uname -r
# 应�?�输�?: 5.4.144
```

---

### F2FS挂载�?�?

#### �? F2FS挂载失败

**错�??信息**:
```
mount: /mnt: unknown filesystem type 'f2fs'
```

**解决方�??**:
```bash
# 1. 检�?F2FS模块
lsmod | grep f2fs

# 2. 加载F2FS模块
sudo modprobe f2fs

# 3. 重新挂载
sudo mount -t f2fs -o rmw_offload /dev/nvme0n1 /mnt
```

---

#### �? rmw_offload选项不�??识别

**错�??信息**:
```
mount: unknown option 'rmw_offload'
```

**解决方�??**:
```bash
# 1. 检查内核配�?
grep CONFIG_F2FS_MOUNT_RMW_OFFLOAD /boot/config-$(uname -r)
# 应�?�输�?: CONFIG_F2FS_MOUNT_RMW_OFFLOAD=y

# 2. 如果没有，重新编译内�?
cd /home/femu/io-pass-in-iouring
./build-rmw-kernel.sh

# 3. 重新安�?�内�?
cd /mnt/share/linux-5.4.144
sudo make INSTALL_MOD_STRIP=1 modules_install
sudo make install
sudo reboot

# 4. 重启后重新挂�?
sudo mount -t f2fs -o rmw_offload /dev/nvme0n1 /mnt
```

---

### RMW卸载�?�?

#### �? RMW卸载不工�?

**症状**: 写入成功但没有RMW卸载日志

**解决方�??**:
```bash
# 1. 验证内核配置
grep CONFIG_F2FS_MOUNT_RMW_OFFLOAD /boot/config-$(uname -r)
# 应�?�输�?: CONFIG_F2FS_MOUNT_RMW_OFFLOAD=y

# 2. 验证挂载选项
mount | grep f2fs
# 应�?�包�?: rmw_offload

# 3. 检查内核日�?
dmesg | grep -i "rmw\|offload"

# 4. 创建测试文件
dd if=/dev/urandom of=/mnt/test.bin bs=512 count=1 seek=2

# 5. 再�?��?�查日�?
dmesg | grep RMW-OFFLOAD
```

---

#### �? 没有看到RMW日志

**症状**: 写入成功但dmesg�?没有RMW-OFFLOAD消息

**解决方�??**:
```bash
# 1. 检查是否启用了日志
dmesg | tail -50

# 2. 增加日志级别
sudo sysctl kernel.printk="8 8 1 7"

# 3. 重新运�?�测�?
dd if=/dev/urandom of=/mnt/test.bin bs=512 count=1 seek=2

# 4. 检查日�?
dmesg | grep RMW-OFFLOAD

# 5. 恢�?�日志级�?
sudo sysctl kernel.printk="4 4 1 7"
```

---

### 性能�?�?

#### �? 性能没有改进

**症状**: �?用RMW卸载后性能没有改进

**解决方�??**:
```bash
# 1. 验证RMW卸载�?否�??使用
dmesg | grep RMW-OFFLOAD | wc -l
# 应�?�有多个RMW操作

# 2. 检查工作负�?
# �?保有非页对齐写入
dd if=/dev/urandom of=/mnt/test.bin bs=512 count=100 seek=1

# 3. 监控CPU使用
top
# 查看CPU使用�?否降�?

# 4. 监控I/O统�??
iostat -x 1 5
```

---

## �? 验证清单

### 编译验证

- [ ] 脚本有执行权�?: `ls -la build-rmw-kernel.sh`
- [ ] 内核编译成功: `ls -la linux-5.4.144/arch/x86/boot/bzImage`
- [ ] FEMU编译成功: `ls -la src/iodaFEMU-b13b482/build/qemu-system-x86_64`

### 安�?�验�?

- [ ] 挂载点已创建: `ls -la /mnt/share`
- [ ] 共享�?录已挂载: `mount | grep share`
- [ ] 内核已安�?: `ls -la /boot/vmlinuz-5.4.144`
- [ ] 新内核已�?�?: `uname -r` 输出 `5.4.144`

### 配置验证

- [ ] RMW_OFFLOAD已启�?: `grep CONFIG_F2FS_MOUNT_RMW_OFFLOAD /boot/config-$(uname -r)`
- [ ] F2FS已挂�?: `mount | grep f2fs`
- [ ] rmw_offload选项已启�?: `mount | grep rmw_offload`

### 功能验证

- [ ] 非页对齐写入成功: `dd if=/dev/urandom of=/mnt/test.bin bs=512 count=1 seek=2`
- [ ] RMW操作已�?�录: `dmesg | grep RMW-OFFLOAD`
- [ ] 数据完整性�?�常: `md5sum /mnt/test.bin`

---

## 🔍 调试技�?

### 查看详细日志

```bash
# 查看所有RMW相关日志
dmesg | grep -i "rmw\|offload\|partial"

# 查看最近的日志
dmesg | tail -100

# 实时监控日志
sudo tail -f /var/log/kern.log | grep -i "rmw\|offload"
```

### 检查系统状�?

```bash
# 检查内核版�?
uname -a

# 检�?F2FS模块
lsmod | grep f2fs

# 检�?9p模块
lsmod | grep 9p

# 检查挂载信�?
mount | grep -E "f2fs|share"
```

### 性能分析

```bash
# 监控I/O性能
iostat -x 1 10

# 监控CPU使用
mpstat -P ALL 1 10

# 监控内存使用
free -h

# 监控磁盘空间
df -h
```

---

## 📞 获取�?�?

### 查看文档

- **�?速参�?**: `QUICK_REFERENCE.md`
- **虚拟机安�?**: `VM_INSTALLATION_GUIDE.md`
- **配置指南**: `RMW_OFFLOAD_CONFIG.md`
- **详细指南**: `RMW_OFFLOAD_README.md`
- **实现细节**: `RMW_OFFLOAD_IMPLEMENTATION.md`

### 收集诊断信息

```bash
# 收集系统信息
uname -a > diagnosis.txt
mount >> diagnosis.txt
dmesg >> diagnosis.txt
lsmod >> diagnosis.txt

# 收集编译日志
cat /home/femu/io-pass-in-iouring/rmw-kernel-build.log >> diagnosis.txt
cat /home/femu/workspace/femu-src/rmw-femu-build.log >> diagnosis.txt

# 查看诊断信息
cat diagnosis.txt
```

---

## 🚀 �?速恢�?

### 如果一切都出错�?

```bash
# 1. 重新编译内核
cd /home/femu/io-pass-in-iouring
./build-rmw-kernel.sh

# 2. 重新编译FEMU
cd /home/femu/workspace/femu-src
./build-rmw-femu.sh

# 3. 在虚拟机�?重新安�??
sudo mount -t 9p -o trans=virtio hostshare /mnt/share/ -oversion=9p2000.L
cd /mnt/share/linux-5.4.144
sudo make clean
sudo make INSTALL_MOD_STRIP=1 modules_install
sudo make install
sudo reboot

# 4. 重新挂载F2FS
sudo mount -t f2fs -o rmw_offload /dev/nvme0n1 /mnt

# 5. 运�?�测�?
cd /home/femu/io-pass-in-iouring
./test-rmw-offload.sh
```

---

**需要帮助？** 查看相关文档或收集诊�?信息�?  
**准�?�就�?�?** 按照�?速参考开始使用�?
