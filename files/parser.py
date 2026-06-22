#!/usr/bin/env python3
import json
import base64
import sys
from pathlib import Path
from urllib.parse import unquote, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed
from logger import Logger

logger = Logger()

def parse_vless(uri: str) -> dict:
    try:
        uri_clean = uri.replace("vless://", "")
        name = ""
        if "#" in uri_clean:
            uri_clean, name = uri_clean.split("#", 1)
            name = unquote(name)
        query = ""
        if "?" in uri_clean:
            uri_clean, query = uri_clean.split("?", 1)
        uuid, host_port = uri_clean.split("@", 1)
        host, port = (host_port.split(":", 1) + ["443"])[:2]
        params = {}
        if query:
            for k, v in parse_qs(query).items():
                params[k] = v[0] if len(v) == 1 else v
        return {
            "type": "vless", "uuid": uuid.strip(), "host": host.strip(),
            "port": int(port), "params": params, "name": name, "raw_uri": f"vless://{uri}"
        }
    except Exception:
        return None

def parse_ss(uri: str) -> dict:
    try:
        uri_clean = uri.replace("ss://", "")
        name = ""
        if "#" in uri_clean:
            uri_clean, name = uri_clean.split("#", 1)
            name = unquote(name)
        query = ""
        if "?" in uri_clean:
            uri_clean, query = uri_clean.split("?", 1)
        if "@" not in uri_clean:
            decoded = base64.b64decode(uri_clean + "=" * (4 - len(uri_clean) % 4)).decode()
            uri_clean = decoded
        userinfo, host_port = uri_clean.split("@", 1)
        try:
            decoded_user = base64.b64decode(userinfo + "=" * (4 - len(userinfo) % 4)).decode()
            method, password = decoded_user.split(":", 1)
        except:
            method, password = userinfo.split(":", 1)
        host, port = (host_port.split(":", 1) + ["8388"])[:2]
        params = {}
        if query:
            for k, v in parse_qs(query).items():
                params[k] = v[0] if len(v) == 1 else v
        return {
            "type": "ss", "method": method.strip(), "password": password.strip(),
            "host": host.strip(), "port": int(port), "params": params,
            "name": name, "raw_uri": f"ss://{uri}"
        }
    except Exception:
        return None

def parse_trojan(uri: str) -> dict:
    try:
        uri_clean = uri.replace("trojan://", "")
        name = ""
        if "#" in uri_clean:
            uri_clean, name = uri_clean.split("#", 1)
            name = unquote(name)
        query = ""
        if "?" in uri_clean:
            uri_clean, query = uri_clean.split("?", 1)
        password, host_port = uri_clean.split("@", 1)
        host, port = (host_port.split(":", 1) + ["443"])[:2]
        params = {}
        if query:
            for k, v in parse_qs(query).items():
                params[k] = v[0] if len(v) == 1 else v
        return {
            "type": "trojan", "password": password.strip(), "host": host.strip(),
            "port": int(port), "params": params, "name": name, "raw_uri": f"trojan://{uri}"
        }
    except Exception:
        return None

def parse_hysteria(uri: str) -> dict:
    try:
        uri_clean = uri.replace("hysteria://", "")
        name = ""
        if "#" in uri_clean:
            uri_clean, name = uri_clean.split("#", 1)
            name = unquote(name)
        query = ""
        if "?" in uri_clean:
            uri_clean, query = uri_clean.split("?", 1)
        host, port = (uri_clean.split(":", 1) + ["443"])[:2]
        params = {}
        if query:
            for k, v in parse_qs(query).items():
                params[k] = v[0] if len(v) == 1 else v
        return {
            "type": "hysteria", "host": host.strip(), "port": int(port),
            "auth": params.get("auth", ""), "obfs": params.get("obfs", ""),
            "obfs_password": params.get("obfs-password", ""),
            "protocol": params.get("protocol", "udp"),
            "up_mbps": int(params.get("upmbps", 100)),
            "down_mbps": int(params.get("downmbps", 200)),
            "sni": params.get("peer", ""),
            "alpn": [params.get("alpn")] if params.get("alpn") else [],
            "insecure": params.get("insecure", "0") == "1",
            "name": name, "params": params, "raw_uri": f"hysteria://{uri}"
        }
    except Exception:
        return None

PARSERS = {
    "vless://": parse_vless,
    "ss://": parse_ss,
    "trojan://": parse_trojan,
    "hysteria://": parse_hysteria,
}

def parse_single_uri(uri: str) -> dict:
    uri = uri.strip()
    if not uri:
        return None
    for prefix, parser_fn in PARSERS.items():
        if uri.startswith(prefix):
            return parser_fn(uri)
    return None

