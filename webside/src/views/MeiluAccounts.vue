<template>
  <div>
    <el-card shadow="never" class="list-card" v-loading="loading">
      <el-row :gutter="16">
        <el-col :xs="24" :sm="12" :md="8" :lg="6" class="card-col">
          <div class="add-card">
            <div class="add-card-main" @click="openCreate">
              <el-icon class="add-card-icon"><Plus /></el-icon>
              <span>新增账号</span>
            </div>
            <el-button
              type="primary"
              plain
              size="small"
              :loading="browserLoadingKeys.has('meilu_prepare')"
              @click.stop="openBrowserByKey('meilu_prepare', '新增前登录')"
            >
              打开浏览器
            </el-button>
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
            <div class="card-item"><span>平台：</span>{{ row.value?.x_platform || '-' }}</div>
            <div class="card-item"><span>卖家ID：</span>{{ row.seller_id || '-' }}</div>
            <div class="card-item">
              <span>自动数据获取：</span>
              <template v-if="row.is_open === 1">开启 · {{ fetchIntervalLabel(row.fetch_interval) }}</template>
              <template v-else>关闭</template>
            </div>
            <div class="card-item"><span>备注：</span>{{ row.remark || '-' }}</div>
            <div class="card-actions">
              <el-button
                size="small"
                type="primary"
                plain
                :loading="browserLoadingKeys.has(browserKeyFor(row.id))"
                @click="openBrowserForSavedAccount(row)"
              >打开浏览器</el-button>
              <el-button
                size="small"
                type="warning"
                plain
                :loading="mitmAuthLoadingId === row.id"
                :disabled="!row.seller_id"
                @click="fetchAuthViaMitmForRow(row)"
              >获取新的认证</el-button>
              <el-button
                size="small"
                type="success"
                :loading="syncingIds.has(row.id)"
                @click="fetchHistory(row)"
              >获取历史数据</el-button>
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
      <el-form :model="form" :rules="rules" ref="formRef" label-width="168px" class="meilu-form">
        <el-divider content-position="left">从 RAW 导入</el-divider>
        <el-form-item label="请求头 RAW">
          <div class="raw-row">
            <el-input
              v-model="rawHeaderPaste"
              type="textarea"
              :rows="6"
              placeholder="粘贴 RAW（每行「名称: 值」）、完整 URL 或 Chrome「Copy as cURL」；含 seller_id= 会自动填卖家ID与账号名称。失焦时也会尝试解析"
              class="raw-textarea"
              @paste="onRawPaste"
              @blur="onRawBlur"
            />
            <div class="raw-actions">
              <el-button type="primary" plain @click="applyRawHeaders(false)">解析并填入</el-button>
              <el-button plain @click="readClipboardAndApply">从剪贴板导入</el-button>
            </div>
          </div>
        </el-form-item>

        <el-divider content-position="left">基础信息</el-divider>
        <el-form-item label="账号名称" prop="account_name">
          <el-input v-model="form.account_name" maxlength="60" clearable />
        </el-form-item>
        <el-form-item label="卖家ID" prop="seller_id">
          <el-input
            v-model="form.seller_id"
            maxlength="30"
            clearable
            placeholder="纯数字，与 items/get_items 请求 URL 中的 seller_id= 一致"
          />
          <p class="form-item-tip">
            与监控煤炉列表接口时抓包得到的地址一致，例如
            <span class="mono">GET …/items/get_items?sort_type=updated&amp;order_by=desc&amp;seller_id=908563766&amp;…&amp;status=trading</span>
            中的查询参数 <span class="mono">seller_id</span>（出售中订单等场景也使用同一卖家 ID）。
            将含该 URL 或 <span class="mono">:path:</span> 的 RAW 粘到上方时，会尝试自动填入本字段。
          </p>
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

        <div class="form-block form-block--auth">
          <el-divider content-position="left">鉴权与 DPoP</el-divider>
          <p class="form-block-hint">
            与登录态、接口 URL 绑定的令牌；与下方「浏览器请求头」分开维护。
            <strong>DPoP_Info</strong>（选填）、<strong>DPoP_OnSale-List</strong>、<strong>DPoP_ItemGet-Info</strong>
            各自对应不同 API 的完整 URL，须从该请求的抓包里取 DPoP；具体 URL 与操作步骤你稍后补充即可。未填 DPoP_Info 时，保存账号不受影响，但拉取订单详情等接口会提示补全。
          </p>
          <el-form-item label="Authorization" prop="authorization">
            <el-input v-model="form.authorization" type="textarea" :rows="2" clearable placeholder="浏览器里复制的完整 token（通常无 Bearer 前缀）" />
          </el-form-item>
          <el-form-item label="DPoP_List" prop="dpop_list">
            <el-input v-model="form.dpop_list" type="textarea" :rows="3" clearable placeholder="HTTP 头 DPoP（与 items/get_items 等 URL 绑定）" />
          </el-form-item>
          <el-form-item label="DPoP_Info（选填）" prop="dpop_info">
            <el-input
              v-model="form.dpop_info"
              type="textarea"
              :rows="2"
              clearable
              placeholder="选填。绑定「订单/交易详情」等接口的 DPoP（须与该请求的完整 URL 一致）。不填则调用相关接口时会报错提示补全；需要时可暂用 DPoP_List 试通。"
            />
          </el-form-item>
          <el-form-item label="DPoP_OnSale-List" prop="dpop_on_sale_list">
            <el-input
              v-model="form.dpop_on_sale_list"
              type="textarea"
              :rows="2"
              clearable
              placeholder="绑定「在售列表」对应请求的 DPoP；具体 URL 将另行说明。不填则无法从煤炉同步在售页。"
            />
          </el-form-item>
          <el-form-item label="DPoP_ItemGet-Info" prop="dpop_item_get_info">
            <el-input
              v-model="form.dpop_item_get_info"
              type="textarea"
              :rows="2"
              clearable
              placeholder="绑定「单件商品详情」对应请求的 DPoP；具体 URL 将另行说明。不填则无法在售页「获取详情」。"
            />
          </el-form-item>
        </div>

        <div class="form-block form-block--headers">
          <el-divider content-position="left">浏览器请求头（Web / jp.mercari.com）</el-divider>
          <p class="form-block-hint">与浏览器环境一致的常规头；可从开发者工具或抓包中复制。</p>
          <el-form-item label="X-Platform" prop="x_platform">
            <el-input v-model="form.x_platform" clearable placeholder="如 web" />
          </el-form-item>
          <el-form-item label="Sec-CH-UA-Platform" prop="sec_ch_ua_platform">
            <el-input v-model="form.sec_ch_ua_platform" clearable placeholder='如 "Windows"' />
          </el-form-item>
          <el-form-item label="Accept-Language" prop="accept_language">
            <el-input v-model="form.accept_language" clearable placeholder="如 ja" />
          </el-form-item>
          <el-form-item label="Sec-CH-UA" prop="sec_ch_ua">
            <el-input v-model="form.sec_ch_ua" type="textarea" :rows="2" clearable />
          </el-form-item>
          <el-form-item label="Sec-CH-UA-Mobile" prop="sec_ch_ua_mobile">
            <el-input v-model="form.sec_ch_ua_mobile" clearable placeholder="如 ?0" />
          </el-form-item>
          <el-form-item label="User-Agent" prop="user_agent">
            <el-input v-model="form.user_agent" type="textarea" :rows="2" clearable />
          </el-form-item>
          <el-form-item label="Accept" prop="accept">
            <el-input v-model="form.accept" clearable placeholder="如 application/json, text/plain, */*" />
          </el-form-item>
          <el-form-item label="Origin" prop="origin">
            <el-input v-model="form.origin" clearable placeholder="如 https://jp.mercari.com" />
          </el-form-item>
          <el-form-item label="Sec-Fetch-Site" prop="sec_fetch_site">
            <el-input v-model="form.sec_fetch_site" clearable placeholder="如 cross-site" />
          </el-form-item>
          <el-form-item label="Sec-Fetch-Mode" prop="sec_fetch_mode">
            <el-input v-model="form.sec_fetch_mode" clearable placeholder="如 cors" />
          </el-form-item>
          <el-form-item label="Sec-Fetch-Dest" prop="sec_fetch_dest">
            <el-input v-model="form.sec_fetch_dest" clearable placeholder="如 empty" />
          </el-form-item>
          <el-form-item label="Referer" prop="referer">
            <el-input v-model="form.referer" clearable placeholder="如 https://jp.mercari.com/" />
          </el-form-item>
          <el-form-item label="Accept-Encoding" prop="accept_encoding">
            <el-input v-model="form.accept_encoding" clearable />
          </el-form-item>
          <el-form-item label="Priority" prop="priority">
            <el-input v-model="form.priority" clearable placeholder="如 u=1, i" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button
          v-if="!form.id"
          type="primary"
          plain
          :loading="browserLoadingKeys.has('meilu_prepare')"
          @click="openBrowserByKey('meilu_prepare', '新增前登录')"
        >打开浏览器</el-button>
        <el-button
          v-else
          type="primary"
          plain
          :loading="browserLoadingKeys.has(browserKeyFor(form.id))"
          @click="openBrowserFromDialog"
        >打开浏览器</el-button>
        <el-button
          v-if="form.id"
          type="warning"
          plain
          :loading="mitmAuthLoadingId === form.id"
          :disabled="!form.seller_id"
          @click="fetchAuthViaMitmFromDialog"
        >获取新的认证</el-button>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { meiluAccountApi, mercariApi, webDriveApi } from '@/api/index.js'

