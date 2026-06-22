#!/usr/bin/env python3
import json
import socket
import ssl
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from logger import Logger

logger = Logger()

TIMEOUT = 5
RETRIES = 2
MAX_WORKERS = 20
TLS_PORTS = {443, 8443, 2053, 2083, 2087, 2096}

def tcp_connect(host: str, port: int, retries: int = RETRIES) -> dict:
    for attempt in range(retries + 1):
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        try:
            sock.connect((host, port))
            rtt = round((time.time() - start) * 1000)
            sock.close()
            return {"tcp_ok": True, "rtt_ms": rtt, "error": None, "attempts": attempt + 1}
        except socket.timeout:
            err = "timeout"
        except ConnectionRefusedError:
            err = "refused"
        except ConnectionResetError:
            err = "reset"
        except OSError as e:
            err = f"os_error:{e.errno}"
        except Exception as e:
            err = f"unknown:{str(e)[:50]}"
        finally:
            sock.close()
        if attempt < retries:
            time.sleep(1)
    return {"tcp_ok": False, "rtt_ms": None, "error": err, "attempts": retries + 1}

def tls_check(host: str, port: int, sni: str = None) -> dict:
    sni = sni or host
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect((host, port))
        with ctx.wrap_socket(sock, server_hostname=sni) as tls_sock:
            cert = tls_sock.getpeercert()
            subject = next((f[0][1] for f in cert.get("subject", []) if f[0][0] == "commonName"), None)
            issuer = next((f[0][1] for f in cert.get("issuer", []) if f[0][0] == "commonName"), None)
            return {"tls_ok": True, "tls_error": None, "cert_subject": subject, "cert_issuer": issuer}
    except ssl.SSLError as e:
        return {"tls_ok": False, "tls_error": f"ssl:{str(e)[:80]}"}
    except socket.timeout:
        return {"tls_ok": False, "tls_error": "timeout"}
    except ConnectionResetError:
        return {"tls_ok": False, "tls_error": "reset"}
    except Exception as e:
        return {"tls_ok": False, "tls_error": f"{type(e).__name__}:{str(e)[:50]}"}

def analyze_dpi(tcp: dict, tls: dict) -> list:
    symptoms = []
    if not tcp["tcp_ok"]:
        if tcp["error"] == "reset":
            symptoms.append("RST (DPI active)")
        elif tcp["error"] == "timeout":
            symptoms.append("timeout (DPI silent drop)")
        elif tcp["error"] == "refused":
            symptoms.append("refused (dead server)")
        else:
            symptoms.append(f"tcp:{tcp['error']}")
    if tls and not tls.get("tls_ok"):
        symptoms.append(f"TLS fail: {tls.get('tls_error')}")
    return symptoms

def test_config(cfg: dict) -> dict:
    host = cfg.get("host", "")
    port = cfg.get("port", 443)
    sni = cfg.get("sni", "") or cfg.get("params", {}).get("sni", "") or host
    tcp = tcp_connect(host, port)
    tls = tls_check(host, port, sni) if (tcp["tcp_ok"] and port in TLS_PORTS) else {}
    passed = tcp["tcp_ok"]
    symptoms = analyze_dpi(tcp, tls)
    cfg["tcp_test"] = {
        "passed": passed, "tcp": tcp, "tls": tls,
        "dpi_symptoms": symptoms, "tested_at": datetime.now(timezone.utc).isoformat()
    }
    return cfg

def run(input_file: str, output_dir: str):
    in_path = Path(input_file)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.start("tcp_test", f"TCP/TLS тест {input_file}")

    with open(in_path, 'r', encoding='utf-8') as f:
        configs = json.load(f)

    passed, blocked = [], []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(test_config, cfg): cfg for cfg in configs}
        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            ts = result.get("tcp_test", {})
            host = result.get("host", "?")
            port = result.get("port", "?")
            status = "PASS" if ts.get("passed") else "FAIL"
            symptoms = ", ".join(ts.get("dpi_symptoms", [])) or "OK"
            logger.info("tcp_test", f"[{i+1}/{len(configs)}] {host}:{port} -> {status} | {symptoms}")
            (passed if ts.get("passed") else blocked).append(result)

    logger.ok("tcp_test", f"Пройдено: {len(passed)} | Заблокировано: {len(blocked)}")

    with open(out_dir / "alive.txt", 'w', encoding='utf-8') as f:
        for cfg in passed:
            f.write(json.dumps(cfg, ensure_ascii=False) + "\n")

    with open(out_dir / "garbage.txt", 'w', encoding='utf-8') as f:
        f.write(f"# TCP-TEST {datetime.now(timezone.utc).isoformat()} | Blocked: {len(blocked)}\n\n")
        for cfg in blocked:
            s = ", ".join(cfg.get("tcp_test", {}).get("dpi_symptoms", []))
            f.write(f"# BLOCKED | {s}\n{json.dumps(cfg, ensure_ascii=False)}\n")

    with open(out_dir / "tcp_passed.json", 'w', encoding='utf-8') as f:
        json.dump(passed, f, ensure_ascii=False, indent=2)

    logger.save()
    return passed, blocked

if __name__ == "__main__":
    i = sys.argv[1] if len(sys.argv) > 1 else "output/deduped.json"
    o = sys.argv[2] if len(sys.argv) > 2 else "output"
    run(i, o)
