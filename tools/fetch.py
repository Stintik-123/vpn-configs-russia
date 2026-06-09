#!/usr/bin/env python3
"""fetch.py - small utility that exposes fetch function and a CLI for one-off downloads.
This file is backwards compatible with previous behavior but improved error handling.
"""
import asyncio
import aiohttp
import base64
import os
import json
import logging
from typing import List

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
TIMEOUT = int(os.getenv("FETCH_TIMEOUT", "10"))


async def fetch(session: aiohttp.ClientSession, url: str) -> List[str]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as resp:
            if resp.status != 200:
                logging.warning("%s -> HTTP %s", url, resp.status)
                return []
            text = await resp.text()
            s = text.strip()
            # Try base64 decode
            if s and all(c.isalnum() or c in "+/=\n\r" for c in s.replace('\n','')) and len(s) % 4 == 0:
                try:
                    decoded = base64.b64decode(s + "==").decode("utf-8", errors="ignore")
                    return [l.strip() for l in decoded.splitlines() if l.strip()]
                except Exception:
                    pass
            return [l.strip() for l in text.splitlines() if l.strip()]
    except Exception as e:
        logging.warning("%s -> error: %s", url, e)
        return []


async def main():
    urls_raw = os.getenv("SOURCES_LIST")
    if not urls_raw:
        print("Set SOURCES_LIST env var to a JSON array of URLs")
        return
    urls = json.loads(urls_raw)
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[fetch(session, u) for u in urls])
    raw = []
    for r in results:
        raw.extend(r)
    with open("raw_configs.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(raw))
    print(f"Wrote {len(raw)} lines to raw_configs.txt")


if __name__ == "__main__":
    asyncio.run(main())
