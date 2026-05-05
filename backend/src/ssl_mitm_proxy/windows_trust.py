# -*- coding: utf-8 -*-
"""Windows：将 mitmproxy 根证书自动导入当前用户「受信任的根证书颁发机构」（无需管理员）。"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict

log = logging.getLogger(__name__)

# 供 /api/ssl-mitm/status 展示最近一次自动导入结果
last_windows_trust_result: Dict[str, Any] = {}


def _certutil_exe() -> str:
    sys_root = os.environ.get("SystemRoot", r"C:\Windows")
    built_in = os.path.join(sys_root, "System32", "certutil.exe")
    if os.path.isfile(built_in):
        return built_in
    w = shutil.which("certutil")
    return w or "certutil"


def _run_certutil_add_user_root(cert_path: str) -> subprocess.CompletedProcess[str]:
    certutil = _certutil_exe()
    kw: Dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "timeout": 90,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if sys.platform == "win32":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if flags:
            kw["creationflags"] = flags
    return subprocess.run(
        [certutil, "-user", "-addstore", "Root", cert_path],
        **kw,
    )


def _looks_like_already_trusted(combined_lower: str, combined_raw: str) -> bool:
    if "already exists" in combined_lower or "already in" in combined_lower:
        return True
    if "已经存在" in combined_raw or "已存在于" in combined_raw:
        return True
    return False


def _pem_to_der_temp(pem_path: str) -> str:
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization

    with open(pem_path, "rb") as f:
        cert = x509.load_pem_x509_certificate(f.read())
    der = cert.public_bytes(serialization.Encoding.DER)
    fd, tmp = tempfile.mkstemp(suffix=".cer")
    try:
        os.write(fd, der)
    finally:
        os.close(fd)
    return tmp


def install_mitm_ca_pem_to_current_user_root(pem_path: str) -> Dict[str, Any]:
    """使用 certutil 导入当前用户 Root 存储；失败时尝试 DER 临时文件。"""
    if sys.platform != "win32":
        return {"ok": True, "skipped": True, "reason": "non_windows"}

    env = (os.environ.get("SSL_MITM_AUTO_TRUST_WINDOWS") or "1").strip().lower()
    if env in ("0", "false", "no", "off"):
        return {"ok": True, "skipped": True, "reason": "SSL_MITM_AUTO_TRUST_WINDOWS disabled"}

    pem_path = os.path.abspath(pem_path)
    if not os.path.isfile(pem_path):
        return {"ok": False, "error": "pem_missing"}

    proc = _run_certutil_add_user_root(pem_path)
    out = f"{proc.stdout or ''}\n{proc.stderr or ''}".strip()
    low = out.lower()

    if proc.returncode == 0:
        log.info("MITM 根证书已写入当前用户「受信任的根证书颁发机构」")
        return {"ok": True, "installed": True}

    if _looks_like_already_trusted(low, out):
        log.info("MITM 根证书已在当前用户受信任根库中，跳过")
        return {"ok": True, "installed": False, "already_trusted": True}

    tmp: str | None = None
    try:
        tmp = _pem_to_der_temp(pem_path)
        proc2 = _run_certutil_add_user_root(tmp)
        out2 = f"{proc2.stdout or ''}\n{proc2.stderr or ''}".strip()
        low2 = out2.lower()
        if proc2.returncode == 0:
            log.info("MITM 根证书已写入受信任根库（DER 回退）")
            return {"ok": True, "installed": True, "via_der": True}
        if _looks_like_already_trusted(low2, out2):
            return {"ok": True, "installed": False, "already_trusted": True, "via_der": True}
        log.warning("自动导入 MITM 根证书失败（certutil）: %s", out2[:600])
        return {"ok": False, "error": "certutil_failed", "detail": out2[:800]}
    except Exception as exc:
        log.warning("自动导入 MITM 根证书失败: %s | 首次 certutil 输出: %s", exc, out[:400])
        return {"ok": False, "error": str(exc), "detail": out[:800]}
    finally:
        if tmp:
            try:
                os.remove(tmp)
            except OSError:
                pass


def maybe_trust_mitm_ca_windows(pem_path: str) -> Dict[str, Any]:
    """供 runner 调用；仅记录日志，不抛异常。"""
    global last_windows_trust_result
    try:
        last_windows_trust_result = install_mitm_ca_pem_to_current_user_root(pem_path)
        return last_windows_trust_result
    except Exception as exc:
        log.warning("maybe_trust_mitm_ca_windows: %s", exc)
        last_windows_trust_result = {"ok": False, "error": str(exc)}
        return last_windows_trust_result
