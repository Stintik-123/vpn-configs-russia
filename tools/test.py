#!/usr/bin/env python3
"""test.py - improved testing of cleaned configs.
Performs TCP checks with configurable concurrency and timeouts, optional TLS handshake to validate SNI.
Outputs alive.txt and data/alive.txt and a JSON report with counts.
"""
import asyncio
import os
import json
import ssl
import logging
from urllib.parse import urlparse
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

CONCURRENCY = int(os.getenv("TEST_CONCURRENCY", "200"))
TIMEOUT_SHORT = float(os.getenv("TEST_TIMEOUT_SHORT", "3"))
TIMEOUT_LONG = float(os.getenv("TEST_TIMEOUT_LONG", "5"))
INPUT_FILE = os.getenv("INPUT_FILE", "cleaned.txt")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "alive.txt")


async def check_tcp(host: str, port: int, timeout: float) -> bool:
    try:
        fut = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(fut, timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception as e:
        logging.debug("TCP %s:%s -> %s", host, port, e)
        return False


async def check_tls(host: str, port: int, server_hostname: Optional[str], timeout: float) -> bool:
    try:
        ctx = ssl.create_default_context()
        # do not verify cert, we only want handshake to succeed
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        fut = asyncio.open_connection(host, port, ssl=ctx, server_hostname=server_hostname or host)
        reader, writer = await asyncio.wait_for(fut, timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception as e:
        logging.debug("TLS %s:%s (sni=%s) -> %s", host, port, server_hostname, e)
        return False


async def test_config(config: str) -> Optional[str]:
    try:
        parsed = urlparse(config)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme in ("https", "vless", "trojan") else 80)
        if not host or not port:
            return None
        # first quick tcp check
        ok = await check_tcp(host, port, TIMEOUT_SHORT)
        if not ok:
            return None
        await asyncio.sleep(0.2)
        # second longer check, prefer TLS handshake if security=tls/xtls
        params = dict([p.split("=", 1) if "=" in p else (p, "") for p in (parsed.query or "").split("&") if p])
        security = params.get("security") or None
        sni = params.get("sni") or None
        if security in ("tls", "xtls"):
            ok2 = await check_tls(host, port, sni, TIMEOUT_LONG)
        else:
            ok2 = await check_tcp(host, port, TIMEOUT_LONG)
        if ok2:
            return config
    except Exception:
        pass
    return None


async def main():
    if not os.path.exists(INPUT_FILE):
        logging.error("Input file %s not found", INPUT_FILE)
        return
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        configs = [l.strip() for l in f if l.strip()]

    sem = asyncio.Semaphore(CONCURRENCY)

    async def limited(c):
        async with sem:
            return await test_config(c)

    tasks = [limited(c) for c in configs]
    results = []
    for chunk_start in range(0, len(tasks), 500):
        chunk = tasks[chunk_start:chunk_start+500]
        results.extend(await asyncio.gather(*chunk))

    alive = [r for r in results if r]
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(alive))
    os.makedirs("data", exist_ok=True)
    with open(os.path.join("data", os.path.basename(OUTPUT_FILE)), "w", encoding="utf-8") as f:
        f.write("\n".join(alive))

    report = {"total": len(configs), "passed": len(alive)}
    with open(os.path.join("data", "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f)

    logging.info("Test complete: %d/%d alive", len(alive), len(configs))


if __name__ == "__main__":
    asyncio.run(main())
