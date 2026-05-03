# -*- coding: utf-8 -*-
"""
煤炉 Android 客户端 DPoP 头（近似）生成工具。

依据 jadx 反编译逻辑（com.mercari.lib.dpop.api.GetDpopHeaderUseCaseImpl / zy0.i）：
  - JWT payload：jti, htm, htu, iat, uuid, iv_cert
  - 签名：RSA + RS256（与 KeyStore 中 PKCS1 + SHA-256 一致）
  - htu：完整 URL 字符串去掉首个「?」或「#」及其后面（与 Kotlin split 行为一致）

注意：线上接口是否接受取决于服务端是否已绑定你的设备公钥 / uuid；
若仅供本地对照抓包或自有密钥实验，可直接运行本脚本。
"""

from __future__ import annotations

import argparse
import json
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from jwt.algorithms import RSAAlgorithm


def normalize_htu(url: str) -> str:
    """
    与客户端一致：只保留协议 + 主机 + 路径，去掉 query 与 fragment。
    等价于按「先出现的 ? 或 #」截断（多数 URL 仅含 ?query）。
    """
    if not url:
        return url
    m = re.match(r"^[^?#]*", url.strip())
    return m.group(0) if m else url.strip()


@dataclass(frozen=True)
class DpopParams:
    method: str
    url: str
    device_uuid: str
    android_id: str


def build_payload(params: DpopParams, iat: int | None = None, jti: str | None = None) -> dict[str, Any]:
    iat = int(time.time()) if iat is None else iat
    jti = str(uuid.uuid4()) if jti is None else jti
    return {
        "jti": jti,
        "htm": params.method.upper(),
        "htu": normalize_htu(params.url),
        "iat": iat,
        "uuid": params.device_uuid,
        "iv_cert": params.android_id,
    }


def load_rsa_private_key(pem_or_path: str | Path) -> RSAPrivateKey:
    s = pem_or_path if isinstance(pem_or_path, str) else str(pem_or_path)
    if s.strip().startswith("-----"):
        data = s.encode("utf-8")
    else:
        data = Path(s).expanduser().read_bytes()
    key = serialization.load_pem_private_key(data, password=None, backend=default_backend())
    if not isinstance(key, RSAPrivateKey):
        raise TypeError("需要 RSA 私钥 PEM")
    return key


def generate_dpop_header_value(
    private_key: RSAPrivateKey,
    params: DpopParams,
    *,
    include_jwk_header: bool = True,
    iat: int | None = None,
    jti: str | None = None,
) -> str:
    """
    返回可直接作为 HTTP 头 ``DPoP`` 的 JWT 字符串（三段式）。
    include_jwk_header：是否在 JWT 头中加入 jwk（公钥），煤炉栈使用 Nimbus JOSE，常见带 jwk。
    """
    payload = build_payload(params, iat=iat, jti=jti)
    public_key = private_key.public_key()

    headers: dict[str, Any] = {"typ": "dpop+jwt", "alg": "RS256"}
    if include_jwk_header:
        headers["jwk"] = json.loads(RSAAlgorithm.to_jwk(public_key))

    token = jwt.encode(payload, private_key, algorithm="RS256", headers=headers)
    # PyJWT>=2 返回 str
    return token if isinstance(token, str) else token.decode("ascii")


def main() -> None:
    p = argparse.ArgumentParser(description="生成煤炉风格 DPoP JWT（RS256）")
    p.add_argument("--method", "-X", default="GET", help="HTTP 方法，如 GET、POST")
    p.add_argument("--url", "-u", required=True, help="完整请求 URL（含 query 亦可，会规范为 htu）")
    p.add_argument("--uuid", required=True, help="设备 uuid（应用 DataStore 中的 device uuid 字符串）")
    p.add_argument("--android-id", required=True, dest="android_id", help="Settings.Secure.ANDROID_ID（payload 中 iv_cert）")
    p.add_argument("--key", "-k", required=True, help="RSA 私钥 PEM 文件路径")
    p.add_argument("--no-jwk-header", action="store_true", help="JWT 头不包含 jwk（默认包含）")
    p.add_argument("--print-payload", action="store_true", help="打印规范化后的 payload JSON")
    args = p.parse_args()

    key = load_rsa_private_key(args.key)
    params = DpopParams(
        method=args.method,
        url=args.url,
        device_uuid=args.uuid,
        android_id=args.android_id,
    )
    if args.print_payload:
        print(json.dumps(build_payload(params), ensure_ascii=False, indent=2))
    token = generate_dpop_header_value(
        key,
        params,
        include_jwk_header=not args.no_jwk_header,
    )
    print(token)


if __name__ == "__main__":
    main()
