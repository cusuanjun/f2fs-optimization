#!/bin/bash
#
# Build script for F2FS with RMW offload support
# This script compiles the modified Linux kernel with RMW offload enabled
#

set -e

KERNEL_DIR="/home/femu/io-pass-in-iouring/linux-5.4.144"
BUILD_LOG="/home/femu/io-pass-in-iouring/rmw-kernel-build.log"

red=`tput setaf 1`
green=`tput setaf 2`
blue=`tput setaf 4`
reset=`tput sgr0`

echo ""
echo "====> Building Linux kernel with F2FS RMW offload support ..."
echo ""

cd ${KERNEL_DIR}

# Clean previous build
echo "Cleaning previous build..."
make clean >/dev/null 2>&1 || true

# Copy config
if [ -f "ioda-config" ]; then
    cp ioda-config .config
    echo "Using ioda-config"
elif [ -f ".config" ]; then
    echo "Using existing .config"
else
    echo "${red}ERROR:${reset} No kernel config found"
    exit 1
fi

# Enable RMW_OFFLOAD option in config
echo "Enabling F2FS_MOUNT_RMW_OFFLOAD in kernel config..."
if grep -q "CONFIG_F2FS_MOUNT_RMW_OFFLOAD" .config; then
    sed -i 's/# CONFIG_F2FS_MOUNT_RMW_OFFLOAD.*/CONFIG_F2FS_MOUNT_RMW_OFFLOAD=y/' .config
else
    echo "CONFIG_F2FS_MOUNT_RMW_OFFLOAD=y" >> .config
fi

# Build kernel
echo "Building kernel (this may take a while)..."
make -j$(nproc) >${BUILD_LOG} 2>&1

KERNEL_BIN="${KERNEL_DIR}/arch/x86/boot/bzImage"

if [ -e ${KERNEL_BIN} ]; then
    echo ""
    echo "===> ${green}Success!${reset} Kernel with RMW offload support built successfully!"
    echo ""
    echo "Compiled kernel binary:"
    echo "  - ${blue}${KERNEL_BIN}${reset}"
    echo ""
    echo "To install in the VM:"
    echo "  1. Mount the kernel directory in the VM"
    echo "  2. Run: sudo make INSTALL_MOD_STRIP=1 modules_install && sudo make install"
    echo "  3. Reboot the VM"
    echo ""
else
    echo ""
    echo "===> ${red}ERROR:${reset} Failed to build kernel, please check [${BUILD_LOG}]."
    echo ""
    exit 1
fi
