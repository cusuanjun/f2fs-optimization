# F2FS RMW Offload - 虚拟机安装指�?

## 🔧 在虚拟机�?安�?�内�?

### 前置条件

�?保你已经�?
1. �? 在服务器上编译了内核: `./build-rmw-kernel.sh`
2. �? 在服务器上编译了FEMU: `./build-rmw-femu.sh`
3. �? 虚拟机已�?动并�?以�?�问

---

## 📋 安�?��?��??

### 步�??1: 创建挂载点（在虚拟机�?�?

```bash
# 创建挂载点目�?
sudo mkdir -p /mnt/share

# 验证创建成功
ls -la /mnt/ | grep share
```

**预期输出**:
```
drwxr-xr-x  2 root root 4096 Mar 21 10:00 share
```

### 步�??2: 挂载共享�?录（在虚拟机�?�?

```bash
# 挂载9p共享�?�?
sudo mount -t 9p -o trans=virtio hostshare /mnt/share/ -oversion=9p2000.L

# 验证挂载成功
mount | grep share
```

**预期输出**:
```
hostshare on /mnt/share type 9p (rw,relatime,...)
```

### 步�??3: 验证共享�?录内容（在虚拟机�?�?

```bash
# 列出共享�?录内�?
ls -la /mnt/share/

# 应�?�看到linux-5.4.144�?�?
ls -la /mnt/share/linux-5.4.144/
```

**预期输出**:
```
total 412
drwxrwxr-x  5 1008 1008 4096 Mar 21 10:00 .
drwxr-xr-x  3 root root 4096 Mar 21 10:00 ..
-rw-r--r--  1 1008 1008  983 Mar 18 06:38 4-nn-vm.sh
...
drwxrwxrwx  8 1008 1008 4096 Mar 18 06:49 .git
...
```

### 步�??4: 进入内核�?录（在虚拟机�?�?

```bash
# 进入内核源码�?�?
cd /mnt/share/linux-5.4.144

# 验证�?录内�?
ls -la | head -20
```

### 步�??5: 安�?�内核模块（在虚拟机�?�?

```bash
# 安�?�内核模�?
sudo make INSTALL_MOD_STRIP=1 modules_install

# 这会输出类似的信�?�?
# INSTALL crypto/ablk_helper.ko
# INSTALL crypto/aead.ko
# ...
# INSTALL sound/usb/snd-usbmidi-lib.ko
# DEPMOD  5.4.144
```

**预期时间**: 2-5分钟

### 步�??6: 安�?�内核（在虚拟机�?�?

```bash
# 安�?�内�?
sudo make install

# 这会输出类似的信�?�?
# sh /mnt/share/linux-5.4.144/arch/x86/boot/install.sh 5.4.144 ...
# run-parts: executing /etc/kernel/postinst.d/initramfs-tools 5.4.144 /boot/vmlinuz-5.4.144
# ...
```

**预期时间**: 1-3分钟

### 步�??7: 验证安�?�（在虚拟机�?�?

```bash
# 检查新内核�?否安�?
ls -la /boot/vmlinuz-*

# 应�?�看到新�?5.4.144内核
# -rw-r--r-- 1 root root 8765432 Mar 21 10:00 /boot/vmlinuz-5.4.144
```

### 步�??8: 重启虚拟机（在虚拟机�?�?

```bash
# 重启虚拟�?
sudo reboot

# 或者使用poweroff然后重启
sudo poweroff
```

### 步�??9: 验证新内核启�?（在虚拟机中�?

重启后，检查是否使用了新内核：

```bash
# 检查当前运行的内核版本
uname -r

# 应�?�输�?: 5.4.144

# 检�?RMW_OFFLOAD配置
grep CONFIG_F2FS_MOUNT_RMW_OFFLOAD /boot/config-$(uname -r)

# 应�?�输�?: CONFIG_F2FS_MOUNT_RMW_OFFLOAD=y
```

---

## 🔍 故障排除

### �?�?1: 挂载点不存在

**错�??信息**:
```
mount: /mnt/share/: mount point does not exist.
```

**解决方�??**:
```bash
# 创建挂载�?
sudo mkdir -p /mnt/share

# 重新挂载
sudo mount -t 9p -o trans=virtio hostshare /mnt/share/ -oversion=9p2000.L
```

### �?�?2: 无法挂载9p

**错�??信息**:
```
mount: unknown filesystem type '9p'
```

