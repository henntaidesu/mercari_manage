# -*- coding: utf-8 -*-
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..ssl_mitm_proxy.capture_config import read_capture_file
from ..ssl_mitm_proxy.runner import (
    ensure_mitm_ca_material,
    ensure_ssl_mitm_dir,
    mitm_ca_cert_path,
    mitm_status,
    start_mitm_proxy,
    stop_mitm_proxy,
)

router = APIRouter(prefix="/api/ssl-mitm", tags=["ssl-mitm"])


@router.get("/status")
def get_status():
    return mitm_status()


@router.post("/start")
def post_start():
    r = start_mitm_proxy()
    if r.get("error"):
        raise HTTPException(status_code=500, detail=r["error"])
    return {"success": True, **r}


@router.post("/stop")
def post_stop():
    stop_mitm_proxy()
    return {"success": True, **mitm_status()}


@router.get("/ca-cert")
def download_ca_cert():
    conf = ensure_ssl_mitm_dir()
    ensure_mitm_ca_material(conf)
    path = mitm_ca_cert_path()
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="无法生成 mitmproxy CA")
    return FileResponse(
        path,
        filename="mitmproxy-ca-cert.pem",
        media_type="application/x-x509-ca-cert",
    )


@router.get("/last-capture")
def get_last_capture():
    return read_capture_file() or {}
