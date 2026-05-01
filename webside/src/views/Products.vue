<template>
  <div>
    <el-card shadow="never" class="search-card">
      <el-row :gutter="0" align="middle" class="search-row">
        <el-col :xs="24" :md="16" class="search-left-group">
          <el-input v-model="keyword" class="search-input-control" placeholder="搜索商品名称 / 条形码" clearable @change="load" prefix-icon="Search" />
          <div class="search-filters-row">
            <el-select v-model="filterCat" class="search-select-control" placeholder="所有分类" clearable @change="load">
              <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
            <el-select v-model="filterWarehouse" class="search-select-control" placeholder="所有仓库" clearable @change="load">
              <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
            </el-select>
          </div>
        </el-col>
        <el-col :xs="24" :md="8" class="search-actions" :class="{ 'search-actions--ios': isIOS }">
          <template v-if="isIOS">
            <div class="search-actions-ios-row">
              <el-button type="success" @click="openContScan('in')">条码入库</el-button>
              <el-button type="danger" @click="openContScan('out')">条码出库</el-button>
              <el-button type="primary" @click="openLookupScan">条码寻找</el-button>
            </div>
            <div class="search-actions-ios-row">
              <el-button type="info" @click="openImageFind">拍照寻找</el-button>
              <el-button type="warning" @click="openNoBarcodeEntry">无码录入</el-button>
            </div>
          </template>
          <template v-else>
            <el-button type="success" @click="openContScan('in')">条码入库</el-button>
            <el-button type="danger" @click="openContScan('out')">条码出库</el-button>
            <el-button type="primary" @click="openLookupScan">条码寻找</el-button>
            <el-button type="info" @click="openImageFind">拍照寻找</el-button>
            <el-button type="warning" @click="openNoBarcodeEntry">无码录入</el-button>
          </template>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="table-scroll">
      <el-table :data="pagedList" v-loading="loading" stripe :size="isMobile ? 'small' : 'default'">
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
        <el-table-column label="游戏分类" width="120">
          <template #default="{ row }">
            <el-select
              v-if="editingCategoryRowId === row.id"
              :model-value="row.category_id"
              size="small"
              style="width: 100%"
              placeholder="选择分类"
              @change="saveCategoryInline(row, $event)"
              @visible-change="(v) => { if (!v) editingCategoryRowId = null }"
            >
              <el-option label="未分类" :value="null" />
              <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
            <div v-else class="editable-cell" @click="editingCategoryRowId = row.id">{{ row.category_name || '未分类' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="所属仓库" width="120">
          <template #default="{ row }">{{ row.warehouse_name || '-' }}</template>
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
        <el-table-column label="操作" :width="isMobile ? 180 : 240" :fixed="isMobile ? false : 'right'">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button size="small" type="success" @click="openOcrForRow(row)">OCR</el-button>
              <el-button size="small" @click="openDialog(row)">编辑</el-button>
              <el-popconfirm title="确认删除该商品？" @confirm="remove(row.id)">
                <template #reference>
                  <el-button size="small" type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
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
          <el-input
            v-model="form.barcode"
            placeholder="条形码（必填）"
            size="large"
            clearable
            :disabled="Boolean(form.id)"
          >
            <template #append>
              <el-button @click="openScanDialog">
                <el-icon><Camera /></el-icon> 扫码
              </el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="游戏分类" prop="category_id">
          <el-select v-model="form.category_id" clearable :filterable="!isIOS" placeholder="请选择分类" style="width:100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <div class="quick-create-row">
            <el-input
              v-model="newCategoryName"
              placeholder="输入新分类名称"
              clearable
              @keyup.enter="createCategoryQuick"
            />
            <el-button type="primary" plain @click="createCategoryQuick">新建分类</el-button>
          </div>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :xs="24" :sm="16">
            <el-form-item label="所属仓库" prop="warehouse_id">
              <el-select v-model="form.warehouse_id" clearable :filterable="!isIOS" placeholder="请选择仓库" style="width:100%">
                <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
              </el-select>
              <div class="quick-create-row">
                <el-input
                  v-model="newWarehouseName"
                  placeholder="输入新仓库名称"
                  clearable
                  @keyup.enter="createWarehouseQuick"
                />
                <el-button type="primary" plain @click="createWarehouseQuick">新建仓库</el-button>
              </div>
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
              <div class="img-actions">
                <el-button v-if="form.image_front" size="small" type="danger" text @click="form.image_front = null">移除</el-button>
                <el-button v-if="form.image_front" size="small" type="primary" text @click="openOcr('front')">OCR识别名称</el-button>
              </div>
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
              <div class="img-actions">
                <el-button v-if="form.image_back" size="small" type="danger" text @click="form.image_back = null">移除</el-button>
                <el-button v-if="form.image_back" size="small" type="primary" text @click="openOcr('back')">OCR识别名称</el-button>
              </div>
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
      :title="contAction === 'out' ? '条码出库' : '条码入库'"
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
      </div>

      <!-- 找到商品（须同时有 contProduct，避免二次入库时 contState 仍为 found 但 product 已清空导致渲染报错、弹窗空白） -->
      <div v-if="contState === 'found' && contProduct" class="cont-result">
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
          <el-tag size="small" effect="plain">所属仓库 {{ contProduct.warehouse_name || '未设置' }}</el-tag>
        </div>
        <div class="cont-actions">
          <el-button @click="resumeContScan">继续扫码</el-button>
          <el-button type="primary" size="large" :loading="contConfirming" @click="confirmContAction">
            {{ contAction === 'out' ? '确认出库 -1' : '确认入库 +1' }}
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
          <el-button v-if="contAction !== 'out'" type="primary" @click="openAddFromScan">新增商品</el-button>
        </div>
      </div>

      <template #footer>
        <el-button @click="contScanVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- ===== 条形码寻找对话框 ===== -->
    <el-dialog
      v-model="lookupScanVisible"
      title="条形码寻找"
      :width="isMobile ? '94vw' : '640px'"
      class="scan-dialog"
      @closed="stopLookupScan"
    >
      <div class="scan-box">
        <video ref="lookupVideoRef" class="scan-video" autoplay playsinline muted />
        <div class="scan-tip">
          <span v-if="lookupScanning" class="scanning-hint">识别中…</span>
          <span v-else>扫描后自动定位该条形码物品</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="triggerLookupCapture" v-if="lookupScanMode === 'fallback'">拍照识别</el-button>
        <el-button @click="lookupScanVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <input
      ref="lookupCameraRef"
      type="file"
      accept="image/*"
      capture="environment"
      style="display:none"
      @change="handleLookupCapture"
    />

    <input
      ref="imageFindCameraRef"
      type="file"
      accept="image/*"
      capture="environment"
      style="display:none"
      @change="handleImageFindCapture"
    />

    <!-- 双 input 轮换：iOS 上同一 file 连续拍照/选图时 change 可能不触发，换节点可稳定再次唤起 -->
    <input
      ref="contCameraRefA"
      type="file"
      accept="image/*"
      capture="environment"
      style="display:none"
      @change="handleContCapture"
    />
    <input
      ref="contCameraRefB"
      type="file"
      accept="image/*"
      capture="environment"
      style="display:none"
      @change="handleContCapture"
    />
    <!-- ===== OCR 框选弹窗 ===== -->
    <el-dialog
      v-model="ocrVisible"
      title="框选文字区域 → OCR识别名称"
      :width="isMobile ? '96vw' : '700px'"
      class="ocr-dialog"
      destroy-on-close
      @opened="initOcrCanvas"
    >
      <div v-if="ocrTargetRow" class="ocr-img-tabs">
        <el-button
          :type="ocrSide === 'front' ? 'primary' : 'default'"
          size="small"
          @click="switchOcrSide('front')"
          :disabled="!getOcrSrc('front')"
        >正面图</el-button>
        <el-button
          :type="ocrSide === 'back' ? 'primary' : 'default'"
          size="small"
          @click="switchOcrSide('back')"
          :disabled="!getOcrSrc('back')"
        >背面图</el-button>
      </div>
      <p class="ocr-hint">在图片上拖动框选要识别的文字区域，松手后自动识别写入商品名称</p>
      <div class="ocr-canvas-wrap" ref="ocrWrapRef">
        <canvas
          ref="ocrCanvasRef"
          class="ocr-canvas"
          @mousedown.prevent="ocrDragStart"
          @mousemove.prevent="ocrDragMove"
          @mouseup.prevent="ocrDragEnd"
          @mouseleave.prevent="ocrDragEnd"
          @touchstart.prevent="ocrDragStart"
          @touchmove.prevent="ocrDragMove"
          @touchend.prevent="ocrDragEnd"
        />
      </div>
      <div v-if="ocrLoading" class="ocr-loading">
        <span class="scanning-hint">识别中，请稍候…</span>
      </div>
      <template #footer>
        <el-button @click="ocrVisible = false">取消</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { inventoryApi, categoryApi, warehouseApi, scanApi, ocrApi } from '@/api/index.js'

const list = ref([])
const loading = ref(false)
const categories = ref([])
const warehouses = ref([])
const keyword = ref('')
const filterCat = ref(null)
const filterWarehouse = ref(null)
const currentPage = ref(1)
const pageSize = 15
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
const editingCategoryRowId = ref(null)
const newCategoryName = ref('')
const newWarehouseName = ref('')

// ---- OCR 状态 ----
const ocrVisible = ref(false)
const ocrSide = ref('front')
const ocrTargetRow = ref(null)  // 从列表行直接调用时存储 row
const ocrCanvasRef = ref()
const ocrWrapRef = ref()
const ocrLoading = ref(false)
let _ocrDrawing = false
let _ocrStart = { x: 0, y: 0 }
let _ocrRect = { x: 0, y: 0, w: 0, h: 0 }
let _ocrNativeImg = null
let mediaStream = null
let scanTimer = null

// ---- 连续扫码状态 ----
const contScanVisible = ref(false)
const contState = ref('scanning')   // 'scanning' | 'found' | 'notfound' | 'ios-fallback'
const contBarcode = ref('')
const contProduct = ref(null)
const contAction = ref('in') // 'in' | 'out'
const contWarehouseId = ref(null)
const contScanning = ref(false)
const contConfirming = ref(false)
const contVideoRef = ref()
const contCameraRefA = ref()
const contCameraRefB = ref()
const contScanMode = ref('stream') // 'stream' | 'fallback'
/** 下次拍照识别点击的 input（与另一路交替，缓解 iOS 重复选择同一 input 不触发 change） */
let contCaptureUseA = true
let contStream = null
let contTimer = null

// ---- 条形码寻找状态 ----
const lookupScanVisible = ref(false)
const lookupScanning = ref(false)
const lookupVideoRef = ref()
const lookupCameraRef = ref()
const imageFindCameraRef = ref()
const lookupScanMode = ref('stream') // 'stream' | 'fallback'
let lookupStream = null
let lookupTimer = null
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
  warehouse_id: null,
  price: 0,
  quantity: 1,
  description: '',
  image_front: null,
  image_back: null
})