**解决方�??**:
```bash
# 加载9p模块
sudo modprobe 9p
sudo modprobe 9pnet_virtio

# 重新尝试挂载
sudo mount -t 9p -o trans=virtio hostshare /mnt/share/ -oversion=9p2000.L
```

### �?�?3: 权限�?拒绝

**错�??信息**:
```
Permission denied
```

**解决方�??**:
```bash
# �?保使用sudo
sudo mount -t 9p -o trans=virtio hostshare /mnt/share/ -oversion=9p2000.L

# 或者�?�查目录权�?
sudo chmod 777 /mnt/share
```

### �?�?4: 内核安�?�失�?

**错�??信息**:
```
make: *** [install] Error 1
```

**解决方�??**:
```bash
# 检查是否有足�?�的磁盘空间
df -h /boot

# 检查是否有足�?�的权限
sudo make install

# 查看详细错�??信息
sudo make install 2>&1 | tail -20
```

### �?�?5: 重启后仍然是旧内�?

**解决方�??**:
```bash
# 检�?GRUB配置
sudo update-grub

# 重启
sudo reboot

# 重启后�?��?
uname -r
```

---

## �? 验证清单

安�?�完成后，�?�查以下项�?�?

- [ ] 挂载点已创建: `ls -la /mnt/share`
- [ ] 共享�?录已挂载: `mount | grep share`
- [ ] 内核已安�?: `ls -la /boot/vmlinuz-5.4.144`
- [ ] 新内核已�?�?: `uname -r` 输出 `5.4.144`
- [ ] RMW_OFFLOAD已启�?: `grep CONFIG_F2FS_MOUNT_RMW_OFFLOAD /boot/config-$(uname -r)`

---

## 📝 完整安�?�脚�?

如果你想一次性执行所有�?��?�，�?以使用以下脚�?�?

```bash
#!/bin/bash

echo "=== F2FS RMW Offload 内核安�?�脚�? ==="
echo ""

# 步�??1: 创建挂载�?
echo "步�??1: 创建挂载�?..."
sudo mkdir -p /mnt/share
echo "�? 挂载点已创建"
echo ""

# 步�??2: 挂载共享�?�?
echo "步�??2: 挂载共享�?�?..."
sudo mount -t 9p -o trans=virtio hostshare /mnt/share/ -oversion=9p2000.L
echo "�? 共享�?录已挂载"
echo ""

# 步�??3: 进入内核�?�?
echo "步�??3: 进入内核�?�?..."
cd /mnt/share/linux-5.4.144
echo "�? 已进�? $(pwd)"
echo ""

# 步�??4: 安�?�模�?
echo "步�??4: 安�?�内核模�?..."
sudo make INSTALL_MOD_STRIP=1 modules_install
echo "�? 内核模块已安�?"
echo ""

# 步�??5: 安�?�内�?
echo "步�??5: 安�?�内�?..."
sudo make install
echo "�? 内核已安�?"
echo ""

# 步�??6: 验证
echo "步�??6: 验证安�??..."
echo "内核文件:"
ls -la /boot/vmlinuz-5.4.144
echo ""
echo "RMW_OFFLOAD配置:"
grep CONFIG_F2FS_MOUNT_RMW_OFFLOAD /boot/config-5.4.144 || echo "配置文件不存�?，重�?后�?��?"
echo ""

echo "=== 安�?�完�? ==="
echo ""
echo "下一�?: 重启虚拟�?"
echo "  sudo reboot"
echo ""
echo "重启后验�?:"
echo "  uname -r"
echo "  grep CONFIG_F2FS_MOUNT_RMW_OFFLOAD /boot/config-\$(uname -r)"
```

保存�? `install-kernel.sh` 并执行：

```bash
chmod +x install-kernel.sh
./install-kernel.sh
```

---

## 🚀 下一�?

安�?�完成并重启后：

1. **格式化F2FS**:
```bash
sudo mkfs.f2fs /dev/nvme0n1
```

2. **挂载F2FS**:
```bash
sudo mount -t f2fs -o rmw_offload /dev/nvme0n1 /mnt
```

3. **运�?�测�?**:
```bash
cd /home/femu/io-pass-in-iouring
./test-rmw-offload.sh
```

4. **验证RMW卸载**:
```bash
dmesg | grep RMW-OFFLOAD
```

---

## 📞 需要帮助？

- 查看�?速参�?: `QUICK_REFERENCE.md`
- 查看配置指南: `RMW_OFFLOAD_CONFIG.md`
- 查看完整指南: `RMW_OFFLOAD_README.md`

---

**准�?�就�?**: �? �?  
**�?以开�?**: �? 立即开�?
