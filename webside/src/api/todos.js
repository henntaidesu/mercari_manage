import http from './http'

// 代办事项（本地缓存 services/todolist/v1/list）→ /mercariV2/src/use_web/todos/*
export const todosApi = {
  list: (params) => http.get('/use_web/todos', { params }),
  kinds: () => http.get('/use_web/todos/kinds'),
  sync: (data, axiosConfig = {}) =>
    http.post('/use_web/todos/sync', data, { timeout: 0, ...axiosConfig })
}
