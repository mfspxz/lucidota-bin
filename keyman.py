#!/usr/bin/env python3
"""keyman.py — tiny key manager that actually works with this stack.

Keys live in ~/workspace/keys/<NAME> (0600). No vault dance, no stale
surrogates: the file is the source of truth, and `sync`/`rotate` push to
Cloudflare worker secrets automatically. Vercel env vars are the one thing
the current OAuth scope can't touch — keyman prints the exact dashboard step.

Usage:
  keyman.py auth                  # store CF API token + account id (paste once)
  keyman.py set NAME [value]      # store a key (value via arg or stdin)
  keyman.py get NAME              # print a key (for scripts)
  keyman.py list                  # names only, never values
  keyman.py sync NAME             # push local value -> Cloudflare worker secret
  keyman.py rotate NAME           # mint fresh -> CF + local (prints Vercel step)

Destinations (NAME -> worker secret):
  ROUTER_KEY -> ai-router / ROUTER_KEY
  NVIDIA_KEY -> ai-router / NVIDIA_KEY
"""
import json
import os
import secrets
import stat
import sys
import urllib.request
import urllib.error

KEYS_DIR = os.path.expanduser("~/workspace/keys")
AUTH_FILE = os.path.join(KEYS_DIR, ".cf_auth.json")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

DESTS = {
    "ROUTER_KEY": ("ai-router", "ROUTER_KEY"),
    "NVIDIA_KEY": ("ai-router", "NVIDIA_KEY"),
    "NVIDIA_MODEL": ("ai-router", "NVIDIA_MODEL"),
    "GEMINI_KEY": ("ai-router", "GEMINI_KEY"),
}


def _ensure_dir():
    os.makedirs(KEYS_DIR, mode=0o700, exist_ok=True)


def _key_path(name):
    if not name.replace("_", "").isalnum() or len(name) > 64:
        raise ValueError("bad key name")
    return os.path.join(KEYS_DIR, name)


def cmd_set(name, value=None):
    _ensure_dir()
    if value is None:
        value = sys.stdin.read().strip()
    else:
        value = value.strip()
    if not value:
        print("empty value, refusing", file=sys.stderr)
        return 1
    p = _key_path(name)
    with open(p, "w") as f:
        f.write(value + "\n")
    os.chmod(p, 0o600)
    print(f"stored {name} ({len(value)} chars)")
    return 0


def cmd_get(name):
    p = _key_path(name)
    try:
        with open(p) as f:
            sys.stdout.write(f.read().strip())
    except OSError:
        print(f"no such key: {name}", file=sys.stderr)
        return 1
    return 0


def cmd_list():
    _ensure_dir()
    for fn in sorted(os.listdir(KEYS_DIR)):
        if fn.startswith("."):
            continue
        print(fn)
    return 0


def _cf_auth():
    try:
        with open(AUTH_FILE) as f:
            a = json.load(f)
        return a["token"], a["account_id"]
    except (OSError, KeyError, ValueError):
        return None, None


def cmd_auth():
    _ensure_dir()
    print("Paste Cloudflare API token (cfut_...), then account ID. Ctrl-D when done with each.")
    sys.stdout.write("token: ")
    sys.stdout.flush()
    token = sys.stdin.readline().strip()
    sys.stdout.write("account_id: ")
    sys.stdout.flush()
    account_id = sys.stdin.readline().strip()
    if not token or not account_id:
        print("both required", file=sys.stderr)
        return 1
    with open(AUTH_FILE, "w") as f:
        json.dump({"token": token, "account_id": account_id}, f)
    os.chmod(AUTH_FILE, 0o600)
    print("CF auth stored")
    return 0


def _cf_set_secret(token, account_id, script, name, value):
    body = json.dumps({"name": name, "text": value, "type": "secret_text"}).encode()
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts/{script}/secrets",
        data=body, method="PUT",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json", "User-Agent": UA})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=30).read())
        return bool(d.get("success"))
    except urllib.error.HTTPError as e:
        print(f"CF HTTP {e.code}: {e.read()[:160]}", file=sys.stderr)
        return False


def cmd_sync(name):
    if name not in DESTS:
        print(f"no destination mapped for {name}", file=sys.stderr)
        return 1
    token, account_id = _cf_auth()
    if not token:
        print("run `keyman.py auth` first", file=sys.stderr)
        return 1
    try:
        with open(_key_path(name)) as f:
            value = f.read().strip()
    except OSError:
        print(f"no local key: {name}", file=sys.stderr)
        return 1
    script, secret = DESTS[name]
    ok = _cf_set_secret(token, account_id, script, secret, value)
    print(f"CF {script}/{secret}: {'OK' if ok else 'FAILED'}")
    if name == "ROUTER_KEY":
        print("NOTE: Vercel env ROUTER_KEY still needs a dashboard update "
              "(Vercel dashboard > indy-reads-ui > Settings > Environment Variables), then redeploy.")
    return 0 if ok else 1


def cmd_rotate(name):
    if name not in DESTS:
        print(f"no destination mapped for {name}", file=sys.stderr)
        return 1
    prefix = {"ROUTER_KEY": "rk_", "NVIDIA_KEY": "nvapi-"}.get(name, "k_")
    value = prefix + secrets.token_urlsafe(32)
    if cmd_set(name, value) != 0:
        return 1
    return cmd_sync(name)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "auth":
        return cmd_auth()
    if cmd == "set" and args:
        return cmd_set(args[0], args[1] if len(args) > 1 else None)
    if cmd == "get" and args:
        return cmd_get(args[0])
    if cmd == "list":
        return cmd_list()
    if cmd == "sync" and args:
        return cmd_sync(args[0])
    if cmd == "rotate" and args:
        return cmd_rotate(args[0])
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
