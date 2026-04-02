#!/bin/sh

# Download and install hev-socks5-tunnel prebuilt binary for FreeBSD/x86_64.

HEV_BIN="/usr/local/bin/hev-socks5-tunnel"
HEV_REPO="heiher/hev-socks5-tunnel"

if [ -x "$HEV_BIN" ]; then
    echo "hev-socks5-tunnel already installed at $HEV_BIN"
    exit 0
fi

TAG=$(fetch -qo - "https://api.github.com/repos/${HEV_REPO}/releases/latest" \
      | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')

if [ -z "$TAG" ]; then
    echo "Error: could not determine latest release tag"
    exit 1
fi

URL="https://github.com/${HEV_REPO}/releases/download/${TAG}/hev-socks5-tunnel-freebsd-x86_64"
echo "Downloading hev-socks5-tunnel ${TAG}..."
fetch -o "$HEV_BIN" "$URL" || exit 1
chmod 0755 "$HEV_BIN"
echo "hev-socks5-tunnel installed to $HEV_BIN"
