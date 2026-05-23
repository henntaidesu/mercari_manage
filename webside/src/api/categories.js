import http from './http'

// 分类（System 二级页面）→ /mercariV2/src/use_web/system/categories/*
export const categoryApi = {
  list: () => http.get('/use_web/system/categories'),
  create: (data) => http.post('/use_web/system/categories', data),
  update: (id, data) => http.put(`/use_web/system/categories/${id}`, data),
  remove: (id) => http.delete(`/use_web/system/categories/${id}`)
}
