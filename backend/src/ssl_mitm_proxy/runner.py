# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from . import windows_trust as _mitm_windows_trust
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
        log.warning("mitmproxy 未安装，无法生成 CA 证书")
        return
    try:
        Path(confdir).mkdir(parents=True, exist_ok=True)
        CertStore.from_store(Path(confdir), "mitmproxy", 2048)
        log.info("已生成 mitmproxy CA: %s", cert_path)
    except Exception as exc:
        log.exception("生成 mitmproxy CA 失败: %s", exc)


def _mitmdump_executable() -> str:
    """mitmproxy 10+ 须通过 mitmdump 入口启动；``python -m mitmproxy.tools.dump`` 不是有效 CLI。"""
    w = shutil.which("mitmdump")
    if w:
        return w
    if sys.platform == "win32":
        scripts = os.path.join(os.path.dirname(sys.executable), "Scripts", "mitmdump.exe")
        if os.path.isfile(scripts):
            return scripts
    raise FileNotFoundError(
        "找不到 mitmdump。请在 backend 所在环境执行: pip install mitmproxy"
    )


def _wait_proxy_listen(host: str, port: int, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def mitm_status() -> Dict[str, Any]:
    running = _mitm_proc is not None and _mitm_proc.poll() is None
    ca = mitm_ca_cert_path()
    conf = ensure_ssl_mitm_dir()
    out: Dict[str, Any] = {
        "running": running,
        "listen_port": mitm_listen_port(),
        "proxy_url": default_mitm_proxy_url(),
        "confdir": conf,
        "ca_cert_path": ca,
        "ca_cert_exists": os.path.isfile(ca),
        "stderr_log": os.path.join(conf, "mitmdump_stderr.log"),
    }
    if sys.platform == "win32" and _mitm_windows_trust.last_windows_trust_result:
        out["windows_ca_trust"] = dict(_mitm_windows_trust.last_windows_trust_result)
    return out


def start_mitm_proxy() -> Dict[str, Any]:
    global _mitm_proc

    conf = ensure_ssl_mitm_dir()
    ensure_mitm_ca_material(conf)
    ca_path = mitm_ca_cert_path()
    if os.path.isfile(ca_path):
        trust = _mitm_windows_trust.maybe_trust_mitm_ca_windows(ca_path)
        if not trust.get("ok") and not trust.get("skipped"):
            log.warning("MITM 根证书未自动导入受信任库: %s", trust)

    if _mitm_proc is not None and _mitm_proc.poll() is None:
        return {"started": False, **mitm_status(), "message": "已在运行"}

    addon = os.path.abspath(mitm_addon_path())
    if not os.path.isfile(addon):
        return {"started": False, "error": f"找不到插件: {addon}"}

    env = os.environ.copy()
    port = mitm_listen_port()
    err_log = os.path.join(conf, "mitmdump_stderr.log")
    try:
        mitm_bin = _mitmdump_executable()
    except FileNotFoundError as exc:
        return {"started": False, "error": str(exc)}
    try:
        import mitmproxy  # noqa: F401
    except ImportError:
        return {"started": False, "error": "未安装 mitmproxy: pip install mitmproxy"}

    cmd = [
        mitm_bin,
        "-q",
        "--listen-port",
        str(port),
        "--set",
        f"confdir={os.path.abspath(conf)}",
        "-s",
        addon,
    ]
    try:
        err_f = open(err_log, "ab", buffering=0)
    except OSError:
        err_f = subprocess.DEVNULL  # type: ignore
    try:
        _mitm_proc = subprocess.Popen(
            cmd,
            env=env,
            cwd=backend_root(),
            stdout=subprocess.DEVNULL,
            stderr=err_f,
        )
    except Exception as exc:
        if err_f is not subprocess.DEVNULL:
            try:
                err_f.close()
            except Exception:
                pass
        return {"started": False, "error": str(exc)}

    time.sleep(0.4)
    if _mitm_proc.poll() is not None:
        _mitm_proc = None
        tail = ""
        try:
            if os.path.isfile(err_log):
                with open(err_log, "rb") as rf:
                    tail = rf.read()[-800:].decode("utf-8", errors="replace")
        except Exception:
            pass
        msg = "mitmdump 启动后立即退出，请检查端口占用或插件错误。"
        if tail.strip():
            msg += f" 详见 {err_log} 末尾: {tail.strip()[:400]}"
        return {"started": False, "error": msg}

    if not _wait_proxy_listen("127.0.0.1", port, timeout=10.0):
        try:
            _mitm_proc.terminate()
            _mitm_proc.wait(timeout=5)
        except Exception:
            pass
        _mitm_proc = None
        tail = ""
        try:
            if os.path.isfile(err_log):
                with open(err_log, "rb") as rf:
                    tail = rf.read()[-800:].decode("utf-8", errors="replace")
        except Exception:
            pass
        msg = (
            f"mitmdump 未在 127.0.0.1:{port} 监听（代理连不上）。"
            f" 请查看日志: {err_log}"
        )
        if tail.strip():
            msg += f" 末尾输出: {tail.strip()[:400]}"
        return {"started": False, "error": msg}

    log.info("mitmdump 已启动 port=%s", port)
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
