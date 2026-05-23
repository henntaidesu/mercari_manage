import http from './http'

// 代办事项（本地缓存 services/todolist/v1/list）→ /mercariV2/src/use_web/todos/*
export const todosApi = {
  list: (params) => http.get('/use_web/todos', { params }),
  kinds: () => http.get('/use_web/todos/kinds'),
  sync: (data, axiosConfig = {}) =>
    http.post('/use_web/todos/sync', data, { timeout: 0, ...axiosConfig }),
  /** 处理按钮：打开浏览器到 transaction 页并抓取 DOM 字段 */
  fetchTransactionDetail: (todoId, axiosConfig = {}) =>
    http.post(`/use_web/todos/${encodeURIComponent(todoId)}/transaction-detail`, {}, { timeout: 0, ...axiosConfig }),
  /** 关闭交易详情 dialog 时关掉对应账号的 __auto 浏览器（fire-and-forget） */
  closeDetailBrowser: (accountId, axiosConfig = {}) =>
    http.post(`/use_web/todos/close-detail-browser/${encodeURIComponent(accountId)}`, {}, { timeout: 0, ...axiosConfig }),
  /** 在已开浏览器内填回复并点击「取引メッセージを送る」 */
  sendTransactionMessage: (todoId, text, axiosConfig = {}) =>
    http.post(`/use_web/todos/${encodeURIComponent(todoId)}/send-message`, { text }, { timeout: 60000, ...axiosConfig }),
  /** 在已开浏览器（取引評価页）填评价并点击「購入者を評価して取引完了する」 */
  submitTransactionReview: (todoId, text, axiosConfig = {}) =>
    http.post(`/use_web/todos/${encodeURIComponent(todoId)}/submit-review`, { text }, { timeout: 60000, ...axiosConfig }),
  /** 点「商品サイズと発送場所を選択する」→ 抓 shipping_classes → 返回可选项 */
  startShippingClass: (todoId, axiosConfig = {}) =>
    http.post(`/use_web/todos/${encodeURIComponent(todoId)}/shipping/start`, {}, { timeout: 60000, ...axiosConfig }),
  /** 提交所选 size+facility：浏览器内完成全套点击 */
  confirmShippingSelection: (todoId, data, axiosConfig = {}) =>
    http.post(`/use_web/todos/${encodeURIComponent(todoId)}/shipping/confirm`, data, { timeout: 60000, ...axiosConfig }),
  /** 点「発送方法を変更する」（仅导航，后续由用户在浏览器内手动） */
  changeShippingMethod: (todoId, axiosConfig = {}) =>
    http.post(`/use_web/todos/${encodeURIComponent(todoId)}/shipping/change-method`, {}, { timeout: 60000, ...axiosConfig })
}
