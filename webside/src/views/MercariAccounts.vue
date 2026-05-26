<template>
  <div>
    <el-card shadow="never" class="list-card" v-loading="loading">
      <el-row :gutter="16">
        <el-col :xs="24" :sm="12" :md="8" :lg="6" class="card-col">
          <div class="add-card">
            <div class="add-card-main" @click="openCreate">
              <el-icon class="add-card-icon"><Plus /></el-icon>
              <span>{{ t('mercariAccounts.addAccount') }}</span>
            </div>
          </div>
        </el-col>
        <el-col v-for="row in list" :key="row.id" :xs="24" :sm="12" :md="8" :lg="6" class="card-col">
          <el-card shadow="hover" class="account-card">
            <div class="card-header">
              <div class="card-title">{{ row.account_name || '-' }}</div>
              <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small" effect="light">
                {{ row.status === 'active' ? t('mercariAccounts.enabled') : t('mercariAccounts.disabled') }}
              </el-tag>
            </div>
            <div class="card-item"><span>{{ t('mercariAccounts.platformLabel') }}</span>{{ row.value?.x_platform || '-' }}</div>
            <div class="card-item"><span>{{ t('mercariAccounts.sellerIdLabel') }}</span>{{ row.seller_id || '-' }}</div>
            <div class="card-item">
              <span>{{ t('mercariAccounts.autoFetchLabel') }}</span>
              <template v-if="row.is_open === 1">
                {{ t('mercariAccounts.autoFetchOn') }} · {{ fetchIntervalLabel(row.fetch_interval) }}
                <template v-if="autoFetchTasksLabel(row)">（{{ autoFetchTasksLabel(row) }}）</template>
                <template v-if="pauseWindowLabel(row)"> · {{ t('mercariAccounts.pauseShort') }} {{ pauseWindowLabel(row) }}</template>
              </template>
              <template v-else>{{ t('mercariAccounts.autoFetchOff') }}</template>
            </div>
            <div class="card-item"><span>{{ t('mercariAccounts.remarkLabel') }}</span>{{ row.remark || '-' }}</div>
            <div class="card-actions">
              <el-button
                size="small"
                type="primary"
                plain
                :loading="browserLoadingKeys.has(browserKeyFor(row.id))"
                @click="openBrowserForSavedAccount(row)"
              >{{ t('mercariAccounts.openBrowser') }}</el-button>
              <el-button
                size="small"
                type="success"
                :loading="syncingIds.has(row.id)"
                @click="fetchHistory(row)"
              >{{ t('mercariAccounts.fetchHistory') }}</el-button>
              <el-button size="small" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
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
          size="small"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? t('mercariAccounts.editDialogTitle') : t('mercariAccounts.addDialogTitle')"
      width="620px"
      top="6vh"
      destroy-on-close
      class="mercari-dialog"
    >
      <p v-if="!form.id" class="form-intro-tip">
        {{ t('mercariAccounts.formIntroTip') }}
      </p>
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="120px" class="mercari-form">
        <el-divider content-position="left">{{ t('mercariAccounts.sectionBasicInfo') }}</el-divider>
        <el-form-item :label="t('mercariAccounts.accountNameLabel')" prop="account_name">
          <el-input v-model="form.account_name" maxlength="60" clearable />
        </el-form-item>
        <el-form-item :label="t('mercariAccounts.sellerId')" prop="seller_id">
          <el-input
            v-model="form.seller_id"
            maxlength="30"
            clearable
            :placeholder="t('mercariAccounts.sellerIdPlaceholder')"
          >
            <template #append>
              <el-button
                :loading="fetchSellerIdLoading"
                @click="fetchSellerIdViaMitm"
              >{{ t('mercariAccounts.fetch') }}</el-button>
            </template>
          </el-input>
          <p class="seller-id-hint">
            {{ t('mercariAccounts.sellerIdHintPrefix') }}
            <a href="https://jp.mercari.com/mypage/listings" target="_blank" rel="noopener">{{ t('mercariAccounts.sellerIdHintLink') }}</a>
            {{ t('mercariAccounts.sellerIdHintMiddle') }}
            <code>api.mercari.jp/items/get_items</code>
            {{ t('mercariAccounts.sellerIdHintSuffix') }}
          </p>
        </el-form-item>
        <el-form-item :label="t('mercariAccounts.accountStatus')" prop="status">
          <el-select v-model="form.status" style="width: 100%">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('common.remark')">
          <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="200" show-word-limit />
        </el-form-item>

        <el-divider content-position="left">{{ t('mercariAccounts.sectionAutoFetch') }}</el-divider>
        <p class="form-section-hint">
          {{ t('mercariAccounts.autoFetchSectionHint') }}
        </p>
        <el-form-item :label="t('mercariAccounts.autoFetch')" prop="is_open">
          <el-select v-model="form.is_open" style="width: 100%" @change="onAutoFetchToggle">
            <el-option v-for="opt in autoFetchSwitchOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>
        <template v-if="form.is_open === 1">
          <el-form-item :label="t('mercariAccounts.syncItems')">
            <div class="af-task-checks">
              <el-checkbox
                v-model="form.auto_fetch_order_list"
                :true-value="1"
                :false-value="0"
                @change="onAutoFetchTaskChange"
              >{{ t('mercariAccounts.taskOrderList') }}</el-checkbox>
              <el-checkbox
                v-model="form.auto_fetch_on_sale"
                :true-value="1"
                :false-value="0"
                @change="onAutoFetchTaskChange"
              >{{ t('mercariAccounts.taskOnSale') }}</el-checkbox>
              <el-checkbox
                v-model="form.auto_fetch_todos"
                :true-value="1"
                :false-value="0"
                @change="onAutoFetchTaskChange"
              >{{ t('mercariAccounts.taskTodos') }}</el-checkbox>
              <el-checkbox
                v-model="form.auto_fetch_notifications"
                :true-value="1"
                :false-value="0"
                @change="onAutoFetchTaskChange"
              >{{ t('mercariAccounts.taskNotifications') }}</el-checkbox>
            </div>
          </el-form-item>
          <el-form-item :label="t('mercariAccounts.interval')" prop="fetch_interval">
            <el-select v-model="form.fetch_interval" style="width: 100%" :placeholder="t('mercariAccounts.intervalPlaceholder')" @change="onAutoFetchTaskChange">
              <el-option v-for="opt in fetchIntervalOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('mercariAccounts.pauseRange')" prop="pause_window">
            <div class="af-pause-row">
              <el-time-picker
                v-model="form.pause_start_time"
                :placeholder="t('mercariAccounts.pauseStartPlaceholder')"
                format="HH:mm"
                value-format="HH:mm"
                :clearable="true"
                class="af-pause-picker"
              />
              <span class="af-pause-sep">{{ t('common.to') }}</span>
              <el-time-picker
                v-model="form.pause_end_time"
                :placeholder="t('mercariAccounts.pauseEndPlaceholder')"
                format="HH:mm"
                value-format="HH:mm"
                :clearable="true"
                class="af-pause-picker"
              />
            </div>
            <p class="af-pause-hint">
              {{ t('mercariAccounts.pauseHint') }}
            </p>
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <div class="mercari-dialog-footer">
          <el-popconfirm v-if="form.id" :title="t('mercariAccounts.deleteConfirm')" @confirm="removeFromDialog">
            <template #reference>
              <el-button type="danger" plain>{{ t('common.delete') }}</el-button>
            </template>
          </el-popconfirm>
          <div class="mercari-dialog-footer__actions">
            <el-button
              v-if="!form.id"
              plain
              :loading="browserLoadingKeys.has(MERCARI_PREPARE_KEY)"
              @click="openPrepareLoginBrowser"
            >{{ t('mercariAccounts.openLoginBrowser') }}</el-button>
            <el-button v-if="!form.id" plain @click="onFetchUserInfoPlaceholder">{{ t('mercariAccounts.fetchUserInfo') }}</el-button>
            <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
            <el-button type="primary" :loading="submitting" @click="submit">{{ t('common.save') }}</el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { mercariAccountApi, mercariApi, webDriveApi } from '@/api/index.js'

