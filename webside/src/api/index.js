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
  remove: (id) => http.delete(`/warehouses/${id}`)
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
  create: (data) => http.post('/inventory', data),
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

// 订单管理
export const orderApi = {
  list: (params) => http.get('/orders', { params }),
  create: (data) => http.post('/orders', data),
  update: (id, data) => http.put(`/orders/${id}`, data),
  remove: (id) => http.delete(`/orders/${id}`)
}

// Mercari 操作
export const mercariApi = {
  syncOrders: (data) => http.post('/mercari/sync-orders', data)
}

// 煤炉账号
export const meiluAccountApi = {
  list: (params) => http.get('/meilu-accounts', { params }),
  create: (data) => http.post('/meilu-accounts', data),
  update: (id, data) => http.put(`/meilu-accounts/${id}`, data),
  remove: (id) => http.delete(`/meilu-accounts/${id}`)
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

// 认证
export const authApi = {
  login: (data) => http.post('/auth/login', data),
  listUsers: () => http.get('/auth/users'),
  createUser: (data) => http.post('/auth/users', data),
  changePassword: (data) => http.post('/auth/change-password', data)
}
