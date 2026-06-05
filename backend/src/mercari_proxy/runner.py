# -*- coding: utf-8 -*-
"""mercari-proxy（Node 反代）子进程生命周期 + Cookie 注入。

源自 github.com/Gosoki/mercari-proxy，改造为后端托管的子进程，随系统启停。
- 独立 HTTPS 端口、根挂载（与原项目设计一致，SPA 导航/刷新/前进后退均正常）；
- 默认仅监听 127.0.0.1:<MERCARI_PROXY_PORT>（默认 9610），仅本机可访问；
- 自签证书使浏览器处于安全上下文（DPoP 所需），用户首次访问点「继续」即可；
- ``register_injection`` 把账号 Cookie 以一次性 token 推送到 Node 进程内存，
  用户随后访问 ``/__boot?token=...`` 时写入本地浏览器。
"""
from __future__ import annotations

import logging
import os
import shutil
import socket
import subprocess
import time
from typing import Any, Dict, List, Optional

import requests

from .cert import ensure_cert

log = logging.getLogger(__name__)

_proc: Optional[subprocess.Popen] = None
_internal_secret: str = ""
_scheme: str = "http"


def proxy_port() -> int:
    return int(os.environ.get("MERCARI_PROXY_PORT", "9610"))


def bind_host() -> str:
    # 仅本机可访问（Cookie 注入含登录态，限制为环回地址）。
    return os.environ.get("MERCARI_PROXY_BIND_HOST", "127.0.0.1")


def proxy_scheme() -> str:
    return _scheme


def proxy_upstream() -> str:
    return os.environ.get("MERCARI_PROXY_UPSTREAM", "jp.mercari.com")


def server_js_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.js")


def boot_path(token: str) -> str:
    """根挂载下的引导地址路径（前端结合 scheme/port + 当前主机名拼成完整 URL）。"""
    return f"/__boot?token={token}"


def _ensure_secret() -> str:
    global _internal_secret
    if not _internal_secret:
        _internal_secret = os.environ.get("MERCARI_PROXY_INTERNAL_SECRET") or os.urandom(24).hex()
    return _internal_secret


def _node_executable() -> Optional[str]:
    return shutil.which("node") or shutil.which("node.exe")


def _wait_listen(host: str, port: int, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    target = "127.0.0.1" if host in ("0.0.0.0", "") else host
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((target, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def is_running() -> bool:
    return _proc is not None and _proc.poll() is None


def proxy_status() -> Dict[str, Any]:
    return {
        "running": is_running(),
        "port": proxy_port(),
        "scheme": proxy_scheme(),
        "upstream": proxy_upstream(),
        "node_available": bool(_node_executable()),
    }


def start_proxy() -> Dict[str, Any]:
    global _proc, _scheme
    if is_running():
        return {"started": False, **proxy_status(), "message": "已在运行"}

    node = _node_executable()
    if not node:
        return {"started": False, "error": "未找到 node（请安装 Node 18+ 并加入 PATH）"}

    js = server_js_path()
    if not os.path.isfile(js):
        return {"started": False, "error": f"找不到 server.js: {js}"}

    port = proxy_port()
    host = bind_host()
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["BIND_HOST"] = host
    env["BASE_PATH"] = ""  # 根挂载
    env["UPSTREAM"] = proxy_upstream()
    env["MERCARI_PROXY_INTERNAL_SECRET"] = _ensure_secret()

    cert_path, key_path = ensure_cert()
    if cert_path and key_path:
        env["TLS_CERT"] = cert_path
        env["TLS_KEY"] = key_path
        _scheme = "https"
    else:
        _scheme = "http"
        log.warning("mercari-proxy 无法生成自签证书，回退 http（仅 localhost 可用，DPoP 在内网/远程会失败）")

    try:
        _proc = subprocess.Popen(
            [node, js],
            env=env,
            cwd=os.path.dirname(js),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:  # noqa: BLE001
        return {"started": False, "error": str(exc)}

    if not _wait_listen(host, port, timeout=10.0):
        stop_proxy()
        return {"started": False, "error": f"mercari-proxy 未在 {host}:{port} 监听"}

    log.info("mercari-proxy 已启动 %s://%s:%s（根挂载）", _scheme, host, port)
    return {"started": True, **proxy_status()}


def stop_proxy() -> None:
    global _proc
    if _proc is None:
        return
    if _proc.poll() is None:
        try:
            _proc.terminate()
            try:
                _proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                _proc.kill()
        except Exception:  # noqa: BLE001
            pass
    _proc = None


def register_injection(token: str, cookies: List[Dict[str, Any]], ttl_sec: int = 120) -> None:
    """把一次性 token + Cookie 列表推送到 Node 进程内存（用户随后访问 /__boot 时写入浏览器）。

    cookies: [{"name": str, "value": str, "httpOnly": bool}, ...]
    抛出异常表示推送失败（Node 未运行 / 网络错误）。
    """
    url = f"{proxy_scheme()}://127.0.0.1:{proxy_port()}/__inject"
    resp = requests.post(
        url,
        json={"token": token, "cookies": cookies, "ttl_sec": ttl_sec},
        headers={"x-internal-secret": _ensure_secret()},
        timeout=5,
        verify=False,  # 自签证书
    )
    resp.raise_for_status()