const rules = {
  barcode: [{ required: true, message: '请填写或扫描条形码', trigger: 'blur' }],
  warehouse_id: [{ required: true, message: '请选择所属仓库', trigger: 'change' }],
  image_front: [{ validator: (_, val, cb) => val ? cb() : cb(new Error('请拍摄或上传正面图')), trigger: 'change' }],
  image_back: [{ validator: (_, val, cb) => val ? cb() : cb(new Error('请拍摄或上传背面图')), trigger: 'change' }]
}

function updateViewportState() {
  isMobile.value = window.matchMedia('(max-width: 768px)').matches
  const ua = navigator.userAgent || ''
  const platform = navigator.platform || ''
  isIOS.value = /iPhone|iPad|iPod/i.test(ua) || (platform === 'MacIntel' && navigator.maxTouchPoints > 1)
}

// ============ OCR 框选 ============

function getOcrSrc(side) {
  if (ocrTargetRow.value) {
    return side === 'front'
      ? (ocrTargetRow.value.image_front || ocrTargetRow.value.image)
      : ocrTargetRow.value.image_back
  }
  return side === 'front' ? form.value.image_front : form.value.image_back
}

function openOcr(side) {
  ocrTargetRow.value = null
  ocrSide.value = side
  _ocrReset()
  ocrVisible.value = true
}