const MERCARI_HOME = 'https://jp.mercari.com/'

function browserKeyFor(accountId) {
  return `meilu_${accountId}`
}

/** 小写 HTTP 头名 -> 表单字段名（Web 抓包 / curl -H） */
const HEADER_TO_FORM = {
  accept: 'accept',
  authorization: 'authorization',
  dpop: 'dpop_list',
  'dpop-list': 'dpop_list',
  dpop_list: 'dpop_list',
  dpop_info: 'dpop_info',
  'dpop-info': 'dpop_info',
  dpop_on_sale_list: 'dpop_on_sale_list',
  'dpop-on-sale-list': 'dpop_on_sale_list',
  dpop_item_get_info: 'dpop_item_get_info',
  'dpop-item-get-info': 'dpop_item_get_info',
  priority: 'priority',
  'accept-language': 'accept_language',
  'accept-encoding': 'accept_encoding',
  'user-agent': 'user_agent',
  'x-platform': 'x_platform',
  'sec-ch-ua-platform': 'sec_ch_ua_platform',
  'sec-ch-ua': 'sec_ch_ua',
  'sec-ch-ua-mobile': 'sec_ch_ua_mobile',
  origin: 'origin',
  'sec-fetch-site': 'sec_fetch_site',
  'sec-fetch-mode': 'sec_fetch_mode',
  'sec-fetch-dest': 'sec_fetch_dest',
  referer: 'referer',
}

