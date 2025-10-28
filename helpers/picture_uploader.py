"""
Helper functions for uploading ad pictures via the marketplace API.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Optional


__all__ = [
    "upload_ad_picture",
    "_build_upload_params",
    "_upload_picture_raw",
    "_upload_picture_multipart",
    "_extract_picture_id",
]


def _build_upload_params(
    api_version: str,
    access_token: Optional[str],
    fcm_token: Optional[str],
    new_version: bool,
) -> dict:
    params = {"api_version": api_version}
    if access_token:
        params["access_token"] = access_token
    if fcm_token:
        params["fcm_token"] = fcm_token
    if new_version:
        params["new_version"] = "true"
    return params


def _upload_picture_raw(api_client, endpoint: str, file_path: Path, params: dict):
    url = f"{api_client.base_url}{endpoint}"
    filename = file_path.name
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    with file_path.open("rb") as fh:
        resp = api_client.session.post(
            url,
            params=params,
            data=fh,
            headers={
                "Content-Type": mime,
                "Accept": "application/json",
            },
            timeout=90,
        )
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text}
    return {"status_code": resp.status_code, "json": body}


def _upload_picture_multipart(api_client, endpoint: str, file_path: Path, params: dict):
    url = f"{api_client.base_url}{endpoint}"
    filename = file_path.name
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    last = None
    for field_name in ("file", "pictures[]"):
        try:
            with file_path.open("rb") as fh:
                files = {field_name: (filename, fh, mime)}
                resp = api_client.session.post(
                    url,
                    params=params,
                    files=files,
                    headers={"Accept": "application/json"},
                    timeout=90,
                )
            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.text}
            last = {"status_code": resp.status_code, "json": body}
            if 200 <= resp.status_code < 300:
                return last
        except Exception as exc:
            last = {"status_code": 0, "json": {"error": str(exc)}}
    return last


def _extract_picture_id(payload: dict) -> Optional[int]:
    if not isinstance(payload, dict):
        return None
    for key in ("picture_id", "id"):
        value = payload.get(key)
        if value is not None:
            try:
                return int(value)
            except Exception:
                pass
    for key in ("picture", "image", "photo"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            for inner in ("picture_id", "id"):
                value = nested.get(inner)
                if value is not None:
                    try:
                        return int(value)
                    except Exception:
                        pass
    for arr_key in ("pictures", "data", "items", "results"):
        arr = payload.get(arr_key)
        if isinstance(arr, list) and arr:
            first = arr[0]
            if isinstance(first, dict):
                for inner in ("picture_id", "id"):
                    value = first.get(inner)
                    if value is not None:
                        try:
                            return int(value)
                        except Exception:
                            pass
    return None


def upload_ad_picture(
    api_client,
    file_path: str,
    api_version: str = "18",
    access_token: Optional[str] = None,
    fcm_token: Optional[str] = None,
    new_version: bool = True,
) -> int:
    """
    Upload a local image and return its picture_id.
    Mirrors the UI behaviour: tries the raw upload first, then multipart.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Picture file not found: {file_path}")

    params = _build_upload_params(api_version, access_token, fcm_token, new_version)

    endpoints = [
        "/pictures/multi_file_uploader/ad_listing.json",
        "/multi_file_uploader/ad_listing.json",
    ]

    last = None
    for endpoint in endpoints:
        raw = _upload_picture_raw(api_client, endpoint, path, params)
        last = raw
        if 200 <= raw["status_code"] < 300:
            pic_id = _extract_picture_id(raw.get("json") or {})
            if pic_id is not None:
                return pic_id

        multipart = _upload_picture_multipart(api_client, endpoint, path, params)
        last = multipart
        if multipart and 200 <= multipart["status_code"] < 300:
            pic_id = _extract_picture_id(multipart.get("json") or {})
            if pic_id is not None:
                return pic_id

    raise AssertionError(
        f"Picture upload failed or no picture_id found. "
        f"Last status={last['status_code'] if last else 'n/a'} body={last and last.get('json')}"
    )

