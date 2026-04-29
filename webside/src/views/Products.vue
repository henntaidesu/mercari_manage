<template>
  <div>
    <div class="page-header">
      <span class="page-title">商品管理</span>
      <el-button type="primary" @click="openDialog()">
        <el-icon><Plus /></el-icon> 新增商品
      </el-button>
    </div>

    <el-card shadow="never" class="search-card">
      <el-row :gutter="12" align="middle">
        <el-col :xs="24" :sm="12" :md="8">
          <el-input v-model="keyword" placeholder="搜索商品名称 / 条形码" clearable @change="load" prefix-icon="Search" />
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <el-select v-model="filterCat" placeholder="所有分类" clearable @change="load" style="width:100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="正面图" width="80" align="center">
          <template #default="{ row }">
            <el-image
              v-if="row.image_front || row.image"
              :src="row.image_front || row.image"
              :preview-src-list="[row.image_front || row.image, row.image_back].filter(Boolean)"
              style="width:40px;height:40px;border-radius:4px;object-fit:cover"
              fit="cover"
            />
            <el-icon v-else size="30" color="#ddd"><Picture /></el-icon>
          </template>
        </el-table-column>
        <el-table-column label="背面图" width="80" align="center">
          <template #default="{ row }">
            <el-image
              v-if="row.image_back"
              :src="row.image_back"
              :preview-src-list="[row.image_front || row.image, row.image_back].filter(Boolean)"
              style="width:40px;height:40px;border-radius:4px;object-fit:cover"
              fit="cover"
            />
            <el-icon v-else size="30" color="#ddd"><Picture /></el-icon>
          </template>
        </el-table-column>
        <el-table-column label="条形码" prop="barcode" min-width="150" />
        <el-table-column label="商品名称" min-width="130">
          <template #default="{ row }">{{ row.name || '-' }}</template>
        </el-table-column>
        <el-table-column label="分类" prop="category_name" width="100" />
        <el-table-column label="单位" prop="unit" width="70" align="center" />
        <el-table-column label="单价" prop="price" width="90" align="right">
          <template #default="{ row }">¥{{ Number(row.price || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="数量" prop="quantity" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="(row.quantity || 0) > 0 ? 'success' : 'info'" size="small">{{ row.quantity || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除该商品？" @confirm="remove(row.id)">
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑商品' : '新增商品'" width="520px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef">
        <!-- 条形码行 -->
        <el-form-item prop="barcode">
          <el-input v-model="form.barcode" placeholder="条形码（必填）" size="large" clearable>
            <template #append>
              <el-button @click="openScanDialog">
                <el-icon><Camera /></el-icon> 扫码
              </el-button>
            </template>
          </el-input>
        </el-form-item>

        <!-- 正面图 / 背面图 -->
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item prop="image_front" style="display:block">
              <div class="img-label">正面图</div>
              <div class="image-upload-area large" @click="triggerUpload('front')">
                <img v-if="form.image_front" :src="form.image_front" class="preview-img" />
                <div v-else class="upload-placeholder">
                  <el-icon size="36" color="#4a5a72"><Camera /></el-icon>
                  <div class="upload-tip">点击上传正面图</div>
                </div>
              </div>
              <input ref="fileInputFront" type="file" accept="image/*" capture="environment" style="display:none" @change="handleImageUpload($event, 'front')" />
              <el-button v-if="form.image_front" size="small" type="danger" text style="margin-top:4px" @click="form.image_front = null">移除</el-button>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item prop="image_back" style="display:block">
              <div class="img-label">背面图</div>
              <div class="image-upload-area large" @click="triggerUpload('back')">
                <img v-if="form.image_back" :src="form.image_back" class="preview-img" />
                <div v-else class="upload-placeholder">
                  <el-icon size="36" color="#4a5a72"><Camera /></el-icon>
                  <div class="upload-tip">点击上传背面图</div>
                </div>
              </div>
              <input ref="fileInputBack" type="file" accept="image/*" capture="environment" style="display:none" @change="handleImageUpload($event, 'back')" />
              <el-button v-if="form.image_back" size="small" type="danger" text style="margin-top:4px" @click="form.image_back = null">移除</el-button>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="scanVisible" title="摄像头扫描条形码" width="640px" @closed="stopScan">
      <div class="scan-box">
        <video ref="videoRef" class="scan-video" autoplay playsinline muted />
        <div class="scan-tip">请将条形码置于画面中央，识别后会自动填充</div>
      </div>
      <template #footer>
        <el-button @click="scanVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 拍照扫码降级方案（iOS Safari / 非安全上下文）-->
    <input
      ref="cameraInputRef"
      type="file"
      accept="image/*"
      capture="environment"
      style="display:none"
      @change="handleCameraCapture"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { productApi, categoryApi } from '@/api/index.js'

