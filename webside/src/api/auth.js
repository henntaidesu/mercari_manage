import http from './http'

// 认证（按后端页面归类：login 端点 → /use_web/login，用户管理 → /use_web/system）
export const authApi = {
  login: (data) => http.post('/use_web/login/', data),
  listUsers: () => http.get('/use_web/system/users'),
  createUser: (data) => http.post('/use_web/system/users', data),
  changePassword: (data) => http.post('/use_web/system/change-password', data)
}