def parse_base64_subscription(text: str) -> list:
    configs = []
    try:
        text = text.strip()
        padding = 4 - len(text) % 4
        if padding != 4:
            text += "=" * padding
        decoded = base64.b64decode(text).decode('utf-8', errors='ignore')
        for line in decoded.splitlines():
            cfg = parse_single_uri(line.strip())
            if cfg:
                configs.append(cfg)
    except Exception:
        pass
    return configs

def parse_singbox_json(data: dict) -> list:
    configs = []
    for out in data.get("outbounds", []):
        tag = out.get("tag", "")
        proto = out.get("type", "").lower()
        try:
            if proto == "vless":
                configs.append({
                    "type": "vless", "uuid": out.get("uuid", ""),
                    "host": out.get("server", ""), "port": int(out.get("server_port", 443)),
                    "name": tag, "params": {
                        "flow": out.get("flow", ""),
                        "security": "tls" if out.get("tls", {}).get("enabled") else "none",
                        "sni": out.get("tls", {}).get("server_name", ""),
                        "alpn": out.get("tls", {}).get("alpn", []),
                        "fingerprint": out.get("tls", {}).get("utls", {}).get("fingerprint", "chrome"),
                    }
                })
            elif proto == "shadowsocks":
                configs.append({
                    "type": "ss", "method": out.get("method", "aes-256-gcm"),
                    "password": out.get("password", ""), "host": out.get("server", ""),
                    "port": int(out.get("server_port", 8388)), "name": tag,
                })
            elif proto == "trojan":
                configs.append({
                    "type": "trojan", "password": out.get("password", ""),
                    "host": out.get("server", ""), "port": int(out.get("server_port", 443)),
                    "name": tag, "params": {
                        "sni": out.get("tls", {}).get("server_name", ""),
                        "alpn": out.get("tls", {}).get("alpn", []),
                    }
                })
            elif proto == "hysteria":
                configs.append({
                    "type": "hysteria", "host": out.get("server", ""),
                    "port": int(out.get("server_port", 443)), "auth": out.get("auth_str", ""),
                    "obfs": out.get("obfs", ""), "protocol": "udp",
                    "up_mbps": int(out.get("up_mbps", 100)), "down_mbps": int(out.get("down_mbps", 200)),
                    "sni": out.get("tls", {}).get("server_name", ""),
                    "insecure": out.get("tls", {}).get("insecure", False), "name": tag,
                })
        except Exception:
            pass
    return configs

def parse_file(filepath: str) -> list:
    path = Path(filepath)
    if not path.exists():
        return []
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    configs = []
    if content.startswith("{") or content.startswith("["):
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                configs = parse_singbox_json(data)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, str):
                        cfg = parse_single_uri(item)
                        if cfg:
                            configs.append(cfg)
            if configs:
                return configs
        except json.JSONDecodeError:
            pass
    if "\n" not in content and len(content) > 20:
        b64 = parse_base64_subscription(content)
        if b64:
            return b64
    for line in content.splitlines():
        if line.strip() and not line.strip().startswith("#"):
            cfg = parse_single_uri(line.strip())
            if cfg:
                configs.append(cfg)
    return configs

def run(input_dir: str = "configs", output_dir: str = "output"):
    in_dir = Path(input_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.start("parser", f"Сканирую {in_dir}/")

    all_configs = []
    files_to_parse = []
    if in_dir.exists() and in_dir.is_dir():
        files_to_parse = [f for f in sorted(in_dir.iterdir()) if f.suffix in ['.txt', '.json', '.yaml', '.yml', '.conf', '']]

    if not files_to_parse:
        logger.warn("parser", "Нет файлов в configs/")
        logger.save()
        return []

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(parse_file, str(f)): f for f in files_to_parse}
        for future in as_completed(futures):
            f = futures[future]
            try:
                configs = future.result()
                for cfg in configs:
                    cfg["source"] = f.name
                all_configs.extend(configs)
                logger.info("parser", f"{f.name}: {len(configs)} конфигов")
            except Exception as e:
                logger.error("parser", f"{f.name}: {e}")

    logger.ok("parser", f"Итого: {len(all_configs)} конфигов")

    with open(out_dir / "parsed.json", 'w', encoding='utf-8') as f:
        json.dump(all_configs, f, ensure_ascii=False, indent=2)

    logger.save()
    return all_configs

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--input", "-i", default="configs")
    p.add_argument("--output", "-o", default="output")
    args = p.parse_args()
    run(args.input, args.output)
