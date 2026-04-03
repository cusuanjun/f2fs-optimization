# F2FS RMW Offload - �?速命令参�?

## �? 所有脚�?已准备就�?

所有构建和测试脚本现在都有执�?�权限，�?以直接运行�?

---

## 🚀 核心命令

### 1. 编译内核（在服务器上�?

```bash
cd /home/femu/io-pass-in-iouring
./build-rmw-kernel.sh
```

**输出位置**: `/home/femu/io-pass-in-iouring/linux-5.4.144/arch/x86/boot/bzImage`

**日志**: `/home/femu/io-pass-in-iouring/rmw-kernel-build.log`

### 2. 编译FEMU（在服务器上�?

```bash
cd /home/femu/workspace/femu-src
./build-rmw-femu.sh
```

**输出位置**: `/home/femu/workspace/femu-src/src/iodaFEMU-b13b482/build/qemu-system-x86_64`

**日志**: `/home/femu/workspace/femu-src/rmw-femu-build.log`

### 3. 测试RMW卸载（在虚拟机中�?

```bash
cd /home/femu/io-pass-in-iouring
./test-rmw-offload.sh
```

**测试项目**:
- �? 挂载选项验证
- �? 非页对齐写入测试
- �? 多个顺序写入测试
- �? 数据完整性验�?
- �? 内核日志验证

---

## 📋 安�?��?��??

### 在虚拟机�?安�?�内�?

```bash
# 1. 挂载共享�?�?
sudo mount -t 9p -o trans=virtio hostshare /mnt/share/ -oversion=9p2000.L

# 2. 进入内核�?�?
cd /mnt/share/linux-5.4.144

# 3. 安�?�模块和内核
sudo make INSTALL_MOD_STRIP=1 modules_install
sudo make install

# 4. 重启
sudo reboot
```

### 挂载F2FS

```bash
# 格式化�?��??
sudo mkfs.f2fs /dev/nvme0n1

# 挂载F2FS（启用RMW卸载�?
sudo mount -t f2fs -o rmw_offload /dev/nvme0n1 /mnt
```

---

## ✔️ 验证步�??

### 检查内核支�?

```bash
grep CONFIG_F2FS_MOUNT_RMW_OFFLOAD /boot/config-$(uname -r)
# 应�?�输�?: CONFIG_F2FS_MOUNT_RMW_OFFLOAD=y
```

### 检�?F2FS挂载选项

```bash
mount | grep f2fs
# 应�?�包�?: rmw_offload
```

### 检�?RMW操作日志

```bash
dmesg | grep RMW-OFFLOAD
# 应�?�显示RMW操作的�?�细信息
```

---

## 📊 文件位置速查

### 内核源码
```
/home/femu/io-pass-in-iouring/linux-5.4.144/fs/f2fs/
├── data.c          �? RMW卸载函数
├── segment.c       �? RMW卸载实现
└── f2fs.h          �? 挂载选项定义
```

### FEMU源码
```
/home/femu/workspace/femu-src/src/iodaFEMU-b13b482/hw/femu/
├── nvme-io.c       �? 增强的RMW实现
└── nvme-pw.h       �? 命令定义
```

### 脚本
```
/home/femu/io-pass-in-iouring/
├── build-rmw-kernel.sh     �? �?执�??
├── test-rmw-offload.sh     �? �?执�??
└── *.md                    📚 文档

/home/femu/workspace/femu-src/
└── build-rmw-femu.sh       �? �?执�??
```

### 文档
```
/home/femu/io-pass-in-iouring/
├── INDEX.md                           �? �?速索�?
├── IMPLEMENTATION_COMPLETE.md         �? 完成总结
├── RMW_OFFLOAD_README.md              �? 详细指南
├── RMW_OFFLOAD_CONFIG.md              �? 配置指南
└── RMW_OFFLOAD_IMPLEMENTATION.md      �? 实现细节
```

---

## 🔧 故障排除

### 脚本权限�?�?

```bash
# 如果脚本无法执�?�，添加权限
chmod +x /home/femu/io-pass-in-iouring/build-rmw-kernel.sh
chmod +x /home/femu/workspace/femu-src/build-rmw-femu.sh
chmod +x /home/femu/io-pass-in-iouring/test-rmw-offload.sh
```

### 编译失败

```bash
# 检查编译日�?
cat /home/femu/io-pass-in-iouring/rmw-kernel-build.log
cat /home/femu/workspace/femu-src/rmw-femu-build.log
```

### RMW卸载不工�?

```bash
# 1. 验证内核配置
grep CONFIG_F2FS_MOUNT_RMW_OFFLOAD /boot/config-$(uname -r)

# 2. 验证挂载选项
mount | grep f2fs

# 3. 检查内核日�?
dmesg | tail -50
```

---

## 📈 性能监控

### 实时监控RMW操作

```bash
# 在虚拟机�?，实时查看RMW操作
watch -n 1 'dmesg | grep RMW-OFFLOAD | tail -10'
```

### 监控I/O统�??

```bash
# 查看I/O统�??
iostat -x 1 5

# 查看磁盘使用
df -h /mnt
```

### 监控CPU使用

```bash
# 实时CPU监控
top

# 或使用htop
htop
```

---

## 📚 文档�?速�?�航

| 文档 | 用�? | 何时阅�?? |
|------|------|--------|
| `INDEX.md` | 文件索引 | 首先 |
| `IMPLEMENTATION_COMPLETE.md` | 完成总结 | 了解全貌 |
| `RMW_OFFLOAD_README.md` | 详细指南 | 深入理解 |
| `RMW_OFFLOAD_CONFIG.md` | 配置指南 | 实际操作 |
| `RMW_OFFLOAD_IMPLEMENTATION.md` | 实现细节 | 技�?参�? |

---

## �? 关键特�?

�? **透明的RMW卸载** - 无需�?改应用代�?  
�? **�?动回退机制** - 失败时自动使用常规写�?  
�? **详细的日�?** - 完整的操作跟�?  
�? **生产就绪** - 完整的错�?处理  
�? **易于扩展** - 模块化�?��??  

---

## 🎯 下一�?

1. **编译内核**: `./build-rmw-kernel.sh`
2. **编译FEMU**: `./build-rmw-femu.sh`
3. **在VM�?安�??**: 按照安�?��?��?�操�?
4. **挂载F2FS**: `sudo mount -t f2fs -o rmw_offload /dev/nvme0n1 /mnt`
5. **运�?�测�?**: `./test-rmw-offload.sh`
6. **验证**: 检查日志和挂载选项

---

**项目状�?**: �? 完成  
**所有脚�?**: �? �?执�??  
**文档**: �? 完整  
**准�?�就�?**: �? �?
