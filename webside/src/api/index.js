import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({
  baseURL: '/api',
  timeout: 15000
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.code === 'ERR_CANCELED' || err.name === 'CanceledError') {
      return Promise.reject(err)
    }
    if (err.response?.status === 401) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_user')
      if (window.location.hash !== '#/login') {
        window.location.hash = '#/login'
      }
    }
    const msg = err.response?.data?.detail || err.message || '请求失败'
    ElMessage.error(msg)
    return Promise.reject(err)
  }
)

// 分类
export const categoryApi = {
  list: () => http.get('/categories'),
  create: (data) => http.post('/categories', data),
  update: (id, data) => http.put(`/categories/${id}`, data),
  remove: (id) => http.delete(`/categories/${id}`)
}

// 仓库
export const warehouseApi = {
  list: () => http.get('/warehouses'),
  create: (data) => http.post('/warehouses', data),
  update: (id, data) => http.put(`/warehouses/${id}`, data),
  remove: (id) => http.delete(`/warehouses/${id}`),
  /** 批量修改同一仓库展示名（其下所有货架位的 warehouse 字段） */
  renameGroup: (data) => http.put('/warehouses/rename-group', data),
  /** 同一仓库下批量修改 shelf_name 分组名称 */
  renameShelfNameGroup: (data) => http.put('/warehouses/rename-shelf-name-group', data),
  /** 将该货架位上全部库存改到目标货架位（warehouses.id） */
  migrateInventory: (fromId, data) => http.post(`/warehouses/${fromId}/migrate-inventory`, data)
}

// 游戏类型
export const productTypeApi = {
  list: () => http.get('/product-types'),
  create: (data) => http.post('/product-types', data),
  update: (id, data) => http.put(`/product-types/${id}`, data),
  remove: (id) => http.delete(`/product-types/${id}`)
}

// 游戏类型与类别字段映射
export const productTypeCategoryMappingApi = {
  list: () => http.get('/product-type-category-mappings'),
  create: (data) => http.post('/product-type-category-mappings', data),
  update: (id, data) => http.put(`/product-type-category-mappings/${id}`, data),
  remove: (id) => http.delete(`/product-type-category-mappings/${id}`)
}

// 库存
export const inventoryApi = {
  list: (params) => http.get('/inventory', { params }),
  get: (id) => http.get(`/inventory/${id}`),
  findByBarcode: (barcode) => http.get(`/inventory/barcode/${encodeURIComponent(barcode)}`),
  findByImage: (file) => {
    const fd = new FormData()
    fd.append('file', file, file?.name || 'query.jpg')
    return http.post('/inventory/find-by-image', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 15000
    })
  },
  uploadImage: (file, onUploadProgress, signal) => {
    const fd = new FormData()
    fd.append('file', file, file?.name || 'inventory.jpg')
    return http.post('/inventory/upload-image', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
      onUploadProgress,
      signal
    })
  },
  create: (data) => http.post('/inventory', data),
  combine: (data) => http.post('/inventory/combine', data),
  update: (id, data) => http.put(`/inventory/${id}`, data),
  remove: (id) => http.delete(`/inventory/${id}`),
  stockIn: (id, data) => http.post(`/inventory/${id}/stock-in`, data),
  stockOut: (id, data) => http.post(`/inventory/${id}/stock-out`, data)
}

// 出入库
export const transactionApi = {
  list: (params) => http.get('/transactions', { params }),
  create: (data) => http.post('/transactions', data)
}

// 成本记录
export const costRecordApi = {
  list: (params) => http.get('/cost-records', { params }),
  listPackagingItems: () => http.get('/cost-records/packaging-items'),
  create: (data) => http.post('/cost-records', data),
  update: (id, data) => http.put(`/cost-records/${id}`, data),
  remove: (id) => http.delete(`/cost-records/${id}`),
  uploadImage: (file) => {
    const fd = new FormData()
    fd.append('file', file, file?.name || 'cost.jpg')
    return http.post('/cost-records/upload-image', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 15000
    })
  }
}

// 成本支出
export const costExpenseApi = {
  list: (params) => http.get('/cost-expenses', { params }),
  create: (data) => http.post('/cost-expenses', data),
  update: (id, data) => http.put(`/cost-expenses/${id}`, data),
  remove: (id) => http.delete(`/cost-expenses/${id}`)
}

// 订单管理
export const orderApi = {
  list: (params) => http.get('/orders', { params }),
  stats: (params) => http.get('/orders/stats', { params }),
  /** 订单展开：从说明解析的待出库明细（管理 ID、仓库等） */
  outboundLines: (params) => http.get('/orders/outbound-lines', { params }),
  /** 订单二级列表：单行手动出库（已出库不可重复） */
  stockOutOutboundLine: (lineId, data = {}) => http.post(`/orders/outbound-lines/${lineId}/stock-out`, data),
  /** 订单二级列表：手动新增出库明细（预扣库存并进入待出库） */
  addManualOutboundLine: (data) => http.post('/orders/outbound-lines/manual', data),
  /** 订单二级列表：手动批量新增出库明细（多选商品） */
  addManualOutboundLinesBatch: (data) => http.post('/orders/outbound-lines/manual/batch', data),
  create: (data) => http.post('/orders', data),
  update: (id, data) => http.put(`/orders/${id}`, data),
  remove: (id) => http.delete(`/orders/${id}`),
  /** 单行 items/get 刷新：传 order_no + data_user（卖家ID），与煤炉账号 seller_id 对应 */
  refreshInfo: (data, axiosConfig = {}) =>
    http.post('/orders/refresh-info', data, { timeout: 60000, ...axiosConfig })
}

