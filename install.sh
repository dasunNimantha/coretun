#!/bin/sh

# coretun installer for OPNsense
# Usage: fetch -o - https://raw.githubusercontent.com/dasunNimantha/coretun/main/install.sh | sh

set -e

REPO="dasunNimantha/coretun"
BRANCH="main"
PREFIX="/usr/local"

if [ "$(id -u)" -ne 0 ]; then
    echo "Error: run this installer as root." >&2
    exit 1
fi

echo "==> Installing coretun..."

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
rm -rf coretun-${BRANCH} coretun.tar.gz
fetch -o coretun.tar.gz "https://github.com/${REPO}/archive/refs/heads/${BRANCH}.tar.gz" || {
    echo "Error: failed to download coretun source" >&2
    exit 1
}
tar xzf coretun.tar.gz
cd coretun-${BRANCH}/src

# Install files
find . -type f | while read FILE; do
    DIR=$(dirname "${PREFIX}/${FILE}")
    mkdir -p "${DIR}"
    cp "${FILE}" "${PREFIX}/${FILE}"
done

# Set executable permissions
chmod +x "${PREFIX}/opnsense/scripts/coretun/"*.py \
         "${PREFIX}/opnsense/scripts/coretun/"*.sh \
         "${PREFIX}/opnsense/scripts/coretun/"*.php 2>/dev/null || true

echo "==> Installing hev-socks5-tunnel..."
"${PREFIX}/opnsense/scripts/coretun/setup.sh"

if [ -x "${PREFIX}/bin/php" ] && [ -f "${PREFIX}/opnsense/scripts/coretun/migrate_from_xproxy.php" ]; then
    echo "==> Migrating legacy xproxy config (if any)..."
    "${PREFIX}/bin/php" "${PREFIX}/opnsense/scripts/coretun/migrate_from_xproxy.php" || true
fi

# Clean up legacy PID files from tun2socks era
rm -f /var/run/coretun_tun2socks.pid 2>/dev/null || true
rm -f /usr/local/bin/tun2socks 2>/dev/null || true

cd /tmp
rm -rf coretun-${BRANCH} coretun.tar.gz

echo "==> Restarting configd..."
service configd restart

echo "==> Done. Navigate to VPN > Coretun in the OPNsense web UI."
