#!/usr/bin/env python3
import json
import sys
import time
import ipaddress
from datetime import datetime, timezone
from pathlib import Path
from logger import Logger
from geoip import get_country

logger = Logger()

VPS_HOST = None
VPS_USER = None
VPS_KEY_PATH = None

def load_or_empty(path: Path) -> list:
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            items = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
            return items
    return []

def test_config_live(cfg: dict) -> dict:
    import paramiko
    host = cfg["host"]
    port = cfg["port"]
    ctype = cfg["type"]
    name = cfg.get("name", host)

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USER, key_filename=VPS_KEY_PATH, timeout=10)

        config_json = json.dumps(cfg)
        cmd = f"""
cat > /tmp/test_config.json << 'EOF'
{config_json}
EOF
python3 /opt/vpn-tester/test_single.py /tmp/test_config.json
"""
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
        output = stdout.read().decode()
        error_output = stderr.read().decode()
        ssh.close()

        if "ALIVE: True" in output:
            cfg["tested"] = True
            cfg["alive"] = True
            cfg["tg_ok"] = True
            cfg["error"] = None
            for line in output.splitlines():
                if "LATENCY:" in line:
                    cfg["latency_ms"] = int(line.split("LATENCY:")[1].strip())
            cfg["tested_at"] = datetime.now(timezone.utc).isoformat()
        else:
            cfg["tested"] = True
            cfg["alive"] = False
            cfg["tg_ok"] = False
            cfg["latency_ms"] = None
            cfg["error"] = error_output.strip()[:100] or "tunnel_failed"
            cfg["tested_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        cfg["tested"] = True
        cfg["alive"] = False
        cfg["tg_ok"] = False
        cfg["latency_ms"] = None
        cfg["error"] = f"ssh_error:{str(e)[:80]}"
        cfg["tested_at"] = datetime.now(timezone.utc).isoformat()

    return cfg

def to_uri(cfg: dict) -> str:
    ctype, host, port, name = cfg["type"], cfg["host"], cfg["port"], cfg.get("name", "")
    if ctype == "vless":
        uuid = cfg.get("uuid", "")
        params = "&".join(f"{k}={v}" for k, v in cfg.get("params", {}).items() if v)
        uri = f"vless://{uuid}@{host}:{port}"
        if params: uri += f"?{params}"
        if name: uri += f"#{name}"
        return uri
    elif ctype == "ss":
        import base64
        ui = base64.b64encode(f"{cfg.get('method','aes-256-gcm')}:{cfg.get('password','')}".encode()).decode().rstrip("=")
        uri = f"ss://{ui}@{host}:{port}"
        if name: uri += f"#{name}"
        return uri
    elif ctype == "trojan":
        pwd = cfg.get("password", "")
        params = "&".join(f"{k}={v}" for k, v in cfg.get("params", {}).items() if v)
        uri = f"trojan://{pwd}@{host}:{port}"
        if params: uri += f"?{params}"
        if name: uri += f"#{name}"
        return uri
    elif ctype == "hysteria":
        a, o, op = cfg.get("auth",""), cfg.get("obfs",""), cfg.get("obfs_password","")
        params = f"protocol=udp&auth={a}"
        if o: params += f"&obfs={o}"
        if op: params += f"&obfs-password={op}"
        uri = f"hysteria://{host}:{port}?{params}"
        if name: uri += f"#{name}"
        return uri
    return cfg.get("raw_uri", "")

def run(input_file: str, output_dir: str):
    global VPS_HOST, VPS_USER, VPS_KEY_PATH
    VPS_HOST = sys.argv[3] if len(sys.argv) > 3 else None
    VPS_USER = sys.argv[4] if len(sys.argv) > 4 else "root"
    VPS_KEY_PATH = sys.argv[5] if len(sys.argv) > 5 else None

    in_path = Path(input_file)
    out_dir = Path(output_dir)
    root_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.start("tester", f"Боевой тест {input_file}")

    if not in_path.exists():
        logger.error("tester", f"Файл не найден: {input_file}")
        logger.save()
        return

    with open(in_path, 'r', encoding='utf-8') as f:
        configs = json.load(f)

    alive, dead = [], []
    country_data = {}

    for i, cfg in enumerate(configs):
        country = get_country(cfg.get("host", ""))
        cfg["country"] = country

        if VPS_HOST and VPS_USER and VPS_KEY_PATH:
            result = test_config_live(cfg)
            time.sleep(0.3)
        else:
            cfg["tested"] = False
            cfg["alive"] = False
            result = cfg

        if country not in country_data:
            country_data[country] = {"alive": [], "dead": []}

        if result.get("alive"):
            alive.append(result)
            country_data[country]["alive"].append(result)
        else:
            dead.append(result)
            country_data[country]["dead"].append(result)

        status = "ALIVE" if result.get("alive") else "DEAD"
        logger.info("tester", f"[{i+1}/{len(configs)}] {cfg.get('name', cfg.get('host','?'))} ({country}) -> {status}")

    logger.ok("tester", f"Живых: {len(alive)} | Мёртвых: {len(dead)}")
    ts = datetime.now(timezone.utc)

    def sort_by_latency(configs_list, limit=None):
        sorted_list = sorted(configs_list, key=lambda x: x.get("latency_ms") or 9999)
        if limit:
            return sorted_list[:limit]
        return sorted_list

    black = sort_by_latency(alive, 50)

    mobile_ports = {80, 443, 8080, 8443}
    mobile_candidates = [c for c in alive if c.get("port") in mobile_ports and c.get("type") != "hysteria"]
    black_mobile = sort_by_latency(mobile_candidates, 20)

    white_candidates = [c for c in alive if c.get("params", {}).get("security") == "reality"
                        or c.get("params", {}).get("flow") == "xtls-rvision"
                        or c.get("obfs")]
    white = sort_by_latency(white_candidates, 20)

    white_sni_candidates = [c for c in alive if c.get("sni") and c.get("sni") != c.get("host")]
    white_sni = sort_by_latency(white_sni_candidates, 20)

    def is_ip(host):
        try:
            ipaddress.ip_address(host)
            return True
        except:
            return False
    white_cidr_candidates = [c for c in alive if is_ip(c.get("host", ""))]
    white_cidr = sort_by_latency(white_cidr_candidates, 20)

    def write_configs(filename, configs):
        with open(root_dir / filename, 'w', encoding='utf-8') as f:
            f.write(f"# {filename} - {ts.isoformat()} - {len(configs)} шт.\n")
            for cfg in configs:
                f.write(to_uri(cfg) + "\n")

    write_configs("black.txt", black)
    write_configs("black_mobile.txt", black_mobile)
    write_configs("white.txt", white)
    write_configs("white_sni.txt", white_sni)
    write_configs("white_cidr.txt", white_cidr)

    with open(out_dir / "alive.txt", 'w', encoding='utf-8') as f:
        f.write(f"# Alive VPN Configs - {ts.isoformat()}\n# Всего: {len(alive)}\n\n")
        for cfg in alive:
            f.write(to_uri(cfg) + "\n")

    with open(out_dir / "garbage.txt", 'a', encoding='utf-8') as f:
        f.write(f"\n# Боевой тест: {ts.isoformat()} | Провалено: {len(dead)}\n\n")
        for cfg in dead:
            f.write(f"# DEAD | {cfg.get('error','?')}\n{to_uri(cfg)}\n\n")

    with open(out_dir / "tg_proxy.txt", 'w', encoding='utf-8') as f:
        f.write(f"# Telegram Proxy List - {ts.isoformat()}\n\n")
        for cfg in alive:
            host, port, ctype = cfg["host"], cfg["port"], cfg["type"]
            name = cfg.get("name", host)
            if ctype == "ss":
                f.write(f"ss://{cfg.get('method','aes-256-gcm')}:{cfg.get('password','')}@{host}:{port}#{name}\n")
            elif ctype == "trojan":
                f.write(f"trojan://{cfg.get('password','')}@{host}:{port}?sni=cloudflare.com&type=tcp#tg-{name}\n")
            elif ctype == "vless":
                f.write(f"vless://{cfg.get('uuid','')}@{host}:{port}?security=reality&sni=cloudflare.com&type=tcp#tg-{name}\n")
            else:
                f.write(f"{to_uri(cfg)}\n")

    by_proto = {"vless": [], "ss": [], "trojan": [], "hysteria": []}
    for cfg in alive:
        if cfg["type"] in by_proto:
            by_proto[cfg["type"]].append(cfg)
    proto_dir = out_dir / "by_protocol"
    proto_dir.mkdir(exist_ok=True)
    for proto, cfgs in by_proto.items():
        with open(proto_dir / f"{proto}.txt", 'w', encoding='utf-8') as f:
            f.write(f"# {proto.upper()} - {ts.isoformat()} - {len(cfgs)} шт.\n\n")
            for cfg in cfgs:
                f.write(to_uri(cfg) + "\n")

    country_dir = out_dir / "by_country"
    country_dir.mkdir(exist_ok=True)
    for country, data in country_data.items():
        if data["alive"]:
            with open(country_dir / f"{country}.txt", 'w', encoding='utf-8') as f:
                f.write(f"# {country} - {len(data['alive'])} живых\n# Обновлено: {ts.isoformat()}\n\n")
                for cfg in data["alive"]:
                    f.write(to_uri(cfg) + "\n")

    report = f"""# VPN Config Test Report
**Дата:** {ts.strftime('%Y-%m-%d %H:%M UTC')}
**Всего:** {len(configs)} | **Живых:** {len(alive)} ({len(alive)/max(len(configs),1)*100:.1f}%) | **Мёртвых:** {len(dead)}

## Категории
| Категория | Файл | Конфигов |
|-----------|------|----------|
| Универсальные | black.txt | {len(black)} |
| Мобильные | black_mobile.txt | {len(black_mobile)} |
| Обход РКН (обфускация) | white.txt | {len(white)} |
| SNI-обход | white_sni.txt | {len(white_sni)} |
| CIDR-обход | white_cidr.txt | {len(white_cidr)} |
| Telegram прокси | output/tg_proxy.txt | {len(alive)} |
"""
    with open(out_dir / "report.md", 'w', encoding='utf-8') as f:
        f.write(report)

    logger.done("tester", "Готово! Категории сформированы.")
    logger.save()

if __name__ == "__main__":
    i = sys.argv[1] if len(sys.argv) > 1 else "output/tcp_passed.json"
    o = sys.argv[2] if len(sys.argv) > 2 else "output"
    run(i, o)
