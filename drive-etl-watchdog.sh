#!/bin/bash
# drive-etl-watchdog.sh — keep the deterministic Drive ETL pipelines alive.
# Pipelines are resume-safe/idempotent; this only starts what's missing.
# Called by cron every 15 min. Never touches Drive data, only (re)starts scripts.
LOG="$HOME/workspace/drive-map/watchdog.log"
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# 1. zip-scan supervisor (supervise.sh) — done when ZIPSCAN-REPORT marked complete; check scan first
if ! pgrep -f "bash supervise.sh" >/dev/null; then
  if grep -q "SUPERVISOR COMPLETE" "$HOME/workspace/drive-zipscan/supervisor.log" 2>/dev/null \
     && [ -s "$HOME/workspace/drive-zipscan/zip-contents.jsonl" ]; then
    echo "[$(ts)] supervisor: already complete, not restarting" >> "$LOG"
  else
    cd "$HOME/workspace/drive-zipscan" && rm -f scratch/*.zip
    bash supervise.sh >> supervisor.log 2>&1 &
    echo "[$(ts)] supervisor: restarted pid=$!" >> "$LOG"
  fi
fi

# 2. chat-zip cracker — done when results show 0 remaining
if ! pgrep -f "crack_chat28.py" >/dev/null; then
  remaining=$(python3 -c "
import json
try:
    r = json.load(open('$HOME/workspace/drive-zipscan/chat28-resume.json'))
    done = {d['name'] for d in json.load(open('$HOME/workspace/drive-zipscan/chat28-results.json')).get('done', [])}
    print(len([z for z in r if z['name'] not in done]))
except Exception:
    print(1)" 2>/dev/null)
  if [ "${remaining:-1}" = "0" ]; then
    echo "[$(ts)] crack_chat28: all done, not restarting" >> "$LOG"
  else
    cd "$HOME/workspace/drive-zipscan" && python3 crack_chat28.py >> crack_chat28.log 2>&1 &
    echo "[$(ts)] crack_chat28: restarted pid=$! remaining=$remaining" >> "$LOG"
  fi
fi

# 3. phase-2 driver (moves + quarantine) — done when DRIVER COMPLETE in log
if ! pgrep -f "drive-map/driver.py" >/dev/null; then
  if grep -q "DRIVER COMPLETE" "$HOME/workspace/drive-map/driver.log" 2>/dev/null; then
    echo "[$(ts)] driver: already complete, not restarting" >> "$LOG"
  else
    cd "$HOME/workspace/drive-map" && python3 driver.py >> driver.log 2>&1 &
    echo "[$(ts)] driver: restarted pid=$!" >> "$LOG"
  fi
fi
