#!/usr/bin/env python3
import asyncio
import aiohttp
import socket

GEO_SERVICES = [
    "http://ip-api.com/json/{ip}?fields=countryCode",
    "https://ipapi.co/{ip}/country/",
    "https://ipwhois.app/json/{ip}",
    "http://ip-api.com/json/{ip}?fields=countryCode",
]

async def fetch_country(session, url, ip):
    try:
        async with session.get(url.format(ip=ip), timeout=aiohttp.ClientTimeout(total=3)) as resp:
            if resp.status != 200:
                return None
            text = await resp.text()
            if "ip-api.com" in url or "ipwhois" in url:
                import json
                data = json.loads(text)
                return data.get("countryCode") or data.get("country_code")
            elif "ipapi.co" in url:
                return text.strip()
    except Exception:
        return None

async def get_country_code_async(ip: str) -> str:
    async with aiohttp.ClientSession() as session:
        for url in GEO_SERVICES:
            result = await fetch_country(session, url, ip)
            if result and len(result) == 2:
                return result.upper()
    return "UNKNOWN"

def get_country(host: str) -> str:
    try:
        ip = socket.gethostbyname(host)
        if ip.startswith("127.") or ip.startswith("10.") or ip.startswith("192.168."):
            return "LOCAL"
        return asyncio.run(get_country_code_async(ip))
    except Exception:
        return "UNKNOWN"