function openOcrForRow(row) {
  ocrTargetRow.value = row
  // 优先正面，若无则背面
  ocrSide.value = (row.image_front || row.image) ? 'front' : 'back'
  _ocrReset()
  ocrVisible.value = true
}

function switchOcrSide(side) {
  ocrSide.value = side
  _ocrReset()
  initOcrCanvas()
}

function _ocrReset() {
  _ocrNativeImg = null
  _ocrDrawing = false
  _ocrRect = { x: 0, y: 0, w: 0, h: 0 }
}

async function initOcrCanvas() {
  await nextTick()
  const canvas = ocrCanvasRef.value
  const wrap = ocrWrapRef.value
  if (!canvas || !wrap) return
  const src = getOcrSrc(ocrSide.value)
  if (!src) return
  _ocrNativeImg = null
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  await new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      _ocrNativeImg = img
      canvas.width = wrap.clientWidth
      canvas.height = Math.round((img.naturalHeight / img.naturalWidth) * wrap.clientWidth)
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
      resolve()
    }
    img.onerror = reject
    img.src = src
  }).catch(() => {
    ElMessage.error('图片加载失败，无法进行 OCR')
  })
}

function _ocrGetPos(e) {
  const canvas = ocrCanvasRef.value
  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  let clientX, clientY
  if (e.touches && e.touches.length > 0) {
    clientX = e.touches[0].clientX
    clientY = e.touches[0].clientY
  } else if (e.changedTouches && e.changedTouches.length > 0) {
    clientX = e.changedTouches[0].clientX
    clientY = e.changedTouches[0].clientY
  } else {
    clientX = e.clientX
    clientY = e.clientY
  }
  return {
    x: Math.max(0, Math.min(canvas.width, Math.round((clientX - rect.left) * scaleX))),
    y: Math.max(0, Math.min(canvas.height, Math.round((clientY - rect.top) * scaleY))),
  }
}

