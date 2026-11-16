#!/bin/sh
# Runs when the codespace's container starts (like the SSH service). It must return quickly, so the watcher runs
# in the background. Things started from postStartCommand are stopped by Codespaces, this is not.
nohup sh /usr/local/share/shorts-studio-keep.sh > /tmp/shorts-studio-keeper.log 2>&1 < /dev/null &
exit 0
