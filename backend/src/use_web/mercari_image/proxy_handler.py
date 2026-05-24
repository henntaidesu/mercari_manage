# -*- coding: utf-8 -*-
"""Mercari 图片代理处理器：由后端拉取煤炉 CDN 图片，再返回给前端。

设计要点：
- 部分用户网络环境无法直连 static.mercdn.net 等煤炉 CDN，由后端代拉图片。
- 仅允许白名单域名，防止被滥用为通用 SSRF 代理。
- 拉取到的图片缓存到 backend/imges/_mercari_cache/，以 SHA1(url) 为文件名。
"""
import asyncio
import hashlib
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional, Tuple

from fastapi import HTTPException
from fastapi.responses import FileResponse

from ..image_storage import get_image_root

_ALLOWED_HOST_SUFFIXES = (
    ".mercdn.net",
    ".mercari.com",
    ".mercari-shops.com",
    ".mercariapp.com",
)

_ALLOWED_EXACT_HOSTS = {
    "mercdn.net",
    "mercari.com",
    "mercari-shops.com",
}

_MAX_BYTES = 20 * 1024 * 1024  # 20MB
_FETCH_TIMEOUT = 15.0  # seconds

_EXT_BY_CONTENT_TYPE = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/avif": "avif",
}


def _cache_dir() -> str:
    d = os.path.join(get_image_root(), "_mercari_cache")
    os.makedirs(d, exist_ok=True)
    return d


def _host_allowed(host: str) -> bool:
    h = (host or "").lower().split(":", 1)[0]
    if not h:
        return False
    if h in _ALLOWED_EXACT_HOSTS:
        return True
    return any(h.endswith(suf) for suf in _ALLOWED_HOST_SUFFIXES)


def _ext_from_url_or_type(url: str, content_type: Optional[str]) -> str:
    ct = (content_type or "").split(";", 1)[0].strip().lower()
    if ct in _EXT_BY_CONTENT_TYPE:
        return _EXT_BY_CONTENT_TYPE[ct]
    path = urllib.parse.urlsplit(url).path.lower()
    for suf in ("jpg", "jpeg", "png", "webp", "gif", "avif"):
        if path.endswith("." + suf):
            return "jpg" if suf == "jpeg" else suf
    return "jpg"


def _media_type_from_ext(ext: str) -> str:
    return {
        "jpg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
        "avif": "image/avif",
    }.get(ext, "image/jpeg")


def _find_cached(url_hash: str) -> Optional[Tuple[str, str]]:
    d = _cache_dir()
    for ext in ("jpg", "png", "webp", "gif", "avif"):
        p = os.path.join(d, f"{url_hash}.{ext}")
        if os.path.exists(p):
            return p, ext
    return None


def _download(url: str) -> Tuple[bytes, Optional[str]]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
            ),
            "Accept": "image/avif,image/webp,image/png,image/jpeg,image/*,*/*;q=0.8",
            "Referer": "https://jp.mercari.com/",
        },
    )
    with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
        ct = resp.headers.get("Content-Type")
        data = resp.read(_MAX_BYTES + 1)
        if len(data) > _MAX_BYTES:
            raise HTTPException(status_code=502, detail="图片体积过大")
        return data, ct


async def proxy_mercari_image(u: str):
    """
    GET /mercariV2/src/use_web/mercari-image?u=<encoded mercari CDN url>

    - 仅允许煤炉 CDN 域名
    - 命中本地缓存直接返回，否则后端代下载、缓存到 imges/_mercari_cache/。
    """
    raw = (u or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="缺少 u 参数")

    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="非法 URL")
    if not _host_allowed(parsed.hostname or ""):
        raise HTTPException(status_code=403, detail="不允许的域名")

    url_hash = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    hit = _find_cached(url_hash)
    if hit is not None:
        path, ext = hit
        return FileResponse(
            path,
            media_type=_media_type_from_ext(ext),
            headers={"Cache-Control": "public, max-age=2592000"},
        )

    try:
        data, content_type = await asyncio.to_thread(_download, raw)
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"煤炉返回 {e.code}")
    except urllib.error.URLError as e:
        raise HTTPException(status_code=502, detail=f"拉取失败: {e.reason}")
    except TimeoutError:
        raise HTTPException(status_code=504, detail="拉取超时")
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"拉取失败: {e}")

    ext = _ext_from_url_or_type(raw, content_type)
    out_path = os.path.join(_cache_dir(), f"{url_hash}.{ext}")
    tmp_path = out_path + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(data)
    os.replace(tmp_path, out_path)

    return FileResponse(
        out_path,
        media_type=_media_type_from_ext(ext),
        headers={"Cache-Control": "public, max-age=2592000"},
    )
