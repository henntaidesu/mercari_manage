# -*- coding: utf-8 -*-
import os

from src.app_paths import backend_root_str


def backend_root() -> str:
    return backend_root_str()


def ssl_mitm_data_dir() -> str:
    """MITM 运行时数据目录（CA 证书、capture JSON、stderr 日志、IPC 文件等）。

    存放规则（优先级从高到低）：
      1. 环境变量 ``MERCARI_SSL_MITM_DIR``（用户自定义绝对路径）
      2. 用户主目录下 ``~/.mercari/ssl_mitm``（Windows: %USERPROFILE%\\.mercari\\ssl_mitm）

    不再使用项目内 ``backend/ssl_mitm`` —— 避免运行时数据污染源码目录、
    且 CA 证书需要持久化以避免每次启动都需要重新被系统信任。
    """
    override = (os.environ.get("MERCARI_SSL_MITM_DIR") or "").strip()
    if override:
        return os.path.abspath(override)
    return os.path.join(os.path.expanduser("~"), ".mercari", "ssl_mitm")
