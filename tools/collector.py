#!/usr/bin/env python3
"""collector.py - fetch lists from remote sources with retries, concurrency and basic normalization.
Writes raw lists to data/raw.txt and raw.txt for backward compatibility.
"""
import asyncio
import aiohttp
import base64
import os
import json
import logging
from typing import List

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

CONCURRENCY = int(os.getenv("COLLECT_CONCURRENCY", "20"))
TIMEOUT = int(os.getenv("COLLECT_TIMEOUT", "10"))
RETRIES = int(os.getenv("COLLECT_RETRIES", "2"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def fetch_once(session: aiohttp.ClientSession, url: str) -> List[str]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as resp:
            if resp.status != 200:
                logging.warning("%s -> HTTP %s", url, resp.status)
                return []
            text = await resp.text()
            # Try base64 decode if it looks like base64
            s = text.strip()
            lines: List[str] = []
            if s and all(c.isalnum() or c in "+/=\n\r" for c in s.replace('\n','')) and len(s) % 4 == 0:
                try:
                    decoded = base64.b64decode(s + "==").decode("utf-8", errors="ignore")
                    lines = [l.strip() for l in decoded.splitlines() if l.strip()]
                    logging.info("%s -> decoded base64 (%d lines)", url, len(lines))
                    return lines
                except Exception:
                    pass
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            logging.info("%s -> fetched (%d lines)", url, len(lines))
            return lines
    except Exception as e:
        logging.warning("%s -> error: %s", url, e)
        return []


async def fetch_with_retries(session: aiohttp.ClientSession, url: str) -> List[str]:
    for i in range(RETRIES + 1):
        res = await fetch_once(session, url)
        if res:
            return res
        logging.debug("retry %d for %s", i + 1, url)
        await asyncio.sleep(0.5)
    return []


async def main():
    sources_raw = os.getenv("SOURCES_LIST")
    urls = []
    if sources_raw:
        try:
            urls = json.loads(sources_raw)
            if not isinstance(urls, list):
                logging.error("SOURCES_LIST is not a JSON array")
                return
        except Exception:
            logging.exception("Failed to parse SOURCES_LIST")
            return
    else:
        # fallback to config/sources.json if exists
        cfg = os.path.join("config", "sources.json")
        if os.path.exists(cfg):
            with open(cfg, "r", encoding="utf-8") as f:
                try:
                    urls = json.load(f)
                except Exception:
                    logging.exception("Failed to parse config/sources.json")
                    return
    if not urls:
        logging.info("No source URLs provided")
        return

    connector = aiohttp.TCPConnector(limit_per_host=10)
    sem = asyncio.Semaphore(CONCURRENCY)

    async with aiohttp.ClientSession(connector=connector) as session:
        async def limited_fetch(u):
            async with sem:
                return await fetch_with_retries(session, u)

        results = await asyncio.gather(*[limited_fetch(u) for u in urls], return_exceptions=False)

    raw = []
    for r in results:
        raw.extend(r)

    # normalize whitespace and remove empty
    raw = [l.strip() for l in raw if l and l.strip()]
    # write outputs for backward compatibility
    out1 = os.path.join(OUTPUT_DIR, "raw.txt")
    out2 = "raw.txt"
    with open(out1, "w", encoding="utf-8") as f:
        f.write("\n".join(raw))
    with open(out2, "w", encoding="utf-8") as f:
        f.write("\n".join(raw))
    logging.info("Wrote %d raw entries to %s and %s", len(raw), out1, out2)


if __name__ == "__main__":
    asyncio.run(main())
