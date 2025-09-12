from __future__ import annotations

import io
import os
import time
from typing import Optional

import boto3
from botocore.client import Config

from ..core.config import settings


def _s3_client():
    # Allow local S3-compatible endpoint (e.g., MinIO) via S3_ENDPOINT_URL
    endpoint_url = (
        os.getenv("S3_ENDPOINT_URL")
        or (f"https://{settings.r2_account_id}.r2.cloudflarestorage.com" if settings.r2_account_id else None)
    )
    if not (settings.r2_access_key_id and settings.r2_secret_access_key and endpoint_url):
        raise RuntimeError("S3/R2 credentials are not configured")
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def put_object(key: str, data: bytes, content_type: str = "image/png") -> None:
    s3 = _s3_client()
    s3.put_object(Bucket=settings.r2_bucket, Key=key, Body=io.BytesIO(data), ContentType=content_type)


def presign_get_url(key: str, expires_seconds: int = 900) -> str:
    s3 = _s3_client()
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": settings.r2_bucket, "Key": key},
        ExpiresIn=expires_seconds,
    )


def signed_public_url(key: str, expires_seconds: int = 900) -> str:
    # If using a Cloudflare Worker signer, this is where you'd call it.
    # Otherwise, return S3-style presigned URL which works for R2.
    return presign_get_url(key, expires_seconds)


def get_object(key: str) -> Optional[bytes]:
    """
    Retrieve an object from R2/S3 storage.
    
    Args:
        key: Object key
        
    Returns:
        Object bytes or None if not found
    """
    try:
        s3 = _s3_client()
        response = s3.get_object(Bucket=settings.r2_bucket, Key=key)
        return response["Body"].read()
    except Exception:
        return None


def delete_object(key: str) -> bool:
    """
    Delete an object from R2/S3 storage.
    
    Args:
        key: Object key
        
    Returns:
        True if deleted, False otherwise
    """
    try:
        s3 = _s3_client()
        s3.delete_object(Bucket=settings.r2_bucket, Key=key)
        return True
    except Exception:
        return False


def list_objects(prefix: str = "", max_keys: int = 100) -> list:
    """
    List objects in R2/S3 storage.
    
    Args:
        prefix: Prefix to filter objects
        max_keys: Maximum number of keys to return
        
    Returns:
        List of object keys
    """
    try:
        s3 = _s3_client()
        response = s3.list_objects_v2(
            Bucket=settings.r2_bucket,
            Prefix=prefix,
            MaxKeys=max_keys
        )
        return [obj["Key"] for obj in response.get("Contents", [])]
    except Exception:
        return []
