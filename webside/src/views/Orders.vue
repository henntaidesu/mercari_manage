<template>
  <div>
    <el-card shadow="never" class="search-card">
      <el-row :gutter="0" align="middle" class="search-row">
        <el-col :xs="24" :md="16" class="search-left-group">
          <el-input
            v-model="filters.keyword"
            placeholder="搜索订单号/买家ID"
            clearable
            @change="onFilterChange"
          />
          <el-select v-model="filters.status" placeholder="订单状态" clearable style="width: 100%" @change="onFilterChange">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
            @change="onFilterChange"
          />
        </el-col>
        <el-col :xs="24" :md="8" class="search-actions">
          <el-button type="success" :icon="RefreshRight" disabled>更新数据</el-button>
          <el-button type="primary" @click="openCreate">新增订单</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="图片" width="76" align="center" header-align="center">
          <template #default="{ row }">
            <el-image
              v-if="firstThumbUrl(row)"
              class="order-thumb"
              :src="firstThumbUrl(row)"
              fit="cover"
              referrerpolicy="no-referrer"
              lazy
            >
              <template #error>
                <span class="thumb-fallback">-</span>
              </template>
            </el-image>
            <span v-else class="thumb-fallback">-</span>
          </template>
        </el-table-column>
        <el-table-column label="订单号" prop="order_no" width="150" align="center" header-align="center" />
        <el-table-column label="商品名称" prop="remark" min-width="180" show-overflow-tooltip align="left" header-align="center" />
        <el-table-column label="创建时间" width="176" show-overflow-tooltip align="center" header-align="center">
          <template #default="{ row }">{{ displayUtcAsLocal(row.order_date) }}</template>
        </el-table-column>
        <el-table-column label="最后更新" width="176" show-overflow-tooltip align="center" header-align="center">
          <template #default="{ row }">{{ displayUtcAsLocal(row.order_updated_at) }}</template>
        </el-table-column>
        <el-table-column label="买家ID" prop="customer_name" width="120" align="center" header-align="center">
          <template #default="{ row }">{{ row.customer_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center" header-align="center">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]?.tag || 'info'" size="small" effect="light">
              {{ statusMap[row.status]?.label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="金额" width="120" align="center" header-align="center">
          <template #default="{ row }">
            <span class="amount">{{ Math.round(Number(row.amount || 0)) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="手续费" width="112" align="center" header-align="center">
          <template #default="{ row }">
            <span v-if="orderMoneyField(row.service_fee) != null" class="col-fee">
              {{ orderMoneyField(row.service_fee) }}
            </span>
            <span v-else class="cell-dash">-</span>
          </template>
        </el-table-column>
        <el-table-column label="快递费" width="112" align="center" header-align="center">
          <template #default="{ row }">
            <span v-if="orderMoneyField(row.shipping_fee) != null" class="col-fee">
              {{ orderMoneyField(row.shipping_fee) }}
            </span>
            <span v-else class="cell-dash">-</span>
          </template>
        </el-table-column>
        <el-table-column label="净收益" width="112" align="center" header-align="center">
          <template #default="{ row }">
            <span v-if="orderMoneyField(row.net_income) != null" class="col-net">
              {{ orderMoneyField(row.net_income) }}
            </span>
            <span v-else class="cell-dash">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="88" fixed="right" align="center" header-align="center">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @change="load"
          background
          small
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? '编辑订单' : '新增订单'"
      width="680px"
      destroy-on-close
      class="order-edit-dialog"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="132px" class="order-edit-form">
        <el-form-item v-if="form.id != null" label="数据库 ID">
          <el-input :model-value="String(form.id)" disabled />
        </el-form-item>
        <el-form-item label="订单号" prop="order_no">
          <el-input v-model="form.order_no" placeholder="请输入订单号" maxlength="60" clearable />
        </el-form-item>
        <el-form-item label="创建时间" prop="order_date">
          <el-date-picker
            v-model="form.order_date"
            type="datetime"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
            placeholder="本地时间（保存时转为 UTC 与服务器一致）"
          />
          <div class="form-hint">列表与选择器为本地时间；接口存 UTC（格林尼治）</div>
        </el-form-item>
        <el-form-item label="最后更新">
          <el-date-picker
            v-model="form.order_updated_at"
            type="datetime"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
            placeholder="可选"
            clearable
          />
        </el-form-item>
        <el-form-item label="买家ID">
          <el-input v-model="form.customer_name" placeholder="Mercari 买家用户 ID（数字）" maxlength="30" clearable />
        </el-form-item>
        <el-form-item label="订单状态" prop="status">
          <el-select v-model="form.status" filterable style="width: 100%">
            <el-option v-for="item in formStatusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="订单金额" prop="amount">
          <el-input-number v-model="form.amount" :min="0.01" :precision="2" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="手续费">
          <el-input-number
            v-model="form.service_fee"
            :precision="2"
            :controls="false"
            style="width: 100%"
            placeholder="可选"
          />
        </el-form-item>
        <el-form-item label="净收益">
          <el-input-number
            v-model="form.net_income"
            :precision="2"
            :controls="false"
            style="width: 100%"
            placeholder="可选"
          />
        </el-form-item>
        <el-form-item label="快递公司">
          <el-input v-model="form.carrier_display_name" clearable placeholder="carrier_display_name" />
        </el-form-item>
        <el-form-item label="寄件方式名">
          <el-input v-model="form.request_class_display_name" clearable placeholder="request_class_display_name" />
        </el-form-item>
        <el-form-item label="快递费">
          <el-input-number
            v-model="form.shipping_fee"
            :precision="2"
            :controls="false"
            style="width: 100%"
            placeholder="可选"
          />
        </el-form-item>
        <el-form-item label="快递单号">
          <el-input v-model="form.tracking_no" clearable placeholder="tracking_no" />
        </el-form-item>
        <el-form-item label="商品名称">
          <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="2000" show-word-limit />
        </el-form-item>
        <el-form-item label="缩略图 JSON">
          <el-input
            v-model="form.thumbnails_text"
            type="textarea"
            :rows="4"
            placeholder='JSON 数组，如 ["https://..."]；也可每行一个 URL'
          />
          <div class="form-hint">对应库字段 thumbnails；留空表示不设置（更新时传空可清空）</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="order-dialog-footer">
          <el-popconfirm
            v-if="form.id"
            title="确认删除该订单？"
            @confirm="removeFromDialog"
          >
            <template #reference>
              <el-button type="danger">删除</el-button>
            </template>
          </el-popconfirm>
          <div class="order-dialog-footer-right">
            <el-button @click="dialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 同步订单弹窗 -->
    <el-dialog v-model="syncDialogVisible" title="更新 Mercari 订单数据" width="420px" destroy-on-close>
      <div class="sync-desc">
        <el-icon class="sync-icon"><InfoFilled /></el-icon>
        <span>将从 Mercari 拉取最新出售中订单并同步到订单管理表，已有记录自动更新状态。</span>
      </div>
      <el-form label-width="86px" style="margin-top: 20px;">
        <el-form-item label="煤炉账号">
          <el-select
            v-model="syncAccountId"
            placeholder="自动选取第一个活跃账号"
            clearable
            style="width: 100%"
            :loading="accountsLoading"
          >
            <el-option
              v-for="acc in accountOptions"
              :key="acc.id"
              :label="acc.account_name"
              :value="acc.id"
            />
          </el-select>
          <div class="form-hint">不选择则自动使用第一个 active 账号</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="syncDialogVisible = false">取消</el-button>
        <el-button type="success" :loading="syncLoading" @click="confirmSync">开始同步</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { RefreshRight, InfoFilled } from '@element-plus/icons-vue'
import { orderApi, mercariApi, meiluAccountApi } from '@/api/index.js'

const loading = ref(false)
const submitting = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dateRange = ref([])
const dialogVisible = ref(false)
const formRef = ref()

const filters = ref({ keyword: '', status: '' })

const statusOptions = [
  { label: '待包装', value: 'to_pack' },
  { label: '待发货', value: 'to_ship' },
  { label: '已发送', value: 'sent' },
  { label: '已签收', value: 'signed' },
  { label: '已确认', value: 'confirmed' },
]

const statusMap = {
  to_pack:       { label: '待包装', tag: 'info' },
  to_ship:       { label: '待发货', tag: 'warning' },
  sent:          { label: '已发送', tag: 'primary' },
  signed:        { label: '已签收', tag: 'success' },
  confirmed:     { label: '已确认', tag: 'danger' },
  pending:       { label: '待处理', tag: 'info' },
  trading:       { label: '交易中', tag: 'warning' },
  wait_payment:  { label: '待支付', tag: 'warning' },
  wait_shipping: { label: '待发货', tag: 'warning' },
  wait_review:   { label: '待卖家确认', tag: 'primary' },
  done:          { label: '已完成', tag: 'success' },
  sold_out:      { label: '已售完', tag: 'info' },
  cancelled:     { label: '已取消', tag: 'info' },
  cancel_request:{ label: '申请取消', tag: 'danger' },
}

/** 表单内状态：手工状态优先，其余与列表 statusMap 一致（含煤炉同步状态） */
const formStatusOptions = computed(() => {
  const seen = new Set()
  const out = []
  for (const o of statusOptions) {
    seen.add(o.value)
    out.push(o)
  }
  for (const [value, meta] of Object.entries(statusMap)) {
    if (seen.has(value)) continue
    seen.add(value)
    out.push({ label: meta.label, value })
  }
  return out
})

// ---- 同步订单弹窗 ----
const syncDialogVisible = ref(false)
const syncLoading = ref(false)
const syncAccountId = ref(null)
const accountOptions = ref([])
const accountsLoading = ref(false)

async function openSyncDialog() {
  syncAccountId.value = null
  syncDialogVisible.value = true
  accountsLoading.value = true
  try {
    const res = await meiluAccountApi.list({ page: 1, page_size: 100 })
    accountOptions.value = (res.items || []).filter(a => a.status === 'active')
  } catch (_) {
    accountOptions.value = []
  } finally {
    accountsLoading.value = false
  }
}

async function confirmSync() {
  syncLoading.value = true
  try {
    const payload = {}
    if (syncAccountId.value) payload.account_id = syncAccountId.value
    const res = await mercariApi.syncOrders(payload)
    const d = res.data || {}
    ElMessage.success(
      `同步完成：新增 ${d.inserted ?? 0} 条，更新 ${d.updated ?? 0} 条，共 ${d.total_item_count ?? d.total ?? 0} 条`
    )
    syncDialogVisible.value = false
    load()
  } finally {
    syncLoading.value = false
  }
}

function formatLocalDatetime(d = new Date()) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

/** 旧数据仅 YYYY-MM-DD 时补全为当天 00:00:00（按 UTC 日界） */
function normalizeDatetimeStr(v) {
  if (!v) return ''
  const s = String(v).trim()
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return `${s} 00:00:00`
  return s
}

const pad2 = (n) => String(n).padStart(2, '0')

/**
 * 将服务端存库的 UTC 时间字符串解析为 Date（本地显示用）
 * 格式 YYYY-MM-DD 或 YYYY-MM-DD HH:mm:ss，均按 UTC 理解
 */
function parseUtcDbToDate(v) {
  if (v == null || v === '') return null
  const s = normalizeDatetimeStr(String(v).trim())
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:\s+(\d{2}):(\d{2}):(\d{2}))?$/)
  if (!m) return null
  const y = +m[1]
  const mo = +m[2] - 1
  const d = +m[3]
  const h = m[4] != null ? +m[4] : 0
  const mi = m[5] != null ? +m[5] : 0
  const sec = m[6] != null ? +m[6] : 0
  return new Date(Date.UTC(y, mo, d, h, mi, sec))
}

/** 表格：UTC 存库串 -> 本地展示 YYYY-MM-DD HH:mm:ss */
function displayUtcAsLocal(v) {
  if (v == null || v === '') return '-'
  const dt = parseUtcDbToDate(v)
  if (!dt || Number.isNaN(dt.getTime())) return String(v)
  return `${dt.getFullYear()}-${pad2(dt.getMonth() + 1)}-${pad2(dt.getDate())} ${pad2(dt.getHours())}:${pad2(dt.getMinutes())}:${pad2(dt.getSeconds())}`
}

function formatLocalWallToStr(dt) {
  if (!dt || Number.isNaN(dt.getTime())) return ''
  return `${dt.getFullYear()}-${pad2(dt.getMonth() + 1)}-${pad2(dt.getDate())} ${pad2(dt.getHours())}:${pad2(dt.getMinutes())}:${pad2(dt.getSeconds())}`
}

/** 编辑：服务端 UTC 串 -> 本地串，供 datetime 选择器 */
function utcDbStringToLocalForm(v) {
  if (!v) return ''
  const dt = parseUtcDbToDate(v)
  if (!dt || Number.isNaN(dt.getTime())) return normalizeDatetimeStr(v)
  return formatLocalWallToStr(dt)
}

/**
 * 保存：选择器本地时间串 -> UTC 存库串 YYYY-MM-DD HH:mm:ss
 */
function localFormStringToUtcDb(v) {
  if (!v || !String(v).trim()) return null
  const s = String(v).trim()
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:\s+(\d{2}):(\d{2}):(\d{2}))?$/)
  if (!m) return s
  const y = +m[1]
  const mo = +m[2] - 1
  const d = +m[3]
  const h = m[4] != null ? +m[4] : 0
  const mi = m[5] != null ? +m[5] : 0
  const sec = m[6] != null ? +m[6] : 0
  const local = new Date(y, mo, d, h, mi, sec)
  if (Number.isNaN(local.getTime())) return s
  return `${local.getUTCFullYear()}-${pad2(local.getUTCMonth() + 1)}-${pad2(local.getUTCDate())} ${pad2(local.getUTCHours())}:${pad2(local.getUTCMinutes())}:${pad2(local.getUTCSeconds())}`
}

