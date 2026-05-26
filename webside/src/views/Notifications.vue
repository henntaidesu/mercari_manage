<template>
  <div>
    <el-card shadow="never" class="search-card">
      <el-row :gutter="0" align="middle" class="search-row">
        <el-col :xs="24" :md="16" class="search-left-group">
          <el-input
            v-model="filters.keyword"
            :placeholder="t('notifications.searchKeywordPlaceholder')"
            clearable
            @change="onFilterChange"
          />
          <el-select
            v-model="filters.account_id"
            :placeholder="t('notifications.account')"
            clearable
            filterable
            style="min-width: 200px"
            @change="onFilterChange"
          >
            <el-option
              v-for="a in accountOptions"
              :key="a.id"
              :label="a.label"
              :value="a.id"
            />
          </el-select>
          <el-select
            v-model="filters.kind"
            :placeholder="t('common.type')"
            clearable
            filterable
            style="min-width: 200px"
            @change="onFilterChange"
          >
            <el-option
              v-for="k in kindOptions"
              :key="k"
              :label="kindLabel(k)"
              :value="k"
            />
          </el-select>
          <el-checkbox v-model="filters.only_unread" @change="onFilterChange">
            {{ t('notifications.onlyUnread') }}
          </el-checkbox>
          <el-checkbox v-model="filters.show_likes" @change="onFilterChange">
            {{ t('notifications.showLikes') }}
          </el-checkbox>
        </el-col>
        <el-col :xs="24" :md="8" class="search-actions">
          <el-select
            v-model="globalAccountId"
            :placeholder="t('notifications.selectMercariAccount')"
            filterable
            class="sync-account-select"
            :loading="mercariAccountStore.loading"
          >
            <el-option
              v-for="acc in mercariAccountStore.activeAccounts"
              :key="acc.id"
              :label="acc.account_name"
              :value="acc.id"
            />
          </el-select>
          <el-button type="primary" :icon="Download" :loading="syncLoading" @click="runSync">
            {{ t('notifications.syncFromMercari') }}
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table :data="list" v-loading="loading" stripe row-key="id">
        <el-table-column :label="t('notifications.colImage')" width="80" align="center" header-align="center">
          <template #default="{ row }">
            <el-image
              v-if="row.photo_url"
              class="ntf-thumb"
              :src="row.photo_url"
              :preview-src-list="[row.photo_url]"
              :preview-teleported="true"
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

        <el-table-column :label="t('common.type')" width="160" align="center" header-align="center">
          <template #default="{ row }">
            <el-tag :type="kindTagType(row.kind)" size="small" effect="light">
              {{ kindLabel(row.kind) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="t('notifications.colMessage')" min-width="360" align="left" header-align="center">
          <template #default="{ row }">
            <div :class="['cell-message', !row.is_read ? 'cell-message-unread' : '']">
              {{ row.message || '-' }}
            </div>
            <div v-if="row.item_id" class="cell-itemid">
              <span class="cell-itemid-text">{{ row.item_id }}</span>
              <span v-if="row.item_name" class="cell-itemname">{{ row.item_name }}</span>
            </div>
            <div v-if="row.price" class="cell-extra">{{ t('notifications.priceDownRequest') }}: ¥{{ formatYen(row.price) }}</div>
            <div v-if="row.bid_price" class="cell-extra">{{ t('notifications.bidLabel') }}: ¥{{ formatYen(row.bid_price) }}</div>
          </template>
        </el-table-column>

        <el-table-column :label="t('notifications.colSender')" width="160" align="center" header-align="center">
          <template #default="{ row }">
            <div v-if="senderNameFromMessage(row.message)" class="cell-buyer">
              {{ senderNameFromMessage(row.message) }}
            </div>
            <div v-if="row.sender_id && row.sender_id !== '0'" class="cell-sender-id">
              ID: {{ row.sender_id }}
            </div>
            <span
              v-if="!row.sender_id && !senderNameFromMessage(row.message)"
              class="cell-muted"
            >-</span>
          </template>
        </el-table-column>

        <el-table-column :label="t('common.time')" width="170" align="center" header-align="center">
          <template #default="{ row }">
            <div>{{ displayTs(row.mercari_created) }}</div>
          </template>
        </el-table-column>

        <el-table-column :label="t('notifications.account')" width="140" align="center" header-align="center">
          <template #default="{ row }">
            <span>{{ row.account_name || `#${row.account_id}` }}</span>
          </template>
        </el-table-column>

        <el-table-column :label="t('common.operate')" width="170" align="center" header-align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="actionForKind(row.kind) === 'open'"
              type="primary"
              link
              size="small"
              :disabled="!hasTargetUrl(row)"
              @click="onOpenTarget(row)"
            >
              {{ t('notifications.open') }}
            </el-button>
            <el-button
              v-else-if="actionForKind(row.kind) === 'detail'"
              type="primary"
              link
              size="small"
              @click="onViewDetail(row)"
            >
              {{ t('notifications.viewDetail') }}
            </el-button>
            <el-button
              v-if="!row.is_read"
              type="success"
              link
              size="small"
              :loading="markReadLoadingIds.has(row.id)"
              @click="onMarkRead(row)"
            >
              {{ t('notifications.read') }}
            </el-button>
            <el-button
              v-else
              type="info"
              link
              size="small"
              :loading="markReadLoadingIds.has(row.id)"
              @click="onMarkUnread(row)"
            >
              {{ t('notifications.markUnread') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pagination"
        background
        layout="prev, pager, next, sizes, total"
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        @current-change="onPageChange"
        @size-change="onPageSizeChange"
      />
    </el-card>

    <BundlePurchaseDialog
      v-model="bundleDialogVisible"
      :bundle-id="bundleDialogBundleId"
      :account-id="bundleDialogAccountId"
      :notification-id="bundleDialogNotificationId"
    />

    <ItemCommentDialog
      v-model="commentDialogVisible"
      :item-id="commentDialogItemId"
      :item-name="commentDialogItemName"
      :account-id="commentDialogAccountId"
    />

    <DesiredPriceDialog
      v-model="desiredPriceDialogVisible"
      :item-id="desiredPriceDialogItemId"
      :item-name="desiredPriceDialogItemName"
      :account-id="desiredPriceDialogAccountId"
      :notification-id="desiredPriceDialogNotificationId"
    />

    <teleport to="body">
      <div
        v-show="syncOverlayVisible"
        class="notifications-sync-overlay notifications-sync-overlay--dark"
        :class="{ 'notifications-sync-overlay--failed': syncOverlayFailed }"
        role="status"
        aria-live="polite"
      >
        <div class="notifications-sync-overlay__box">
          <el-icon class="is-loading notifications-sync-overlay__icon" :size="40"><Loading /></el-icon>
          <div class="notifications-sync-overlay__title">{{ syncOverlayTitle }}</div>
          <div class="notifications-sync-overlay__step">{{ syncProgressLabel || t('notifications.pleaseWait') }}</div>
        </div>
      </div>
    </teleport>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Loading } from '@element-plus/icons-vue'
import { notificationsApi, mercariAccountApi } from '@/api'
import { useMercariAccountStore } from '@/stores/mercariAccount.js'
import BundlePurchaseDialog from '@/components/BundlePurchaseDialog.vue'
import ItemCommentDialog from '@/components/ItemCommentDialog.vue'
import DesiredPriceDialog from '@/components/DesiredPriceDialog.vue'

const { t } = useI18n()
const mercariAccountStore = useMercariAccountStore()
const globalAccountId = computed({
  get: () => mercariAccountStore.selectedId,
  set: (v) => mercariAccountStore.setSelected(v),
})

const KIND_LABEL_KEYS = {
  Like: 'notifications.kindLike',
  Comment: 'notifications.kindComment',
  LikedItemReceiveComment: 'notifications.kindLikedItemReceiveComment',
  DesiredPriceOfferCreated: 'notifications.kindDesiredPriceOfferCreated',
  AuctionBidCreated: 'notifications.kindAuctionBidCreated',
  BundleRequestCreated: 'notifications.kindBundleRequestCreated',
  WaitPayment: 'notifications.kindWaitPayment',
  PrivateMessage: 'notifications.kindPrivateMessage',
  'merpay-egp-ian-promotion': 'notifications.kindPromotion',
  'merpay-egp-ian-promotion-action-url': 'notifications.kindPromotion',
}

const KIND_TAG_TYPES = {
  Like: 'danger',
  Comment: 'primary',
  LikedItemReceiveComment: 'primary',
  DesiredPriceOfferCreated: 'warning',
  AuctionBidCreated: 'warning',
  BundleRequestCreated: 'warning',
  WaitPayment: 'success',
  PrivateMessage: 'info',
  'merpay-egp-ian-promotion': 'info',
  'merpay-egp-ian-promotion-action-url': 'info',
}

// 操作列按 kind 区分动作类型：
// - 'none'   不显示业务按钮（仅保留 标已读/标未读）
// - 'detail' 显示「查看详情」按钮（占位，暂不对接）
// - 'open'   其他默认走「打开」（跳 target_url / action_url / item 页）
const KIND_ACTION = {
  Like: 'none',
  AuctionBidCreated: 'none',
  'merpay-egp-ian-promotion': 'none',
  'merpay-egp-ian-promotion-action-url': 'none',
  Comment: 'detail',
  BundleRequestCreated: 'detail',
  DesiredPriceOfferCreated: 'detail',
}

function actionForKind(kind) {
  return KIND_ACTION[kind] || 'open'
}

const list = ref([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)

const filters = ref({
  keyword: '',
  account_id: null,
  kind: '',
  // 默认仅显示未读，已读的需要勾掉才能看到
  only_unread: true,
  // 默认不显示「点赞」类型；用户勾选后或主动按 kind=Like 过滤时才显示
  show_likes: false,
})

const accountOptions = ref([])
const kindOptions = ref([])
const syncLoading = ref(false)
const markReadLoadingIds = ref(new Set())

/** 「从煤炉同步」全屏等待与步骤文案（与后端 progress_job_id 轮询同步） */
const syncOverlayVisible = ref(false)
const syncOverlayTitle = ref(t('notifications.syncingFromMercari'))
const syncOverlayFailed = ref(false)
const syncProgressLabel = ref('')
let syncProgressTimer = null

function listParams() {
  const p = { page: page.value, page_size: pageSize.value }
  const kw = filters.value.keyword?.trim()
  if (kw) p.keyword = kw
  if (filters.value.account_id) p.account_id = filters.value.account_id
  if (filters.value.kind) p.kind = filters.value.kind
  if (filters.value.only_unread) p.only_unread = true
  // 用户没显式按 kind=Like 过滤且未勾选「显示点赞」时，排除 Like
  if (!filters.value.show_likes && filters.value.kind !== 'Like') {
    p.exclude_kinds = 'Like'
  }
  return p
}

async function load() {
  loading.value = true
  try {
    const res = await notificationsApi.list(listParams())
    list.value = res?.items || []
    total.value = Number(res?.total || 0)
  } catch (e) {
    ElMessage.error(e?.message || t('notifications.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function loadAccountOptions() {
  try {
    const res = await mercariAccountApi.list({ page: 1, page_size: 200 })
    accountOptions.value = (res.items || []).map((a) => ({
      id: a.id,
      label: `${a.account_name}${a.seller_id ? ` (${a.seller_id})` : ''}`,
    }))
  } catch {
    accountOptions.value = []
  }
}

async function loadKindOptions() {
  try {
    const res = await notificationsApi.kinds()
    const arr = res?.kinds
    kindOptions.value = Array.isArray(arr) ? arr : []
  } catch {
    kindOptions.value = []
  }
}

function onFilterChange() {
  page.value = 1
  load()
}
function onPageChange(p) {
  page.value = p
  load()
}
function onPageSizeChange(s) {
  pageSize.value = s
  page.value = 1
  load()
}

async function runSync() {
  if (syncLoading.value) return
  const aid = mercariAccountStore.selectedId
  if (!aid) {
    ElMessage.warning(t('notifications.pleaseSelectMercariAccount'))
    return
  }
  const name = mercariAccountStore.selectedAccountName || `#${aid}`
  try {
    await ElMessageBox.confirm(
      t('notifications.syncConfirmContent', { name }),
      t('notifications.syncConfirmTitle'),
      { type: 'info', confirmButtonText: t('notifications.startBtn'), cancelButtonText: t('common.cancel') },
    )
  } catch {
    return
  }

  const progressJobId =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `job_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`

  let lastConsoleStep = ''
  async function pollSyncProgress() {
    try {
      const pr = await notificationsApi.getSyncProgress(progressJobId)
      const d = pr?.data
      const zh = d?.label_zh
      if (zh) {
        syncProgressLabel.value = zh
        if (zh !== lastConsoleStep) {
          lastConsoleStep = zh
          console.log('[通知同步]', zh)
        }
      }
    } catch {
      /* 轮询失败忽略 */
    }
  }

  syncOverlayTitle.value = t('notifications.syncingFromMercari')
  syncOverlayFailed.value = false
  syncProgressLabel.value = t('notifications.connectingServer')
  syncOverlayVisible.value = true
  syncLoading.value = true
  await pollSyncProgress()
  syncProgressTimer = setInterval(pollSyncProgress, 400)

  let syncHadError = false
  try {
    const d = (await notificationsApi.sync({ account_id: aid, progress_job_id: progressJobId })) || {}
    ElMessageBox.alert(
      t('notifications.syncResultContent', {
        accountId: d.account_id ?? '-',
        inserted: d.inserted ?? 0,
        updated: d.updated ?? 0,
        total: d.total ?? 0,
      }),
      t('notifications.syncResultTitle'),
      { type: 'success', confirmButtonText: t('dialog.confirmBtn') },
    )
    await Promise.all([load(), loadKindOptions()])
  } catch (e) {
    syncHadError = true
    syncOverlayTitle.value = t('notifications.syncFailed')
    syncOverlayFailed.value = true
    const msg = e?.response?.data?.detail || e?.message || t('notifications.syncFailed')
    syncProgressLabel.value = String(msg)
    ElMessage.error(msg)
  } finally {
    if (syncProgressTimer != null) {
      clearInterval(syncProgressTimer)
      syncProgressTimer = null
    }
    if (syncHadError) {
      await new Promise((r) => setTimeout(r, 1200))
    }
    syncOverlayVisible.value = false
    syncOverlayTitle.value = t('notifications.syncingFromMercari')
    syncOverlayFailed.value = false
    syncProgressLabel.value = ''
    syncLoading.value = false
  }
}

function hasTargetUrl(row) {
  return !!(row?.target_url || row?.action_url || row?.item_id)
}

function itemUrlFor(row) {
  const iid = String(row?.item_id || '').trim()
  if (iid) return `https://jp.mercari.com/item/${iid}`
  return '#'
}

const bundleDialogVisible = ref(false)
const bundleDialogBundleId = ref('')
const bundleDialogAccountId = ref(null)
const bundleDialogNotificationId = ref(null)

const commentDialogVisible = ref(false)
const commentDialogItemId = ref('')
const commentDialogItemName = ref('')
const commentDialogAccountId = ref(null)

const desiredPriceDialogVisible = ref(false)
const desiredPriceDialogItemId = ref('')
const desiredPriceDialogItemName = ref('')
const desiredPriceDialogAccountId = ref(null)
const desiredPriceDialogNotificationId = ref(null)

function extractBundleId(row) {
  const raw = String(row?.intent_json || '').trim()
  if (!raw) return ''
  try {
    const obj = JSON.parse(raw)
    const id = obj?.extra?.bundle_id
    return typeof id === 'string' ? id.trim() : ''
  } catch {
    return ''
  }
}

// 部分通知 (如 DesiredPriceOfferCreated) item_id 不在 args 而在 intent.extra.id;
// 后端旧版同步未覆盖此情况,前端这里兜底从 intent_json 解析。
function resolveItemId(row) {
  const direct = String(row?.item_id || '').trim()
  if (direct) return direct
  const raw = String(row?.intent_json || '').trim()
  if (!raw) return ''
  try {
    const obj = JSON.parse(raw)
    if (String(obj?.activity || '').trim() === 'ItemDetailActivity') {
      const id = obj?.extra?.id
      return typeof id === 'string' ? id.trim() : ''
    }
  } catch { /* ignore */ }
  return ''
}

function autoMarkRead(row) {
  if (row?.id && !row.is_read) {
    notificationsApi.markRead([row.id], true).then(() => {
      row.is_read = 1
    }).catch(() => {})
  }
}

function onViewDetail(row) {
  if (row?.kind === 'BundleRequestCreated') {
    const bid = extractBundleId(row)
    if (!bid) {
      ElMessage.warning(t('notifications.noBundleId'))
      return
    }
    bundleDialogBundleId.value = bid
    bundleDialogAccountId.value = row.account_id || null
    bundleDialogNotificationId.value = row.id || null
    bundleDialogVisible.value = true
    autoMarkRead(row)
    return
  }
  if (row?.kind === 'Comment') {
    const iid = resolveItemId(row)
    if (!iid) {
      ElMessage.warning(t('notifications.noItemIdComment'))
      return
    }
    commentDialogItemId.value = iid
    commentDialogItemName.value = row.item_name || ''
    commentDialogAccountId.value = row.account_id || null
    commentDialogVisible.value = true
    autoMarkRead(row)
    return
  }
  if (row?.kind === 'DesiredPriceOfferCreated') {
    const iid = resolveItemId(row)
    if (!iid) {
      ElMessage.warning(t('notifications.noItemIdDesiredPrice'))
      return
    }
    desiredPriceDialogItemId.value = iid
    desiredPriceDialogItemName.value = row.item_name || ''
    desiredPriceDialogAccountId.value = row.account_id || null
    desiredPriceDialogNotificationId.value = row.id || null
    desiredPriceDialogVisible.value = true
    autoMarkRead(row)
    return
  }
  ElMessage.info(t('notifications.detailNotReady', { kind: row.kind }))
}

async function onMarkRead(row) {
  if (!row?.id || row.is_read) return
  if (markReadLoadingIds.value.has(row.id)) return
  const next = new Set(markReadLoadingIds.value)
  next.add(row.id)
  markReadLoadingIds.value = next
  try {
    await notificationsApi.markRead([row.id], true)
    row.is_read = 1
    // 默认筛选「仅未读」时，该行需从列表中移除以保持视图一致
    if (filters.value.only_unread) {
      list.value = list.value.filter((r) => r.id !== row.id)
      total.value = Math.max(0, total.value - 1)
    }
  } catch (e) {
    ElMessage.error(e?.message || t('notifications.markReadFailed'))
  } finally {
    const after = new Set(markReadLoadingIds.value)
    after.delete(row.id)
    markReadLoadingIds.value = after
  }
}

async function onMarkUnread(row) {
  if (!row?.id || !row.is_read) return
  if (markReadLoadingIds.value.has(row.id)) return
  const next = new Set(markReadLoadingIds.value)
  next.add(row.id)
  markReadLoadingIds.value = next
  try {
    await notificationsApi.markRead([row.id], false)
    row.is_read = 0
  } catch (e) {
    ElMessage.error(e?.message || t('notifications.markUnreadFailed'))
  } finally {
    const after = new Set(markReadLoadingIds.value)
    after.delete(row.id)
    markReadLoadingIds.value = after
  }
}

async function onOpenTarget(row) {
  let url = String(row?.target_url || row?.action_url || '').trim()
  if (!url && row?.item_id) {
    url = `https://jp.mercari.com/item/${row.item_id}`
  }
  if (!url) {
    ElMessage.warning(t('notifications.noTargetUrl'))
    return
  }
  window.open(url, '_blank', 'noopener')
  // 打开后自动标已读（fire-and-forget）
  if (!row.is_read) {
    try {
      await notificationsApi.markRead([row.id], true)
      row.is_read = 1
    } catch { /* 忽略 */ }
  }
}

function kindLabel(kind) {
  if (!kind) return '-'
  const key = KIND_LABEL_KEYS[kind]
  return key ? t(key) : kind
}
function kindTagType(kind) {
  return KIND_TAG_TYPES[kind] || 'info'
}

function displayTs(ms) {
  const n = Number(ms || 0)
  if (!n) return '-'
  const d = new Date(n)
  if (Number.isNaN(d.getTime())) return '-'
  const pad = (x) => String(x).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function formatYen(n) {
  const v = Number(n || 0)
  if (!v) return '0'
  return v.toLocaleString('ja-JP')
}

function senderNameFromMessage(msg) {
  const s = String(msg || '')
  const m = s.match(/^(.+?)さん[がにへ、]/)
  return m ? m[1].trim() : ''
}

onMounted(() => {
  mercariAccountStore.ensureLoaded()
  Promise.all([loadAccountOptions(), loadKindOptions()])
  load()
})

onBeforeUnmount(() => {
  if (syncProgressTimer != null) {
    clearInterval(syncProgressTimer)
    syncProgressTimer = null
  }
})
</script>

<style scoped>
.search-card {
  margin-bottom: 16px;
  border-radius: 8px;
}
.search-row {
  justify-content: space-between;
  row-gap: 10px;
}
.search-left-group {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.search-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.sync-account-select {
  width: 180px;
}
.table-card {
  border-radius: 8px;
}
.ntf-thumb {
  width: 56px;
  height: 56px;
  border-radius: 6px;
  display: block;
}
.thumb-fallback {
  color: var(--el-text-color-placeholder);
  font-size: 12px;
}
.cell-message {
  color: var(--el-text-color-regular);
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}
.cell-message-unread {
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.cell-itemid {
  margin-top: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.cell-itemname {
  color: var(--el-text-color-secondary);
}
.cell-extra {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-color-warning);
}
.cell-buyer {
  font-weight: 500;
}
.cell-sender-id {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-top: 2px;
}
.cell-muted {
  color: var(--el-text-color-placeholder);
}
.cell-muted-sm {
  color: var(--el-text-color-placeholder);
  font-size: 11px;
  margin-top: 2px;
}
.row-tag-unread {
  margin-top: 4px;
  color: var(--el-color-danger);
  font-size: 11px;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
  display: flex;
}
</style>

<!-- 「从煤炉同步」全屏等待（teleport 到 body，须无 scoped；黑色主题） -->
<style>
.notifications-sync-overlay.notifications-sync-overlay--dark {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(6px);
}
.notifications-sync-overlay--dark .notifications-sync-overlay__box {
  min-width: 280px;
  max-width: min(440px, 92vw);
  padding: 28px 32px;
  background: linear-gradient(165deg, #1c1c1f 0%, #121214 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  text-align: center;
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.04) inset,
    0 20px 50px rgba(0, 0, 0, 0.65);
}
.notifications-sync-overlay--dark .notifications-sync-overlay__icon {
  color: #94a3b8;
}
.notifications-sync-overlay--dark .notifications-sync-overlay__title {
  margin-top: 14px;
  font-size: 17px;
  font-weight: 600;
  color: #f1f5f9;
  letter-spacing: 0.02em;
}
.notifications-sync-overlay--dark.notifications-sync-overlay--failed .notifications-sync-overlay__title {
  color: #f87171;
}
.notifications-sync-overlay--dark.notifications-sync-overlay--failed .notifications-sync-overlay__step {
  color: #cbd5e1;
}
.notifications-sync-overlay--dark .notifications-sync-overlay__step {
  margin-top: 10px;
  font-size: 14px;
  color: #94a3b8;
  line-height: 1.55;
  word-break: break-word;
}
</style>
