from __future__ import annotations

import hashlib
import math
from typing import List


DIM = 768


def _hash_token(token: str) -> int:
    return int(hashlib.sha1(token.encode("utf-8")).hexdigest(), 16)


def embed_text(text: str) -> List[float]:
    """Deterministic local embedding via hashed bag-of-words.

    Not state-of-the-art, but local and sufficient for cache/Qdrant tests.
    """
    vec = [0.0] * DIM
    tokens = [t for t in text.lower().split() if t]
    if not tokens:
        return vec
    for t in tokens:
        h = _hash_token(t)
        idx = h % DIM
        vec[idx] += 1.0
    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]
