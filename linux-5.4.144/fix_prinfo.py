#!/usr/bin/env python3
INFILE = '/home/femu/io-pass-in-iouring/linux-5.4.144/fs/f2fs/data.c'
with open(INFILE, 'r', errors='replace') as f:
    lines = f.readlines()

fixed = []
i = 0
while i < len(lines):
    line = lines[i]
    # Check if this line has an unterminated string (pr_info/pr_err with newline before closing quote)
    stripped = line.rstrip('\n')
    if ('pr_info(' in stripped or 'pr_err(' in stripped) and stripped.count('"') % 2 == 1:
        # Join with next line(s) until quotes balance
        combined = stripped
        i += 1
        while i < len(lines) and combined.count('"') % 2 == 1:
            combined = combined + ' ' + lines[i].strip()
            i += 1
        # Now combined should be the full statement
        # But we need \n inside the format string, not a real newline
        # The issue is the format string has a real newline instead of \n
        # Find the broken part: between last format char and closing "
        # Simple fix: if pattern is 'msg\n' split across lines, rejoin
        fixed.append(combined + '\n')
    else:
        fixed.append(line)
        i += 1

with open(INFILE, 'w') as f:
    f.writelines(fixed)
print('Done, lines:', len(fixed))
