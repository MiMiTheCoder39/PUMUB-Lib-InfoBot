"""Cloudflare R2 storage helpers.

R2 is optional: when R2_ENABLED is false or credentials are absent, callers
continue to use the existing local library storage paths.  Object keys use
small fixed prefixes (books/, covers/, profiles/, qrcodes/) and filenames are
validated by the caller before they reach this module.
"""
from __future__ import annotations

import mimetypes
import os
from typing import BinaryIO

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from flask import current_app


class R2StorageError(RuntimeError):
    """Raised when an R2 operation cannot be completed."""


def is_enabled() -> bool:
    """Return True only when R2 is explicitly enabled and configured."""
    return bool(
        current_app.config.get("R2_ENABLED")
        and current_app.config.get("R2_BUCKET_NAME")
        and current_app.config.get("R2_ACCESS_KEY_ID")
        and current_app.config.get("R2_SECRET_ACCESS_KEY")
        and current_app.config.get("R2_ENDPOINT")
    )


def _client():
    return boto3.client(
        "s3",
        endpoint_url=current_app.config["R2_ENDPOINT"],
        aws_access_key_id=current_app.config["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=current_app.config["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def object_key(prefix: str, filename: str) -> str:
    prefix = (prefix or "").strip("/")
    filename = os.path.basename(filename or "")
    return f"{prefix}/{filename}" if prefix else filename


def upload_fileobj(fileobj: BinaryIO, prefix: str, filename: str, content_type: str | None = None) -> None:
    key = object_key(prefix, filename)
    try:
        extra = {"ContentType": content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"}
        _client().upload_fileobj(
            fileobj,
            current_app.config["R2_BUCKET_NAME"],
            key,
            ExtraArgs=extra,
        )
    except (BotoCoreError, ClientError) as exc:
        raise R2StorageError(f"R2 upload failed for {key}") from exc


def upload_path(path: str, prefix: str, filename: str | None = None) -> None:
    name = filename or os.path.basename(path)
    with open(path, "rb") as fileobj:
        upload_fileobj(fileobj, prefix, name)


def download_bytes(prefix: str, filename: str) -> tuple[bytes, str | None]:
    key = object_key(prefix, filename)
    try:
        response = _client().get_object(Bucket=current_app.config["R2_BUCKET_NAME"], Key=key)
        body = response["Body"].read()
        return body, response.get("ContentType")
    except (BotoCoreError, ClientError) as exc:
        raise R2StorageError(f"R2 download failed for {key}") from exc


def delete_object(prefix: str, filename: str) -> None:
    key = object_key(prefix, filename)
    try:
        _client().delete_object(Bucket=current_app.config["R2_BUCKET_NAME"], Key=key)
    except (BotoCoreError, ClientError) as exc:
        raise R2StorageError(f"R2 delete failed for {key}") from exc