// 在售商品（本地缓存 items/get_items）
export const onSaleItemApi = {
  list: (params) => http.get('/on-sale-items', { params }),
  /** 按煤炉商品 ID 查本地 on_sale_items（二级表） */
  listByItemId: (params) => http.get('/on-sale-items/by-item-id', { params }),
  /** 按多个煤炉商品 ID 批量查本地 on_sale_items（逗号分隔） */
  listByItemIds: (params) => http.get('/on-sale-items/by-item-ids', { params }),
  sync: (data, axiosConfig = {}) =>
    http.post('/on-sale-items/sync', data, { timeout: 0, ...axiosConfig }),
  /** items/get 详情并同步库存 mercari_item_id / on_sale_quantity；须配置 dpop_item_get_info */
  fetchDetail: (data, axiosConfig = {}) =>
    http.post('/on-sale-items/fetch-detail', data, { timeout: 120000, ...axiosConfig }),
}

// Mercari 操作
export const mercariApi = {
  /** 「获取历史数据」前置校验：orders 是否已有该卖家 data_user 数据 */
  historySyncPrecheck: (params) => http.get('/mercari/history-sync-precheck', { params }),
  /** 同步订单：默认不设置超时（一直等到服务端返回）。axiosConfig 可覆盖，例如 { timeout: 60000 } */
  syncOrders: (data, axiosConfig = {}) =>
    http.post('/mercari/sync-orders', data, { timeout: 0, ...axiosConfig }),
  /** 订单页增量更新：仅入库列表中尚未存在的出售中单 */
  syncNewData: (data, axiosConfig = {}) =>
    http.post('/mercari/sync-new-data', data, { timeout: 0, ...axiosConfig }),
  /** 批量 items/get：库内未完成订单 + data_user，与列表「刷新」相同逻辑 */
  batchRefreshInfo: (data, axiosConfig = {}) =>
    http.post('/mercari/batch-refresh-info', data, { timeout: 0, ...axiosConfig }),
}

// 煤炉账号
export const meiluAccountApi = {
  list: (params) => http.get('/meilu-accounts', { params }),
  create: (data) => http.post('/meilu-accounts', data),
  update: (id, data) => http.put(`/meilu-accounts/${id}`, data),
  remove: (id) => http.delete(`/meilu-accounts/${id}`),
  /** MITM 抓取 items/get_items(trading) 请求头并写回账号（可能较久，timeout: 0） */
  fetchAuthViaMitm: (id, axiosConfig = {}) =>
    http.post(`/meilu-accounts/${id}/fetch-auth-via-mitm`, {}, { timeout: 0, ...axiosConfig })
}

/** Edge 持久化会话：按 account_key 隔离 Cookie（与后端 web_drive 一致） */
export const webDriveApi = {
  openSession: (data, axiosConfig = {}) =>
    http.post('/web-drive/sessions/open', data, { timeout: 0, ...axiosConfig }),
  closeSession: (data) => http.post('/web-drive/sessions/close', data),
  listSessions: () => http.get('/web-drive/sessions'),
  profilesRoot: () => http.get('/web-drive/profiles-root')
}

/**
 * 出品自动化：打开 Edge（SSL 中间人）→ 填写 Mercari 出品页
 *   account_key  webdrive 账号标识（通常 meilu_{id}）
 *   name         商品名称
 *   description  商品说明（含管理番号）
 *   image_urls   图片路径数组，如 ['/imges/xxx.jpg']
 *   use_mitm_proxy 是否启用 MITM 代理（默认 true）
 */
export const listingApi = {
  postToMarket: (data, axiosConfig = {}) =>
    http.post('/web-drive/listing/post-to-market', data, { timeout: 0, ...axiosConfig }),
  /** 与 postToMarket 的 progress_job_id 配合，轮询当前自动化步骤 */
  getPostProgress: (jobId, axiosConfig = {}) =>
    http.get(`/web-drive/listing/post-progress/${encodeURIComponent(jobId)}`, axiosConfig)
}

// OCR 识别
export const ocrApi = {
  ocrRegion: (base64Image) => http.post('/ocr-region', { image: base64Image })
}

// 条形码识别（后端 ZXing）
export const scanApi = {
  scanBarcode: (blob) => {
    const fd = new FormData()
    fd.append('file', blob, 'frame.jpg')
    return http.post('/scan-barcode', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 8000
    })
  }
}

// 应用配置（系统页：出品默认值等，对应库存出品表单）
export const configApi = {
  getListingDefaults: () => http.get('/config/listing-defaults'),
  putListingDefaults: (data) => http.put('/config/listing-defaults', data)
}

// 认证
export const authApi = {
  login: (data) => http.post('/auth/login', data),
  listUsers: () => http.get('/auth/users'),
  createUser: (data) => http.post('/auth/users', data),
  changePassword: (data) => http.post('/auth/change-password', data)
}
