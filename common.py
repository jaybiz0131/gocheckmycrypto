#!/usr/bin/env python3
"""common.py: shared helpers for the Crypto Cronkite pipeline stages."""

import json
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "out")
PROMPTS = os.path.join(HERE, "prompts")
CONFIG = os.path.join(HERE, "config.json")
UA = "CryptoCronkite/1.0 (+news pipeline)"


def gh(level, msg):
    """GitHub Actions annotation, also readable in a plain terminal."""
    print(f"::{level}::{msg}")


def load_config():
    return json.load(open(CONFIG, encoding="utf-8"))


def load_prompt(name, **subs):
    text = open(os.path.join(PROMPTS, name), encoding="utf-8").read()
    for k, v in subs.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def read_out(name):
    return json.load(open(os.path.join(OUT_DIR, name), encoding="utf-8"))


def write_out(name, obj):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    json.dump(obj, open(path, "w", encoding="utf-8"), indent=2)
    return path


def fetch_text(url, timeout=25):
    """Fetch a URL and return (http_status, plain_text_excerpt). Never raises; on failure
    returns (None, error string) so the verifier can treat unreachable as unconfirmed."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            code = r.getcode()
            body = r.read(200000).decode("utf-8", "replace")
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)).strip()
        return code, text
    except Exception as e:
        return None, f"fetch failed: {e}"
