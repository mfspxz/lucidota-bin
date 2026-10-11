#!/usr/bin/env python3
"""Push a working tree to a GitHub repo via the Contents API.

Works on empty repos (bootstraps the first commit). Used when `git push`
stalls — git's GnuTLS TLS handshake hangs through the egress proxy while
OpenSSL-based clients work fine.
"""
import base64
import json
import os
import sys
import urllib.request
import urllib.parse

REPO = sys.argv[1]
WORKTREE = sys.argv[2]
BRANCH = sys.argv[3] if len(sys.argv) > 3 else "main"
MESSAGE = sys.argv[4] if len(sys.argv) > 4 else "initial commit"

PAT = open("/home/hatch/workspace/keys/GITHUB_PAT").read().strip()
API = f"https://api.github.com/repos/{REPO}"
SKIP_DIRS = {".git", "target", "node_modules", "__pycache__"}


def api(method, path, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        API + path,
        method=method,
        data=body,
        headers={
            "Authorization": f"Bearer {PAT}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "sitg-api-push",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r) if r.status != 204 else None


def collect(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            out.append((os.path.relpath(full, root), full))
    return out


def main():
    files = collect(WORKTREE)
    print(f"{len(files)} files -> {REPO}@{BRANCH}", flush=True)
    for rel, full in files:
        with open(full, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        path = "/contents/" + urllib.parse.quote(rel)
        try:
            # fetch sha if the file already exists (update path)
            existing = api("GET", path + f"?ref={BRANCH}")
            sha = existing["sha"]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                sha = None
            else:
                raise
        payload = {"message": f"{MESSAGE} — {rel}", "content": content, "branch": BRANCH}
        if sha:
            payload["sha"] = sha
        api("PUT", path, payload)
        print(f"  {'upd' if sha else 'new'} {rel}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
