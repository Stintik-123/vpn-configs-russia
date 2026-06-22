#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from logger import Logger

logger = Logger()

def get_key(cfg: dict) -> str:
    ctype = cfg.get("type", "")
    if ctype == "hysteria":
        return f"{cfg['host']}:{cfg['port']}:{cfg.get('auth','')}:{cfg.get('obfs_password','')}"
    return f"{cfg['host']}:{cfg['port']}:{cfg.get('uuid','')}:{cfg.get('password','')}"

def run(input_file: str, output_dir: str):
    in_path = Path(input_file)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.start("dedup", f"Дедупликация {input_file}")

    with open(in_path, 'r', encoding='utf-8') as f:
        configs = json.load(f)

    seen, unique, dups = set(), [], []
    for cfg in configs:
        key = get_key(cfg)
        if key not in seen:
            seen.add(key)
            unique.append(cfg)
        else:
            dups.append(cfg)

    logger.ok("dedup", f"Вход: {len(configs)} -> Уник: {len(unique)} | Дублей: {len(dups)}")

    with open(out_dir / "deduped.json", 'w', encoding='utf-8') as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    if dups:
        with open(out_dir / "garbage.txt", 'a', encoding='utf-8') as f:
            for d in dups:
                f.write(f"# DUPLICATE\n{json.dumps(d, ensure_ascii=False)}\n")

    logger.save()
    return unique

if __name__ == "__main__":
    i = sys.argv[1] if len(sys.argv) > 1 else "output/normalized.json"
    o = sys.argv[2] if len(sys.argv) > 2 else "output"
    run(i, o)
