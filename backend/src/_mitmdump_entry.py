# -*- coding: utf-8 -*-
"""mitmdump 入口。

两种使用方式：
- 独立 exe（旧 mitmdump.spec 方案）：本文件作为该 exe 的 __main__。
- 单文件方案：backend.exe 带环境变量 MERCARI_RUN_MITMDUMP=1 自调用时，
  main.py 顶部守卫会调用 run_mitmdump()，让同一个 exe 充当 mitmdump。

打包后 `import src...`（mitm_addon.py 里用到）从 exe 内置归档解析，无需磁盘源码。
"""
from __future__ import annotations

import sys


def run_mitmdump() -> "None":
    """以当前进程的 sys.argv[1:] 作为 mitmdump 参数运行，运行结束即退出进程。"""
    from mitmproxy.tools.main import mitmdump

    sys.exit(mitmdump())


if __name__ == "__main__":
    run_mitmdump()
