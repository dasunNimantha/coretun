"""Tests for service_control.py — xray config generation."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                '..', 'src', 'opnsense', 'scripts', 'xproxy'))

from service_control import (
    build_xray_config, build_outbound, build_stream_settings, _safe_int,
)


def _base_cfg(**overrides):
    cfg = {
        'socks_port': 10808,
        'http_port': 10809,
        'socks_listen': '127.0.0.1',
        'http_listen': '127.0.0.1',
        'log_level': 'warning',
        'bypass_ips': '10.0.0.0/8,172.16.0.0/12,192.168.0.0/16',
        'servers': [],
    }
    cfg.update(overrides)
    return cfg


def _vless_server(**overrides):
    srv = {
        'protocol': 'vless',
        'address': 'proxy.example.com',
        'port': 443,
        'user_id': 'test-uuid',
        'encryption': 'none',
        'flow': 'xtls-rprx-vision',
        'transport': 'tcp',
        'transport_host': '',
        'transport_path': '',
        'security': 'reality',
        'sni': 'www.spotify.com',
        'fingerprint': 'chrome',
        'alpn': '',
        'reality_pubkey': 'pubkey123',
        'reality_short_id': 'shortid456',
        'password': '',
    }
    srv.update(overrides)
    return srv


class TestSafeInt(unittest.TestCase):

    def test_valid(self):
        self.assertEqual(_safe_int('443', 80), 443)

    def test_default_on_invalid(self):
        self.assertEqual(_safe_int('abc', 80), 80)
        self.assertEqual(_safe_int('', 80), 80)
        self.assertEqual(_safe_int(None, 80), 80)

    def test_min_max(self):
        self.assertEqual(_safe_int('0', 80, minimum=1), 80)
        self.assertEqual(_safe_int('99999', 80, maximum=65535), 80)
        self.assertEqual(_safe_int('443', 80, minimum=1, maximum=65535), 443)


class TestBuildStreamSettings(unittest.TestCase):

    def test_tcp_no_security(self):
        srv = _vless_server(security='none', transport='tcp')
        stream = build_stream_settings(srv)
        self.assertEqual(stream['network'], 'tcp')
        self.assertNotIn('security', stream)

    def test_tls(self):
        srv = _vless_server(security='tls', sni='example.com', fingerprint='firefox', alpn='h2,http/1.1')
        stream = build_stream_settings(srv)
        self.assertEqual(stream['security'], 'tls')
        self.assertEqual(stream['tlsSettings']['serverName'], 'example.com')
        self.assertEqual(stream['tlsSettings']['fingerprint'], 'firefox')
        self.assertEqual(stream['tlsSettings']['alpn'], ['h2', 'http/1.1'])

    def test_reality(self):
        srv = _vless_server()
        stream = build_stream_settings(srv)
        self.assertEqual(stream['security'], 'reality')
        self.assertEqual(stream['realitySettings']['publicKey'], 'pubkey123')
        self.assertEqual(stream['realitySettings']['shortId'], 'shortid456')
        self.assertEqual(stream['realitySettings']['serverName'], 'www.spotify.com')

    def test_websocket(self):
        srv = _vless_server(transport='ws', transport_path='/ws', transport_host='cdn.example.com')
        stream = build_stream_settings(srv)
        self.assertEqual(stream['wsSettings']['path'], '/ws')
        self.assertEqual(stream['wsSettings']['headers']['Host'], 'cdn.example.com')

    def test_grpc(self):
        srv = _vless_server(transport='grpc', transport_path='my-grpc-svc')
        stream = build_stream_settings(srv)
        self.assertEqual(stream['grpcSettings']['serviceName'], 'my-grpc-svc')

    def test_h2(self):
        srv = _vless_server(transport='h2', transport_path='/h2', transport_host='h2.host')
        stream = build_stream_settings(srv)
        self.assertEqual(stream['httpSettings']['path'], '/h2')
        self.assertEqual(stream['httpSettings']['host'], ['h2.host'])

    def test_httpupgrade(self):
        srv = _vless_server(transport='httpupgrade', transport_path='/upgrade', transport_host='up.host')
        stream = build_stream_settings(srv)
        self.assertEqual(stream['httpupgradeSettings']['path'], '/upgrade')
        self.assertEqual(stream['httpupgradeSettings']['host'], 'up.host')


class TestBuildOutbound(unittest.TestCase):

    def test_vless_outbound(self):
        srv = _vless_server()
        out = build_outbound(srv)
        self.assertEqual(out['tag'], 'proxy')
        self.assertEqual(out['protocol'], 'vless')
        vnext = out['settings']['vnext'][0]
        self.assertEqual(vnext['address'], 'proxy.example.com')
        self.assertEqual(vnext['port'], 443)
        self.assertEqual(vnext['users'][0]['id'], 'test-uuid')
        self.assertEqual(vnext['users'][0]['flow'], 'xtls-rprx-vision')

    def test_vmess_outbound(self):
        srv = _vless_server(protocol='vmess', encryption='auto', flow='')
        out = build_outbound(srv)
        self.assertEqual(out['protocol'], 'vmess')
        user = out['settings']['vnext'][0]['users'][0]
        self.assertEqual(user['alterId'], 0)
        self.assertEqual(user['security'], 'auto')

    def test_shadowsocks_outbound(self):
        srv = _vless_server(protocol='shadowsocks', encryption='aes-256-gcm', password='secret')
        out = build_outbound(srv)
        self.assertEqual(out['protocol'], 'shadowsocks')
        server = out['settings']['servers'][0]
        self.assertEqual(server['method'], 'aes-256-gcm')
        self.assertEqual(server['password'], 'secret')

    def test_trojan_outbound(self):
        srv = _vless_server(protocol='trojan', password='trojan-pass')
        out = build_outbound(srv)
        self.assertEqual(out['protocol'], 'trojan')
        server = out['settings']['servers'][0]
        self.assertEqual(server['password'], 'trojan-pass')

    def test_vless_no_flow(self):
        srv = _vless_server(flow='')
        out = build_outbound(srv)
        self.assertNotIn('flow', out['settings']['vnext'][0]['users'][0])


class TestBuildXrayConfig(unittest.TestCase):

    def test_full_config_structure(self):
        cfg = _base_cfg()
        srv = _vless_server()
        config = build_xray_config(cfg, srv)

        self.assertIn('log', config)
        self.assertIn('dns', config)
        self.assertIn('inbounds', config)
        self.assertIn('outbounds', config)
        self.assertIn('routing', config)
        self.assertEqual(config['log']['loglevel'], 'warning')
        self.assertIn('error', config['log'])
        self.assertNotIn('access', config['log'])
        self.assertEqual(config['routing']['domainStrategy'], 'AsIs')

    def test_inbounds(self):
        cfg = _base_cfg()
        srv = _vless_server()
        config = build_xray_config(cfg, srv)
        inbounds = config['inbounds']

        socks = next(i for i in inbounds if i['tag'] == 'socks-in')
        self.assertEqual(socks['port'], 10808)
        self.assertEqual(socks['listen'], '127.0.0.1')
        self.assertTrue(socks['settings']['udp'])

        http = next(i for i in inbounds if i['tag'] == 'http-in')
        self.assertEqual(http['port'], 10809)

    def test_outbounds_include_direct_and_block(self):
        cfg = _base_cfg()
        srv = _vless_server()
        config = build_xray_config(cfg, srv)
        tags = [o['tag'] for o in config['outbounds']]
        self.assertEqual(tags, ['proxy', 'direct', 'block'])

    def test_bypass_ips_routing(self):
        cfg = _base_cfg(bypass_ips='10.0.0.0/8,192.168.0.0/16')
        srv = _vless_server()
        config = build_xray_config(cfg, srv)
        bypass_rule = config['routing']['rules'][0]
        self.assertEqual(bypass_rule['outboundTag'], 'direct')
        self.assertIn('10.0.0.0/8', bypass_rule['ip'])
        self.assertIn('192.168.0.0/16', bypass_rule['ip'])

    def test_domain_address_routing(self):
        cfg = _base_cfg(bypass_ips='')
        srv = _vless_server(address='proxy.example.com')
        config = build_xray_config(cfg, srv)
        domain_rule = next(
            r for r in config['routing']['rules'] if 'domain' in r
        )
        self.assertIn('full:proxy.example.com', domain_rule['domain'])
        self.assertEqual(domain_rule['outboundTag'], 'direct')

    def test_ip_address_routing(self):
        cfg = _base_cfg(bypass_ips='')
        srv = _vless_server(address='1.2.3.4')
        config = build_xray_config(cfg, srv)
        ip_rule = next(
            r for r in config['routing']['rules'] if 'ip' in r
        )
        self.assertIn('1.2.3.4', ip_rule['ip'])

    def test_custom_listen_addresses(self):
        cfg = _base_cfg(socks_listen='0.0.0.0', http_listen='0.0.0.0')
        srv = _vless_server()
        config = build_xray_config(cfg, srv)
        socks = config['inbounds'][0]
        http = config['inbounds'][1]
        self.assertEqual(socks['listen'], '0.0.0.0')
        self.assertEqual(http['listen'], '0.0.0.0')

    def test_dns_section_domain_server(self):
        cfg = _base_cfg()
        srv = _vless_server(address='proxy.example.com')
        config = build_xray_config(cfg, srv)
        dns = config['dns']['servers']
        pinned = dns[0]
        self.assertIsInstance(pinned, dict)
        self.assertEqual(pinned['address'], '1.1.1.1')
        self.assertIn('full:proxy.example.com', pinned['domains'])
        self.assertIn('1.1.1.1', dns)
        self.assertIn('8.8.8.8', dns)
        self.assertIn('localhost', dns)

    def test_dns_section_ip_server(self):
        cfg = _base_cfg()
        srv = _vless_server(address='1.2.3.4')
        config = build_xray_config(cfg, srv)
        dns = config['dns']['servers']
        for entry in dns:
            if isinstance(entry, dict):
                self.fail('IP-address server should not get a pinned DNS entry')
        self.assertIn('1.1.1.1', dns)
        self.assertIn('8.8.8.8', dns)


class TestNoDnsLoop(unittest.TestCase):
    """Guard against the socket/FD leak that caused OOM on OPNsense.

    When Xray uses domainStrategy "IPIfNonMatch" without explicit DNS
    servers, every unmatched domain triggers a DNS lookup.  If DNS itself
    routes through the tunnel, each lookup spawns more connections,
    exhausting kern.maxfiles / kern.ipc.maxsockets and eventually swap.

    These tests ensure the generated config is safe regardless of
    protocol, address type, or bypass settings.
    """

    PROTOCOLS = ('vless', 'vmess', 'shadowsocks', 'trojan')

    def _build(self, **server_overrides):
        cfg = _base_cfg()
        srv = _vless_server(**server_overrides)
        return build_xray_config(cfg, srv)

    # -- domainStrategy must never be IPIfNonMatch -------------------------

    def test_domain_strategy_is_not_ipifnonmatch(self):
        for proto in self.PROTOCOLS:
            with self.subTest(protocol=proto):
                kw = {'protocol': proto}
                if proto in ('shadowsocks', 'trojan'):
                    kw['password'] = 'pass'
                config = self._build(**kw)
                strategy = config['routing']['domainStrategy']
                self.assertNotEqual(
                    strategy, 'IPIfNonMatch',
                    f'{proto}: IPIfNonMatch causes DNS loop → FD exhaustion',
                )

    # -- DNS section must always be present --------------------------------

    def test_dns_section_always_present(self):
        for proto in self.PROTOCOLS:
            with self.subTest(protocol=proto):
                kw = {'protocol': proto}
                if proto in ('shadowsocks', 'trojan'):
                    kw['password'] = 'pass'
                config = self._build(**kw)
                self.assertIn('dns', config)
                servers = config['dns']['servers']
                self.assertGreaterEqual(len(servers), 2,
                                        'Need at least two DNS servers for redundancy')

    def test_dns_contains_public_resolvers(self):
        config = self._build()
        flat = [s for s in config['dns']['servers'] if isinstance(s, str)]
        self.assertTrue(
            any(s in ('1.1.1.1', '8.8.8.8') for s in flat),
            'DNS must include at least one public resolver to avoid tunnel loop',
        )

    # -- Domain-based proxy server must be DNS-pinned direct ---------------

    def test_domain_server_has_dns_pin(self):
        config = self._build(address='proxy.example.com')
        dns = config['dns']['servers']
        pinned_domains = []
        for entry in dns:
            if isinstance(entry, dict):
                pinned_domains.extend(entry.get('domains', []))
        self.assertIn(
            'full:proxy.example.com', pinned_domains,
            'Proxy server domain must be pinned to a direct DNS server',
        )

    def test_domain_server_has_direct_routing_rule(self):
        config = self._build(address='proxy.example.com')
        direct_domains = []
        for rule in config['routing']['rules']:
            if rule.get('outboundTag') == 'direct' and 'domain' in rule:
                direct_domains.extend(rule['domain'])
        self.assertIn(
            'full:proxy.example.com', direct_domains,
            'Proxy server domain must route direct to avoid tunnel loop',
        )

    # -- IP-based proxy server must route direct but skip DNS pin ----------

    def test_ip_server_has_direct_routing_rule(self):
        config = self._build(address='203.0.113.1')
        direct_ips = []
        for rule in config['routing']['rules']:
            if rule.get('outboundTag') == 'direct' and 'ip' in rule:
                direct_ips.extend(rule['ip'])
        self.assertIn(
            '203.0.113.1', direct_ips,
            'Proxy server IP must route direct',
        )

    def test_ip_server_no_dns_pin(self):
        config = self._build(address='203.0.113.1')
        for entry in config['dns']['servers']:
            if isinstance(entry, dict):
                self.fail('IP-based server should not have a DNS pin entry')

    # -- Every protocol produces a loop-safe config ------------------------

    def test_all_protocols_loop_safe(self):
        servers = [
            _vless_server(address='vless.example.com'),
            _vless_server(protocol='vmess', address='vmess.example.com',
                          flow='', encryption='auto'),
            _vless_server(protocol='shadowsocks', address='ss.example.com',
                          password='pass', encryption='aes-256-gcm'),
            _vless_server(protocol='trojan', address='trojan.example.com',
                          password='pass'),
        ]
        for srv in servers:
            with self.subTest(protocol=srv['protocol']):
                cfg = _base_cfg()
                config = build_xray_config(cfg, srv)
                strategy = config['routing']['domainStrategy']
                self.assertNotEqual(strategy, 'IPIfNonMatch')
                self.assertIn('dns', config)
                dns_pins = []
                for entry in config['dns']['servers']:
                    if isinstance(entry, dict):
                        dns_pins.extend(entry.get('domains', []))
                self.assertIn(
                    'full:' + srv['address'], dns_pins,
                    f"{srv['protocol']}: server domain must be DNS-pinned",
                )

    # -- Edge cases --------------------------------------------------------

    def test_empty_bypass_still_has_dns_and_direct_rule(self):
        cfg = _base_cfg(bypass_ips='')
        srv = _vless_server(address='proxy.example.com')
        config = build_xray_config(cfg, srv)
        self.assertIn('dns', config)
        has_direct = any(
            r.get('outboundTag') == 'direct'
            for r in config['routing']['rules']
        )
        self.assertTrue(has_direct,
                        'Even with empty bypass_ips, proxy server must route direct')


if __name__ == '__main__':
    unittest.main()
