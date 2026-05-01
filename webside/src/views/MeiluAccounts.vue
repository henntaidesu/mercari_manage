<template>
  <div>
    <el-card shadow="never" class="list-card" v-loading="loading">
      <el-row :gutter="16">
        <el-col :xs="24" :sm="12" :md="8" :lg="6" class="card-col">
          <div class="add-card" @click="openCreate">
            <el-icon class="add-card-icon"><Plus /></el-icon>
            <span>新增账号</span>
          </div>
        </el-col>
        <el-col v-for="row in list" :key="row.id" :xs="24" :sm="12" :md="8" :lg="6" class="card-col">
          <el-card shadow="hover" class="account-card">
            <div class="card-header">
              <div class="card-title">{{ row.account_name || '-' }}</div>
              <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small" effect="light">
                {{ row.status === 'active' ? '启用' : '停用' }}
              </el-tag>
            </div>
            <div class="card-item"><span>平台 / 版本：</span>{{ row.value?.x_platform || '-' }} / {{ row.value?.x_app_version || '-' }}</div>
            <div class="card-item">
              <span>自动数据获取：</span>
              <template v-if="row.is_open === 1">开启 · {{ fetchIntervalLabel(row.fetch_interval) }}</template>
              <template v-else>关闭</template>
            </div>
            <div class="card-item"><span>备注：</span>{{ row.remark || '-' }}</div>
            <div class="card-actions">
              <el-button size="small" @click="openEdit(row)">编辑</el-button>
              <el-popconfirm title="确认删除该账号？" @confirm="remove(row.id)">
                <template #reference>
                  <el-button size="small" type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </el-card>
        </el-col>
      </el-row>

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
      :title="form.id ? '编辑煤炉账号' : '新增煤炉账号'"
      width="720px"
      top="4vh"
      destroy-on-close
      class="meilu-dialog"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="132px" class="meilu-form">
        <el-divider content-position="left">从 RAW 导入</el-divider>
        <el-form-item label="请求头 RAW">
          <div class="raw-row">
            <el-input
              v-model="rawHeaderPaste"
              type="textarea"
              :rows="6"
              placeholder="粘贴 RAW（每行「名称: 值」）；支持 curl 的 -H 行。粘贴后会自动解析，也可点按钮再次解析"
              class="raw-textarea"
              @paste="onRawPaste"
            />
            <el-button type="primary" plain @click="applyRawHeaders(false)">解析并填入</el-button>
          </div>
        </el-form-item>

        <el-divider content-position="left">基础信息</el-divider>
        <el-form-item label="账号名称" prop="account_name">
          <el-input v-model="form.account_name" maxlength="60" clearable />
        </el-form-item>
        <el-form-item label="账号状态" prop="status">
          <el-select v-model="form.status" style="width: 100%">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="200" show-word-limit />
        </el-form-item>

        <el-divider content-position="left">自动数据获取</el-divider>
        <el-form-item label="自动数据获取" prop="is_open">
          <el-select v-model="form.is_open" style="width: 100%" @change="onAutoFetchToggle">
            <el-option v-for="opt in autoFetchSwitchOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>
        <el-form-item v-show="form.is_open === 1" label="时间间隔" prop="fetch_interval">
          <el-select v-model="form.fetch_interval" style="width: 100%" placeholder="请选择间隔">
            <el-option v-for="opt in fetchIntervalOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">HTTP 请求头</el-divider>
        <el-form-item label="Accept" prop="accept">
          <el-input v-model="form.accept" clearable />
        </el-form-item>
        <el-form-item label="X-App-Type" prop="x_app_type">
          <el-input v-model="form.x_app_type" clearable />
        </el-form-item>
        <el-form-item label="Authorization" prop="authorization">
          <el-input v-model="form.authorization" type="textarea" :rows="2" clearable placeholder="含 Bearer 的完整值" />
        </el-form-item>
        <el-form-item label="DPoP" prop="dpop">
          <el-input v-model="form.dpop" type="textarea" :rows="3" clearable />
        </el-form-item>
        <el-form-item label="Priority" prop="priority">
          <el-input v-model="form.priority" clearable />
        </el-form-item>
        <el-form-item label="Accept-Language" prop="accept_language">
          <el-input v-model="form.accept_language" clearable />
        </el-form-item>
        <el-form-item label="Accept-Encoding" prop="accept_encoding">
          <el-input v-model="form.accept_encoding" clearable />
        </el-form-item>
        <el-form-item label="User-Agent" prop="user_agent">
          <el-input v-model="form.user_agent" type="textarea" :rows="2" clearable />
        </el-form-item>
        <el-form-item label="X-App-Version" prop="x_app_version">
          <el-input v-model="form.x_app_version" clearable />
        </el-form-item>
        <el-form-item label="X-Platform" prop="x_platform">
          <el-input v-model="form.x_platform" clearable />
        </el-form-item>
        <el-form-item label="X-Mcc" prop="x_mcc">
          <el-input v-model="form.x_mcc" type="textarea" :rows="2" clearable />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { meiluAccountApi } from '@/api/index.js'

