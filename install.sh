#!/bin/sh

# xproxy installer for OPNsense
# Usage: fetch -o - https://raw.githubusercontent.com/dasunNimantha/xproxy/main/install.sh | sh

set -e

REPO="dasunNimantha/xproxy"
BRANCH="main"
PREFIX="/usr/local"

if [ "$(id -u)" -ne 0 ]; then
    echo "Error: run this installer as root." >&2
    exit 1
fi

echo "==> Installing xproxy..."

# Install xray-core if missing
MISSING_PKGS=""
for PKG in xray-core; do
    if ! pkg info -e "${PKG}" >/dev/null 2>&1; then
        MISSING_PKGS="${MISSING_PKGS} ${PKG}"
    fi
done

if [ -n "${MISSING_PKGS}" ]; then
    echo "==> Installing required packages:${MISSING_PKGS}"
    pkg install -y ${MISSING_PKGS}
else
    echo "==> Required packages already installed."
fi

# Download and extract
cd /tmp
rm -rf xproxy-${BRANCH} xproxy.tar.gz
fetch -o xproxy.tar.gz "https://github.com/${REPO}/archive/refs/heads/${BRANCH}.tar.gz" || {
    echo "Error: failed to download xproxy source" >&2
    exit 1
}
tar xzf xproxy.tar.gz
cd xproxy-${BRANCH}/src

# Install files
find . -type f | while read FILE; do
    DIR=$(dirname "${PREFIX}/${FILE}")
    mkdir -p "${DIR}"
    cp "${FILE}" "${PREFIX}/${FILE}"
done

# Set executable permissions
chmod +x "${PREFIX}/opnsense/scripts/xproxy/"*.py \
         "${PREFIX}/opnsense/scripts/xproxy/"*.sh \
         "${PREFIX}/opnsense/scripts/xproxy/"*.php 2>/dev/null || true

echo "==> Installing hev-socks5-tunnel..."
"${PREFIX}/opnsense/scripts/xproxy/setup.sh"

# Clean up legacy PID files from tun2socks era
rm -f /var/run/xproxy_tun2socks.pid 2>/dev/null || true
rm -f /usr/local/bin/tun2socks 2>/dev/null || true

cd /tmp
rm -rf xproxy-${BRANCH} xproxy.tar.gz

echo "==> Restarting configd..."
service configd restart

echo "==> Done. Navigate to VPN > Xproxy in the OPNsense web UI."
