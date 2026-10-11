#!/usr/bin/env python3
"""Classify a tree's bytes into incompressible vs compressible classes.
Incompressible: archives, media, model weights, binaries, git objects.
Everything else counts as compressible (zstd:3 eats it ~2.5-4x).
JSON lines per input root."""
import os, sys, json

INCOMP_EXT = {'.zip', '.gz', '.tgz', '.zst', '.bz2', '.xz', '.7z', '.rar',
              '.mp4', '.mkv', '.webm', '.mp3', '.ogg', '.wav', '.flac',
              '.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif',
              '.safetensors', '.onnx', '.pt', '.pth', '.gguf', '.bin',
              '.whl', '.so', '.dylib', '.o', '.rlib', '.rmeta',
              '.pdf', '.idx', '.pack', '.sqlite-wal'}
INCOMP_NAME = {'HEAD'}  # skip
INCOMP_DIR_FRAG = {'/objects/pack/', '/.git/objects/'}

def classify(root):
    inc = comp = 0
    n_inc = n_comp = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # skip nested target dirs? no — count everything, classify honestly
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if not (st.st_mode & 0o100000):
                continue
            sz = st.st_size
            ext = os.path.splitext(fn)[1].lower()
            if ext in INCOMP_EXT or any(f in p for f in INCOMP_DIR_FRAG):
                inc += sz; n_inc += 1
            else:
                comp += sz; n_comp += 1
    return {'path': root, 'incomp_gb': round(inc / 2**30, 2),
            'comp_gb': round(comp / 2**30, 2),
            'incomp_files': n_inc, 'comp_files': n_comp}

if __name__ == '__main__':
    for a in sys.argv[1:]:
        try:
            print(json.dumps(classify(os.path.abspath(a))), flush=True)
        except Exception as e:
            print(json.dumps({'path': a, 'error': str(e)[:100]}), flush=True)
