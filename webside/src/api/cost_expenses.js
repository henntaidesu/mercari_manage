import http from './http'

// 成本支出（System 二级页面）→ /mercariV2/src/use_web/system/cost-expenses/*
export const costExpenseApi = {
  list: (params) => http.get('/use_web/system/cost-expenses', { params }),
  create: (data) => http.post('/use_web/system/cost-expenses', data),
  update: (id, data) => http.put(`/use_web/system/cost-expenses/${id}`, data),
  remove: (id) => http.delete(`/use_web/system/cost-expenses/${id}`)
}
