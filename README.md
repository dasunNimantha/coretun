# xproxy

OPNsense plugin for Xray-core with transparent LAN routing.

When enabled, all LAN traffic is routed through a VLESS, VMess, Shadowsocks, or Trojan tunnel — no configuration needed on individual devices.

## Features

- Transparent proxying via TUN interface (hev-socks5-tunnel) — phones, IoT, smart TVs, and guest devices are covered automatically
- VLESS (with XTLS-Vision / Reality), VMess, Shadowsocks, and Trojan protocols
- Import server profiles from standard proxy URIs (`vless://`, `vmess://`, `ss://`, `trojan://`)
- Policy-based routing with dynamic firewall rules — rules are only active while the service is running
- Multiple server profiles with quick switching and auto-select on add/import/delete
- Hardened process lifecycle — file locking, PID verification, orphan cleanup, crash recovery
- Optimized xray config — sniffing with routeOnly, connection policy tuning, TCP Fast Open, DNS caching
- Persistent TCP buffer tuning via `sysctl.d` for high-throughput proxy workloads
- Service log viewer with rotation

## How it works

1. **Xray-core** connects to the remote proxy server and exposes a local SOCKS5 endpoint
2. **hev-socks5-tunnel** creates a TUN interface (`tun9`) that routes traffic through the SOCKS5 endpoint
3. The plugin registers a virtual interface (`xproxytun`) and gateway (`XPROXY_TUN`) in OPNsense
4. Firewall rules route LAN traffic through the TUN gateway using OPNsense's `_firewall()` plugin hook

## Dependencies

| Package | Source | Status |
|---|---|---|
| xray-core | [security/xray-core](https://www.freshports.org/security/xray-core/) | Installed by `install.sh` or manual setup |
| hev-socks5-tunnel | [heiher/hev-socks5-tunnel](https://github.com/heiher/hev-socks5-tunnel) | Downloaded by `install.sh` / `xproxy setup` |

## Installation

SSH into your OPNsense firewall and run:

```bash
fetch -o - https://raw.githubusercontent.com/dasunNimantha/xproxy/main/install.sh | sh
```

The installer copies the plugin files, installs `xray-core`, downloads the `hev-socks5-tunnel` binary, and restarts `configd`.

Then navigate to **VPN > Xproxy** in the web UI to configure.

### Manual installation

```bash
# Install runtime dependency
pkg install -y xray-core

# Clone and copy plugin files
cd /tmp
fetch -o xproxy.tar.gz https://github.com/dasunNimantha/xproxy/archive/refs/heads/main.tar.gz
tar xzf xproxy.tar.gz
cd xproxy-main/src
find . -type f | while read FILE; do
  mkdir -p "$(dirname /usr/local/$FILE)"
  cp "$FILE" "/usr/local/$FILE"
done
chmod +x /usr/local/opnsense/scripts/xproxy/*.py /usr/local/opnsense/scripts/xproxy/*.sh /usr/local/opnsense/scripts/xproxy/*.php 2>/dev/null || true
/usr/local/opnsense/scripts/xproxy/setup.sh
service configd restart
```

### Uninstall

```bash
fetch -o - https://raw.githubusercontent.com/dasunNimantha/xproxy/main/uninstall.sh | sh
```

## UI

The plugin adds **VPN > Xproxy** to the OPNsense sidebar with four tabs:

- **General** — Enable/disable the service, select active server, toggle transparent routing
- **Servers** — View and manage imported server profiles
- **Import** — Paste proxy URIs to import server configurations
- **Log** — Live service log viewer

The Active Server dropdown refreshes automatically when servers are added, deleted, edited, or imported — no page reload needed. When no active server is set, the plugin auto-selects the first available server on add or import.

## Performance tuning

The plugin applies TCP buffer tuning via `/usr/local/etc/sysctl.d/xproxy.conf` on service start.

For ISP connections with high packet loss on international paths (common in South/Southeast Asia), switching OPNsense's TCP congestion control from CUBIC to **CDG** (CAIA Delay Gradient) can significantly improve upload throughput:

```bash
# Load the module
kldload cc_cdg

# Switch to CDG
sysctl net.inet.tcp.cc.algorithm=cdg

# Persist across reboots
echo 'cc_cdg_load="YES"' >> /boot/loader.conf
echo 'net.inet.tcp.cc.algorithm=cdg' >> /etc/sysctl.conf
```

On the VPS/server side, enable **BBR** congestion control and tune TCP buffers for matched performance:

```bash
# Enable BBR (Linux)
modprobe tcp_bbr
sysctl -w net.ipv4.tcp_congestion_control=bbr
sysctl -w net.core.default_qdisc=fq

# Persist
echo tcp_bbr >> /etc/modules-load.d/bbr.conf
echo 'net.ipv4.tcp_congestion_control=bbr' >> /etc/sysctl.d/99-xray-tuning.conf
echo 'net.core.default_qdisc=fq' >> /etc/sysctl.d/99-xray-tuning.conf
```

## License

BSD 2-Clause. See [LICENSE](https://github.com/opnsense/plugins/blob/master/LICENSE).
