#!/usr/bin/env python3
import json
import hashlib
import sys
from pathlib import Path
from logger import Logger

logger = Logger()

DEFAULTS = {
    "vless": {"port": 443, "security": "none", "flow": ""},
    "ss": {"port": 8388, "method": "aes-256-gcm"},
    "trojan": {"port": 443, "security": "tls"},
    "hysteria": {"port": 443, "obfs": "", "auth": "", "protocol": "udp"}
}

REQUIRED = {
    "vless": ["uuid", "host"],
    "ss": ["host", "password", "method"],
    "trojan": ["host", "password"],
    "hysteria": ["host"]
}

def validate(cfg: dict) -> bool:
    ctype = cfg.get("type", "")
    if ctype not in REQUIRED:
        return False
    for field in REQUIRED[ctype]:
        if not cfg.get(field):
            return False
    host = cfg.get("host", "")
    if not host or len(host) < 3 or ".." in host:
        return False
    try:
        port = int(cfg.get("port", 0))
        if port < 1 or port > 65535:
            return False
    except:
        return False
    return True

def normalize(config: dict) -> dict:
    ctype = config.get("type", "").lower().strip()
    if ctype not in DEFAULTS:
        return None
    for key, val in DEFAULTS[ctype].items():
        if key not in config or config[key] in [None, ""]:
            config[key] = val
    str_fields = ["host", "uuid", "password", "auth", "sni", "path",
                  "flow", "security", "method", "name", "public_key",
                  "short_id", "spider_x", "obfs", "obfs_password"]
    for f in str_fields:
        if f in config and isinstance(config[f], str):
            config[f] = config[f].strip()
    try:
        config["port"] = int(config["port"])
    except:
        config["port"] = DEFAULTS[ctype]["port"]
    if "alpn" in config and isinstance(config["alpn"], str):
        config["alpn"] = [a.strip() for a in config["alpn"].split(",") if a.strip()]
    config.setdefault("alpn", [])
    config.setdefault("fingerprint", "chrome")
    if ctype == "hysteria":
        uid = f"{config['host']}:{config['port']}:{config.get('auth','')}:{config.get('obfs_password','')}"
    else:
        uid = f"{config['host']}:{config['port']}:{config.get('uuid','')}:{config.get('password','')}"
    config["id"] = hashlib.sha256(uid.encode()).hexdigest()[:16]
    for k in ["tested", "alive", "tg_ok"]:
        config.setdefault(k, False)
    for k in ["latency_ms", "error", "tested_at", "country"]:
        config.setdefault(k, None)
    return config

def run(input_file: str, output_dir: str):
    in_path = Path(input_file)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.start("normalizer", f"Обработка {input_file}")

    with open(in_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    configs = data if isinstance(data, list) else data.get("configs", [])

    normalized, garbage = [], []
    for cfg in configs:
        if not validate(cfg):
            garbage.append(cfg)
            continue
        res = normalize(cfg)
        if res:
            normalized.append(res)
        else:
            garbage.append(cfg)

    logger.ok("normalizer", f"Вход: {len(configs)} -> Ок: {len(normalized)} | Мусор: {len(garbage)}")

    with open(out_dir / "normalized.json", 'w', encoding='utf-8') as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)
    if garbage:
        with open(out_dir / "garbage.txt", 'a', encoding='utf-8') as f:
            for g in garbage:
                f.write(f"# VALIDATION_FAIL\n{json.dumps(g, ensure_ascii=False)}\n")

    logger.save()
    return normalized

if __name__ == "__main__":
    i = sys.argv[1] if len(sys.argv) > 1 else "output/parsed.json"
    o = sys.argv[2] if len(sys.argv) > 2 else "output"
    run(i, o)
