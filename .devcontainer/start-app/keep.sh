#!/bin/sh
# Every 10 seconds: if nothing answers on port 8000, start Shorts Studio (once the code and its Python packages
# are there: on a new codespace they are still being installed for a few minutes).
as_user() {                       # run a command as the codespace user (this watcher usually runs as root)
  if [ "$(id -u)" = "0" ]; then su vscode -s /bin/sh -c "$1"; else sh -c "$1"; fi
}
while true; do
  sleep 10
  curl -s -o /dev/null --max-time 5 http://127.0.0.1:8000/ && continue
  W=""
  for d in /workspaces/*/; do
    [ -f "${d}run.py" ] && [ -d "${d}studio" ] && W="$d"
  done
  [ -n "$W" ] || continue
  as_user "python -c 'import PIL, edge_tts'" > /dev/null 2>&1 || continue
  echo "$(date) starting Shorts Studio in $W"
  # the log is written by the codespace user (root may not write a user's file in /tmp)
  as_user "sh /usr/local/share/shorts-studio-run.sh '$W' >> /tmp/shorts-studio.log 2>&1" &
  sleep 20
done
