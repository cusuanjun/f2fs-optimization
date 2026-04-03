# 9P 挂载�?题诊�?和解决方�?

## �?题描�?

```
mount: /mnt/share: special device hostshare does not exist.
```

这表示QEMU虚拟机中�?9p共享配置不�?�确�?

---

## 🔍 诊断步�??

### 步�??1: 检�?9p模块�?否加�?

在虚拟机�?运�?�：

```bash
# 检�?9p模块
lsmod | grep 9p

# 应�?�看�?:
# 9pnet_virtio
# 9pnet
# 9p
```

如果没有看到，加载模块：

```bash
sudo modprobe 9p
sudo modprobe 9pnet_virtio
```

### 步�??2: 检查可用的挂载�?

在虚拟机�?运�?�：

```bash
# 列出所有可用的9p挂载�?
mount -t 9p

# 或者查�?/proc/mounts
cat /proc/mounts | grep 9p
```

### 步�??3: 检�?QEMU配置

在服务器上�?��?QEMU�?动命令：

```bash
# 查看QEMU进程
ps aux | grep qemu

# 查找-fsdev�?-device参数
# 应�?�看到类�?:
# -fsdev local,security_model=passthrough,id=fsdev0,path=/home/femu/io-pass-in-iouring
# -device virtio-9p-pci,id=fs0,fsdev=fsdev0,mount_tag=hostshare
```

---

## �? 解决方�??

### 方�??1: 使用正确的QEMU�?动参�?

�?保QEMU�?动时包含9p配置�?

```bash
qemu-system-x86_64 \
    -m 8G \
    -smp 4 \
    -drive file=vm.img,if=none,id=drive0,format=qcow2 \
    -device virtio-blk-pci,drive=drive0 \
    -fsdev local,security_model=passthrough,id=fsdev0,path=/home/femu/io-pass-in-iouring \
    -device virtio-9p-pci,id=fs0,fsdev=fsdev0,mount_tag=hostshare \
    -net user,hostfwd=tcp::2222-:22 \
    -net nic \
    -nographic
```

### 方�??2: 如果QEMU配置正确但仍然失�?

在虚拟机�?尝试�?

```bash
# 1. 加载9p模块
sudo modprobe 9p
sudo modprobe 9pnet_virtio

# 2. 创建挂载�?
sudo mkdir -p /mnt/share

# 3. 尝试挂载（使用不同的参数�?
sudo mount -t 9p -o trans=virtio hostshare /mnt/share/

# 或者尝试不指定version
sudo mount -t 9p hostshare /mnt/share/

# 或者尝试指定不同的version
sudo mount -t 9p -o trans=virtio,version=9p2000.u hostshare /mnt/share/
```

### 方�??3: 使用替代方法 - SCP/SFTP

如果9p不工作，�?以使用SCP复制文件�?

```bash
# 在服务器上，复制内核到虚拟机
scp -P 2222 -r /home/femu/io-pass-in-iouring/linux-5.4.144 femu@localhost:/home/femu/

# 在虚拟机�?
cd /home/femu/linux-5.4.144
sudo make INSTALL_MOD_STRIP=1 modules_install
sudo make install
sudo reboot
```

### 方�??4: 使用NFS共享

如果9p和SCP都不工作，可以使用NFS�?

**在服务器�?**:

```bash
# 1. 安�?�NFS服务�?
sudo apt-get install nfs-kernel-server

# 2. 编辑/etc/exports
sudo nano /etc/exports

# 添加以下�?:
# /home/femu/io-pass-in-iouring *(rw,sync,no_subtree_check,no_root_squash)

# 3. 重启NFS服务
sudo exportfs -a
sudo systemctl restart nfs-kernel-server
```

**在虚拟机�?**:

```bash
# 1. 安�?�NFS客户�?
sudo apt-get install nfs-common

# 2. 创建挂载�?
sudo mkdir -p /mnt/share

# 3. 挂载NFS
sudo mount -t nfs <server-ip>:/home/femu/io-pass-in-iouring /mnt/share/

# 4. 验证
mount | grep nfs
```

---

## 🔧 �?速�?�查清�?

- [ ] 9p模块已加�?: `lsmod | grep 9p`
- [ ] QEMU配置包含-fsdev�?-device参数
- [ ] 挂载点已创建: `ls -la /mnt/share`
- [ ] 尝试了不同的mount参数
- [ ] 检查了QEMU进程参数: `ps aux | grep qemu`

---

## 📝 推荐步�??

### 如果使用9p（推荐）

1. **在服务器�?**:
   - �?保QEMU�?动参数�?�确
   - 检查路径是否存�?

2. **在虚拟机�?**:
   - 加载9p模块
   - 创建挂载�?
   - 尝试挂载

### 如果9p不工�?

1. **使用SCP方法**:
   ```bash
   # 在服务器�?
   scp -P 2222 -r /home/femu/io-pass-in-iouring/linux-5.4.144 femu@localhost:/home/femu/
   ```

2. **在虚拟机�?**:
   ```bash
   cd /home/femu/linux-5.4.144
   sudo make INSTALL_MOD_STRIP=1 modules_install
   sudo make install
   sudo reboot
   ```

---

## 🆘 需要帮助？

### 检�?QEMU�?动脚�?

查看你的QEMU�?动脚�?（通常在`/home/femu/workspace/femu-src/`�?）：

```bash
# 查找�?动脚�?
find /home/femu/workspace/femu-src -name "*.sh" -type f | xargs grep -l "qemu-system"

# 查看脚本内�??
cat <script-name>
```

### 查看QEMU进程

```bash
# 在服务器上查看QEMU进程
ps aux | grep qemu | grep -v grep
```

### 查看虚拟机内核日�?

```bash
# 在虚拟机�?查看9p相关日志
dmesg | grep -i "9p\|virtio"
```

---

## 📞 常�?�错�?和解决方�?

| 错�?? | 原因 | 解决方�?? |
|------|------|--------|
| `special device hostshare does not exist` | 9p�?配置或模块未加载 | 加载9p模块或�?��?QEMU配置 |
| `mount: unknown filesystem type '9p'` | 9p模块�?加载 | `sudo modprobe 9p 9pnet_virtio` |
| `Permission denied` | 权限�?�? | 使用sudo或�?�查文件权�? |
| `Connection refused` | NFS/SCP连接失败 | 检查网络配�?和防�?�? |

---

**准�?�就�?**: �? 选择合适的方法继续