/** 小写 HTTP 头名 -> 表单字段名 */
const HEADER_TO_FORM = {
  accept: 'accept',
  'x-app-type': 'x_app_type',
  authorization: 'authorization',
  dpop: 'dpop',
  priority: 'priority',
  'accept-language': 'accept_language',
  'accept-encoding': 'accept_encoding',
  'user-agent': 'user_agent',
  'x-app-version': 'x_app_version',
  'x-platform': 'x_platform',
  'x-mcc': 'x_mcc',
}

const HEADER_LABELS = {
  accept: 'Accept',
  x_app_type: 'X-App-Type',
  authorization: 'Authorization',
  dpop: 'DPoP',
  priority: 'Priority',
  accept_language: 'Accept-Language',
  accept_encoding: 'Accept-Encoding',
  user_agent: 'User-Agent',
  x_app_version: 'X-App-Version',
  x_platform: 'X-Platform',
  x_mcc: 'X-Mcc',
}

/** 与后端 value JSON 键一致 */
const HEADER_KEYS = Object.keys(HEADER_LABELS)

function buildValueFromForm(f) {
  const o = {}
  for (const k of HEADER_KEYS) {
    o[k] = String(f[k] ?? '').trim()
  }
  return o
}

function normalizeHeaderLine(line) {
  let s = String(line || '').trim()
  if (!s || s.startsWith('#')) return null
  // curl -H "Name: Value" 或 -H 'Name: Value'
  const curl = s.match(/^-H\s+(['"])([\s\S]*)\1\s*,?\s*$/i)
  if (curl) s = curl[2].trim()
  const m = s.match(/^([^:]+?)\s*:\s*(.*)$/)
  if (!m) return null
  const name = m[1].trim().toLowerCase()
  const value = m[2].trim()
  if (!name) return null
  return { name, value }
}

/**
 * 解析 RAW 文本，返回 { formKey: value }（仅包含能识别的头）
 */
function parseRawHeaders(raw) {
  const text = String(raw || '')
  const lines = text.split(/\r?\n/)
  const out = {}
  for (const line of lines) {
    const parsed = normalizeHeaderLine(line)
    if (!parsed) continue
    const key = HEADER_TO_FORM[parsed.name]
    if (key) out[key] = parsed.value
  }
  return out
}

const loading = ref(false)
const submitting = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)
const formRef = ref()
const rawHeaderPaste = ref('')

const statusOptions = [
  { label: '启用', value: 'active' },
  { label: '停用', value: 'disabled' },
]

const autoFetchSwitchOptions = [
  { label: '关闭', value: 0 },
  { label: '开启', value: 1 },
]

const fetchIntervalOptions = [
  { label: '10 分钟', value: '10' },
  { label: '30 分钟', value: '30' },
  { label: '60 分钟', value: '60' },
  { label: '3 小时', value: '3h' },
  { label: '6 小时', value: '6h' },
  { label: '12 小时', value: '12h' },
  { label: '24 小时', value: '24h' },
]

const fetchIntervalLabelMap = Object.fromEntries(fetchIntervalOptions.map((o) => [o.value, o.label]))

function fetchIntervalLabel(v) {
  if (v == null || v === '') return '-'
  return fetchIntervalLabelMap[v] || v
}

function onAutoFetchToggle() {
  if (form.value.is_open !== 1) {
    form.value.fetch_interval = ''
  }
  nextTick(() => formRef.value?.clearValidate(['fetch_interval']))
}

const createDefaultForm = () => ({
  id: null,
  account_name: '',
  status: 'active',
  remark: '',
  is_open: 0,
  fetch_interval: '',
  accept: '',
  x_app_type: '',
  authorization: '',
  dpop: '',
  priority: '',
  accept_language: '',
  accept_encoding: '',
  user_agent: '',
  x_app_version: '',
  x_platform: '',
  x_mcc: '',
})

const form = ref(createDefaultForm())

const reqBlur = { required: true, message: '不能为空', trigger: 'blur' }
const rules = {
  account_name: [{ required: true, message: '请输入账号名称', trigger: 'blur' }],
  status: [{ required: true, message: '请选择账号状态', trigger: 'change' }],
  is_open: [{ required: true, message: '请选择', trigger: 'change' }],
  fetch_interval: [
    {
      validator(_rule, val, cb) {
        if (form.value.is_open === 1) {
          if (!val || !String(val).trim()) {
            cb(new Error('请选择时间间隔'))
            return
          }
        }
        cb()
      },
      trigger: 'change',
    },
  ],
  accept: [reqBlur],
  x_app_type: [reqBlur],
  authorization: [reqBlur],
  dpop: [reqBlur],
  priority: [reqBlur],
  accept_language: [reqBlur],
  accept_encoding: [reqBlur],
  user_agent: [reqBlur],
  x_app_version: [reqBlur],
  x_platform: [reqBlur],
  x_mcc: [reqBlur],
}

function onRawPaste() {
  nextTick(() => applyRawHeaders(true))
}

/** @param {boolean} silent 为 true 时（如粘贴过程中）未识别到内容不弹警告 */
function applyRawHeaders(silent = false) {
  const parsed = parseRawHeaders(rawHeaderPaste.value)
  const keys = Object.keys(parsed)
  if (!keys.length) {
    if (!silent) ElMessage.warning('未识别到任何已知请求头，请确认格式为每行「名称: 值」')
    return
  }
  const next = { ...form.value }
  for (const k of keys) next[k] = parsed[k]
  form.value = next
  const names = keys.map((k) => HEADER_LABELS[k] || k).join('、')
  ElMessage.success(`已填入 ${keys.length} 项：${names}`)
}

watch(dialogVisible, (open) => {
  if (open) rawHeaderPaste.value = ''
})

async function load() {
  loading.value = true
  const params = { page: page.value, page_size: pageSize.value }
  const res = await meiluAccountApi.list(params).finally(() => {
    loading.value = false
  })
  list.value = res.items || []
  total.value = res.total || 0
}

function openCreate() {
  form.value = createDefaultForm()
  dialogVisible.value = true
}

function openEdit(row) {
  const v = row.value && typeof row.value === 'object' ? row.value : {}
  const next = {
    ...createDefaultForm(),
    id: row.id,
    account_name: row.account_name || '',
    status: row.status || 'active',
    remark: row.remark || '',
  }
  for (const k of HEADER_KEYS) {
    next[k] = v[k] != null ? String(v[k]) : ''
  }
  next.is_open = row.is_open === 1 || row.is_open === true ? 1 : 0
  next.fetch_interval = row.fetch_interval != null && row.is_open === 1 ? String(row.fetch_interval) : ''
  form.value = next
  dialogVisible.value = true
}

function buildPayload() {
  const name = String(form.value.account_name || '').trim()
  const open = form.value.is_open === 1 ? 1 : 0
  return {
    account_name: name,
    login_id: name,
    status: form.value.status,
    remark: form.value.remark || null,
    value: buildValueFromForm(form.value),
    is_open: open,
    fetch_interval: open === 1 ? String(form.value.fetch_interval || '').trim() || null : null,
  }
}

async function submit() {
  await formRef.value?.validate()
  submitting.value = true
  const payload = buildPayload()
  try {
    if (form.value.id) {
      await meiluAccountApi.update(form.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await meiluAccountApi.create(payload)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    load()
  } finally {
    submitting.value = false
  }
}

async function remove(id) {
  await meiluAccountApi.remove(id)
  ElMessage.success('删除成功')
  if (list.value.length === 1 && page.value > 1) page.value -= 1
  load()
}

onMounted(() => {
  load()
})
</script>

<style scoped>
.list-card {
  border-radius: 8px;
}
.card-col {
  margin-bottom: 16px;
}
.add-card {
  height: 100%;
  min-height: 220px;
  border: 1px dashed #3a4a65;
  border-radius: 8px;
  background: rgba(19, 28, 47, 0.85);
  color: #a8b4c8;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.add-card:hover {
  color: #69b1ff;
  border-color: #409eff;
  background: #1b2942;
}
.add-card-icon {
  font-size: 24px;
}
.account-card {
  border-radius: 8px;
  height: 100%;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #e6edf7;
}
.card-item {
  margin-bottom: 8px;
  color: #a8b4c8;
  word-break: break-all;
  font-size: 13px;
}
.card-item span {
  color: #7d8da6;
}
.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.raw-row {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}
.raw-row .el-button {
  align-self: flex-start;
}
.meilu-form {
  max-height: 70vh;
  overflow-y: auto;
  padding-right: 8px;
}
</style>

<style>
.meilu-dialog .el-dialog__body {
  padding-top: 8px;
}
</style>
