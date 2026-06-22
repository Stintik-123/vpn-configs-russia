#!/usr/bin/env python3
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

class Logger:
    def __init__(self, log_dir: str = "output"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "pipeline.log"
        self.entries = []

    def log(self, level: str, module: str, message: str, **kwargs):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "module": module,
            "message": message,
            **kwargs
        }
        self.entries.append(entry)
        prefix = f"[{level}]"
        stream = sys.stderr if level == "ERROR" else sys.stdout
        print(f"  {prefix} [{module}] {message}", file=stream)

    def info(self, module: str, message: str, **kwargs):
        self.log("INFO", module, message, **kwargs)

    def warn(self, module: str, message: str, **kwargs):
        self.log("WARN", module, message, **kwargs)

    def error(self, module: str, message: str, **kwargs):
        self.log("ERROR", module, message, **kwargs)

    def ok(self, module: str, message: str, **kwargs):
        self.log("OK", module, message, **kwargs)

    def start(self, module: str, message: str, **kwargs):
        self.log("START", module, message, **kwargs)

    def done(self, module: str, message: str, **kwargs):
        self.log("DONE", module, message, **kwargs)

    def debug(self, module: str, message: str, **kwargs):
        self.log("DEBUG", module, message, **kwargs)

    def save(self):
        with open(self.log_file, 'w', encoding='utf-8') as f:
            for entry in self.entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_summary(self) -> dict:
        errors = [e for e in self.entries if e["level"] == "ERROR"]
        return {
            "total": len(self.entries),
            "errors": len(errors),
            "last_error": errors[-1]["message"] if errors else None
        }
