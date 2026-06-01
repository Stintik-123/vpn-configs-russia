import asyncio
import aiohttp
import base64
import os
import json


async def fetch(session, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return []
            text = await resp.text()
            try:
                decoded = base64.b64decode(text.strip() + "==").decode("utf-8", errors="ignore")
                return [l.strip() for l in decoded.split("\n") if l.strip()]
            except Exception:
                return [l.strip() for l in text.split("\n") if l.strip()]
    except Exception:
        return []


async def main():
    sources_raw = os.getenv("SOURCES_LIST")
    if not sources_raw:
        return
    urls = json.loads(sources_raw)
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[fetch(session, u) for u in urls])
    raw = []
    for r in results:
        raw.extend(r)
    with open("raw_configs.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(raw))


if __name__ == "__main__":
    asyncio.run(main())
