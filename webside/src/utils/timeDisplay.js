/** 出入库等待展示：Unix 秒 → 本地 YYYY-MM-DD HH:mm:ss；旧接口若为字符串则原样返回 */

export function formatUnixSecLocal(v) {
  if (v == null || v === '') return '-'
  const n = typeof v === 'number' ? v : Number(String(v).trim())
  if (!Number.isFinite(n)) return String(v)
  const ms = n > 1e11 ? n : n * 1000
  const d = new Date(ms)
  if (Number.isNaN(d.getTime())) return String(v)
  const pad = (x) => String(x).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}