const HEADER_LABELS = {
  x_platform: 'X-Platform',
  authorization: 'Authorization',
  sec_ch_ua_platform: 'Sec-CH-UA-Platform',
  accept_language: 'Accept-Language',
  sec_ch_ua: 'Sec-CH-UA',
  sec_ch_ua_mobile: 'Sec-CH-UA-Mobile',
  dpop_list: 'DPoP_List',
  dpop_info: 'DPoP_Info',
  dpop_on_sale_list: 'DPoP_OnSale-List',
  dpop_item_get_info: 'DPoP_ItemGet-Info',
  user_agent: 'User-Agent',
  accept: 'Accept',
  origin: 'Origin',
  sec_fetch_site: 'Sec-Fetch-Site',
  sec_fetch_mode: 'Sec-Fetch-Mode',
  sec_fetch_dest: 'Sec-Fetch-Dest',
  referer: 'Referer',
  accept_encoding: 'Accept-Encoding',
  priority: 'Priority',
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

/** 将单行转为可解析的「名称: 值」候选（支持行首带缩进、结尾反斜杠的 curl -H） */
function lineToHeaderCandidate(line) {
  let s = String(line || '').trim()
  if (!s) return ''
  const curlH = s.match(/^\s*(?:-H|--header)\s+(['"])([\s\S]*?)\1\s*\\?\s*$/i)
  if (curlH) return curlH[2].trim()
  return s
}

function normalizeHeaderLine(line) {
  let s = lineToHeaderCandidate(line)
  if (!s || s.startsWith('#')) return null
  if (/^https?:\/\//i.test(s)) return null
  if (/^curl\s/i.test(s)) return null
  const m = s.match(/^([^:]+?)\s*:\s*(.*)$/)
  if (!m) return null
  const name = m[1].trim().toLowerCase()
  const value = m[2].trim()
  if (!name || name === 'http' || name === 'https') return null
  return { name, value }
}

/** 从 RAW 中取请求 path+query（HTTP/2 :path: 或正文中的 https URL） */
function extractPathFromRaw(raw) {
  const lines = String(raw || '').split(/\r?\n/)
  for (const line of lines) {
    const s = String(line || '').trim()
    const m = s.match(/^:path:\s*(.+)$/i)
    if (m) return m[1].trim()
  }
  const text = String(raw || '')
  const um = text.match(/https?:\/\/[^\s'"]+/i)
  if (um) {
    try {
      const u = new URL(um[0].replace(/[,;\\]+$/, ''))
      return `${u.pathname}${u.search}` || ''
    } catch {
      return ''
    }
  }
  return ''
}

/** 从 RAW / URL 文本中解析 items/get_items 等请求里的 seller_id=（纯数字） */
function extractSellerIdFromRaw(raw) {
  const m = String(raw || '').match(/[?&]seller_id=(\d+)/i)
  return m ? m[1] : ''
}

/**
 * 按 :path: 决定 dpop 写入表单哪一项（须与 backend mercari_req_scheduling 一致）：
 * - /items/get_items 且含在售参数（on_sale、stop）→ dpop_on_sale_list
 * - /items/get_items 其他（如 trading）→ dpop_list
 * - /transaction_evidences/get → dpop_info（订单详情；与 get_order_info 使用同一头）
 * - /items/get（且非 get_items）→ dpop_item_get_info（在售单件详情）
 */
function dpopTargetFormKeyFromPath(pathStr) {
  const p = String(pathStr || '').trim()
  if (!p) return null
  if (p.includes('/items/get_items') && (p.includes('on_sale') || p.includes('stop'))) {
    return 'dpop_on_sale_list'
  }
  if (p.includes('/items/get_items')) return 'dpop_list'
  if (p.includes('/transaction_evidences/get')) return 'dpop_info'
  if (p.includes('/items/get')) return 'dpop_item_get_info'
  return null
}

/**
 * 解析 RAW 文本，返回 { formKey: value }（仅包含能识别的头）
 */
function parseRawHeaders(raw) {
  const pathVal = extractPathFromRaw(raw)
  const dpopTarget = dpopTargetFormKeyFromPath(pathVal)

  const text = String(raw || '')
  const lines = text.split(/\r?\n/)
  const out = {}
  for (const line of lines) {
    const parsed = normalizeHeaderLine(line)
    if (!parsed) continue
    if (parsed.name === 'dpop') {
      const key = dpopTarget || 'dpop_list'
      out[key] = parsed.value
      continue
    }
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
  seller_id: '',
  status: 'active',
  remark: '',
  is_open: 0,
  fetch_interval: '',
  x_platform: '',
  authorization: '',
  sec_ch_ua_platform: '',
  accept_language: '',
  sec_ch_ua: '',
  sec_ch_ua_mobile: '',
  dpop_list: '',
  dpop_info: '',
  dpop_on_sale_list: '',
  dpop_item_get_info: '',
  user_agent: '',
  accept: '',
  origin: '',
  sec_fetch_site: '',
  sec_fetch_mode: '',
  sec_fetch_dest: '',
  referer: '',
  accept_encoding: '',
  priority: '',
})

const form = ref(createDefaultForm())

const reqBlur = { required: true, message: '不能为空', trigger: 'blur' }
const rules = {
  account_name: [{ required: true, message: '请输入账号名称', trigger: 'blur' }],
  seller_id: [
    { required: true, message: '请输入卖家ID', trigger: 'blur' },
    {
      validator(_rule, val, cb) {
        const text = String(val || '').trim()
        if (!text) return cb(new Error('请输入卖家ID'))
        if (!/^\d+$/.test(text)) return cb(new Error('卖家ID必须为纯数字'))
        cb()
      },
      trigger: 'blur',
    },
  ],
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
  x_platform: [reqBlur],
  authorization: [reqBlur],
  sec_ch_ua_platform: [reqBlur],
  accept_language: [reqBlur],
  sec_ch_ua: [reqBlur],
  sec_ch_ua_mobile: [reqBlur],
  dpop_list: [reqBlur],
  user_agent: [reqBlur],
  accept: [reqBlur],
  origin: [reqBlur],
  sec_fetch_site: [reqBlur],
  sec_fetch_mode: [reqBlur],
  sec_fetch_dest: [reqBlur],
  referer: [reqBlur],
  accept_encoding: [reqBlur],
  priority: [reqBlur],
}

/** 粘贴后 v-model 往往尚未更新，延后到宏任务再解析 */
function onRawPaste() {
  setTimeout(() => applyRawHeaders(true, false), 0)
}

/** RAW 失焦时静默再解析一次（避免仅粘贴未触发完成等情况） */
function onRawBlur() {
  setTimeout(() => applyRawHeaders(true, true), 0)
}

/**
 * @param silent 为 true 时：无匹配不弹警告
 * @param quietSuccess 为 true 时：匹配成功也不弹成功提示（如失焦）
 */
function applyRawHeaders(silent = false, quietSuccess = false) {
  const raw = rawHeaderPaste.value
  const parsed = parseRawHeaders(raw)
  const keys = Object.keys(parsed)
  const sid = extractSellerIdFromRaw(raw)
  if (!keys.length && !sid) {
    if (!silent) {
      ElMessage.warning('未识别到任何已知请求头，也未在文本中找到 seller_id= 参数，请检查格式')
    }
    return
  }
  const next = { ...form.value }
  for (const k of keys) next[k] = parsed[k]
  let autoAccountName = false
  if (sid) {
    next.seller_id = sid
    if (!String(next.account_name || '').trim()) {
      next.account_name = `煤炉-${sid}`
      autoAccountName = true
    }
  }
  form.value = next
  if (quietSuccess) return
  const parts = []
  if (keys.length) parts.push(`请求头 ${keys.length} 项：${keys.map((k) => HEADER_LABELS[k] || k).join('、')}`)
  if (sid) parts.push(`卖家ID ${sid}${autoAccountName ? '（已生成账号名称）' : ''}`)
  ElMessage.success(parts.join('；'))
}

async function readClipboardAndApply() {
  try {
    const text = await navigator.clipboard.readText()
    if (!String(text || '').trim()) {
      ElMessage.warning('剪贴板为空')
      return
    }
    rawHeaderPaste.value = text
    await nextTick()
    applyRawHeaders(false, false)
  } catch {
    ElMessage.warning('无法读取剪贴板，请检查浏览器权限，或直接在上方文本框粘贴')
  }
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
    seller_id: row.seller_id != null ? String(row.seller_id) : '',
    status: row.status || 'active',
    remark: row.remark || '',
  }
  for (const k of HEADER_KEYS) {
    next[k] = v[k] != null ? String(v[k]) : ''
  }
  if (!String(next.dpop_list || '').trim() && v.dpop != null && String(v.dpop).trim()) {
    next.dpop_list = String(v.dpop)
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
    seller_id: String(form.value.seller_id || '').trim() || null,
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

// 正在同步的账号 ID 集合（用于按钮 loading 状态）
const syncingIds = ref(new Set())

/** web_drive account_key → loading（含 meilu_prepare、meilu_<id>） */
const browserLoadingKeys = ref(new Set())
/** MITM 拉认证：当前正在处理的账号 id */
const mitmAuthLoadingId = ref(null)

async function fetchAuthViaMitmForRow(row) {
  if (!row?.id) return
  if (!(row.seller_id || '').toString().trim()) {
    ElMessage.warning('请先填写卖家 ID')
    return
  }
  try {
    await ElMessageBox.confirm(
      '将启动 MITM 并打开 Edge（请先将 MITM 根证书安装到「受信任的根证书」）。随后在浏览器进入会产生「取引中」列表的请求（与 items/get_items&status=trading 一致），最多等待约 2 分钟。',
      '获取新的认证',
      { type: 'info', confirmButtonText: '开始', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  mitmAuthLoadingId.value = row.id
  try {
    await meiluAccountApi.fetchAuthViaMitm(row.id, { timeout: 0 })
    ElMessage.success('已根据抓包更新账号中的 Authorization、DPoP_List 等字段')
    await load()
    if (dialogVisible.value && form.value.id === row.id) {
      const refreshed = list.value.find((r) => r.id === row.id)
      if (refreshed) openEdit(refreshed)
    }
  } finally {
    mitmAuthLoadingId.value = null
  }
}

async function fetchAuthViaMitmFromDialog() {
  if (!form.value.id) return
  await fetchAuthViaMitmForRow({
    id: form.value.id,
    seller_id: form.value.seller_id,
  })
}

async function openBrowserByKey(accountKey, label) {
  if (browserLoadingKeys.value.has(accountKey)) return
  const next = new Set(browserLoadingKeys.value)
  next.add(accountKey)
  browserLoadingKeys.value = next
  try {
    const res = await webDriveApi.openSession({
      account_key: accountKey,
      headless: false,
      start_url: MERCARI_HOME,
    })
    const d = res.data || {}
    const tip = d.already_running ? '（已在运行，已跳转首页）' : '已启动 Edge'
    ElMessage.success(`${label || accountKey}：${tip}`)
  } catch {
    /* 错误由 axios 拦截器提示 */
  } finally {
    const s = new Set(browserLoadingKeys.value)
    s.delete(accountKey)
    browserLoadingKeys.value = s
  }
}

function openBrowserForSavedAccount(row) {
  openBrowserByKey(browserKeyFor(row.id), row.account_name || `账号 #${row.id}`)
}

function openBrowserFromDialog() {
  if (!form.value.id) {
    openBrowserByKey('meilu_prepare', '新增前登录')
    return
  }
  openBrowserByKey(browserKeyFor(form.value.id), form.value.account_name || `账号 #${form.value.id}`)
}

async function fetchHistory(row) {
  if (syncingIds.value.has(row.id)) return
  const sid = String(row.seller_id || '').trim()
  if (!sid) {
    ElMessage.warning('请先为该账号配置卖家 ID')
    return
  }

  let preRes
  try {
    preRes = await mercariApi.historySyncPrecheck({ account_id: row.id })
  } catch {
    return
  }
  const pre = preRes?.data || {}
  if (!pre.allowed) {
    ElMessage.warning(pre.message || '该卖家在订单表中已有数据，无法重复获取历史数据')
    return
  }

  try {
    await ElMessageBox.confirm(
      '本地订单库中尚无该卖家的记录。确认从煤炉全量拉取出售中与历史订单？耗时可能较长，请勿关闭页面。',
      '获取历史数据',
      {
        type: 'warning',
        confirmButtonText: '确认拉取',
        cancelButtonText: '取消',
        distinguishCancelAndClose: true,
      }
    )
  } catch {
    return
  }

  syncingIds.value = new Set([...syncingIds.value, row.id])
  try {
    const res = await mercariApi.syncOrders({ account_id: row.id })
    const d = res.data || {}
    ElMessage.success(
      `「${row.account_name}」同步完成：新增 ${d.inserted ?? 0} 条，更新 ${d.updated ?? 0} 条，共 ${d.total_item_count ?? d.total ?? 0} 条`
    )
  } finally {
    const next = new Set(syncingIds.value)
    next.delete(row.id)
    syncingIds.value = next
  }
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
  gap: 12px;
  padding: 12px;
  transition: all 0.2s ease;
}
.add-card:hover {
  border-color: #409eff;
  background: #1b2942;
}
.add-card-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  cursor: pointer;
  width: 100%;
  min-height: 120px;
  color: #a8b4c8;
  transition: color 0.2s ease;
}
.add-card:hover .add-card-main {
  color: #69b1ff;
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
  flex-wrap: wrap;
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
.raw-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.meilu-form {
  max-height: 70vh;
  overflow-y: auto;
  padding-right: 8px;
}
.form-block {
  margin: 12px 0 4px;
  padding: 4px 12px 12px;
  border-radius: 8px;
  border: 1px solid rgba(64, 158, 255, 0.22);
  background: rgba(19, 28, 47, 0.45);
}
.form-block--auth {
  border-color: rgba(230, 162, 60, 0.35);
  background: rgba(45, 35, 20, 0.25);
}
.form-block-hint {
  margin: -4px 0 12px;
  font-size: 12px;
  line-height: 1.5;
  color: #7d8da6;
}
.form-item-tip {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.55;
  color: #7d8da6;
  word-break: break-word;
}
.form-item-tip .mono {
  font-family: ui-monospace, 'Cascadia Code', 'Consolas', monospace;
  font-size: 11px;
  color: #a8b4c8;
}
</style>

<style>
.meilu-dialog .el-dialog__body {
  padding-top: 8px;
}
</style>
