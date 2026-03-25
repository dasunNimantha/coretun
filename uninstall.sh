#!/bin/sh

# os-xproxy uninstaller for OPNsense
# Usage: fetch -o - https://raw.githubusercontent.com/dasunNimantha/os-xproxy/main/uninstall.sh | sh

set -e

PREFIX="/usr/local"

echo "==> Stopping xproxy service..."
configctl xproxy stop 2>/dev/null || true

echo "==> Removing plugin files..."

cd /tmp
fetch -o os-xproxy.tar.gz "https://github.com/dasunNimantha/os-xproxy/archive/refs/heads/main.tar.gz"
tar xzf os-xproxy.tar.gz
cd os-xproxy-main/src

find . -type f | while read FILE; do
    rm -f "${PREFIX}/${FILE}"
done

cd /tmp
rm -rf os-xproxy-main os-xproxy.tar.gz

echo "==> Restarting configd..."
service configd restart

echo "==> Reloading firewall rules..."
configctl filter reload

echo "==> Done. os-xproxy has been removed."
