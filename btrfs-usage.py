#!/usr/bin/env python3
"""btrfs physical-usage walker (compsize-lite).

Uses FS_IOC_FIEMAP to enumerate extents. On btrfs with compression,
multiple logical extents share one physical (compressed) extent; we dedupe
by physical offset so shared/compressed data is counted once — matching
what `df` sees. Outputs: logical bytes, physical bytes, per path.
"""
import os, sys, fcntl, struct, json

FS_IOC_FIEMAP = 0xC020660B
FIEMAP_EXTENT_LAST = 0x00000001

def fiemap(path):
    """Yield (logical_start, logical_len, physical_start, physical_len, flags)."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        return
    try:
        start = 0
        fsize = os.fstat(fd).st_size
        while True:
            # struct fiemap + room for 64 extents; bytearray for read-write ioctl
            buf = bytearray(struct.pack('QQIIII', start, fsize - start if fsize > start else 0, 0, 0, 64, 0))
            buf += b'\x00' * (64 * 56)
            try:
                fcntl.ioctl(fd, FS_IOC_FIEMAP, buf, True)
                out = bytes(buf)
            except OSError:
                break
            _, _, _, mapped, count, _ = struct.unpack('QQIIII', out[:32])
            if count == 0:
                break
            last_logical = start
            for i in range(count):
                e = out[32 + i * 56: 32 + (i + 1) * 56]
                fe_logical, fe_physical, fe_length = struct.unpack('QQQ', e[:24])
                fe_flags = struct.unpack('I', e[40:44])[0]
                yield (fe_logical, fe_length, fe_physical, fe_length, fe_flags)
                last_logical = fe_logical + fe_length
                if fe_flags & FIEMAP_EXTENT_LAST:
                    return
            if mapped < count:
                break
            start = last_logical
    finally:
        os.close(fd)

def scan(root):
    logical = 0
    phys_extents = {}  # (dev, physical_start) -> max physical_len
    files = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if not (st.st_mode & 0o100000):  # regular files only
                continue
            files += 1
            dev = st.st_dev
            for (lo, llen, po, plen, flags) in fiemap(p):
                logical += llen
                key = (dev, po)
                if plen > phys_extents.get(key, 0):
                    phys_extents[key] = plen
    physical = sum(phys_extents.values())
    return {"path": root, "files": files, "logical": logical,
            "physical": physical,
            "ratio": round(logical / physical, 2) if physical else 0}

if __name__ == '__main__':
    results = [scan(os.path.abspath(a)) for a in sys.argv[1:]]
    json.dump(results, sys.stdout, indent=1)
    sys.stdout.write('\n')
