"""Upload the existing LIBRARY_STORAGE folders to Cloudflare R2.

Run locally from PowerShell after installing the project's requirements. The
script prompts for credentials when they are not already environment values;
it never prints the secret key. Existing object keys are overwritten so a
re-run is safe for the same local files.
"""
from __future__ import annotations

import argparse
import getpass
import mimetypes
import os
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

FOLDERS = ("books", "covers", "profiles", "qrcodes")


def _value(name: str, prompt: str, secret: bool = False) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    return (getpass.getpass(prompt) if secret else input(prompt)).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload LIBRARY_STORAGE to Cloudflare R2")
    parser.add_argument(
        "--root",
        default=os.environ.get("LIBRARY_STORAGE_ROOT", r"D:\PU-MAUBIN\LIBRARY_STORAGE"),
        help="Local LIBRARY_STORAGE directory",
    )
    parser.add_argument("--bucket", default=os.environ.get("R2_BUCKET_NAME", "pumub-library-assets"))
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Storage root does not exist: {root}")

    account_id = _value("R2_ACCOUNT_ID", "Cloudflare Account ID: ")
    access_key = _value("R2_ACCESS_KEY_ID", "R2 Access Key ID: ")
    secret_key = _value("R2_SECRET_ACCESS_KEY", "R2 Secret Access Key: ", secret=True)
    endpoint = os.environ.get("R2_ENDPOINT", "").strip() or f"https://{account_id}.r2.cloudflarestorage.com"

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )

    total = 0
    for folder_name in FOLDERS:
        folder = root / folder_name
        if not folder.is_dir():
            print(f"SKIP {folder_name}/ (folder not found)")
            continue
        for path in sorted(p for p in folder.rglob("*") if p.is_file()):
            relative = path.relative_to(folder).as_posix()
            key = f"{folder_name}/{relative}"
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            try:
                s3.upload_file(
                    str(path),
                    args.bucket,
                    key,
                    ExtraArgs={"ContentType": content_type},
                )
            except (BotoCoreError, ClientError) as exc:
                raise SystemExit(f"Upload failed for {key}: {exc}") from exc
            total += 1
            print(f"UPLOADED {total}: {key}")

    print(f"Completed: {total} files uploaded to {args.bucket}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
