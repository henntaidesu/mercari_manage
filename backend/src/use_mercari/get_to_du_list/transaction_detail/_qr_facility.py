# -*- coding: utf-8 -*-
"""shared: ship-code image grab/save + shipping-facility extraction"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional
from ....db_manage.database import DatabaseManager
from ....use_web.image_storage import save_image_bytes
from ._cache import _persist_qr_image_path

log = logging.getLogger(__name__)


# 交易ページ上の発送用コード画像（発行後に表示される）。
# QRコード（2次元コード）は data-testid="qr-code"、らくらくメルカリ便×セブン-イレブン等で
# 返るバーコードは data-testid="bar-code"。两者都要匹配。
_QR_CODE_IMG_SELECTOR = 'img[data-testid="qr-code"], img[data-testid="bar-code"]'

async def _qr_code_exists(page: Any, *, timeout: int = 3000) -> bool:
    """快速判断交易页上是否存在发货码图片（已发行）。兼容 QR 二维码与条形码。"""
    try:
        await page.locator(_QR_CODE_IMG_SELECTOR).first.wait_for(
            state="visible", timeout=timeout
        )
        return True
    except Exception:
        return False

async def _save_qr_code_image(
    page: Any, *, item_id: str, todo_id: int, timeout: int = 8000
) -> Optional[str]:
    """把交易页上的发货码图片下载到本地，返回 /imges 路径。

    兼容 QR 二维码（data-testid="qr-code"）与らくらく×セブン-イレブン等返回的条形码
    （data-testid="bar-code"）——见 ``_QR_CODE_IMG_SELECTOR``。

    ``timeout``：等待发货码出现的毫秒数。发行后流程用默认 8s；刷新抓取/同步场景
    传较短值（页面已加载，有就立刻拿到，没有则快速返回 None）。
    """
    try:
        img = page.locator(_QR_CODE_IMG_SELECTOR)
        await img.first.wait_for(state="visible", timeout=timeout)
        src = await img.first.get_attribute("src")
    except Exception:
        log.debug("[shipping] 交易页无发货二维码 (item_id=%s)", item_id)
        return None
    if not src:
        return None
    try:
        resp = await page.request.get(src)
        body = await resp.body()
    except Exception as exc:
        log.warning("[shipping] 下载二维码图片失败 src=%s: %s", src, exc)
        return None
    low = src.lower()
    ext = "jpg" if (".jpg" in low or ".jpeg" in low) else "png"
    try:
        path = save_image_bytes(body, ext=ext, prefix=f"qr_{item_id}")
    except Exception as exc:
        log.warning("[shipping] 保存二维码图片失败: %s", exc)
        return None
    _persist_qr_image_path(int(todo_id), path)
    log.info("[shipping] 已保存发货二维码 todo_id=%s path=%s", todo_id, path)
    return path

# 交易页发货码上方的「○○から発送」信息：标题（如「ファミリーマートから発送」）、
# 说明文、以及发送场所图标 URL（煤炉 CDN img[src*="shipping_facility"]，如
# family-mart.png / seven-eleven.png / yamato.png / pudo.png）。供前端在发货码旁
# 展示「发送场所 + 图标」。兼容 ファミリーマート/セブン-イレブン/ヤマト営業所/PUDO 等。
_SHIPPING_FACILITY_JS = """
() => {
  const pick = (el) => (el && el.innerText ? el.innerText.trim() : '');
  const titleEl = document.querySelector('[data-testid="qrcode.title"]');
  let title = pick(titleEl);
  let desc = '';
  if (titleEl) {
    let n = titleEl.nextElementSibling;
    while (n) {
      if (n.tagName === 'P') { desc = pick(n); break; }
      if (n.querySelector && n.querySelector('img')) break;
      n = n.nextElementSibling;
    }
  }
  const img = document.querySelector('img[src*="shipping_facility"]');
  const imageUrl = img ? (img.currentSrc || img.src || '') : '';
  return { title, desc, imageUrl };
}
"""

async def _extract_shipping_facility(page: Any) -> Dict[str, str]:
    """从交易页提取「発送場所」展示信息（标题/说明/图标 URL）。无则返回 {}。"""
    try:
        data = await page.evaluate(_SHIPPING_FACILITY_JS)
    except Exception as exc:
        log.debug("[shipping] 提取发送场所信息失败: %s", exc)
        return {}
    if not isinstance(data, dict):
        return {}
    out: Dict[str, str] = {}
    title = (data.get("title") or "").strip()
    desc = (data.get("desc") or "").strip()
    image_url = (data.get("imageUrl") or "").strip()
    if title:
        out["shipping_facility_name"] = title
    if desc:
        out["shipping_facility_desc"] = desc
    if image_url:
        out["shipping_facility_image_url"] = image_url
    return out

# お届け先（買い手の配送先住所）：配送の方法が「未定」(=非匿名配送、らくらく/ゆうゆう
# メルカリ便ではない) のとき、交易ページに買い手の住所が表示される（匿名配送では非表示）。
# SSR HTML の `[data-testid="transaction:delivery-address"]` 配下の <p> 行を集約する。
# 「お届け先」見出しは <span> なので拾わない。住所が無い（匿名配送）なら空文字を返す。
_DELIVERY_ADDRESS_JS = """
() => {
  const root = document.querySelector('[data-testid="transaction:delivery-address"]');
  if (!root) return '';
  const lines = Array.from(root.querySelectorAll('p'))
    .map(p => (p.innerText || '').trim())
    .filter(Boolean);
  return lines.join('\\n');
}
"""

async def _extract_delivery_address(page: Any) -> Optional[str]:
    """从交易页提取「お届け先」(买家收货地址)。仅「未定」(非匿名)发货方式时存在；无则返回 None。"""
    try:
        text = await page.evaluate(_DELIVERY_ADDRESS_JS)
    except Exception as exc:
        log.debug("[shipping] 提取お届け先失败: %s", exc)
        return None
    text = (text or "").strip()
    return text or None

# 発送通知待ち状態（ゆうパケットポスト等のシール読み取り済み／専用箱控え切り取り済みで、
# あとは「梱包した商品に発送用シールを貼りました」等にチェック→「商品を発送したので、発送通知
# をする」を押すだけ）。data-testid="acknowledge-checkbox" の有無＋発送通知ボタンの有無で判定し、
# ポスト発送確認符号・追跡番号も拾う。
_POST_SHIP_READY_JS = """
() => {
  const body = document.body ? (document.body.innerText || '') : '';
  const hasCheckbox = !!document.querySelector('[data-testid="acknowledge-checkbox"]');
  const notifyBtn = Array.from(document.querySelectorAll('button'))
    .some(b => (b.innerText || '').includes('発送通知をする'));
  const ready = hasCheckbox || notifyBtn;
  let code = '';
  let m = body.match(/発送確認符号[\\s:：]*([A-Za-z0-9]+)/);
  if (m) code = m[1];
  let tracking = '';
  m = body.match(/追跡番号[\\s:：]*([0-9\\-]+)/);
  if (m) tracking = m[1];
  return { ready, code, tracking };
}
"""

async def _extract_post_ship_ready(page: Any) -> Dict[str, Any]:
    """检测交易页是否处于「待发送通知」状态（シール贴付/控え切り取りのチェック＋発送通知ボタン）。

    返回 ``{ready, confirm_code, tracking_no}``；抓取失败时 ready=False。
    """
    try:
        data = await page.evaluate(_POST_SHIP_READY_JS)
    except Exception as exc:
        log.debug("[shipping] 提取发送通知待ち状态失败: %s", exc)
        return {"ready": False, "confirm_code": None, "tracking_no": None}
    if not isinstance(data, dict):
        return {"ready": False, "confirm_code": None, "tracking_no": None}
    return {
        "ready": bool(data.get("ready")),
        "confirm_code": (data.get("code") or "").strip() or None,
        "tracking_no": (data.get("tracking") or "").strip() or None,
    }

def _persist_shipping_facility(todo_id: int, fac: Dict[str, str]) -> None:
    """把发送场所信息合并进 todo_items.detail_json（不覆盖其它字段）。"""
    if not fac:
        return
    db = DatabaseManager()
    try:
        rows = db.execute_query(
            "SELECT [detail_json] FROM [todo_items] WHERE [id]=?", (int(todo_id),)
        )
        d: Dict[str, Any] = {}
        if rows and rows[0] and rows[0][0]:
            try:
                parsed = json.loads(rows[0][0])
                if isinstance(parsed, dict):
                    d = parsed
            except Exception:
                d = {}
        d.update(fac)
        db.execute_update(
            "UPDATE [todo_items] SET [detail_json]=? WHERE [id]=?",
            (json.dumps(d, ensure_ascii=False), int(todo_id)),
        )
    except Exception as exc:
        log.warning("[shipping] 缓存发送场所信息失败 todo_id=%s: %s", todo_id, exc)
