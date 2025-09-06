from __future__ import annotations

import base64
import os
from typing import List, Tuple
import json
import os

import httpx
from urllib.parse import urlparse

from ..core.config import settings

from .openrouter import call_openrouter, call_task, call_openrouter_images
from .langfuse import Trace


def _extract_images_from_openrouter(resp: dict) -> List[Tuple[bytes, str]]:
    images: List[Tuple[bytes, str]] = []
    # Try common patterns: choices[].message.content (array of parts) with type=image_url/base64
    choices = resp.get("choices", [])
    for ch in choices:
        message = ch.get("message", {})
        content = message.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "image_url" and "url" in part:
                        url = part["url"]
                        # SSRF guard: only https and allowlist hosts if provided
                        _ssrf_guard(url)
                        with httpx.Client(timeout=30.0) as client:
                            r = client.get(url)
                            r.raise_for_status()
                            images.append((r.content, _infer_format_from_content_type(r.headers.get("content-type"))))
                    elif part.get("type") == "image_base64" and "data" in part:
                        data = base64.b64decode(part["data"])  # assume png
                        images.append((data, "png"))
        # Some providers return message["images"]= [ {"b64":..., "format":"png"} ]
        imgs = message.get("images")
        if isinstance(imgs, list):
            for it in imgs:
                b64 = it.get("b64") or it.get("data")
                fmt = it.get("format") or "png"
                if b64:
                    images.append((base64.b64decode(b64), fmt))
    return images


def _infer_format_from_content_type(ct: str | None) -> str:
    if not ct:
        return "png"
    if "jpeg" in ct:
        return "jpg"
    if "webp" in ct:
        return "webp"
    return "png"


def _ssrf_guard(url: str) -> None:
    u = urlparse(url)
    if u.scheme != "https":
        raise ValueError("Blocked non-HTTPS image URL")
    allow = (settings.__dict__.get("image_fetch_allow_hosts") or os.getenv("IMAGE_FETCH_ALLOW_HOSTS"))
    if allow:
        hosts = {h.strip() for h in allow.split(",") if h.strip()}
        if u.hostname not in hosts:
            raise ValueError("Blocked external host")


def generate_images(prompt: str, n: int = 1, size: str = "1024x1024", trace: Trace | None = None) -> List[Tuple[bytes, str]]:
    # Try chat-completions route first
    resp = None
    try:
        resp = call_task(
            "image",
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            trace=trace,
            n=n,
            size=size,
        )
    except Exception:
        resp = None
    images: List[Tuple[bytes, str]] = []
    if resp is not None:
        try:
            with open("/tmp/openrouter_image_resp.json", "w", encoding="utf-8") as f:
                json.dump(resp, f)
        except Exception:
            pass
        images = _extract_images_from_openrouter(resp)
    # Fallback to Images API if none found or chat-completions failed
    if not images:
        raw = call_openrouter_images("openrouter/gemini-2.5-flash-image", prompt, n=n, size=size)
        try:
            with open("/tmp/openrouter_images_resp.json", "w", encoding="utf-8") as f:
                json.dump(raw, f)
        except Exception:
            pass
        data = raw.get("data") or []
        out: List[Tuple[bytes, str]] = []
        for item in data:
            b64 = item.get("b64_json") or item.get("b64") or item.get("data")
            fmt = item.get("format") or "png"
            if b64:
                out.append((base64.b64decode(b64), fmt))
        images = out
    if not images:
        raise RuntimeError("No images returned from model")
    return images[:n]
