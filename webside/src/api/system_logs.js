import http from './http'

// 系统日志（系统页：自动上架 / 自动获取）→ /mercariV2/src/use_web/system/system-logs
export const systemLogApi = {
  list: (params) => http.get('/use_web/system/system-logs', { params }),
  clear: () => http.post('/use_web/system/system-logs/clear', {})
}
