import http from './http'

// 出入库（System 二级页面）→ /mercariV2/src/use_web/system/transactions/*
export const transactionApi = {
  list: (params) => http.get('/use_web/system/transactions', { params }),
  create: (data) => http.post('/use_web/system/transactions', data)
}