const { t } = useI18n()

const MERCARI_HOME = 'https://jp.mercari.com/'

/** 新增账号前共用的 WebDrive 会话键，与后端抓包/出品等约定一致 */
const MERCARI_PREPARE_KEY = 'mercari_prepare'

function browserKeyFor(accountId) {
  return `mercari_${accountId}`
}

const loading = ref(false)
const submitting = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)
const formRef = ref()

const statusOptions = [
  { label: t('mercariAccounts.enabled'), value: 'active' },
  { label: t('mercariAccounts.disabled'), value: 'disabled' },
]

const autoFetchSwitchOptions = [
  { label: t('mercariAccounts.autoFetchOff'), value: 0 },
  { label: t('mercariAccounts.autoFetchOn'), value: 1 },
]

const fetchIntervalOptions = [
  { label: t('mercariAccounts.interval15min'), value: '15' },
  { label: t('mercariAccounts.interval30min'), value: '30' },
  { label: t('mercariAccounts.interval1h'), value: '60' },
  { label: t('mercariAccounts.interval3h'), value: '3h' },
  { label: t('mercariAccounts.interval6h'), value: '6h' },
]

const legacyFetchIntervalLabels = {
  '10': t('mercariAccounts.interval10min'),
  '12h': t('mercariAccounts.interval12h'),
  '24h': t('mercariAccounts.interval24h'),
}