function _ocrRedraw() {
  const canvas = ocrCanvasRef.value
  if (!canvas || !_ocrNativeImg) return
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.drawImage(_ocrNativeImg, 0, 0, canvas.width, canvas.height)
  const { x, y, w, h } = _ocrRect
  if (w > 2 && h > 2) {
    ctx.strokeStyle = '#409EFF'
    ctx.lineWidth = 2
    ctx.setLineDash([6, 3])
    ctx.strokeRect(x, y, w, h)
    ctx.fillStyle = 'rgba(64,158,255,0.12)'
    ctx.fillRect(x, y, w, h)
  }
}

function ocrDragStart(e) {
  _ocrDrawing = true
  _ocrStart = _ocrGetPos(e)
  _ocrRect = { x: _ocrStart.x, y: _ocrStart.y, w: 0, h: 0 }
}

function ocrDragMove(e) {
  if (!_ocrDrawing) return
  const cur = _ocrGetPos(e)
  _ocrRect = {
    x: Math.min(_ocrStart.x, cur.x),
    y: Math.min(_ocrStart.y, cur.y),
    w: Math.abs(cur.x - _ocrStart.x),
    h: Math.abs(cur.y - _ocrStart.y),
  }
  _ocrRedraw()
}

async function ocrDragEnd(e) {
  if (!_ocrDrawing) return
  _ocrDrawing = false
  const cur = _ocrGetPos(e)
  _ocrRect = {
    x: Math.min(_ocrStart.x, cur.x),
    y: Math.min(_ocrStart.y, cur.y),
    w: Math.abs(cur.x - _ocrStart.x),
    h: Math.abs(cur.y - _ocrStart.y),
  }
  _ocrRedraw()
  if (_ocrRect.w < 10 || _ocrRect.h < 10) return
  await _ocrSendRegion()
}