function optionalNumFromRow(v) {
  if (v == null || v === '') return undefined
  const n = Number(v)
  return Number.isNaN(n) ? undefined : n
}

function numOrNull(v) {
  if (v === null || v === undefined || v === '') return null
  const n = Number(v)
  return Number.isNaN(n) ? null : n
}

function thumbnailsToFormText(row) {
  const t = row.thumbnails
  if (t == null || t === '') return ''
  if (Array.isArray(t)) return JSON.stringify(t, null, 2)
  if (typeof t === 'string') {
    try {
      const o = JSON.parse(t)
      if (Array.isArray(o)) return JSON.stringify(o, null, 2)
    } catch {
      /* 原样展示 */
    }
    return t
  }
  return String(t)
}

/** 解析为 API 所需的 string[]；空串返回 null 表示清空或未传 */
function parseThumbnailsPayload(text) {
  const raw = String(text ?? '').trim()
  if (!raw) return null
  try {
    const p = JSON.parse(raw)
    if (Array.isArray(p)) {
      const urls = p.map((s) => String(s).trim()).filter(Boolean)
      return urls.length ? urls : null
    }
  } catch {
    /* 按行/逗号拆分 */
  }
  const urls = raw.split(/[\n,]+/).map((s) => s.trim()).filter(Boolean)
  return urls.length ? urls : null
}

