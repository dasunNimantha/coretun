#!/bin/sh

# coretun uninstaller for OPNsense
# Usage: fetch -o - https://raw.githubusercontent.com/dasunNimantha/coretun/main/uninstall.sh | sh

PREFIX="/usr/local"

echo "==> Stopping coretun service..."
configctl coretun stop 2>/dev/null || true

echo "==> Destroying TUN device..."
ifconfig tun9 destroy 2>/dev/null || true

echo "==> Removing plugin files..."
cd /tmp
rm -rf coretun-main coretun.tar.gz
if fetch -o coretun.tar.gz "https://github.com/dasunNimantha/coretun/archive/refs/heads/main.tar.gz" 2>/dev/null; then
    tar xzf coretun.tar.gz 2>/dev/null
    if [ -d coretun-main/src ]; then
        cd coretun-main/src
        find . -type f | while read FILE; do
            rm -f "${PREFIX}/${FILE}"
        done
        cd /tmp
    fi
    rm -rf coretun-main coretun.tar.gz
else
    echo "Warning: could not fetch file list from GitHub, removing known paths..."
fi

echo "==> Removing binaries and configs..."
rm -f /usr/local/bin/hev-socks5-tunnel
rm -f /usr/local/bin/tun2socks
rm -rf /usr/local/etc/coretun

echo "==> Removing PID files..."
rm -f /var/run/coretun_xray.pid
rm -f /var/run/coretun_hev.pid
rm -f /var/run/coretun_exporter.pid
rm -f /var/run/coretun_service.active
rm -f /var/run/coretun_tun2socks.pid
rm -f /var/run/coretun.lock

echo "==> Removing log files..."
rm -f /var/log/coretun.log
rm -f /var/log/coretun.log.1

echo "==> Killing any remaining processes..."
pkill -f hev-socks5-tunnel 2>/dev/null || true
pkill -f "xray run -c /usr/local/etc/coretun" 2>/dev/null || true

echo "==> Restarting configd..."
service configd restart

echo "==> Reloading firewall rules..."
configctl filter reload 2>/dev/null || true

echo "==> Done. coretun has been removed."
echo "    Note: coretun entries in config.xml are preserved."
echo "    Remove them via the OPNsense UI if desired."
