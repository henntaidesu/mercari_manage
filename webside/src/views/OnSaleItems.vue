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
      <el-table :data="list" v-loading="loading" stripe>
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
        <el-table-column label="类目" min-width="140" show-overflow-tooltip align="left" header-align="center">
          <template #default="{ row }">{{ categoryCell(row) }}</template>
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
      <p class="sync-hint">
        使用在售专用接口（status=on_sale,stop 等，见后端 on_sale_list）。请在煤炉账号中配置「DPoP_OnSale-List」（dpop_on_sale_list），JWT 须针对该完整 GET URL 生成。
      </p>
      <el-form label-width="88px">
        <el-form-item label="煤炉账号">
          <el-select
            v-model="syncAccountId"
            placeholder="默认第一个活跃账号"
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
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import { onSaleItemApi, meiluAccountApi } from '@/api/index.js'

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
const syncLoading = ref(false)
const syncVisible = ref(false)
const syncAccountId = ref(null)
const accountOptions = ref([])
const accountsLoading = ref(false)

const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const filters = ref({
  keyword: '',
  seller_id: '',
  status: '',
})

const sellerFromAccounts = ref([])

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

async function load() {
  loading.value = true
  try {
    const res = await onSaleItemApi.list(listParams())
    list.value = res.items || []
    total.value = res.total || 0
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

function categoryCell(row) {
  const parts = []
  if (row.category_root_name) parts.push(row.category_root_name)
  if (row.parent_category_name) parts.push(row.parent_category_name)
  if (row.category_name) parts.push(row.category_name)
  if (parts.length) return parts.join(' / ')
  return '-'
}

function formatJsonPretty(raw) {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return String(raw || '')
  }
}

async function openSyncDialog() {
  syncAccountId.value = null
  syncVisible.value = true
  accountsLoading.value = true
  try {
    const res = await meiluAccountApi.list({ page: 1, page_size: 100 })
    accountOptions.value = (res.items || []).filter((a) => a.status === 'active')
  } catch {
    accountOptions.value = []
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
      `同步完成：接口 ${d.api_item_count ?? 0} 条，新增 ${d.inserted ?? 0}，更新 ${d.updated ?? 0}`
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
.sync-hint {
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
  margin: 0 0 12px;
}
.auction-pre {
  margin: 0;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 240px;
  overflow: auto;
}
</style>