function fetchIntervalLabel(v) {
  if (v == null || v === '') return '-'
  const key = String(v)
  const cur = fetchIntervalOptions.find((o) => o.value === key)
  if (cur) return cur.label
  return legacyFetchIntervalLabels[key] || key
}

function pauseWindowLabel(row) {
  if (!row || row.is_open !== 1) return ''
  const s = String(row.pause_start_time || '').trim()
  const e = String(row.pause_end_time || '').trim()
  if (!s || !e || s === e) return ''
  return `${s} - ${e}`
}

function autoFetchTasksLabel(row) {
  if (!row || row.is_open !== 1) return ''
  const parts = []
  if (row.auto_fetch_order_list === 1) parts.push(t('mercariAccounts.taskShortOrderList'))
  if (row.auto_fetch_on_sale === 1) parts.push(t('mercariAccounts.taskShortOnSale'))
  if (row.auto_fetch_todos === 1) parts.push(t('mercariAccounts.taskShortTodos'))
  if (row.auto_fetch_notifications === 1) parts.push(t('mercariAccounts.taskShortNotifications'))
  return parts.join(t('mercariAccounts.taskJoiner'))
}

function onAutoFetchToggle() {
  if (form.value.is_open !== 1) {
    form.value.fetch_interval = ''
    form.value.auto_fetch_order_list = 0
    form.value.auto_fetch_on_sale = 0
    form.value.auto_fetch_todos = 0
    form.value.auto_fetch_notifications = 0
    form.value.pause_start_time = null
    form.value.pause_end_time = null
  }
  nextTick(() => formRef.value?.clearValidate(['fetch_interval', 'pause_window']))
}

function onAutoFetchTaskChange() {
  nextTick(() => formRef.value?.validateField('fetch_interval').catch(() => {}))
}

const createDefaultForm = () => ({
  id: null,
  account_name: '',
  seller_id: '',
  status: 'disabled',
  remark: '',
  is_open: 0,
  fetch_interval: '',
  auto_fetch_order_list: 0,
  auto_fetch_on_sale: 0,
  auto_fetch_todos: 0,
  auto_fetch_notifications: 0,
  pause_start_time: null,
  pause_end_time: null,
})

const form = ref(createDefaultForm())

const sellerIdRules = [
  {
    validator(_rule, val, cb) {
      const text = String(val || '').trim()
      if (!text) return cb()
      if (!/^\d+$/.test(text)) return cb(new Error(t('mercariAccounts.errSellerIdDigits')))
      cb()
    },
    trigger: 'blur',
  },
]

const formRules = {
  account_name: [{ required: true, message: t('mercariAccounts.errAccountNameRequired'), trigger: 'blur' }],
  seller_id: sellerIdRules,
  status: [{ required: true, message: t('mercariAccounts.errStatusRequired'), trigger: 'change' }],
  is_open: [{ required: true, message: t('common.selectPlaceholder'), trigger: 'change' }],
  fetch_interval: [
    {
      validator(_rule, val, cb) {
        if (form.value.is_open === 1) {
          if (!val || !String(val).trim()) {
            cb(new Error(t('mercariAccounts.errIntervalRequired')))
            return
          }
          const anyTask =
            form.value.auto_fetch_order_list === 1 ||
            form.value.auto_fetch_on_sale === 1 ||
            form.value.auto_fetch_todos === 1 ||
            form.value.auto_fetch_notifications === 1
          if (!anyTask) {
            cb(new Error(t('mercariAccounts.errPickOneTask')))
            return
          }
        }
        cb()
      },
      trigger: 'change',
    },
  ],
  pause_window: [
    {
      validator(_rule, _val, cb) {
        if (form.value.is_open !== 1) return cb()
        const s = String(form.value.pause_start_time || '').trim()
        const e = String(form.value.pause_end_time || '').trim()
        if (!s && !e) return cb()
        if (!s || !e) {
          cb(new Error(t('mercariAccounts.errPauseBothRequired')))
          return
        }
        if (s === e) {
          cb(new Error(t('mercariAccounts.errPauseSameTime')))
          return
        }
        cb()
      },
      trigger: 'change',
    },
  ],
}

