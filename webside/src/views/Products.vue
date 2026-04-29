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
          <el-input v-model="keyword" placeholder="搜索商品名称 / SKU / 条形码" clearable @change="load" prefix-icon="Search" />
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
        <el-table-column label="SKU" prop="sku" width="120" />
        <el-table-column label="分类" prop="category_name" width="100" />
        <el-table-column label="单位" prop="unit" width="70" align="center" />
        <el-table-column label="单价" prop="price" width="90" align="right">
          <template #default="{ row }">¥{{ Number(row.price || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="总库存" prop="total_stock" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.total_stock > 0 ? 'success' : 'info'" size="small">{{ row.total_stock }}</el-tag>
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

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑商品' : '新增商品'" width="760px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="90px">
        <el-row :gutter="16">
          <el-col :span="14">
            <el-form-item label="条形码" prop="barcode">
              <el-input v-model="form.barcode" placeholder="条形码必填" clearable>
                <template #append>
                  <el-button @click="openScanDialog"><el-icon><Camera /></el-icon> 扫码</el-button>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item label="商品名称">
              <el-input v-model="form.name" placeholder="可选" />
            </el-form-item>

            <el-form-item label="SKU编码">
              <el-input v-model="form.sku" placeholder="可选，如：P-001" />
            </el-form-item>

            <el-form-item label="分类">
              <el-select v-model="form.category_id" placeholder="选择分类" clearable style="width:100%">
                <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </el-form-item>

            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="单位">
                  <el-input v-model="form.unit" placeholder="件" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="单价">
                  <el-input-number v-model="form.price" :min="0" :precision="2" style="width:100%" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-col>

          <el-col :span="10">
            <el-form-item label="正面图">
              <div class="image-upload-area" @click="triggerUpload('front')">
                <img v-if="form.image_front" :src="form.image_front" class="preview-img" />
                <div v-else class="upload-placeholder">
                  <el-icon size="28" color="#ccc"><Camera /></el-icon>
                  <div class="upload-tip">点击上传正面图</div>
                </div>
              </div>
              <input ref="fileInputFront" type="file" accept="image/*" style="display:none" @change="handleImageUpload($event, 'front')" />
              <el-button v-if="form.image_front" size="small" type="danger" text @click="form.image_front = null">移除</el-button>
            </el-form-item>

            <el-form-item label="背面图">
              <div class="image-upload-area" @click="triggerUpload('back')">
                <img v-if="form.image_back" :src="form.image_back" class="preview-img" />
                <div v-else class="upload-placeholder">
                  <el-icon size="28" color="#ccc"><Camera /></el-icon>
                  <div class="upload-tip">点击上传背面图</div>
                </div>
              </div>
              <input ref="fileInputBack" type="file" accept="image/*" style="display:none" @change="handleImageUpload($event, 'back')" />
              <el-button v-if="form.image_back" size="small" type="danger" text @click="form.image_back = null">移除</el-button>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="可选商品描述" />
        </el-form-item>
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
let mediaStream = null
let scanTimer = null
let zxingControls = null

const form = ref({
  id: null,
  barcode: '',
  name: '',
  sku: '',
  category_id: null,
  unit: '件',
  price: 0,
  description: '',
  image_front: null,
  image_back: null
})

const rules = {
  barcode: [{ required: true, message: '请填写或扫描条形码', trigger: 'blur' }]
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
        name: row.name || '',
        sku: row.sku || '',
        category_id: row.category_id || null,
        unit: row.unit || '件',
        price: row.price || 0,
        description: row.description || '',
        image_front: row.image_front || row.image || null,
        image_back: row.image_back || null
      }
    : {
        id: null,
        barcode: '',
        name: '',
        sku: '',
        category_id: null,
        unit: '件',
        price: 0,
        description: '',
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
    if (side === 'front') form.value.image_front = ev.target.result
    else form.value.image_back = ev.target.result
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
  scanVisible.value = true
  await nextTick()

  if ('BarcodeDetector' in window) {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
      videoRef.value.srcObject = mediaStream
      const detector = new window.BarcodeDetector({
        formats: ['ean_13', 'ean_8', 'code_128', 'code_39', 'upc_a', 'upc_e']
      })

      scanTimer = setInterval(async () => {
        if (!videoRef.value || videoRef.value.readyState < 2) return
        const barcodes = await detector.detect(videoRef.value)
        if (barcodes?.length) {
          form.value.barcode = barcodes[0].rawValue || ''
          ElMessage.success('扫码成功')
          scanVisible.value = false
        }
      }, 300)
      return
    } catch (err) {
      // 回退到 ZXing
    }
  }

  await openScanWithZXing()
}

async function openScanWithZXing() {
  try {
    const { BrowserMultiFormatReader, BarcodeFormat, DecodeHintType } = await import('@zxing/browser')
    const hints = new Map()
    hints.set(DecodeHintType.POSSIBLE_FORMATS, [
      BarcodeFormat.EAN_13,
      BarcodeFormat.EAN_8,
      BarcodeFormat.CODE_128,
      BarcodeFormat.CODE_39,
      BarcodeFormat.UPC_A,
      BarcodeFormat.UPC_E
    ])
    const reader = new BrowserMultiFormatReader(hints)

    zxingControls = await reader.decodeFromConstraints(
      { video: { facingMode: { ideal: 'environment' } } },
      videoRef.value,
      (result) => {
        if (result) {
          form.value.barcode = result.getText() || ''
          ElMessage.success('扫码成功')
          scanVisible.value = false
        }
      }
    )
  } catch (err) {
    ElMessage.error('无法打开摄像头扫码。iPad 请确认使用 Safari 并允许摄像头权限。')
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
.image-upload-area:hover { border-color: #409EFF; }
.preview-img { width: 100%; height: 100%; object-fit: cover; }
.upload-placeholder { text-align: center; }
.upload-tip { font-size: 12px; color: #8e9bb3; margin-top: 6px; }

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
