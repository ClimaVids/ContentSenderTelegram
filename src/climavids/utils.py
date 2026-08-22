from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str) -> str:
    p = urlsplit(url.strip())
    clean = urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip('/'), '', ''))
    return clean


def fingerprint(title: str, url: str = '') -> str:
    text = re.sub(r'\W+', ' ', title.lower()).strip()
    base = f'{text}|{normalize_url(url)}'
    return hashlib.sha256(base.encode('utf-8')).hexdigest()[:24]


def tokens(text: str) -> set[str]:
    return {t for t in re.findall(r'[\w\u0600-\u06ff]+', text.lower()) if len(t) > 2}


def similarity(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)
