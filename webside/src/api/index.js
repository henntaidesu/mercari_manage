import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({
  baseURL: '/api',
  timeout: 15000
})

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
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

// 商品
export const productApi = {
  list: (params) => http.get('/products', { params }),
  get: (id) => http.get(`/products/${id}`),
  findByBarcode: (barcode) => http.get(`/products/barcode/${encodeURIComponent(barcode)}`),
  create: (data) => http.post('/products', data),
  update: (id, data) => http.put(`/products/${id}`, data),
  remove: (id) => http.delete(`/products/${id}`),
  stockIn: (id, data) => http.post(`/products/${id}/stock-in`, data)
}

// 出入库
export const transactionApi = {
  list: (params) => http.get('/transactions', { params }),
  create: (data) => http.post('/transactions', data)
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