async function load() {
  loading.value = true
  const params = { page: page.value, page_size: pageSize.value }
  const res = await mercariAccountApi.list(params).finally(() => {
    loading.value = false
  })
  list.value = res.items || []
  total.value = res.total || 0
}

function openPrepareLoginBrowser() {
  openBrowserByKey(MERCARI_PREPARE_KEY, t('mercariAccounts.prepareLoginBrowserLabel'))
}

function openCreate() {
  form.value = createDefaultForm()
  dialogVisible.value = true
  nextTick(() => {
    openPrepareLoginBrowser()
  })
}

function onFetchUserInfoPlaceholder() {
  fetchSellerIdViaMitm()
}

function sellerIdCaptureAccountKey() {
  return form.value.id ? browserKeyFor(form.value.id) : MERCARI_PREPARE_KEY
}

async function fetchSellerIdViaMitm() {
  if (fetchSellerIdLoading.value) return
  const accountKey = sellerIdCaptureAccountKey()
  const label = form.value.id
    ? (form.value.account_name || t('mercariAccounts.accountFallbackLabel', { id: form.value.id }))
    : t('mercariAccounts.preLoginLabel')
  fetchSellerIdLoading.value = true
  try {
    ElMessage.info(t('mercariAccounts.tipOpeningEdge', { label }))
    const res = await mercariAccountApi.fetchSellerIdViaMitm({
      account_key: accountKey,
      headless: false,
      close_browser_after: false,
    })
    const sid = String(res?.data?.seller_id || '').trim()
    if (!sid) {
      ElMessage.warning(t('mercariAccounts.warnNoSellerIdParsed'))
      return
    }
    form.value.seller_id = sid
    await nextTick()
    formRef.value?.validateField('seller_id').catch(() => {})
    ElMessage.success(t('mercariAccounts.msgSellerIdFilled', { sid }))
  } catch {
    /* 错误由 axios 拦截器提示 */
  } finally {
    fetchSellerIdLoading.value = false
  }
}

function openEdit(row) {
  const open = row.is_open === 1 || row.is_open === true ? 1 : 0
  form.value = {
    ...createDefaultForm(),
    id: row.id,
    account_name: row.account_name || '',
    seller_id: row.seller_id != null ? String(row.seller_id) : '',
    status: row.status || 'active',
    remark: row.remark || '',
    is_open: open,
    fetch_interval: open === 1 ? String(row.fetch_interval != null ? row.fetch_interval : '') : '',
    auto_fetch_order_list: row.auto_fetch_order_list === 1 ? 1 : 0,
    auto_fetch_on_sale: row.auto_fetch_on_sale === 1 ? 1 : 0,
    auto_fetch_todos: row.auto_fetch_todos === 1 ? 1 : 0,
    auto_fetch_notifications: row.auto_fetch_notifications === 1 ? 1 : 0,
    pause_start_time: open === 1 ? (row.pause_start_time || null) : null,
    pause_end_time: open === 1 ? (row.pause_end_time || null) : null,
  }
  dialogVisible.value = true
}

function buildPayload() {
  const name = String(form.value.account_name || '').trim()
  const open = form.value.is_open === 1 ? 1 : 0
  const base = {
    account_name: name,
    login_id: name,
    seller_id: String(form.value.seller_id || '').trim() || null,
    status: form.value.status,
    remark: form.value.remark || null,
    is_open: open,
    fetch_interval: open === 1 ? String(form.value.fetch_interval || '').trim() || null : null,
    auto_fetch_order_list: open === 1 && form.value.auto_fetch_order_list === 1 ? 1 : 0,
    auto_fetch_on_sale: open === 1 && form.value.auto_fetch_on_sale === 1 ? 1 : 0,
    auto_fetch_todos: open === 1 && form.value.auto_fetch_todos === 1 ? 1 : 0,
    auto_fetch_notifications: open === 1 && form.value.auto_fetch_notifications === 1 ? 1 : 0,
    pause_start_time: open === 1 ? (String(form.value.pause_start_time || '').trim() || null) : null,
    pause_end_time: open === 1 ? (String(form.value.pause_end_time || '').trim() || null) : null,
  }
  if (form.value.id) {
    return base
  }
  return { ...base }
}

