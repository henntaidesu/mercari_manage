import http from './http'

// 条形码识别（库存页面辅助功能，后端 ZXing）→ /mercariV2/src/use_web/inventory/scan-barcode
export const scanApi = {
  scanBarcode: (blob) => {
    const fd = new FormData()
    fd.append('file', blob, 'frame.jpg')
    return http.post('/use_web/inventory/scan-barcode', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 8000
    })
  }
}
