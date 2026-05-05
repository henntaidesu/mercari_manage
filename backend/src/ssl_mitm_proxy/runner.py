# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .paths import backend_root, ssl_mitm_data_dir

log = logging.getLogger(__name__)
_mitm_proc: Optional[subprocess.Popen] = None


def mitm_listen_port() -> int:
    return int(os.environ.get("SSL_MITM_LISTEN_PORT", "8890"))


def default_mitm_proxy_url() -> str:
    return f"http://127.0.0.1:{mitm_listen_port()}"


def mitm_ca_cert_path() -> str:
    return os.path.join(ssl_mitm_data_dir(), "mitmproxy-ca-cert.pem")


def mitm_addon_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "mitm_addon.py")


def ensure_ssl_mitm_dir() -> str:
    d = ssl_mitm_data_dir()
    os.makedirs(d, exist_ok=True)
    return d


def ensure_mitm_ca_material(confdir: str) -> None:
    cert_path = os.path.join(confdir, "mitmproxy-ca-cert.pem")
    if os.path.isfile(cert_path):
        return
    try:
        from mitmproxy.certs import CertStore
    except ImportError:
        return
    Path(confdir).mkdir(parents=True, exist_ok=True)
    CertStore.from_store(Path(confdir), "mitmproxy", 2048)


def mitm_status() -> Dict[str, Any]:
    running = _mitm_proc is not None and _mitm_proc.poll() is None
    ca = mitm_ca_cert_path()
    return {
        "running": running,
        "listen_port": mitm_listen_port(),
        "proxy_url": default_mitm_proxy_url(),
        "confdir": ensure_ssl_mitm_dir(),
        "ca_cert_path": ca,
        "ca_cert_exists": os.path.isfile(ca),
    }


def start_mitm_proxy() -> Dict[str, Any]:
    global _mitm_proc

    if _mitm_proc is not None and _mitm_proc.poll() is None:
        return {"started": False, **mitm_status(), "message": "已在运行"}

    conf = ensure_ssl_mitm_dir()
    ensure_mitm_ca_material(conf)
    addon = os.path.abspath(mitm_addon_path())
    if not os.path.isfile(addon):
        return {"started": False, "error": f"找不到插件: {addon}"}

    env = os.environ.copy()
    port = mitm_listen_port()
    cmd = [
        sys.executable,
        "-m",
        "mitmproxy.tools.dump",
        "-q",
        "--listen-port",
        str(port),
        "--set",
        f"confdir={os.path.abspath(conf)}",
        "-s",
        addon,
    ]
    try:
        import mitmproxy  # noqa: F401
    except ImportError:
        return {"started": False, "error": "未安装 mitmproxy: pip install mitmproxy"}

    try:
        _mitm_proc = subprocess.Popen(
            cmd,
            env=env,
            cwd=backend_root(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        return {"started": False, "error": str(exc)}

    time.sleep(0.35)
    if _mitm_proc.poll() is not None:
        _mitm_proc = None
        return {"started": False, "error": "mitmproxy 启动后立即退出，请检查端口占用"}

    log.info("mitmproxy 已启动 port=%s", port)
    return {"started": True, **mitm_status()}


def stop_mitm_proxy() -> None:
    global _mitm_proc
    if _mitm_proc is None:
        return
    if _mitm_proc.poll() is not None:
        _mitm_proc = None
        return
    try:
        _mitm_proc.terminate()
        try:
            _mitm_proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            _mitm_proc.kill()
    except Exception:
        pass
    finally:
        _mitm_proc = None
