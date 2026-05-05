<template>
  <div>
    <el-card shadow="never" class="search-card">
      <el-row :gutter="0" align="middle" class="search-row">
        <el-col :xs="24" :md="14" class="search-left-group">
          <el-input
            v-model="filters.keyword"
            placeholder="搜索商品ID、标题"
            clearable
            @change="onFilterChange"
          />
          <el-select
            v-model="filters.seller_id"
            placeholder="卖家（煤炉ID）"
            clearable
            filterable
            style="min-width: 200px; width: 100%"
            @change="onFilterChange"
          >
            <el-option
              v-for="s in sellerOptions"
              :key="s.value"
              :label="s.label"
              :value="s.value"
            />
          </el-select>
          <el-select
            v-model="filters.status"
            placeholder="商品状态"
            clearable
            filterable
            style="max-width: 180px; width: 100%"
            @change="onFilterChange"
          >
            <el-option
              v-for="opt in onSaleStatusFilterOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-col>
        <el-col :xs="24" :md="10" class="search-actions">
          <el-button type="primary" :icon="Download" :loading="syncLoading" @click="openSyncDialog">
            从煤炉同步
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table
        :data="displayList"
        v-loading="loading"
        stripe
        row-key="item_id"
        :row-class-name="onSaleRowClassName"
        @expand-change="onTableExpandChange"
      >
        <el-table-column type="expand" width="44">
          <template #default="props">
            <div v-loading="expandSlot(props.row.item_id)?.loading" class="os-expand-wrap">
              <el-table
                :data="expandSlot(props.row.item_id)?.rows || []"
                border
                size="small"
                class="os-expand-table"
                empty-text="暂无数据，展开后自动加载"
              >
                <el-table-column label="管理ID" width="120" align="center">
                  <template #default="{ row: r }">
                    <div v-if="inventoryLines(r).length" class="multi-line-cell">
                      <div v-for="(ln, idx) in inventoryLines(r)" :key="`mgmt-${idx}`">{{ ln.management_id || '-' }}</div>
                    </div>
                    <span v-else class="cell-muted">-</span>
                  </template>
                </el-table-column>
                <el-table-column label="条码" min-width="180" show-overflow-tooltip>
                  <template #default="{ row: r }">
                    <div v-if="inventoryLines(r).length" class="multi-line-cell">
                      <div v-for="(ln, idx) in inventoryLines(r)" :key="`bc-${idx}`">{{ ln.barcode || '-' }}</div>
                    </div>
                    <span v-else class="cell-muted">-</span>
                  </template>
                </el-table-column>
                <el-table-column label="商品名称" min-width="180" show-overflow-tooltip>
                  <template #default="{ row: r }">
                    <div v-if="inventoryLines(r).length" class="multi-line-cell">
                      <div v-for="(ln, idx) in inventoryLines(r)" :key="`name-${idx}`">{{ ln.product_name || '-' }}</div>
                    </div>
                    <span v-else class="cell-muted">-</span>
                  </template>
                </el-table-column>
                <el-table-column label="存储位置" min-width="180" show-overflow-tooltip>
                  <template #default="{ row: r }">
                    <div v-if="inventoryLines(r).length" class="multi-line-cell">
                      <div v-for="(ln, idx) in inventoryLines(r)" :key="`loc-${idx}`">{{ ln.location || '-' }}</div>
                    </div>
                    <span v-else class="cell-muted">-</span>
                  </template>
                </el-table-column>
                <el-table-column label="在售数" width="90" align="center">
                  <template #default="{ row: r }">
                    <div v-if="inventoryLines(r).length" class="multi-line-cell">
                      <div v-for="(ln, idx) in inventoryLines(r)" :key="`qty-${idx}`">{{ ln.on_sale_quantity ?? 0 }}</div>
                    </div>
                    <span v-else class="cell-muted">-</span>
                  </template>
                </el-table-column>
                <el-table-column label="更新" width="140" align="center">
                  <template #default="{ row: r }">{{ displayTs(r.updated) }}</template>
                </el-table-column>
              </el-table>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="图" width="72" align="center" header-align="center" fixed>
          <template #default="{ row }">
            <el-image
              v-if="firstThumb(row)"
              class="os-thumb"
              :src="firstThumb(row)"
              :preview-src-list="thumbPreviewList(row)"
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
        <el-table-column label="商品ID" prop="item_id" width="128" show-overflow-tooltip align="center" header-align="center" />
        <el-table-column label="卖家" prop="seller_name" width="120" show-overflow-tooltip align="center" header-align="center">
          <template #default="{ row }">
            <span>{{ row.seller_name || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="标题" prop="name" min-width="200" show-overflow-tooltip align="left" header-align="center" />
        <el-table-column label="价格¥" width="88" align="center" header-align="center">
          <template #default="{ row }">{{ Number(row.price || 0) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="112" align="center" header-align="center">
          <template #default="{ row }">
            <el-tag :type="onSaleStatusTagType(row.status)" size="small" effect="light">
              {{ onSaleStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="赞/评" width="76" align="center" header-align="center">
          <template #default="{ row }">{{ row.num_likes ?? 0 }}/{{ row.num_comments ?? 0 }}</template>
        </el-table-column>
        <el-table-column label="PV/近7日" width="100" align="center" header-align="center">
          <template #default="{ row }">{{ row.item_pv ?? 0 }}/{{ row.recent_item_pv ?? 0 }}</template>
        </el-table-column>
        <el-table-column label="搜索曝光" width="108" align="center" header-align="center">
          <template #default="{ row }">
            <span v-if="row.search_impression != null">{{ row.search_impression }}/{{ row.recent_search_impression ?? '-' }}</span>
            <span v-else class="cell-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="拍卖" width="72" align="center" header-align="center">
          <template #default="{ row }">
            <el-popover v-if="row.auction_info_json" placement="left" :width="280" trigger="click">
              <template #reference>
                <el-button link type="primary" size="small">查看</el-button>
              </template>
              <pre class="auction-pre">{{ formatJsonPretty(row.auction_info_json) }}</pre>
            </el-popover>
            <span v-else class="cell-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="创建" width="160" align="center" header-align="center">
          <template #default="{ row }">{{ displayTs(row.created) }}</template>
        </el-table-column>
        <el-table-column label="更新" width="160" align="center" header-align="center">
          <template #default="{ row }">{{ displayTs(row.updated) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right" align="center" header-align="center">
          <template #default="{ row }">
            <el-button
              type="primary"
              link
              size="small"
              :loading="manageLoadingIds.has(String(row.item_id || '').trim())"
              @click="openMercariManage(row)"
            >
              管理
            </el-button>
            <el-button
              :type="hasSecondaryData(row) ? 'success' : 'warning'"
              link
              size="small"
              :loading="detailLoadingIds.has(String(row.item_id || '').trim())"
              @click="fetchItemDetail(row)"
            >
              获取详情
            </el-button>
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

    <el-dialog v-model="syncVisible" title="从煤炉同步在售列表" width="420px" destroy-on-close>
      <el-form label-width="88px">
        <el-form-item label="煤炉账号">
          <el-select
            v-model="syncAccountId"
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
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="syncVisible = false">取消</el-button>
        <el-button type="primary" :loading="syncLoading" @click="runSync">开始同步</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import { onSaleItemApi, meiluAccountApi, webDriveApi } from '@/api/index.js'

/** 煤炉商品 item.status → 中文（与 API 原始值对应，筛选仍传英文枚举） */
const onSaleStatusMap = {
  on_sale: { label: '出售中', tag: 'success' },
  stop: { label: '暂停出售', tag: 'warning' },
  trading: { label: '交易中', tag: 'primary' },
  wait_payment: { label: '待支付', tag: 'warning' },
  wait_shipping: { label: '待发货', tag: 'warning' },
  wait_review: { label: '待评价', tag: 'primary' },
  sold_out: { label: '已售完', tag: 'info' },
  done: { label: '已完成', tag: 'success' },
  cancelled: { label: '已取消', tag: 'info' },
  cancel_request: { label: '取消申请中', tag: 'danger' },
  deleted: { label: '已删除', tag: 'danger' },
  private: { label: '非公开', tag: 'info' },
  pending: { label: '待处理', tag: 'info' },
}

const onSaleStatusFilterOptions = Object.entries(onSaleStatusMap).map(([value, o]) => ({
  value,
  label: o.label,
}))

function onSaleStatusLabel(status) {
  if (status == null || status === '') return '-'
  const s = String(status).trim()
  return onSaleStatusMap[s]?.label ?? s
}

function onSaleStatusTagType(status) {
  const s = String(status ?? '').trim()
  return onSaleStatusMap[s]?.tag ?? 'info'
}

const loading = ref(false)
/** 正在请求 items/get 的商品 ID（trim 后） */
const detailLoadingIds = ref(new Set())
/** 正在打开管理页的商品 ID（trim 后） */
const manageLoadingIds = ref(new Set())
const syncLoading = ref(false)
const syncVisible = ref(false)
const syncAccountId = ref(null)
const accountOptions = ref([])
const accountsLoading = ref(false)

const list = ref([])
/** 展开区：key 为 trim 后的 item_id */
const expandByItemId = reactive({})
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const filters = ref({
  keyword: '',
  seller_id: '',
  status: '',
})

const sellerFromAccounts = ref([])

function isOnSaleZeroStockAlert(row) {
  if (!row || typeof row !== 'object') return false
  const status = String(row.status ?? '').trim()
  if (status !== 'on_sale') return false
  const q = Number(row.inventory_quantity)
  if (!Number.isFinite(q)) return false
  return q <= 0
}

const displayList = computed(() => {
  const arr = Array.isArray(list.value) ? list.value.slice() : []
  return arr
    .map((row, idx) => ({ row, idx }))
    .sort((a, b) => {
      const aw = isOnSaleZeroStockAlert(a.row) ? 1 : 0
      const bw = isOnSaleZeroStockAlert(b.row) ? 1 : 0
      if (aw !== bw) return bw - aw
      return a.idx - b.idx
    })
    .map((x) => x.row)
})

function onSaleRowClassName({ row }) {
  return isOnSaleZeroStockAlert(row) ? 'on-sale-stock-alert-row' : ''
}

const sellerOptions = computed(() => {
  const m = new Map()
  for (const s of sellerFromAccounts.value) {
    if (s?.value) m.set(String(s.value), s)
  }
  for (const row of list.value) {
    const sid = row.seller_id
    if (sid != null && String(sid).trim()) {
      const k = String(sid).trim()
      if (!m.has(k)) m.set(k, { value: k, label: `卖家 ${k}` })
    }
  }
  return Array.from(m.values())
})

function listParams() {
  const p = { page: page.value, page_size: pageSize.value }
  if (filters.value.keyword?.trim()) p.keyword = filters.value.keyword.trim()
  if (filters.value.seller_id?.trim()) p.seller_id = filters.value.seller_id.trim()
  if (filters.value.status?.trim()) p.status = filters.value.status.trim()
  return p
}

function expandKey(itemId) {
  return String(itemId ?? '').trim()
}

function expandSlot(itemId) {
  const k = expandKey(itemId)
  return k ? expandByItemId[k] : null
}

function hasSecondaryData(row) {
  if (!row || typeof row !== 'object') return false
  const mgmt = String(row.inventory_mgmt_ids_text || '').trim()
  const barcodes = String(row.inventory_barcodes_text || '').trim()
  const matched = Number(row.inventory_match_count || 0)
  return Boolean(mgmt || barcodes || matched > 0)
}

function inventoryLines(row) {
  if (!row || !Array.isArray(row.inventory_lines)) return []
  return row.inventory_lines
}

async function ensureExpandLoaded(row) {
  const k = expandKey(row.item_id)
  if (!k) return
  if (!expandByItemId[k]) {
    expandByItemId[k] = { loading: false, loaded: false, rows: [], total: 0 }
  }
  const slot = expandByItemId[k]
  if (slot.loaded || slot.loading) return
  slot.loading = true
  try {
    const res = await onSaleItemApi.listByItemId({ item_id: k })
    slot.rows = res.items || []
    slot.total = res.total != null ? res.total : slot.rows.length
    slot.loaded = true
  } catch {
    slot.rows = []
    slot.total = 0
    slot.loaded = true
  } finally {
    slot.loading = false
  }
}

/** 展开行时按商品 ID 拉取在售表明细（二级表格） */
function onTableExpandChange(row, expandedRows) {
  const k = expandKey(row.item_id)
  if (!k) return
  const opened = expandedRows.some((r) => expandKey(r.item_id) === k)
  if (opened) ensureExpandLoaded(row)
}

async function load() {
  loading.value = true
  try {
    const res = await onSaleItemApi.list(listParams())
    list.value = res.items || []
    total.value = res.total || 0
    for (const k of Object.keys(expandByItemId)) {
      delete expandByItemId[k]
    }
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  page.value = 1
  load()
}

const pad2 = (n) => String(n).padStart(2, '0')

function displayTs(sec) {
  if (sec == null || sec === '') return '-'
  const n = Number(sec)
  if (!Number.isFinite(n)) return String(sec)
  const ms = n > 1e12 ? n : n * 1000
  const d = new Date(ms)
  if (Number.isNaN(d.getTime())) return String(sec)
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`
}

function thumbPreviewList(row) {
  const raw = row.thumbnails
  if (!raw) return []
  if (Array.isArray(raw)) {
    return raw.map((u) => String(u).trim()).filter(Boolean)
  }
  if (typeof raw === 'string') {
    try {
      const arr = JSON.parse(raw)
      if (Array.isArray(arr)) {
        return arr.map((u) => String(u).trim()).filter(Boolean)
      }
    } catch {
      /* ignore */
    }
  }
  return []
}

function firstThumb(row) {
  const urls = thumbPreviewList(row)
  return urls.length ? urls[0] : ''
}

function formatJsonPretty(raw) {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return String(raw || '')
  }
}

/** 煤炉商品页路径段：API 多为 m 开头，纯数字时补 m */
function mercariItemPathSegment(itemId) {
  const raw = String(itemId ?? '').trim()
  if (!raw) return ''
  return raw.startsWith('m') ? raw : `m${raw}`
}

async function openMercariManage(row) {
  const seg = mercariItemPathSegment(row.item_id)
  if (!seg) {
    ElMessage.warning('缺少商品 ID')
    return
  }
  const sid = String(row.seller_id || '').trim()
  if (!sid) {
    ElMessage.warning('缺少卖家 ID，无法定位对应账号')
    return
  }
  const matched = sellerFromAccounts.value.find((a) => String(a.seller_id || '').trim() === sid)
  if (!matched?.id) {
    ElMessage.warning(`未找到卖家 ${sid} 对应的 active 账号，请先在账号管理配置 seller_id`)
    return
  }
  const iid = String(row.item_id || '').trim()
  if (manageLoadingIds.value.has(iid)) return
  const next = new Set(manageLoadingIds.value)
  next.add(iid)
  manageLoadingIds.value = next
  const url = `https://jp.mercari.com/item/${encodeURIComponent(seg)}`
  try {
    const res = await webDriveApi.openSession({
      account_key: `meilu_${matched.id}`,
      headless: false,
      start_url: url,
    })
    const d = res?.data || {}
    ElMessage.success(d.already_running ? '已使用系统浏览器会话打开管理页（会话已在运行）' : '已使用系统浏览器会话打开管理页')
  } catch {
    /* 错误由 axios 拦截器提示 */
  } finally {
    const done = new Set(manageLoadingIds.value)
    done.delete(iid)
    manageLoadingIds.value = done
  }
}

async function fetchItemDetail(row) {
  const iid = String(row.item_id || '').trim()
  if (!iid) {
    ElMessage.warning('缺少商品 ID')
    return
  }
  if (detailLoadingIds.value.has(iid)) return
  const next = new Set(detailLoadingIds.value)
  next.add(iid)
  detailLoadingIds.value = next
  try {
    const res = await onSaleItemApi.fetchDetail({ item_id: iid })
    const sync = res?.data?.sync || {}
    if (sync.updated) {
      ElMessage.success(
        sync.message ||
          `已关联 ${sync.inventory_ids?.length ?? 0} 条库存，煤炉 ID ${sync.mercari_item_id}`
      )
      await load()
    } else {
      ElMessage.warning(sync.message || '未写入库存（请检查说明中的管理番号/条码与账号 DPoP_ItemGet-Info）')
    }
  } finally {
    const done = new Set(detailLoadingIds.value)
    done.delete(iid)
    detailLoadingIds.value = done
  }
}

async function openSyncDialog() {
  syncVisible.value = true
  syncAccountId.value = null
  accountsLoading.value = true
  try {
    const res = await meiluAccountApi.list({ page: 1, page_size: 100 })
    accountOptions.value = (res.items || []).filter((a) => a.status === 'active')
    syncAccountId.value = accountOptions.value[0]?.id ?? null
  } catch {
    accountOptions.value = []
    syncAccountId.value = null
  } finally {
    accountsLoading.value = false
  }
}

async function runSync() {
  syncLoading.value = true
  try {
    const payload = {}
    if (syncAccountId.value) payload.account_id = syncAccountId.value
    const res = await onSaleItemApi.sync(payload, { timeout: 0 })
    const d = res.data || {}
    ElMessage.success(
      `同步完成：煤炉 ${d.api_item_count ?? 0} 条，新增 ${d.inserted ?? 0}，更新 ${d.updated ?? 0}，标记删除 ${d.marked_deleted ?? 0}`
    )
    syncVisible.value = false
    load()
  } finally {
    syncLoading.value = false
  }
}

async function loadSellerAccounts() {
  try {
    const res = await meiluAccountApi.list({ page: 1, page_size: 200 })
    sellerFromAccounts.value = (res.items || [])
      .filter((a) => a.status === 'active' && (a.seller_id || '').toString().trim())
      .map((a) => ({
        id: a.id,
        seller_id: String(a.seller_id).trim(),
        value: String(a.seller_id).trim(),
        label: `${a.account_name} (${a.seller_id})`,
      }))
  } catch {
    sellerFromAccounts.value = []
  }
}

onMounted(() => {
  loadSellerAccounts()
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
  gap: 16px;
  flex-wrap: wrap;
}
.search-actions {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 10px;
}
.table-card {
  border-radius: 8px;
}
.os-thumb {
  width: 48px;
  height: 48px;
  border-radius: 4px;
  display: block;
  cursor: zoom-in;
}
.thumb-fallback {
  color: #909399;
  font-size: 12px;
}
.cell-muted {
  color: #909399;
}
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.auction-pre {
  margin: 0;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 240px;
  overflow: auto;
}
.os-expand-wrap {
  padding: 8px 12px 12px 36px;
  max-width: 100%;
}
.os-expand-table {
  width: 100%;
}
.multi-line-cell {
  display: flex;
  flex-direction: column;
}
.multi-line-cell > div {
  min-height: 38px;
  line-height: 38px;
  box-sizing: border-box;
}
:deep(.on-sale-stock-alert-row) {
  --el-table-tr-bg-color: #3a1517;
}
:deep(.on-sale-stock-alert-row td) {
  background-color: #3a1517 !important;
}
:deep(.on-sale-stock-alert-row:hover > td) {
  background-color: #4a1a1d !important;
}
:deep(.on-sale-stock-alert-row td .cell) {
  color: #ffd6d9;
  font-weight: 600;
}

</style>
