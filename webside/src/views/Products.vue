<template>
  <div>
    <div class="page-header">
      <span class="page-title">商品管理</span>
      <div class="header-actions">
        <el-button type="success" @click="openContScan">
          <el-icon><VideoCamera /></el-icon> 扫描条形码
        </el-button>
      </div>
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
      <div class="table-scroll">
      <el-table :data="pagedList" v-loading="loading" stripe>
        <el-table-column label="正面图" width="80" align="center">
          <template #default="{ row }">
            <el-image
              v-if="row.image_front || row.image"
              :src="row.image_front || row.image"
              :preview-src-list="[row.image_front || row.image]"
              :hide-on-click-modal="true"
              :preview-teleported="true"
              :z-index="4000"
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
              :preview-src-list="[row.image_back]"
              :hide-on-click-modal="true"
              :preview-teleported="true"
              :z-index="4000"
              style="width:40px;height:40px;border-radius:4px;object-fit:cover"
              fit="cover"
            />
            <el-icon v-else size="30" color="#ddd"><Picture /></el-icon>
          </template>
        </el-table-column>
        <el-table-column label="条形码" prop="barcode" min-width="150" />
        <el-table-column label="商品名称" min-width="130">
          <template #default="{ row }">
            <el-input
              v-if="isEditing(row, 'name')"
              v-model="editingValue"
              size="small"
              class="inline-input"
              @keyup.enter="saveInlineEdit(row, 'name')"
              @blur="saveInlineEdit(row, 'name')"
            />
            <div v-else class="editable-cell" @click="startInlineEdit(row, 'name')">{{ row.name || '-' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="分类" prop="category_name" width="100" />
        <el-table-column label="所属仓库" min-width="150">
          <template #default="{ row }">{{ row.warehouse_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="单位" prop="unit" width="90" align="center">
          <template #default="{ row }">
            <div class="cell-center">{{ row.unit || '-' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="单价" prop="price" width="90" align="right">
          <template #default="{ row }">
            <div class="cell-right">¥{{ Number(row.price || 0).toFixed(2) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="数量" prop="quantity" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="(row.quantity || 0) > 0 ? 'success' : 'info'" size="small">
              {{ row.quantity || 0 }}
            </el-tag>
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
      <div class="table-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          layout="total, prev, pager, next"
          :total="list.length"
          :pager-count="5"
        />
      </div>
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? '编辑商品' : '新增商品'"
      :width="isMobile ? '94vw' : '520px'"
      class="product-dialog"
      destroy-on-close
    >
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
        <el-form-item label="所属仓库" prop="warehouse_id">
          <el-select v-model="form.warehouse_id" clearable :filterable="!isIOS" placeholder="请选择仓库" style="width:100%">
            <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :xs="24" :sm="8">
            <el-form-item label="单位" prop="unit">
              <el-input v-model="form.unit" placeholder="如：件/盒/瓶" clearable />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="8">
            <el-form-item label="单价" prop="price">
              <el-input-number v-model="form.price" :min="0" :precision="2" :step="0.1" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="8">
            <el-form-item label="数量" prop="quantity">
              <el-input-number v-model="form.quantity" :min="0" :precision="0" :step="1" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 正面图 / 背面图 -->
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
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
          <el-col :xs="24" :sm="12">
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
        <div class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit" :loading="submitting">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="scanVisible"
      title="摄像头扫描条形码"
      :width="isMobile ? '94vw' : '640px'"
      class="scan-dialog"
      @closed="stopScan"
    >
      <div class="scan-box">
        <video ref="videoRef" class="scan-video" autoplay playsinline muted />
        <div class="scan-tip">
          <span v-if="scanning" class="scanning-hint">识别中…</span>
          <span v-else>请将条形码置于画面中央，识别后会自动填充</span>
        </div>
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

    <!-- ===== 连续扫码对话框 ===== -->
    <el-dialog
      v-model="contScanVisible"
      title="扫描条形码"
      :width="isMobile ? '94vw' : '580px'"
      class="scan-dialog"
      @closed="stopContScan"
    >
      <!-- 扫码中：显示摄像头 -->
      <div v-show="contState === 'scanning'" class="scan-box">
        <video ref="contVideoRef" class="scan-video" autoplay playsinline muted />
        <div class="scan-tip">
          <span v-if="contScanning" class="scanning-hint">识别中…</span>
          <span v-else>将条形码对准摄像头，自动识别</span>
        </div>
      </div>

      <!-- iOS / HTTP 降级：拍照按钮 -->
      <div v-if="contState === 'ios-fallback'" class="ios-fallback-box">
        <el-icon size="50" color="#4a5a72"><Camera /></el-icon>
        <p style="color:#8e9bb3;margin:12px 0">当前环境不支持实时扫码，请拍照识别</p>
        <el-button type="primary" @click="triggerContCapture">拍照识别</el-button>
        <input ref="contCameraRef" type="file" accept="image/*" capture="environment" style="display:none" @change="handleContCapture" />
      </div>

      <!-- 找到商品 -->
      <div v-if="contState === 'found'" class="cont-result">
        <div class="barcode-tag">
          <el-icon><Tickets /></el-icon>
          <span>{{ contBarcode }}</span>
        </div>
        <div class="product-images-row">
          <div v-if="contProduct.image_front" class="result-img-wrap">
            <span class="img-side-label">正面</span>
            <img :src="contProduct.image_front" class="result-img" />
          </div>
          <div v-if="contProduct.image_back" class="result-img-wrap">
            <span class="img-side-label">背面</span>
            <img :src="contProduct.image_back" class="result-img" />
          </div>
          <div v-if="!contProduct.image_front && !contProduct.image_back" class="no-image-placeholder">
            <el-icon size="40" color="#4a5a72"><Picture /></el-icon>
            <p>暂无图片</p>
          </div>
        </div>
        <div class="product-meta">
          <span class="product-meta-name">{{ contProduct.name || '(未命名)' }}</span>
          <el-tag type="info" size="small">当前库存 {{ contProduct.quantity ?? 0 }} 件</el-tag>
        </div>
        <div class="cont-actions">
          <el-button @click="resumeContScan">继续扫码</el-button>
          <el-button type="primary" size="large" :loading="contConfirming" @click="confirmStockIn">
            确认入库 +1
          </el-button>
        </div>
      </div>

      <!-- 未找到商品 -->
      <div v-if="contState === 'notfound'" class="cont-result">
        <div class="barcode-tag">
          <el-icon><Tickets /></el-icon>
          <span>{{ contBarcode }}</span>
        </div>
        <div class="notfound-box">
          <el-icon size="44" color="#e6a23c"><Warning /></el-icon>
          <p>该条形码尚未登记商品</p>
        </div>
        <div class="cont-actions">
          <el-button @click="resumeContScan">继续扫码</el-button>
          <el-button type="primary" @click="openAddFromScan">新增商品</el-button>
        </div>
      </div>

      <template #footer>
        <el-button @click="contScanVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { productApi, categoryApi, warehouseApi, scanApi } from '@/api/index.js'

const list = ref([])
const loading = ref(false)
const categories = ref([])
const warehouses = ref([])
const keyword = ref('')
const filterCat = ref(null)
const currentPage = ref(1)
const pageSize = 10
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref()
const fileInputFront = ref()
const fileInputBack = ref()

const scanVisible = ref(false)
const scanning = ref(false)
const videoRef = ref()
const cameraInputRef = ref()
const isMobile = ref(false)
const isIOS = ref(false)
const editingCell = ref('')
const editingValue = ref('')
const savingInlineCell = ref('')
let mediaStream = null
let scanTimer = null

// ---- 连续扫码状态 ----
const contScanVisible = ref(false)
const contState = ref('scanning')   // 'scanning' | 'found' | 'notfound' | 'ios-fallback'
const contBarcode = ref('')
const contProduct = ref(null)
const contWarehouseId = ref(null)
const contScanning = ref(false)
const contConfirming = ref(false)
const contVideoRef = ref()
const contCameraRef = ref()
const contScanMode = ref('stream') // 'stream' | 'fallback'
let contStream = null
let contTimer = null
const SCAN_INTERVAL_MS = 500
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

function updateViewportState() {
  isMobile.value = window.matchMedia('(max-width: 768px)').matches
  const ua = navigator.userAgent || ''
  const platform = navigator.platform || ''
  isIOS.value = /iPhone|iPad|iPod/i.test(ua) || (platform === 'MacIntel' && navigator.maxTouchPoints > 1)
}

function getCellKey(row, field) {
  return `${row.id}:${field}`
}

function isEditing(row, field) {
  return editingCell.value === getCellKey(row, field)
}

function startInlineEdit(row, field) {
  editingCell.value = getCellKey(row, field)
  const currentValue = row[field]
  editingValue.value = currentValue === null || currentValue === undefined ? '' : String(currentValue)
}

function normalizeInlineValue(field, rawValue) {
  const value = String(rawValue ?? '').trim()
  if (field === 'name') {
    return value || null
  }
  return value || null
}

async function saveInlineEdit(row, field) {
  const key = getCellKey(row, field)
  if (editingCell.value !== key || savingInlineCell.value === key) return
  let newValue
  try {
    newValue = normalizeInlineValue(field, editingValue.value)
  } catch (err) {
    ElMessage.warning(err.message || '输入格式不正确')
    editingCell.value = ''
    editingValue.value = ''
    return
  }
  if (row[field] === newValue) {
    editingCell.value = ''
    editingValue.value = ''
    return
  }
  savingInlineCell.value = key
  try {
    await productApi.update(row.id, { [field]: newValue })
    row[field] = newValue
    ElMessage.success('已更新')
  } finally {
    if (editingCell.value === key) {
      editingCell.value = ''
      editingValue.value = ''
    }
    savingInlineCell.value = ''
  }
}

/** 从指定 video 元素抓一帧，返回 Blob（JPEG） */
function captureFrame(videoElRef = videoRef) {
  const video = videoElRef.value
  if (!video || video.readyState < 2 || !video.videoWidth) return null
  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  canvas.getContext('2d').drawImage(video, 0, 0)
  return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.85))
}

async function load() {
  loading.value = true
  const params = {}
  if (keyword.value) params.keyword = keyword.value
  if (filterCat.value) params.category_id = filterCat.value
  list.value = await productApi.list(params).finally(() => (loading.value = false))
  currentPage.value = 1
}

const pagedList = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return list.value.slice(start, start + pageSize)
})

function openDialog(row = null) {
  form.value = row
    ? {
        id: row.id,
        barcode: row.barcode || '',
        name: row.name || null,
        sku: row.sku || null,
        category_id: row.category_id || null,
        warehouse_id: row.warehouse_id || null,
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
        warehouse_id: null,
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
  scanning.value = false

  // 非安全上下文（HTTP + IP）或浏览器不支持 getUserMedia → 降级为拍照后送后端识别
  const canStream = !!(navigator.mediaDevices?.getUserMedia) && !!window.isSecureContext
  if (!canStream) {
    cameraInputRef.value.value = ''
    cameraInputRef.value.click()
    return
  }

  scanVisible.value = true
  await nextTick()

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia(CAMERA_CONSTRAINTS)
    videoRef.value.srcObject = mediaStream

    // 等视频就绪后再开始抓帧
    await new Promise((resolve) => {
      videoRef.value.onloadedmetadata = resolve
    })

    scanTimer = setInterval(async () => {
      if (!scanVisible.value || scanning.value) return
      const blob = await captureFrame()
      if (!blob) return
      scanning.value = true
      try {
        const res = await scanApi.scanBarcode(blob)
        if (res?.found && res.barcode) {
          form.value.barcode = res.barcode
          ElMessage.success(`扫码成功：${res.barcode}`)
          scanVisible.value = false
        }
      } catch {
        // 识别失败时静默，继续下一帧
      } finally {
        scanning.value = false
      }
    }, SCAN_INTERVAL_MS)
  } catch {
    ElMessage.error('无法打开摄像头，请检查浏览器摄像头权限后重试。')
    scanVisible.value = false
  }
}

function stopScan() {
  if (scanTimer) {
    clearInterval(scanTimer)
    scanTimer = null
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop())
    mediaStream = null
  }
  scanning.value = false
}

/** iOS Safari / 非安全上下文：拍照后将图片文件送后端识别 */
async function handleCameraCapture(e) {
  const file = e.target.files?.[0]
  if (!file) return
  e.target.value = ''

  try {
    const res = await scanApi.scanBarcode(file)
    if (res?.found && res.barcode) {
      form.value.barcode = res.barcode
      ElMessage.success(`扫码成功：${res.barcode}`)
    } else {
      ElMessage.warning('未能识别条形码，请确保照片清晰并对准条形码')
    }
  } catch {
    ElMessage.warning('识别请求失败，请检查网络连接后重试')
  }
}

// ============ 连续扫码函数 ============

async function openContScan() {
  stopContScan()
  contBarcode.value = ''
  contProduct.value = null
  contState.value = 'scanning'
  contScanVisible.value = true
  await nextTick()

  const canStream = !!(navigator.mediaDevices?.getUserMedia) && !!window.isSecureContext
  if (!canStream) {
    contScanMode.value = 'fallback'
    contState.value = 'ios-fallback'
    return
  }
  contScanMode.value = 'stream'

  try {
    contStream = await navigator.mediaDevices.getUserMedia(CAMERA_CONSTRAINTS)
    contVideoRef.value.srcObject = contStream
    await new Promise((resolve) => { contVideoRef.value.onloadedmetadata = resolve })
    startContTimer()
  } catch {
    ElMessage.error('无法打开摄像头，请检查权限后重试')
    contScanVisible.value = false
  }
}

function startContTimer() {
  contTimer = setInterval(async () => {
    if (contState.value !== 'scanning' || contScanning.value) return
    const blob = await captureFrame(contVideoRef)
    if (!blob) return
    contScanning.value = true
    try {
      const res = await scanApi.scanBarcode(blob)
      if (res?.found && res.barcode) {
        await handleContBarcode(res.barcode)
      }
    } catch { /* 静默失败，继续扫 */ } finally {
      contScanning.value = false
    }
  }, SCAN_INTERVAL_MS)
}

async function handleContBarcode(barcode) {
  // 停止扫码循环，等待用户操作
  clearInterval(contTimer)
  contTimer = null
  contBarcode.value = barcode

  try {
    const res = await productApi.findByBarcode(barcode)
    if (res?.found) {
      contProduct.value = res.product
      contState.value = 'found'
    } else {
      contState.value = 'notfound'
    }
  } catch {
    ElMessage.error('查询商品失败，请检查网络连接')
    contState.value = 'notfound'
  }
}

function resumeContScan() {
  contBarcode.value = ''
  contProduct.value = null
  if (contScanMode.value === 'fallback') {
    contState.value = 'ios-fallback'
    triggerContCapture()
    return
  }
  contState.value = 'scanning'
  if (contStream) {
    startContTimer()
  }
}

async function confirmStockIn() {
  contConfirming.value = true
  try {
    const res = await productApi.stockIn(contProduct.value.id, {
      quantity: 1,
      remark: '连续扫码入库'
    })
    ElMessage.success(`入库成功，当前库存：${res.new_quantity} 件`)
    load()
    resumeContScan()
  } catch {
    // 错误由 axios 拦截器统一提示
  } finally {
    contConfirming.value = false
  }
}

function openAddFromScan() {
  const barcode = contBarcode.value
  contScanVisible.value = false
  openDialog()
  // nextTick 等对话框挂载后再填写 barcode
  nextTick(() => { form.value.barcode = barcode })
}

function stopContScan() {
  clearInterval(contTimer)
  contTimer = null
  if (contStream) {
    contStream.getTracks().forEach((t) => t.stop())
    contStream = null
  }
  contScanning.value = false
}

function triggerContCapture() {
  contCameraRef.value.value = ''
  contCameraRef.value.click()
}

async function handleContCapture(e) {
  const file = e.target.files?.[0]
  if (!file) return
  e.target.value = ''
  contScanning.value = true
  try {
    const res = await scanApi.scanBarcode(file)
    if (res?.found && res.barcode) {
      await handleContBarcode(res.barcode)
    } else {
      ElMessage.warning('未识别到条形码，请重拍')
    }
  } catch {
    ElMessage.warning('识别失败，请重试')
  } finally {
    contScanning.value = false
  }
}

// ============ 生命周期 ============

onBeforeUnmount(stopScan)
onBeforeUnmount(stopContScan)

onMounted(async () => {
  updateViewportState()
  window.addEventListener('resize', updateViewportState)
  const [cats, whs] = await Promise.all([categoryApi.list(), warehouseApi.list()])
  categories.value = cats
  warehouses.value = whs
  load()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateViewportState)
  stopScan()
  stopContScan()
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-title { font-size: 20px; font-weight: 600; }
.search-card { margin-bottom: 16px; border-radius: 8px; }
.table-card { border-radius: 8px; }
.table-scroll { width: 100%; overflow-x: auto; }
.table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
.editable-cell {
  min-height: 24px;
  padding: 2px 6px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}
.editable-cell:hover {
  background: rgba(64, 158, 255, 0.12);
}
.inline-input { width: 100%; }
.cell-center { text-align: center; }
.cell-right { text-align: right; }

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
.scanning-hint { color: #409EFF; animation: pulse 1s infinite; }
@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }

/* ---- 连续扫码结果区 ---- */
.header-actions { display: flex; gap: 10px; }
.barcode-tag {
  display: inline-flex; align-items: center; gap: 8px;
  background: #1e2d42; border: 1px solid #3b4961; border-radius: 20px;
  padding: 6px 16px; font-size: 15px; font-weight: 600;
  color: #7eb8f7; margin-bottom: 16px;
}
.product-images-row {
  display: flex; gap: 12px; justify-content: center; margin-bottom: 14px;
}
.result-img-wrap {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
}
.img-side-label { font-size: 11px; color: #8e9bb3; }
.result-img { width: 130px; height: 130px; object-fit: cover; border-radius: 8px; border: 1px solid #2d3f56; }
.no-image-placeholder {
  display: flex; flex-direction: column; align-items: center;
  color: #4a5a72; padding: 20px;
}
.product-meta {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 4px;
}
.product-meta-name { font-size: 15px; font-weight: 600; color: #c8d8f0; }
.notfound-box {
  display: flex; flex-direction: column; align-items: center;
  padding: 24px 0; color: #e6a23c;
}
.notfound-box p { margin-top: 10px; font-size: 15px; }
.cont-result { display: flex; flex-direction: column; align-items: center; padding: 8px 0 4px; }
.cont-actions { display: flex; gap: 14px; margin-top: 20px; }
.ios-fallback-box { display: flex; flex-direction: column; align-items: center; padding: 32px 0; }

.scan-box { display: flex; flex-direction: column; gap: 10px; }
.scan-video {
  width: 100%;
  max-height: 360px;
  border-radius: 8px;
  background: #000;
  border: 1px solid #2a3446;
}
.scan-tip { color: #9aa7be; font-size: 13px; text-align: center; }

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  .page-title {
    font-size: 18px;
  }
  .add-btn {
    width: 100%;
  }
  .image-upload-area.large {
    height: 150px;
  }
  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }
  :deep(.product-dialog .el-dialog),
  :deep(.scan-dialog .el-dialog) {
    margin-top: 6vh !important;
  }
  :deep(.product-dialog .el-dialog__body),
  :deep(.scan-dialog .el-dialog__body) {
    padding: 14px;
  }
}
</style>