async function submit() {
  await formRef.value?.validate()
  submitting.value = true
  const payload = buildPayload()
  try {
    if (form.value.id) {
      await mercariAccountApi.update(form.value.id, payload)
      ElMessage.success(t('mercariAccounts.msgUpdateSuccess'))
      dialogVisible.value = false
      load()
    } else {
      await mercariAccountApi.create(payload)
      ElMessage.success(t('mercariAccounts.msgCreateSuccess'))
      dialogVisible.value = false
      await load()
    }
  } finally {
    submitting.value = false
  }
}

async function remove(id) {
  await mercariAccountApi.remove(id)
  ElMessage.success(t('mercariAccounts.msgDeleteSuccess'))
  if (list.value.length === 1 && page.value > 1) page.value -= 1
  load()
}

async function removeFromDialog() {
  if (!form.value.id) return
  const id = form.value.id
  await remove(id)
  dialogVisible.value = false
}

const syncingIds = ref(new Set())
const browserLoadingKeys = ref(new Set())
const fetchSellerIdLoading = ref(false)

async function openBrowserByKey(accountKey, label) {
  if (browserLoadingKeys.value.has(accountKey)) return
  const next = new Set(browserLoadingKeys.value)
  next.add(accountKey)
  browserLoadingKeys.value = next
  try {
    const res = await webDriveApi.openSession({
      account_key: accountKey,
      headless: false,
      restore_tabs: true
    })
    const d = res.data || {}
    const tr = d.tab_restore || {}
    const tabHint =
      tr.restored && tr.tab_count
        ? t('mercariAccounts.tabRestoredHint', { count: tr.tab_count })
        : tr.tab_count
          ? t('mercariAccounts.tabOpenedHint', { count: tr.tab_count })
          : ''
    const tip = d.already_running
      ? t('mercariAccounts.browserAlreadyRunning', { tabHint })
      : t('mercariAccounts.browserStarted', { tabHint })
    ElMessage.success(`${label || accountKey}${t('mercariAccounts.colon')}${tip}`)
  } catch {
    /* 错误由 axios 拦截器提示 */
  } finally {
    const s = new Set(browserLoadingKeys.value)
    s.delete(accountKey)
    browserLoadingKeys.value = s
  }
}

function openBrowserForSavedAccount(row) {
  openBrowserByKey(browserKeyFor(row.id), row.account_name || t('mercariAccounts.accountFallbackLabel', { id: row.id }))
}

async function fetchHistory(row) {
  if (syncingIds.value.has(row.id)) return
  const sid = String(row.seller_id || '').trim()
  if (!sid) {
    ElMessage.warning(t('mercariAccounts.warnConfigureSellerIdFirst'))
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
    ElMessage.warning(pre.message || t('mercariAccounts.warnHistoryAlreadyExists'))
    return
  }

  try {
    await ElMessageBox.confirm(
      t('mercariAccounts.confirmFetchHistoryBody'),
      t('mercariAccounts.fetchHistory'),
      {
        type: 'warning',
        confirmButtonText: t('mercariAccounts.confirmFetchBtn'),
        cancelButtonText: t('common.cancel'),
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
      t('mercariAccounts.msgSyncResult', {
        name: row.account_name,
        inserted: d.inserted ?? 0,
        updated: d.updated ?? 0,
        total: d.total_item_count ?? d.total ?? 0,
      })
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
.mercari-dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  width: 100%;
}
.mercari-dialog-footer__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-left: auto;
}
.form-intro-tip {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.55;
  color: #7d8da6;
}
.form-section-hint {
  margin: -4px 0 12px;
  font-size: 12px;
  line-height: 1.55;
  color: #7d8da6;
}
.seller-id-hint {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: #7d8da6;
}
.seller-id-hint a {
  color: #69b1ff;
}
.seller-id-hint code {
  font-size: 11px;
  color: #a8b4c8;
}
.af-task-checks {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
}
.af-task-checks .el-checkbox {
  margin-right: 0;
  height: auto;
  white-space: normal;
}
.af-pause-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}
.af-pause-picker {
  flex: 1;
  min-width: 0;
}
.af-pause-sep {
  color: #7d8da6;
  font-size: 13px;
}
.af-pause-hint {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: #7d8da6;
}
.mercari-form {
  max-height: 70vh;
  overflow-y: auto;
  padding-right: 8px;
}
</style>

<style>
.mercari-dialog .el-dialog__body {
  padding-top: 8px;
}
</style>