const list = ref([])
const loading = ref(false)
const categories = ref([])
const keyword = ref('')
const filterCat = ref(null)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref()
const fileInputFront = ref()
const fileInputBack = ref()

const scanVisible = ref(false)
const videoRef = ref()
const cameraInputRef = ref()
let mediaStream = null
let scanTimer = null
let zxingControls = null
let warnedNonBarcode = false
const SCAN_INTERVAL_MS = 120
const CAMERA_CONSTRAINTS = {
  video: {
    facingMode: { ideal: 'environment' },
    width: { ideal: 1280 },
    height: { ideal: 720 },
    frameRate: { ideal: 30, max: 60 }
  },
  audio: false
}

const form = ref({
  id: null,
  barcode: '',
  name: '',
  category_id: null,
  unit: '件',
  price: 0,
  quantity: 0,
  description: '',
  image_front: null,
  image_back: null
})

const rules = {
  barcode: [{ required: true, message: '请填写或扫描条形码', trigger: 'blur' }],
  image_front: [{ validator: (_, val, cb) => val ? cb() : cb(new Error('请拍摄或上传正面图')), trigger: 'change' }],
  image_back: [{ validator: (_, val, cb) => val ? cb() : cb(new Error('请拍摄或上传背面图')), trigger: 'change' }]
}

const allowedBarcodeFormats = new Set([
  'EAN_13',
  'EAN_8',
  'UPC_A',
  'UPC_E',
  'CODE_128',
  'CODE_39'
])

function isAllowedBarcode(formatValue) {
  const name = String(formatValue || '')
  return allowedBarcodeFormats.has(name)
}

function isIpadSafari() {
  const ua = navigator.userAgent || ''
  const platform = navigator.platform || ''
  const isIpad = /iPad/i.test(ua) || (platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  const isSafari = /Safari/i.test(ua) && !/CriOS|FxiOS|EdgiOS|Chrome/i.test(ua)
  return isIpad && isSafari
}

function normalizeBarcodeText(rawText) {
  const text = String(rawText || '').trim()
  if (!text) return ''

  // 常见场景：条码被识别成 "6 979215 474736" 或夹杂符号
  const digits = text.replace(/[^\d]/g, '')
  if ([8, 12, 13, 14].includes(digits.length)) return digits

  // 如果整段文本里包含可用长度的数字片段，也尝试提取
  const hit = text.match(/\d{8}|\d{12}|\d{13}|\d{14}/g)
  if (hit?.length) {
    const best = hit.sort((a, b) => b.length - a.length)[0]
    return best || ''
  }
  return ''
}

async function load() {
  loading.value = true
  const params = {}
  if (keyword.value) params.keyword = keyword.value
  if (filterCat.value) params.category_id = filterCat.value
  list.value = await productApi.list(params).finally(() => (loading.value = false))
}

function openDialog(row = null) {
  form.value = row
    ? {
        id: row.id,
        barcode: row.barcode || '',
        name: row.name || null,
        sku: row.sku || null,
        category_id: row.category_id || null,
        unit: row.unit || null,
        price: row.price || null,
        description: row.description || null,
        image_front: row.image_front || row.image || null,
        image_back: row.image_back || null
      }
    : {
        id: null,
        barcode: '',
        name: null,
        sku: null,
        category_id: null,
        unit: null,
        price: null,
        description: null,
        image_front: null,
        image_back: null
      }
  dialogVisible.value = true
}

function triggerUpload(side) {
  if (side === 'front') fileInputFront.value?.click()
  else fileInputBack.value?.click()
}

function handleImageUpload(e, side) {
  const file = e.target.files?.[0]
  if (!file) return
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.warning('图片不能超过5MB')
    return
  }
  const reader = new FileReader()
  reader.onload = (ev) => {
    if (side === 'front') {
      form.value.image_front = ev.target.result
      formRef.value?.validateField('image_front')
    } else {
      form.value.image_back = ev.target.result
      formRef.value?.validateField('image_back')
    }
  }
  reader.readAsDataURL(file)
  e.target.value = ''
}

async function submit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    const payload = { ...form.value }
    if (payload.id) await productApi.update(payload.id, payload)
    else await productApi.create(payload)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } finally {
    submitting.value = false
  }
}

async function remove(id) {
  await productApi.remove(id)
  ElMessage.success('删除成功')
  load()
}

