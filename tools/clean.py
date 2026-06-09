#!/usr/bin/env python3
"""clean.py - deduplicate and filter raw configuration lines.
Improved normalization, better junk filtering and outputs.
"""
import re
import argparse
from urllib.parse import urlparse, parse_qs, urlencode
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

JUNK_PATTERNS = [
    r'insecure', r'unsecurity', r'anycast', r'\btest\b', r'expire', r'осталось', r'подписка',
    r'allowinsecure=true', r'skipcertverify=true', r'temp', r'example', r'test-server'
]
JUNK_RE = re.compile("|".join(f"(?:{p})" for p in JUNK_PATTERNS), flags=re.IGNORECASE)


def normalize_params(config: str) -> str:
    try:
        parsed = urlparse(config)
        if not parsed.scheme:
            return config.strip()
        params = parse_qs(parsed.query, keep_blank_values=True)
        # Sort params to make stable key; flatten single values
        items = sorted((k, v[0] if isinstance(v, list) and v else "") for k, v in params.items())
        if items:
            new_query = urlencode(items)
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"
        else:
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except Exception:
        return config.strip()


def get_dedup_key(config: str) -> str:
    try:
        parsed = urlparse(config)
        params = parse_qs(parsed.query)
        security = params.get("security", [""])[0]
        # accept tls or xtls as secure variants
        if security not in ("tls", "xtls"):
            # still produce a key for other entries, but mark as nonsecure
            security = params.get("security", [""])[0]
        return "|".join([
            (parsed.scheme or ""), 
            (parsed.hostname or "").lower(),
            str(parsed.port or ""),
            params.get("type", [""])[0],
            security,
            params.get("sni", [""])[0],
            params.get("fp", [""])[0]
        ])
    except Exception:
        return config.strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="raw.txt")
    p.add_argument("--output", default="cleaned.txt")
    args = p.parse_args()

    if not os.path.exists(args.input):
        logging.error("Input file %s does not exist", args.input)
        return

    with open(args.input, "r", encoding="utf-8") as f:
        raw = [l.strip() for l in f if l.strip()]

    # Filter junk
    filtered = [c for c in raw if not JUNK_RE.search(c)]

    seen = set()
    unique = []
    for c in filtered:
        normalized = normalize_params(c)
        key = get_dedup_key(normalized)
        if key and key not in seen:
            seen.add(key)
            unique.append(normalized)

    # ensure data dir
    os.makedirs("data", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(unique))
    # also write to data/ for workflows that expect it
    with open(os.path.join("data", os.path.basename(args.output)), "w", encoding="utf-8") as f:
        f.write("\n".join(unique))

    logging.info("Wrote %d unique entries to %s", len(unique), args.output)


if __name__ == "__main__":
    main()
