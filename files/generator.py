#!/usr/bin/env python3
import json
import sys
import uuid as uuid_lib
import secrets
import string
from pathlib import Path
from datetime import datetime, timezone
from logger import Logger

logger = Logger()

def gen_uuid() -> str:
    return str(uuid_lib.uuid4())

def gen_password(length: int = 24) -> str:
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))

def generate_vless(host: str, port: int = 443, name: str = "", obfuscated: bool = True) -> dict:
    cfg = {
        "type": "vless", "uuid": gen_uuid(), "host": host, "port": port,
        "name": name or f"VLESS-{host}", "params": {}
    }
    if obfuscated:
        cfg["params"].update({
            "security": "reality", "flow": "xtls-rvision",
            "sni": "cloudflare.com", "fingerprint": "chrome",
            "public_key": "", "short_id": gen_password(8).lower()
        })
    else:
        cfg["params"].update({"security": "tls", "sni": host})
    return cfg

def generate_ss(host: str, port: int = 8388, name: str = "", method: str = "aes-256-gcm") -> dict:
    return {
        "type": "ss", "method": method, "password": gen_password(),
        "host": host, "port": port, "name": name or f"SS-{host}"
    }

def generate_trojan(host: str, port: int = 443, name: str = "", obfuscated: bool = True) -> dict:
    cfg = {
        "type": "trojan", "password": gen_password(), "host": host, "port": port,
        "name": name or f"Trojan-{host}", "params": {}
    }
    cfg["params"]["sni"] = "cloudflare.com" if obfuscated else host
    cfg["params"]["type"] = "tcp"
    return cfg

def generate_hysteria(host: str, port: int = 443, name: str = "", obfuscated: bool = True) -> dict:
    cfg = {
        "type": "hysteria", "host": host, "port": port, "auth": gen_password(),
        "protocol": "udp", "up_mbps": 100, "down_mbps": 200,
        "name": name or f"Hysteria-{host}"
    }
    if obfuscated:
        cfg["obfs"] = "salamander"
        cfg["obfs_password"] = gen_password()
        cfg["sni"] = "cloudflare.com"
    else:
        cfg["sni"] = host
    cfg["insecure"] = True
    return cfg

GENERATORS = {
    "vless": generate_vless,
    "ss": generate_ss,
    "trojan": generate_trojan,
    "hysteria": generate_hysteria,
}

def run(servers_file: str, output_dir: str):
    srv_path = Path(servers_file)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.start("generator", f"Генерация конфигов из {servers_file}")

    if not srv_path.exists():
        logger.warn("generator", f"Файл не найден: {servers_file}, пропускаю")
        logger.save()
        return []

    with open(srv_path, 'r', encoding='utf-8') as f:
        servers = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

    generated = []
    for line in servers:
        parts = line.split()
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 443
        proto = parts[2].lower() if len(parts) > 2 else "vless"
        name = parts[3] if len(parts) > 3 else ""

        if proto not in GENERATORS:
            logger.warn("generator", f"Неизвестный протокол: {proto}")
            continue

        cfg = GENERATORS[proto](host, port, name)
        cfg["source"] = "generated"
        cfg["generated_at"] = datetime.now(timezone.utc).isoformat()
        generated.append(cfg)
        logger.info("generator", f"{proto}://{host}:{port}")

    out_file = out_dir / "generated.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(generated, f, ensure_ascii=False, indent=2)

    logger.ok("generator", f"Сгенерировано: {len(generated)} конфигов")
    logger.save()
    return generated

if __name__ == "__main__":
    i = sys.argv[1] if len(sys.argv) > 1 else "servers.txt"
    o = sys.argv[2] if len(sys.argv) > 2 else "output"
    run(i, o)
