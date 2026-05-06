/** 下拉与简短展示：有货架名称时为「名称（货架号）」，否则为货架号 */
export function warehouseShelfLabel(w) {
  if (!w) return ''
  const code = w.name ?? ''
  const title = (w.shelf_name || '').trim()
  if (title && code) return `${title}（${code}）`
  return title || code || ''
}
