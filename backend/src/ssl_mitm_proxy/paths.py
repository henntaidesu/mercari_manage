# -*- coding: utf-8 -*-
import os


def backend_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(here))


def ssl_mitm_data_dir() -> str:
    return os.path.join(backend_root(), "ssl_mitm")