async function openScanDialog() {
  stopScan()
  warnedNonBarcode = false

  // 非安全上下文（HTTP + IP）或浏览器不支持 getUserMedia → 降级为拍照识别
  const canStream = !!(navigator.mediaDevices?.getUserMedia) && !!window.isSecureContext
  if (!canStream) {
    cameraInputRef.value.value = ''
    cameraInputRef.value.click()
    return
  }

  scanVisible.value = true
  await nextTick()

  const preferZXing = isIpadSafari()
  if (preferZXing) {
    await openScanWithZXing()
    return
  }

  if ('BarcodeDetector' in window) {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia(CAMERA_CONSTRAINTS)
      videoRef.value.srcObject = mediaStream
      const detector = new window.BarcodeDetector({
        formats: ['ean_13', 'ean_8', 'code_128', 'code_39', 'upc_a', 'upc_e']
      })

      scanTimer = setInterval(async () => {
        if (!videoRef.value || videoRef.value.readyState < 2) return
        const barcodes = await detector.detect(videoRef.value)
        if (barcodes?.length) {
          const hit = barcodes.find((item) => isAllowedBarcode(item.format))
          if (!hit) return
          const barcode = normalizeBarcodeText(hit.rawValue)
          if (!barcode) return
          form.value.barcode = barcode
          ElMessage.success('扫码成功')
          scanVisible.value = false
        }
      }, SCAN_INTERVAL_MS)
      return
    } catch (err) {
      // 回退到 ZXing
    }
  }

  await openScanWithZXing()
}

async function openScanWithZXing() {
  try {
    const { BrowserMultiFormatReader } = await import('@zxing/browser')
    const reader = new BrowserMultiFormatReader()
    zxingControls = await reader.decodeFromConstraints(
      CAMERA_CONSTRAINTS,
      videoRef.value,
      (result) => {
        if (result) {
          const format = result.getBarcodeFormat?.()
          const rawText = result.getText?.() || ''
          const barcode = normalizeBarcodeText(rawText)

          // 优先接受明确的一维条码；其次允许纯数字可用条码串
          if (!isAllowedBarcode(format) && !barcode) {
            if (!warnedNonBarcode) {
              warnedNonBarcode = true
              ElMessage.warning('当前识别到二维码/无效码，请稍微靠近并对准左侧一维条形码')
            }
            return
          }
          if (!barcode) return
          form.value.barcode = barcode
          ElMessage.success('扫码成功')
          scanVisible.value = false
        }
      }
    )
  } catch (err) {
    ElMessage.error('无法打开摄像头扫码，请检查浏览器摄像头权限（地址栏右侧）后重试。')
  }
}

function stopScan() {
  if (scanTimer) {
    clearInterval(scanTimer)
    scanTimer = null
  }
  if (zxingControls) {
    zxingControls.stop()
    zxingControls = null
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop())
    mediaStream = null
  }
}

async function handleCameraCapture(e) {
  const file = e.target.files?.[0]
  if (!file) return
  e.target.value = ''

  const url = URL.createObjectURL(file)
  try {
    const { BrowserMultiFormatReader } = await import('@zxing/browser')
    const reader = new BrowserMultiFormatReader()
    const result = await reader.decodeFromImageUrl(url)
    const rawText = result?.getText?.() || ''
    const barcode = normalizeBarcodeText(rawText)
    if (barcode) {
      form.value.barcode = barcode
      ElMessage.success('扫码成功')
    } else {
      ElMessage.warning('未能识别条形码，请重试并确保照片清晰对准条形码')
    }
  } catch {
    ElMessage.warning('未能识别条形码，请重试并确保照片清晰对准条形码')
  } finally {
    URL.revokeObjectURL(url)
  }
}

onBeforeUnmount(stopScan)

onMounted(async () => {
  categories.value = await categoryApi.list()
  load()
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-title { font-size: 20px; font-weight: 600; }
.search-card { margin-bottom: 16px; border-radius: 8px; }
.table-card { border-radius: 8px; }

.image-upload-area {
  width: 120px;
  height: 120px;
  border: 2px dashed #3b4961;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  transition: border-color 0.2s;
}
.image-upload-area.large {
  width: 100%;
  height: 180px;
}
.image-upload-area:hover { border-color: #409EFF; }
.preview-img { width: 100%; height: 100%; object-fit: cover; }
.upload-placeholder { text-align: center; }
.upload-tip { font-size: 12px; color: #8e9bb3; margin-top: 8px; }
.img-label { font-size: 13px; color: #8e9bb3; margin-bottom: 8px; }

.scan-box { display: flex; flex-direction: column; gap: 10px; }
.scan-video {
  width: 100%;
  max-height: 360px;
  border-radius: 8px;
  background: #000;
  border: 1px solid #2a3446;
}
.scan-tip { color: #9aa7be; font-size: 13px; text-align: center; }
</style>
