#!/usr/bin/env bash
# resource-governor.sh — RAM + disk guard for the 7.7GB / 100GB VM.
# Runs as an eventd interval watch (60s). Deterministic, no agent judgment.
#
# RAM:  available < 600MB  -> SIGTERM the largest killable hog, SIGKILL after 3s
#       available < 1200MB -> warn only (exit 2, no kill)
# DISK: /home use > 90%    -> warn only, report top consumers (NEVER auto-delete)
# Exit 0 = all clear (silent). Exit 2 = event fired to outbox.
set -euo pipefail

RAM_CRIT_KB=614400    # 600MB — OOM is NEVER acceptable (Zack 2026-10-11)
RAM_WARN_KB=2097152   # 2GB — warn early
DISK_WARN_PCT=70      # Zack's order 2026-10-11: alert at 70%, not 90%

avail_kb=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
disk_pct=$(df -P "$HOME" | awk 'NR==2 {gsub(/%/,"",$5); print $5}')

fired=0
notes=()

ledger_log() {
  # best-effort ledger entry; never fail the guard on logging
  python3 -c "
import sys, json, hashlib, datetime
sys.path.insert(0, '$HOME/ledger')
import ledger
body = '''$2'''
entry = {
  'id': 'gov-' + hashlib.sha256(body.encode()).hexdigest()[:16],
  'ts': datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'actor': 'lucidota/resource-governor', 'chat': 'main', 'type': 'action',
  'summary': '''$1''', 'body': body, 'access': 'private', 'verdict': 'proven',
  'refs': ['sha256:' + hashlib.sha256(body.encode()).hexdigest()],
}
ledger.cmd_write(entry)
" 2>/dev/null || true
}

# --- RAM ---
if [ "$avail_kb" -lt "$RAM_CRIT_KB" ]; then
  # find largest killable process: skip PID 1, self, and protected daemons
  victim=$(ps -eo pid,rss,comm,args --sort=-rss | awk '
    NR>1 && $1 != 1 {
      cmd=$0
      if (cmd ~ /resource-governor/) next
      if (cmd ~ /eventd --daemon/) next
      if (cmd ~ /redis-server/) next
      if (cmd ~ /hatch daemon/) next
      if (cmd ~ /sshd/) next
      if (cmd ~ /systemd/) next
      print $1; exit
    }')
  if [ -n "${victim:-}" ]; then
    vinfo=$(ps -o comm=,args= -p "$victim" 2>/dev/null | cut -c1-120 || echo "?")
    kill -TERM "$victim" 2>/dev/null || true
    sleep 3
    if kill -0 "$victim" 2>/dev/null; then
      kill -KILL "$victim" 2>/dev/null || true
      how="SIGKILL"
    else
      how="SIGTERM"
    fi
    notes+=("RAM critical (${avail_kb}kB avail): killed pid $victim ($how): $vinfo")
    ledger_log "resource-governor: OOM guard killed pid $victim" \
      "available=${avail_kb}kB < ${RAM_CRIT_KB}kB; method=$how; proc=$vinfo"
    fired=1
  else
    notes+=("RAM critical (${avail_kb}kB avail) but no killable victim found")
    fired=1
  fi
elif [ "$avail_kb" -lt "$RAM_WARN_KB" ]; then
  top3=$(ps -eo rss,comm --sort=-rss | awk 'NR>1 && NR<=4 {printf "%s:%dMB ", $2, $1/1024}')
  notes+=("RAM warning: ${avail_kb}kB available; top: $top3")
  fired=1
fi

# --- DISK (warn only, never auto-delete) ---
# NOTE: du on ~/workspace can take minutes (many small files); bound it hard.
if [ "$disk_pct" -ge "$DISK_WARN_PCT" ]; then
  # NOTE: du on ~/workspace can exceed the 20s bound (btrfs, many small files).
  # `timeout` exits 124 on expiry — swallow it (`|| :`), because with
  # set -e + pipefail an expiry would otherwise exit the whole script 124
  # (eventd watch.error). Partial du output is still useful for the note.
  topd=$(timeout 20 du -x -d1 "$HOME/workspace" 2>/dev/null | sort -rn | head -5 | awk '{printf "%s:%.1fGB ", $2, $1/1048576}' | cut -c1-300 || :)
  [ -z "$topd" ] && topd="(breakdown timed out)"
  notes+=("DISK warning: /home at ${disk_pct}%; largest: $topd")
  ledger_log "resource-governor: disk warning" "/home at ${disk_pct}% (>= ${DISK_WARN_PCT}%); largest: $topd"
  fired=1
fi

if [ "$fired" -eq 1 ]; then
  printf '%s\n' "${notes[@]}"
  exit 2
fi
exit 0
