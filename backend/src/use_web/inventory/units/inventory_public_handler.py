# -*- coding: utf-8 -*-
"""库存公开端点业务处理器：无需认证（如缩略图）。"""
import os

from fastapi import HTTPException
from fastapi.responses import FileResponse
from PIL import Image, ImageOps

from ....image_storage import get_image_root


def get_image_thumb(path: str, size: int = 300):
    """
    按需生成缩略图并缓存到磁盘。
    - path: /imges/xxx.jpg 格式
    - size: 最长边像素（默认 300，列表小图用 200 即可）
    """
    clean = (path or "").strip()
    if not clean.startswith("/imges/") or ".." in clean:
        raise HTTPException(status_code=400, detail="无效路径")
    size = max(50, min(size, 1200))

    filename = clean.split("/imges/", 1)[1].strip("/")
    orig_abs = os.path.join(get_image_root(), filename)
    if not os.path.exists(orig_abs):
        raise HTTPException(status_code=404, detail="图片不存在")

    # 缩略图缓存目录
    thumb_dir = os.path.join(get_image_root(), "_thumbs")
    os.makedirs(thumb_dir, exist_ok=True)

    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    # 将路径分隔符统一替换，避免子目录名带入文件名
    safe_stem = stem.replace("/", "_").replace("\\", "_")
    thumb_filename = f"{safe_stem}_s{size}.jpg"
    thumb_abs = os.path.join(thumb_dir, thumb_filename)

    if not os.path.exists(thumb_abs):
        try:
            img = Image.open(orig_abs)
            # 先应用 EXIF 方向信息，避免手机竖拍图片在缩略图中出现旋转偏差
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")
            w, h = img.size
            if max(w, h) > size:
                scale = size / max(w, h)
                img = img.resize(
                    (int(w * scale), int(h * scale)),
                    Image.Resampling.LANCZOS,
                )
            img.save(thumb_abs, "JPEG", quality=75, optimize=True)
        except Exception:
            # PIL 无法处理时直接返回原图
            return FileResponse(orig_abs)

    return FileResponse(thumb_abs, media_type="image/jpeg")
