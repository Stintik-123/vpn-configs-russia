import re
from urllib.parse import urlparse, parse_qs


JUNK_PATTERNS = [
    r'insecure', r'unsecurity', r'anycast',
    r'test', r'expire', r'осталось', r'подписка',
    r'allowinsecure=true', r'skipcertverify=true'
]


def normalize_params(config):
    try:
        parsed = urlparse(config)
        params = parse_qs(parsed.query, keep_blank_values=True)
        sorted_params = sorted(params.items())
        new_query = "&".join(f"{k}={v[0]}" for k, v in sorted_params)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"
    except Exception:
        return config


def get_dedup_key(config):
    try:
        parsed = urlparse(config)
        params = parse_qs(parsed.query)
        security = params.get("security", [""])[0]
        if security != "tls":
            return None
        return "|".join([
            parsed.scheme, parsed.hostname or "", str(parsed.port or ""),
            params.get("type", [""])[0], security,
            params.get("sni", [""])[0], params.get("fp", [""])[0]
        ])
    except Exception:
        return config


def main():
    with open("raw.txt", "r", encoding="utf-8") as f:
        raw = [l.strip() for l in f if l.strip()]
    filtered = [c for c in raw if not any(re.search(p, c.lower()) for p in JUNK_PATTERNS)]
    seen = set()
    unique = []
    for c in filtered:
        normalized = normalize_params(c)
        key = get_dedup_key(normalized)
        if key and key not in seen:
            seen.add(key)
            unique.append(normalized)
    with open("cleaned.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(unique))


if __name__ == "__main__":
    main()