/** 手续费 / 快递费 / 净收益列：null 表示无数据，单元格显示「-」；展示为整数（四舍五入） */
function orderMoneyField(v) {
  if (v == null || v === '') return null
  const n = Number(v)
  if (Number.isNaN(n)) return null
  return String(Math.round(n))
}

/** thumbnails 为 JSON 字符串或数组时取首张图 URL */
function firstThumbUrl(row) {
  const raw = row.thumbnails
  if (raw == null || raw === '') return ''
  if (Array.isArray(raw)) {
    const u = raw[0]
    return u ? String(u) : ''
  }
  if (typeof raw === 'string') {
    try {
      const arr = JSON.parse(raw)
      if (Array.isArray(arr) && arr.length > 0 && arr[0]) return String(arr[0])
    } catch {
      return ''
    }
  }
  return ''
}

const createDefaultForm = () => ({
  id: null,
  order_no: '',
  order_date: formatLocalDatetime(),
  order_updated_at: '',
  customer_name: '',
  status: 'to_pack',
  amount: null,
  service_fee: undefined,
  net_income: undefined,
  carrier_display_name: '',
  request_class_display_name: '',
  shipping_fee: undefined,
  tracking_no: '',
  remark: '',
  thumbnails_text: '',
})

const form = ref(createDefaultForm())

