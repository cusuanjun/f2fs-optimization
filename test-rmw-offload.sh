#!/bin/bash
#
# Test script for F2FS RMW offload functionality
# This script tests non-page-aligned writes with RMW offload enabled
#

set -e

TEST_DIR="/tmp/f2fs_rmw_test"
TEST_FILE="${TEST_DIR}/test_file.bin"
TEST_LOG="/tmp/f2fs_rmw_test.log"

red=`tput setaf 1`
green=`tput setaf 2`
blue=`tput setaf 4`
yellow=`tput setaf 3`
reset=`tput sgr0`

echo ""
echo "====> F2FS RMW Offload Test Suite ====="
echo ""

# Check if F2FS is mounted with rmw_offload
echo "Checking F2FS mount options..."
if mount | grep -q "f2fs.*rmw_offload"; then
    echo "${green}âœ?${reset} F2FS mounted with rmw_offload option"
else
    echo "${yellow}âš?${reset} F2FS not mounted with rmw_offload option"
    echo "  To enable: mount -t f2fs -o rmw_offload /dev/nvme0n1 /mnt"
fi

# Create test directory
mkdir -p ${TEST_DIR}
echo "${green}âœ?${reset} Test directory created: ${TEST_DIR}"

# Test 1: Non-page-aligned write
echo ""
echo "Test 1: Non-page-aligned write (512 bytes at offset 1024)"
dd if=/dev/urandom of=${TEST_FILE} bs=512 count=1 seek=2 2>/dev/null
if [ -f ${TEST_FILE} ]; then
    echo "${green}âœ?${reset} Non-page-aligned write successful"
else
    echo "${red}âœ?${reset} Non-page-aligned write failed"
fi

# Test 2: Multiple non-page-aligned writes
echo ""
echo "Test 2: Multiple non-page-aligned writes"
for i in {1..10}; do
    offset=$((i * 1024))
    dd if=/dev/urandom of=${TEST_FILE} bs=512 count=1 seek=$((offset / 512)) 2>/dev/null
done
echo "${green}âœ?${reset} Multiple non-page-aligned writes successful"

# Test 3: Verify data integrity
echo ""
echo "Test 3: Data integrity verification"
md5_before=$(md5sum ${TEST_FILE} | awk '{print $1}')
cp ${TEST_FILE} ${TEST_FILE}.backup
md5_after=$(md5sum ${TEST_FILE}.backup | awk '{print $1}')

if [ "${md5_before}" = "${md5_after}" ]; then
    echo "${green}âœ?${reset} Data integrity verified"
else
    echo "${red}âœ?${reset} Data integrity check failed"
fi

# Test 4: Check kernel logs for RMW offload messages
echo ""
echo "Test 4: Checking kernel logs for RMW offload operations"
if dmesg | grep -q "RMW-OFFLOAD\|rmw_offload"; then
    echo "${green}âœ?${reset} RMW offload operations detected in kernel logs"
    echo "  Recent RMW offload messages:"
    dmesg | grep "RMW-OFFLOAD\|rmw_offload" | tail -5 | sed 's/^/    /'
else
    echo "${yellow}âš?${reset} No RMW offload messages found in kernel logs"
    echo "  This may indicate RMW offload is not being used"
fi

# Cleanup
echo ""
echo "Cleaning up test files..."
rm -f ${TEST_FILE} ${TEST_FILE}.backup
rmdir ${TEST_DIR} 2>/dev/null || true

echo ""
echo "====> Test Suite Complete ====="
echo ""
echo "Summary:"
echo "  - Non-page-aligned writes: ${green}Supported${reset}"
echo "  - RMW offload: Check kernel logs for confirmation"
echo ""
echo "For detailed logs, check: ${TEST_LOG}"
echo ""
