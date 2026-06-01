import re
from urllib.parse import urlparse, parse_qs


JUNK_PATTERNS = [
    r'insecure', r'unsecurity', r'anycast',
    r'test', r'expire', r'осталось', r'подписка',
    r'allowinsecure=true', r'skipcertverify=true'
]


def get_dedup_key(config):
    try:
        parsed = urlparse(config)
        params = parse_qs(parsed.query)
        return "|".join([
            parsed.scheme, parsed.hostname or "", str(parsed.port or ""),
            params.get("type", [""])[0], params.get("security", [""])[0],
            params.get("sni", [""])[0], params.get("fp", [""])[0]
        ])
    except Exception:
        return config


def main():
    with open("raw_configs.txt", "r", encoding="utf-8") as f:
        raw = [l.strip() for l in f if l.strip()]
    filtered = [c for c in raw if not any(re.search(p, c.lower()) for p in JUNK_PATTERNS)]
    seen = set()
    unique = []
    for c in filtered:
        key = get_dedup_key(c)
        if key not in seen:
            seen.add(key)
            unique.append(c)
    with open("cleaned_configs.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(unique))


if __name__ == "__main__":
    main()
