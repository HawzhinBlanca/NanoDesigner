from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def health():
    return {"ok": True}


import time

# Track server start time
_start_time = time.time()
_request_count = 0

@router.get("/metrics")
def metrics():
    global _request_count
    _request_count += 1
    uptime = time.time() - _start_time
    return {
        "uptime_seconds": round(uptime, 2),
        "total_requests": _request_count,
        "p95_latency_ms": 0,
        "image_success_rate": 0.0
    }
