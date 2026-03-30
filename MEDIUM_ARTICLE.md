# Xproxy: Transparent Proxy Routing for Your Entire LAN on OPNsense

If you run OPNsense as your home or office firewall, you've probably thought about routing traffic through a proxy tunnel. Maybe you want to bypass geo-restrictions, add a layer of privacy, or tunnel through a VPS for a cleaner IP reputation.

The usual approach is to configure a SOCKS or HTTP proxy on each device individually. That works for your laptop. It doesn't work for your smart TV, your IoT sensors, your gaming console, your partner's phone, or the guest who just connected to your WiFi. Most of those devices don't even have proxy settings.

**Xproxy** is an OPNsense plugin that solves this at the firewall level. When enabled, it transparently routes all LAN IPv4 traffic through a VLESS, VMess, Shadowsocks, or Trojan tunnel. No client-side configuration needed on any device.

## What You Get

- **Transparent routing** — Every device on your LAN is automatically tunneled. Phones, tablets, smart TVs, IoT devices, guest devices. Nothing to install or configure on the client side.
- **Multi-protocol support** — VLESS (with XTLS-Vision and Reality), VMess, Shadowsocks, and Trojan via [Xray-core](https://github.com/XTLS/Xray-core).
- **One-click import** — Paste a `vless://`, `vmess://`, `ss://`, or `trojan://` URI and it's parsed into a full server profile automatically.
- **Multiple server profiles** — Import several servers and switch between them from the UI.
- **Fail-safe design** — Firewall routing rules only exist while the tunnel is actually running. Stop the service or reboot with a dead tunnel, and traffic falls back to your normal WAN gateway.
- **Native OPNsense integration** — Shows up as a managed service with start/stop/restart buttons, registers its own gateway and virtual interface, and uses the standard plugin firewall hooks.

## How It Works

Xproxy chains two open-source tools together and wires them into OPNsense's networking stack:

```
LAN Device → OPNsense (pf route-to) → tun9 → tun2socks → Xray-core SOCKS5 → Remote Server
```

**Xray-core** connects to your remote proxy server and exposes a local SOCKS5 endpoint on `127.0.0.1:10808`. **tun2socks** creates a TUN interface (`tun9`) that translates raw IP packets into SOCKS5 traffic. The plugin registers this TUN as a virtual OPNsense interface (`xproxytun`) with its own gateway (`XPROXY_TUN`), then injects `pf` route-to rules on every LAN-facing interface to redirect traffic through that gateway.

The routing rules are **dynamic** — the plugin checks whether Xray-core is actually running (PID file + process liveness check) before generating any firewall rules. If the process isn't alive, the rules don't exist and traffic flows normally.

## Installation

SSH into your OPNsense firewall and run:

```bash
fetch -o - https://raw.githubusercontent.com/dasunNimantha/xproxy/main/install.sh | sh
```

This copies the plugin files, sets permissions, and restarts `configd`. No packages to compile, no ports to build.

**Prerequisites:** Xray-core must be installed (`pkg install xray-core`). tun2socks is downloaded automatically by the plugin's setup script on first run.

To uninstall:

```bash
fetch -o - https://raw.githubusercontent.com/dasunNimantha/xproxy/main/uninstall.sh | sh
```

## Setup Walkthrough

After installation, navigate to **VPN > Xproxy** in the web UI.

### 1. Import a Server

Go to the **Import** tab. Paste your proxy URI — for example:

```
vless://a3fc68c7-4e5b-4126-a5c3-f1f141222f8e@myserver.com:443?type=tcp&encryption=none&security=reality&pbk=dIDFkKW8sBcz0nPNnYPmcB3xdBIspjwhVwGEuuwLoXk&fp=chrome&sni=www.spotify.com&sid=1cd99c66c393acaf&flow=xtls-rprx-vision#my-vps
```

Click **Import**. The plugin parses the URI and creates a server profile with all the parameters filled in (protocol, encryption, transport, TLS/Reality settings, SNI, fingerprint, etc.). You can import multiple servers at once, one URI per line.

### 2. Configure General Settings

Switch to the **General** tab:

- **Enable** — Check to enable the service.
- **Active Server** — Select the server profile you just imported.
- **Transparent LAN Routing** — Enable this to route all LAN traffic through the tunnel. If disabled, the plugin only provides a local SOCKS5/HTTP proxy that devices can use manually.
- **SOCKS/HTTP ports** — Defaults of `10808`/`10809` work for most setups.
- **Bypass IPs** — Private ranges are bypassed by default. Add any additional IPs or subnets you want to exclude from the tunnel (e.g., your local DNS server).

Click **Apply**.

### 3. Start the Service

Use the start/stop buttons in the service widget at the bottom of the page. Once started, you'll see the service status change to "running."

That's it. Every device on your LAN is now routing through the tunnel. You can verify by checking your external IP from any LAN device — it should show your proxy server's IP, not your ISP's.

### 4. Monitor

The **Log** tab tails `/var/log/xproxy.log`, which receives **Xray-core error output** and plugin messages — not a per-connection access log. (Logging every LAN flow to disk would overwhelm I/O on a busy network.) Use your external IP or a test site to confirm the tunnel; check this log when something fails.

## What Happens When You Stop the Service

When you click **Stop**, Xproxy:

1. Terminates Xray-core and tun2socks
2. Destroys the TUN interface
3. Triggers a firewall reload that removes the route-to rules

Your internet continues working immediately through the default WAN gateway. No manual intervention, no stale rules left behind.

## What Happens on Reboot

If the service was enabled before reboot, Xproxy starts automatically during boot. The plugin registers a boot hook that starts Xray-core and tun2socks, then applies the firewall routing rules.

If your remote proxy server happens to be unreachable at boot time, Xray-core will still start (and retry connections), but traffic will flow through the tunnel interface where the proxy will buffer/retry. If you need to disable the tunnel, just click **Stop** in the UI or run `configctl xproxy stop` from the shell.

## Firewall Integration Details

For those who want to understand what's happening at the `pf` level, Xproxy injects two rules per LAN interface:

**Priority 150 — Self access:**

```
pass in quick on vtnet1 inet from (vtnet1:network) to (self) keep state
```

This ensures LAN devices can always reach the firewall for DNS, DHCP, and web UI access.

**Priority 200 — Tunnel routing:**

```
pass in quick on vtnet1 route-to (tun9 10.255.0.2) inet from (vtnet1:network) to any keep state
```

This redirects all other LAN traffic to the TUN gateway.

These rules are generated dynamically by the `xproxy_firewall()` plugin hook. They only appear when the service is running — the hook checks the actual process state, not just the configuration. Your existing firewall rules are not modified or interfered with.

The plugin skips WAN interfaces, virtual interfaces, and the xproxytun interface itself when applying rules. Only real LAN-side interfaces get the route-to treatment.

## Supported Protocols and Transports


| Protocol    | Encryption                             | Transports                            |
| ----------- | -------------------------------------- | ------------------------------------- |
| VLESS       | None (with XTLS-Vision flow)           | TCP, WebSocket, gRPC, H2, HTTPUpgrade |
| VMess       | auto, AES-128-GCM, ChaCha20-Poly1305   | TCP, WebSocket, gRPC, H2, HTTPUpgrade |
| Shadowsocks | AES-256-GCM, ChaCha20-Poly1305, others | TCP                                   |
| Trojan      | N/A (TLS-based)                        | TCP, WebSocket, gRPC                  |


**TLS options:** TLS 1.3, Reality (with public key + short ID)

**Fingerprint options:** Chrome, Firefox, Safari, Edge, randomized

## Memory Considerations

Traditional OPNsense routing happens entirely in the kernel — `pf` forwards packets between interfaces without any userspace memory overhead. Gigabit transfers on a 2GB VM? No problem.

Xproxy changes this. Every TCP connection from your LAN now flows through **two userspace Go programs**:

1. **tun2socks** reconstructs a full TCP/IP stack in memory (via gVisor) for every connection — SYN/ACK handshakes, retransmits, congestion windows, the works.
2. **Xray-core** maintains a proxy session with TLS/Reality encryption state for each connection.

With 50–100+ concurrent connections (browsers alone maintain dozens), this adds meaningful memory on top of OPNsense's baseline. On a 2GB VM, this can lead to out-of-memory pressure during traffic spikes.

**Mitigations built into the plugin:**

- **TCP buffer limits** — tun2socks is launched with `-tcp-rcvbuf 32k -tcp-sndbuf 32k`, reducing per-connection buffer memory by ~80% compared to defaults (which allow up to 1MB per direction per connection).
- **Go runtime memory controls** — Both processes run with `GOGC=50` (more aggressive garbage collection) and `GOMEMLIMIT=128MiB` (soft cap on Go heap size).
- **UDP session timeout** — Set to 30 seconds to reclaim idle UDP state quickly.

**Recommendation:** If you're running OPNsense on a VM with 2GB RAM, add swap space (1GB is plenty). This gives the kernel a safety valve during traffic spikes instead of killing processes. Without swap, FreeBSD's OOM killer will terminate services when memory is tight — and on a firewall, that means loss of connectivity.

```bash
# Add 1GB swap file (persistent across reboots)
dd if=/dev/zero of=/usr/swap0 bs=1m count=1024
chmod 0600 /usr/swap0
mdconfig -a -t vnode -f /usr/swap0 -u 0
swapon /dev/md0
echo 'md0 none swap sw,file=/usr/swap0,late 0 0' >> /etc/fstab
```

On VMs with 4GB+ RAM, this is unlikely to be an issue.

## Known Limitations

- **IPv4 only** — The transparent routing rules apply to IPv4 traffic. IPv6 is not redirected through the tunnel.
- **UDP over tunnel** — UDP works through the SOCKS5 proxy (Xray-core supports UDP), but performance depends on your proxy server and protocol.
- **Single active server** — Only one server profile can be active at a time. You can switch between profiles from the General tab.
- **Userspace overhead** — Unlike kernel-level `tproxy` (used by tools like v2rayA on OpenWrt), Xproxy processes all traffic in userspace via tun2socks. This adds CPU and memory overhead compared to pure kernel forwarding. See the Memory Considerations section above.

## Source Code

Xproxy is open source under the BSD 2-Clause license. It is currently **not listed in the official OPNsense plugin repository** — installation is done manually via the script above. A proposal to include it upstream has been submitted and is under discussion with the OPNsense maintainers.

**Repository:** [github.com/dasunNimantha/xproxy](https://github.com/dasunNimantha/xproxy)

The plugin follows OPNsense's standard MVC plugin architecture — model, controllers, views, configd actions, and PHP plugin hooks. Contributions and issues are welcome.

---

*Xproxy is an independent community plugin and is not affiliated with or endorsed by Deciso B.V. or the OPNsense project.*