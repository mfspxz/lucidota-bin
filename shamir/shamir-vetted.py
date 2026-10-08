#!/home/hatch/workspace/bin/shamir/venv/bin/python
"""shamir-vetted.py — Shamir secret sharing via Trezor's audited SLIP-0039.

REPLACES the hand-rolled GF(256) shard.py (deprecated 2026-10-08 repair wave:
"debugging field generators is a great intellectual exercise and a terrible
production strategy"). Crypto lives in the vetted `shamir-mnemonic` package;
this file is glue only (packing + CLI).

Same CLI contract as shard.py:
  split:   ./shamir-vetted.py split --n 3 --k 2 < secret.bin
  combine: ./shamir-vetted.py combine < shares.txt   (one mnemonic per line)

Shares are SLIP-0039 mnemonics: human-readable, QR-printable, and they carry
a checksum, so a mistyped share fails loudly instead of silently corrupting.
"""
import argparse
import struct
import sys

from shamir_mnemonic.shamir import combine_mnemonics, generate_mnemonics


def _pack(secret: bytes) -> bytes:
    # SLIP-0039 needs even-length input; prefix the true length, pad to even.
    blob = struct.pack(">I", len(secret)) + secret
    if len(blob) % 2:
        blob += b"\x00"
    return blob


def _unpack(blob: bytes) -> bytes:
    n = struct.unpack(">I", blob[:4])[0]
    out = blob[4:4 + n]
    if len(out) != n:
        raise ValueError("corrupt share set: length prefix mismatch")
    return out


def cmd_split(secret: bytes, n: int, k: int):
    if not secret:
        sys.exit("empty secret on stdin")
    groups = generate_mnemonics(1, [(k, n)], _pack(secret))
    for i, m in enumerate(groups[0], 1):
        print(f"shard {i}/{n}: {m}")
    print(f"\n{k}-of-{n}: any {k} shards reconstruct. One shard alone reveals nothing.",
          file=sys.stderr)


def cmd_combine(lines):
    import itertools
    mnemonics = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            line = line.rsplit(":", 1)[1].strip()
        words = line.split()
        if len(words) >= 10:  # SLIP-0039 shares are 20 or 33 words
            mnemonics.append(" ".join(words))
    if len(mnemonics) < 2:
        sys.exit("need at least 2 mnemonic shares on stdin")
    # SLIP-0039 wants exactly threshold-many shares; threshold is unknown
    # here, so try increasing subset sizes until one reconstructs.
    last_err = None
    for size in range(2, min(len(mnemonics), 8) + 1):
        for combo in itertools.combinations(mnemonics, size):
            try:
                sys.stdout.buffer.write(_unpack(combine_mnemonics(list(combo))))
                return
            except Exception as e:
                last_err = e
    sys.exit(f"no share subset reconstructed: {last_err}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["split", "combine"])
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--k", type=int, default=2)
    a = ap.parse_args()
    if not (2 <= a.k <= a.n <= 16):
        sys.exit("need 2 <= k <= n <= 16")
    if a.cmd == "split":
        cmd_split(sys.stdin.buffer.read().rstrip(b"\n"), a.n, a.k)
    else:
        cmd_combine(sys.stdin)


if __name__ == "__main__":
    main()
