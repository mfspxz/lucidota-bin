#!/usr/bin/env bash
# git-mirror-setup.sh — dual-push mirroring: one `git push` lands on GitHub AND GitLab.
#
# Usage: GITLAB_TOKEN=<token> git-mirror-setup.sh <repo-dir> [--dry-run]
#        GITLAB_TOKEN=<token> git-mirror-setup.sh --fleet [--dry-run]
#
# Maps github.com/mfspxz/REPO -> gitlab.com/mfspx/REPO (his namespaces differ).
# Creates the GitLab repo via API if missing. Adds the GitLab URL as a second
# push URL on `origin`. Verifies with `git ls-remote`.
# Token via env only — never in argv, never on disk.
set -u
GH_NS="mfspxz"
GL_NS="mfspx"
DRY=""

usage() { echo "usage: GITLAB_TOKEN=<t> $0 <repo-dir>|--fleet [--dry-run]" >&2; exit 1; }

if [ "${1:-}" = "--fleet" ]; then
  MODE=fleet; shift
else
  MODE=single; REPO_DIR="${1:-}"; shift || true
fi
[ "${1:-}" = "--dry-run" ] && DRY=1

[ -z "${GITLAB_TOKEN:-}" ] && { echo "GITLAB_TOKEN not set" >&2; exit 1; }

gl_api() { # method path [data]
  curl -s -w "\n%{http_code}" -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
    -H "Content-Type: application/json" \
    ${3:+-d "$3"} -X "$1" "https://gitlab.com/api/v4$2"
}

setup_one() {
  local dir="$1"
  [ -d "$dir/.git" ] || { echo "SKIP $dir: not a repo"; return; }
  local gh_url; gh_url=$(git -C "$dir" remote get-url origin 2>/dev/null) || { echo "SKIP $dir: no origin"; return; }
  case "$gh_url" in
    *github.com*"$GH_NS"* ) ;;
    *) echo "SKIP $dir: origin is not $GH_NS github ($gh_url)"; return ;;
  esac
  local repo; repo=$(basename "$gh_url" .git)
  local gl_url="https://gitlab.com/$GL_NS/$repo.git"

  # ensure the GitLab project exists
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
    "https://gitlab.com/api/v4/projects/$(printf '%s' "$GL_NS/$repo" | sed 's|/|%2F|g')")
  if [ "$code" = "404" ]; then
    if [ -n "$DRY" ]; then
      echo "DRY $dir: would create gitlab $GL_NS/$repo"
    else
      local out; out=$(gl_api POST "/projects" "{\"name\":\"$repo\",\"visibility\":\"private\",\"description\":\"Mirror of github.com/$GH_NS/$repo — dual-push\"}")
      echo "$out" | grep -q '"id"' || { echo "FAIL $dir: create -> $(echo "$out" | tail -1)"; return; }
      echo "CREATED gitlab $GL_NS/$repo"
    fi
  elif [ "$code" != "200" ]; then
    echo "FAIL $dir: gitlab api -> $code"; return
  fi

  if git -C "$dir" remote get-url --push origin 2>/dev/null | grep -q "gitlab.com"; then
    echo "HAVE $dir: gitlab push url already set"
  else
    if [ -n "$DRY" ]; then
      echo "DRY $dir: would add push url $gl_url"
    else
      git -C "$dir" remote set-url --add --push origin "$gl_url"
      echo "MIRROR $dir -> $gl_url"
    fi
  fi
}

if [ "$MODE" = "fleet" ]; then
  while IFS= read -r d; do setup_one "$d"; done < /tmp/git-repos.txt
else
  [ -z "${REPO_DIR:-}" ] && usage
  setup_one "$REPO_DIR"
fi