const rules = {
  order_no: [{ required: true, message: '请输入订单号', trigger: 'blur' }],
  order_date: [{ required: true, message: '请选择订单创建时间', trigger: 'change' }],
  status: [{ required: true, message: '请选择订单状态', trigger: 'change' }],
  amount: [{ required: true, message: '请输入订单金额', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  const params = { page: page.value, page_size: pageSize.value }
  if (filters.value.keyword) params.keyword = filters.value.keyword
  if (filters.value.status) params.status = filters.value.status
  if (dateRange.value?.length === 2) {
    params.start_date = dateRange.value[0]
    params.end_date = dateRange.value[1]
  }
  const res = await orderApi.list(params).finally(() => {
    loading.value = false
  })
  list.value = res.items || []
  total.value = res.total || 0
}

function onFilterChange() {
  page.value = 1
  load()
}

function resetFilters() {
  filters.value = { keyword: '', status: '' }
  dateRange.value = []
  page.value = 1
  load()
}

function openCreate() {
  form.value = createDefaultForm()
  dialogVisible.value = true
}

function openEdit(row) {
  form.value = {
    id: row.id,
    order_no: row.order_no || '',
    order_date: utcDbStringToLocalForm(row.order_date),
    order_updated_at: utcDbStringToLocalForm(row.order_updated_at),
    customer_name: row.customer_name || '',
    status: row.status || 'to_pack',
    amount: Number(row.amount || 0),
    service_fee: optionalNumFromRow(row.service_fee),
    net_income: optionalNumFromRow(row.net_income),
    carrier_display_name: row.carrier_display_name || '',
    request_class_display_name: row.request_class_display_name || '',
    shipping_fee: optionalNumFromRow(row.shipping_fee),
    tracking_no: row.tracking_no || '',
    remark: row.remark || '',
    thumbnails_text: thumbnailsToFormText(row),
  }
  dialogVisible.value = true
}

async function submit() {
  await formRef.value?.validate()
  submitting.value = true
  const payload = {
    order_no: String(form.value.order_no || '').trim(),
    order_date: localFormStringToUtcDb(form.value.order_date),
    order_updated_at: localFormStringToUtcDb(form.value.order_updated_at),
    customer_name: String(form.value.customer_name || '').trim() || null,
    status: form.value.status,
    amount: Number(form.value.amount || 0),
    service_fee: numOrNull(form.value.service_fee),
    net_income: numOrNull(form.value.net_income),
    carrier_display_name: String(form.value.carrier_display_name || '').trim() || null,
    request_class_display_name: String(form.value.request_class_display_name || '').trim() || null,
    shipping_fee: numOrNull(form.value.shipping_fee),
    tracking_no: String(form.value.tracking_no || '').trim() || null,
    remark: String(form.value.remark || '').trim() || null,
    thumbnails: parseThumbnailsPayload(form.value.thumbnails_text),
  }
  try {
    if (form.value.id) {
      await orderApi.update(form.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await orderApi.create(payload)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    load()
  } finally {
    submitting.value = false
  }
}

async function remove(id) {
  await orderApi.remove(id)
  ElMessage.success('删除成功')
  if (list.value.length === 1 && page.value > 1) page.value -= 1
  load()
}

async function removeFromDialog() {
  const id = form.value.id
  if (!id) return
  await remove(id)
  dialogVisible.value = false
}

onMounted(() => {
  load()
})
</script>

<style scoped>
.search-card {
  margin-bottom: 16px;
  border-radius: 8px;
}
.search-row {
  justify-content: space-between;
}
.search-left-group {
  display: flex;
  align-items: center;
  gap: 20px;
}
.search-actions {
  display: flex;
  justify-content: flex-end;
  gap: 20px;
}
.table-card {
  border-radius: 8px;
}
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.amount {
  color: #ffffff;
  font-weight: 600;
}
.col-fee {
  color: #f56c6c;
  font-weight: 600;
}
.col-net {
  color: #ffffff;
  font-weight: 500;
}
.cell-dash {
  color: #c0c4cc;
}
.order-thumb {
  width: 48px;
  height: 48px;
  border-radius: 4px;
  display: block;
}
.thumb-fallback {
  color: #909399;
  font-size: 12px;
}
.sync-desc {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 14px;
  background: #f0f9eb;
  border-radius: 6px;
  color: #606266;
  font-size: 13px;
  line-height: 1.6;
}
.sync-icon {
  color: #67c23a;
  font-size: 16px;
  flex-shrink: 0;
  margin-top: 2px;
}
.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.4;
}
.order-edit-dialog :deep(.el-dialog__body) {
  max-height: 72vh;
  overflow-y: auto;
  padding-top: 8px;
}
.order-dialog-footer {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  width: 100%;
}
.order-dialog-footer-right {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}
</style>
