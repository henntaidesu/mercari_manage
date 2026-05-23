import http from './http'

// OCR 识别（库存页面辅助功能）→ /mercariV2/src/use_web/inventory/ocr-region
export const ocrApi = {
  ocrRegion: (base64Image) => http.post('/use_web/inventory/ocr-region', { image: base64Image })
}