async function _ocrSendRegion() {
  if (!_ocrNativeImg) return
  const { x, y, w, h } = _ocrRect
  const canvas = ocrCanvasRef.value
  const scaleX = _ocrNativeImg.naturalWidth / canvas.width
  const scaleY = _ocrNativeImg.naturalHeight / canvas.height
  const crop = document.createElement('canvas')
  crop.width = Math.round(w * scaleX)
  crop.height = Math.round(h * scaleY)
  crop.getContext('2d').drawImage(
    _ocrNativeImg,
    Math.round(x * scaleX), Math.round(y * scaleY), crop.width, crop.height,
    0, 0, crop.width, crop.height
  )
  const base64 = crop.toDataURL('image/jpeg', 0.95)
  ocrLoading.value = true
  try {
    const res = await ocrApi.ocrRegion(base64)
    if (res?.text) {
      if (ocrTargetRow.value) {
        // 从列表行直接调用：直接保存到后端并更新行数据
        await inventoryApi.update(ocrTargetRow.value.id, { name: res.text })
        ocrTargetRow.value.name = res.text
        ElMessage.success(`识别成功并已保存：${res.text}`)
      } else {
        // 从编辑弹窗调用：写入表单
        form.value.name = res.text
        ElMessage.success(`识别成功：${res.text}`)
      }
      ocrVisible.value = false
    } else {
      ElMessage.warning('未识别到文字，请重新框选更清晰的区域')
    }
  } catch {
    ElMessage.error('OCR 识别失败，请确认后端已安装 easyocr 并已重启服务')
  } finally {
    ocrLoading.value = false
  }
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
    await inventoryApi.update(row.id, { [field]: newValue })
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

async function saveCategoryInline(row, categoryId) {
  const normalizedCategoryId = categoryId || null
  if ((row.category_id || null) === normalizedCategoryId) {
    editingCategoryRowId.value = null
    return
  }
  try {
    await inventoryApi.update(row.id, { category_id: normalizedCategoryId })
    row.category_id = normalizedCategoryId
    const matched = categories.value.find((c) => c.id === normalizedCategoryId)
    row.category_name = matched?.name || null
    ElMessage.success('游戏分类已更新')
  } finally {
    editingCategoryRowId.value = null
  }
}

async function createCategoryQuick() {
  const name = newCategoryName.value.trim()
  if (!name) {
    ElMessage.warning('请输入分类名称')
    return
  }
  const created = await categoryApi.create({ name })
  categories.value = await categoryApi.list()
  form.value.category_id = created?.id ?? form.value.category_id
  newCategoryName.value = ''
  ElMessage.success('分类创建成功')
}

async function createWarehouseQuick() {
  const name = newWarehouseName.value.trim()
  if (!name) {
    ElMessage.warning('请输入仓库名称')
    return
  }
  const created = await warehouseApi.create({ name })
  warehouses.value = await warehouseApi.list()
  form.value.warehouse_id = created?.id ?? form.value.warehouse_id
  newWarehouseName.value = ''
  ElMessage.success('仓库创建成功')
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
  if (filterWarehouse.value) params.warehouse_id = filterWarehouse.value
  list.value = await inventoryApi.list(params).finally(() => (loading.value = false))
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
        price: row.price ?? 0,
        quantity: row.quantity ?? 0,
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
        price: 0,
        quantity: 1,
        description: null,
        image_front: null,
        image_back: null
      }
  dialogVisible.value = true
}

function openNoBarcodeEntry() {
  openDialog()
  const uuid = (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID()
    : `nb-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`
  form.value.barcode = uuid
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
    if (payload.id) await inventoryApi.update(payload.id, payload)
    else await inventoryApi.create(payload)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } finally {
    submitting.value = false
  }
}

