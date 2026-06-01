import asyncio
import socket
from urllib.parse import urlparse


async def check_tcp(host, port, timeout):
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


async def test_config(config):
    try:
        parsed = urlparse(config)
        host = parsed.hostname
        port = parsed.port
        if not host or not port:
            return None
        pass1 = await check_tcp(host, port, 3)
        if not pass1:
            return None
        await asyncio.sleep(0.5)
        pass2 = await check_tcp(host, port, 5)
        if pass2:
            return config
    except Exception:
        pass
    return None


async def main():
    with open("cleaned_configs.txt", "r", encoding="utf-8") as f:
        configs = [l.strip() for l in f if l.strip()]

    sem = asyncio.Semaphore(200)

    async def limited(c):
        async with sem:
            return await test_config(c)

    results = await asyncio.gather(*[limited(c) for c in configs])
    alive = [r for r in results if r]

    with open("tcp_alive.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(alive))


if __name__ == "__main__":
    asyncio.run(main())
