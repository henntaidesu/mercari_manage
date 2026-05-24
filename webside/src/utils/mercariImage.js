/**
 * 煤炉图片代理工具：将煤炉 CDN 的图片 URL 重写为后端代理 URL。
 *
 * 背景：部分用户网络环境无法直连 static.mercdn.net 等煤炉 CDN，
 * 由后端 /mercariV2/src/use_web/mercari-image?u=... 代拉图片，
 * 既能缓存又能绕过用户侧的访问限制。
 *
 * 非煤炉域名（如本地 /imges/ 或空值）原样返回。
 */

const PROXY_PATH = '/mercariV2/src/use_web/mercari-image'

const MERCARI_HOST_SUFFIXES = [
  '.mercdn.net',
  '.mercari.com',
  '.mercari-shops.com',
  '.mercariapp.com'
]

const MERCARI_EXACT_HOSTS = new Set([
  'mercdn.net',
  'mercari.com',
  'mercari-shops.com'
])

function isMercariUrl(raw) {
  if (!raw || typeof raw !== 'string') return false
  const s = raw.trim()
  if (!/^https?:\/\//i.test(s)) return false
  try {
    const u = new URL(s)
    const host = u.hostname.toLowerCase()
    if (MERCARI_EXACT_HOSTS.has(host)) return true
    return MERCARI_HOST_SUFFIXES.some((suf) => host.endsWith(suf))
  } catch {
    return false
  }
}

/** 单张 URL → 代理 URL（非煤炉/空值原样返回） */
export function mercariImageUrl(raw) {
  if (!raw) return ''
  const s = String(raw).trim()
  if (!s) return ''
  if (!isMercariUrl(s)) return s
  return `${PROXY_PATH}?u=${encodeURIComponent(s)}`
}

/** 数组批量包装；过滤空值 */
export function mercariImageUrlList(list) {
  if (!Array.isArray(list)) return []
  return list.map(mercariImageUrl).filter(Boolean)
}