async function remove(id) {
  await inventoryApi.remove(id)
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

async function openContScan(action = 'in') {
  stopContScan()
  contAction.value = action === 'out' ? 'out' : 'in'
  contBarcode.value = ''
  contProduct.value = null
  const canStream = !!(navigator.mediaDevices?.getUserMedia) && !!window.isSecureContext
  // 与“条码寻找”保持同颗粒度：
  // fallback 模式（iOS / 非安全上下文）直接唤起系统相机，不显示扫码弹窗
  if (!canStream || isIOS.value) {
    contScanMode.value = 'fallback'
    // 必须先离开 found，否则再次打开时会在 nextTick 内以 found + null product 渲染导致异常
    contState.value = 'ios-fallback'
    contScanVisible.value = false
    triggerContCapture()
    return
  }

  contScanMode.value = 'stream'
  contState.value = 'scanning'
  contScanVisible.value = true
  await nextTick()

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
    const res = await inventoryApi.findByBarcode(barcode)
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

async function confirmContAction() {
  if (!contProduct.value?.warehouse_id) {
    ElMessage.warning('该商品未设置所属仓库，请先编辑商品后再操作')
    return
  }
  contConfirming.value = true
  try {
    const apiCall = contAction.value === 'out' ? inventoryApi.stockOut : inventoryApi.stockIn
    const res = await apiCall(contProduct.value.id, {
      warehouse_id: contProduct.value.warehouse_id,
      quantity: 1,
      remark: contAction.value === 'out' ? '连续扫码出库' : '连续扫码入库'
    })
    ElMessage.success(`${contAction.value === 'out' ? '出库' : '入库'}成功，当前库存：${res.new_quantity} 件`)
    load()
    contScanVisible.value = false
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
  contCaptureUseA = !contCaptureUseA
  const el = contCaptureUseA ? contCameraRefA.value : contCameraRefB.value
  if (!el) return
  el.value = ''
  el.click()
}

async function handleContCapture(e) {
  const file = e.target.files?.[0]
  if (!file) return
  e.target.value = ''
  contScanning.value = true
  try {
    const res = await scanApi.scanBarcode(file)
    if (res?.found && res.barcode) {
      if (!contScanVisible.value) {
        contScanVisible.value = true
        await nextTick()
      }
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

// ============ 条形码寻找函数 ============

async function openLookupScan() {
  stopLookupScan()
  const canStream = !!(navigator.mediaDevices?.getUserMedia) && !!window.isSecureContext
  if (!canStream) {
    lookupScanMode.value = 'fallback'
    lookupScanVisible.value = false
    triggerLookupCapture()
    return
  }
  lookupScanMode.value = 'stream'
  lookupScanVisible.value = true
  await nextTick()

  try {
    lookupStream = await navigator.mediaDevices.getUserMedia(CAMERA_CONSTRAINTS)
    lookupVideoRef.value.srcObject = lookupStream
    await new Promise((resolve) => { lookupVideoRef.value.onloadedmetadata = resolve })
    lookupTimer = setInterval(async () => {
      if (!lookupScanVisible.value || lookupScanning.value) return
      const blob = await captureFrame(lookupVideoRef)
      if (!blob) return
      lookupScanning.value = true
      try {
        const res = await scanApi.scanBarcode(blob)
        if (res?.found && res.barcode) {
          await handleLookupBarcode(res.barcode)
        }
      } catch {
        // 静默失败，继续扫
      } finally {
        lookupScanning.value = false
      }
    }, SCAN_INTERVAL_MS)
  } catch {
    ElMessage.error('无法打开摄像头，请检查权限后重试')
    lookupScanVisible.value = false
  }
}

async function handleLookupBarcode(barcode) {
  keyword.value = barcode
  filterCat.value = null
  await load()
  ElMessage.success(`已定位条形码：${barcode}`)
  lookupScanVisible.value = false
}

function stopLookupScan() {
  clearInterval(lookupTimer)
  lookupTimer = null
  if (lookupStream) {
    lookupStream.getTracks().forEach((t) => t.stop())
    lookupStream = null
  }
  lookupScanning.value = false
}

function triggerLookupCapture() {
  lookupCameraRef.value.value = ''
  lookupCameraRef.value.click()
}

async function handleLookupCapture(e) {
  const file = e.target.files?.[0]
  if (!file) return
  e.target.value = ''
  lookupScanning.value = true
  try {
    const res = await scanApi.scanBarcode(file)
    if (res?.found && res.barcode) {
      await handleLookupBarcode(res.barcode)
    } else {
      ElMessage.warning('未识别到条形码，请重拍')
    }
  } catch {
    ElMessage.warning('识别失败，请重试')
  } finally {
    lookupScanning.value = false
  }
}

function openImageFind() {
  if (!imageFindCameraRef.value) return
  imageFindCameraRef.value.value = ''
  imageFindCameraRef.value.click()
}

async function handleImageFindCapture(e) {
  const file = e.target.files?.[0]
  if (!file) return
  e.target.value = ''
  loading.value = true
  try {
    const res = await inventoryApi.findByImage(file)
    if (res?.found && res.product) {
      keyword.value = res.product.barcode || res.product.name || ''
      filterCat.value = null
      filterWarehouse.value = null
      await load()
      const distanceText = Number.isFinite(res.distance) ? `（相似度距离 ${res.distance}）` : ''
      ElMessage.success(`已匹配到商品：${res.product.name || res.product.barcode}${distanceText}`)
    } else {
      ElMessage.warning('未找到匹配商品，请拍摄更清晰的正面图后重试')
    }
  } catch {
    // 错误提示由拦截器处理
  } finally {
    loading.value = false
  }
}

// ============ 生命周期 ============

onBeforeUnmount(stopScan)
onBeforeUnmount(stopContScan)
onBeforeUnmount(stopLookupScan)

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
  stopLookupScan()
})
</script>

<style scoped>
.search-card { margin-bottom: 16px; border-radius: 8px; }
.search-actions { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 8px; }
.search-actions--ios {
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
}
.search-actions-ios-row {
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
  width: 100%;
  justify-content: stretch;
}
.search-actions-ios-row :deep(.el-button) {
  flex: 1;
  min-width: 0;
  margin: 0;
}
.search-row {
  justify-content: space-between;
}
.search-left-group {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 20px;
}
.search-filters-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 20px;
  flex-shrink: 0;
}
.search-input-control,
.search-select-control {
  width: 180px;
  max-width: 180px;
}
.search-filters-row .search-select-control {
  width: 180px;
  max-width: 180px;
}
.quick-create-row {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  width: 100%;
}
.quick-create-row :deep(.el-input) {
  flex: 1;
}
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
.row-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
}

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
.img-actions { display: flex; gap: 6px; margin-top: 4px; flex-wrap: wrap; }
.scanning-hint { color: #409EFF; animation: pulse 1s infinite; }
@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }

/* ---- OCR ---- */
.ocr-hint { font-size: 13px; color: #8e9bb3; text-align: center; margin-bottom: 10px; }
.ocr-img-tabs { display: flex; gap: 8px; margin-bottom: 10px; }
.ocr-canvas-wrap { width: 100%; background: #000; border-radius: 6px; overflow: hidden; }
.ocr-canvas { display: block; width: 100%; cursor: crosshair; touch-action: none; user-select: none; }
.ocr-loading { text-align: center; padding: 10px 0; }

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
  .search-card :deep(.el-row) {
    row-gap: 8px;
  }
  .search-left-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
  }
  .search-input-control {
    width: 100%;
    max-width: none;
  }
  .search-filters-row {
    display: flex;
    flex-direction: row;
    flex-wrap: nowrap;
    gap: 8px;
    width: 100%;
  }
  .search-filters-row .search-select-control {
    flex: 1;
    width: 0;
    min-width: 0;
    max-width: none;
  }
  .search-actions {
    justify-content: stretch;
  }
  /* 非 iOS 小屏：保持纵向满宽按钮，与原先一致 */
  .search-actions:not(.search-actions--ios) {
    flex-direction: column;
    align-items: stretch;
  }
  .search-actions:not(.search-actions--ios) :deep(.el-button) {
    width: 100%;
    margin-left: 0;
  }
  .search-actions--ios {
    margin-top: 4px;
  }
  .table-scroll {
    -webkit-overflow-scrolling: touch;
  }
  .row-actions {
    gap: 4px;
  }
  .row-actions :deep(.el-button) {
    padding: 5px 8px;
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
