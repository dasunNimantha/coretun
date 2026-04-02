#!/bin/sh

# xproxy uninstaller for OPNsense
# Usage: fetch -o - https://raw.githubusercontent.com/dasunNimantha/xproxy/main/uninstall.sh | sh

PREFIX="/usr/local"

echo "==> Stopping xproxy service..."
configctl xproxy stop 2>/dev/null || true

echo "==> Destroying TUN device..."
ifconfig tun9 destroy 2>/dev/null || true

echo "==> Removing plugin files..."
cd /tmp
rm -rf xproxy-main xproxy.tar.gz
if fetch -o xproxy.tar.gz "https://github.com/dasunNimantha/xproxy/archive/refs/heads/main.tar.gz" 2>/dev/null; then
    tar xzf xproxy.tar.gz 2>/dev/null
    if [ -d xproxy-main/src ]; then
        cd xproxy-main/src
        find . -type f | while read FILE; do
            rm -f "${PREFIX}/${FILE}"
        done
        cd /tmp
    fi
    rm -rf xproxy-main xproxy.tar.gz
else
    echo "Warning: could not fetch file list from GitHub, removing known paths..."
fi

echo "==> Removing binaries and configs..."
rm -f /usr/local/bin/hev-socks5-tunnel
rm -f /usr/local/bin/tun2socks
rm -rf /usr/local/etc/xproxy

echo "==> Removing PID files..."
rm -f /var/run/xproxy_xray.pid
rm -f /var/run/xproxy_hev.pid
rm -f /var/run/xproxy_tun2socks.pid
rm -f /var/run/xproxy.lock

echo "==> Removing log files..."
rm -f /var/log/xproxy.log
rm -f /var/log/xproxy.log.1

echo "==> Killing any remaining processes..."
pkill -f hev-socks5-tunnel 2>/dev/null || true
pkill -f "xray run -c /usr/local/etc/xproxy" 2>/dev/null || true

echo "==> Restarting configd..."
service configd restart

echo "==> Reloading firewall rules..."
configctl filter reload 2>/dev/null || true

echo "==> Done. xproxy has been removed."
echo "    Note: xproxy entries in config.xml are preserved."
echo "    Remove them via the OPNsense UI if desired."
