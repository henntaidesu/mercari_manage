import http from './http'

// 成本记录（System 二级页面）→ /mercariV2/src/use_web/system/cost-records/*
export const costRecordApi = {
  list: (params) => http.get('/use_web/system/cost-records', { params }),
  listPackagingItems: () => http.get('/use_web/system/cost-records/packaging-items'),
  create: (data) => http.post('/use_web/system/cost-records', data),
  update: (id, data) => http.put(`/use_web/system/cost-records/${id}`, data),
  remove: (id) => http.delete(`/use_web/system/cost-records/${id}`),
  uploadImage: (file) => {
    const fd = new FormData()
    fd.append('file', file, file?.name || 'cost.jpg')
    return http.post('/use_web/system/cost-records/upload-image', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 15000
    })
  }
}
