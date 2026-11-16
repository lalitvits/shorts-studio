#!/bin/sh
# Installs the helper that keeps Shorts Studio running in a codespace.
set -e
cd "$(dirname "$0")"
install -m 755 start.sh /usr/local/share/shorts-studio-start.sh
install -m 755 keep.sh /usr/local/share/shorts-studio-keep.sh
install -m 755 run.sh /usr/local/share/shorts-studio-run.sh
