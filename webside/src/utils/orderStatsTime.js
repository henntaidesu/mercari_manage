/**
 * 订单统计与后端 /orders、/orders/stats 一致：本地自然日边界换算为 Unix 秒，
 * 筛选字段对应 COALESCE(purchase_time, order_date)。
 */

export function formatLocalYmd(d) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** YYYY-MM-DD -> 当日 0:00:00.000 本地 → Unix 秒 */
export function localYmdToDayStartTs(ymd) {
  const m = String(ymd).match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!m) return null
  const d = new Date(+m[1], +m[2] - 1, +m[3], 0, 0, 0, 0)
  return Math.floor(d.getTime() / 1000)
}

/** YYYY-MM-DD -> 当日 23:59:59.999 本地 → Unix 秒 */
export function localYmdToDayEndTs(ymd) {
  const m = String(ymd).match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!m) return null
  const d = new Date(+m[1], +m[2] - 1, +m[3], 23, 59, 59, 999)
  return Math.floor(d.getTime() / 1000)
}

/**
 * 滚动自然日：含今天共 dayCount 天，起止 Unix 秒（与订单页 dateRange 换算法一致）
 */
export function rollingLocalDayRangeTs(dayCount) {
  const end = new Date()
  const start = new Date(end)
  start.setDate(start.getDate() - (dayCount - 1))
  const startYmd = formatLocalYmd(start)
  const endYmd = formatLocalYmd(end)
  return {
    start_ts: localYmdToDayStartTs(startYmd),
    end_ts: localYmdToDayEndTs(endYmd),
  }
}

/** 本地「今天」0 点～结束 → Unix 秒（今日新增副指标） */
export function localTodayRangeTs() {
  const now = new Date()
  const todayStart = Math.floor(
    new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0).getTime() / 1000
  )
  const todayEnd = Math.floor(
    new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999).getTime() / 1000
  )
  return { today_start_ts: todayStart, today_end_ts: todayEnd }
}
