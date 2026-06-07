import http from './http'

// 话术表 → /mercariV2/src/use_web/talk-scripts/*
export const talkScriptApi = {
  /** 列表（可按 category 筛选 / keyword 搜索） */
  list: (params) => http.get('/use_web/talk-scripts', { params }),
  /** 去重后的分类列表 */
  categories: () => http.get('/use_web/talk-scripts/categories'),
  /** 新增 */
  create: (data) => http.post('/use_web/talk-scripts', data),
  /** 更新 */
  update: (id, data) => http.put(`/use_web/talk-scripts/${id}`, data),
  /** 删除 */
  remove: (id) => http.delete(`/use_web/talk-scripts/${id}`),
  /** 复制后使用次数 +1 */
  markUsed: (id) => http.post(`/use_web/talk-scripts/${id}/use`),
}
