<template>
  <div>
    <el-card shadow="never" class="search-card">
      <el-row :gutter="0" align="middle" class="search-row">
        <el-col :xs="24" :md="16" class="search-left-group">
          <el-input
            v-model="filters.keyword"
            placeholder="搜索标题 / 消息 / 商品 ID / 商品名"
            clearable
            @change="onFilterChange"
          />
          <el-select
            v-model="filters.account_id"
            placeholder="账号"
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
            placeholder="类型"
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
          <el-checkbox v-model="filters.include_deleted" @change="onFilterChange">
            含已完成
          </el-checkbox>
        </el-col>
        <el-col :xs="24" :md="8" class="search-actions">
          <el-select
            v-model="globalAccountId"
            placeholder="选择煤炉账号"
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
            从煤炉同步
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table :data="list" v-loading="loading" stripe row-key="id">
        <el-table-column label="图" width="80" align="center" header-align="center">
          <template #default="{ row }">
            <el-image
              v-if="row.photo_url"
              class="todo-thumb"
              :src="mercariImageUrl(row.photo_url)"
              :preview-src-list="[mercariImageUrl(row.photo_url)]"
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

        <el-table-column label="类型" width="140" align="center" header-align="center">
          <template #default="{ row }">
            <el-tag :type="kindTagType(row.kind)" size="small" effect="light">
              {{ kindLabel(row.kind) }}
            </el-tag>
            <div v-if="row.is_delete" class="row-tag-done">已完成</div>
          </template>
        </el-table-column>

        <el-table-column label="标题 / 消息" min-width="320" align="left" header-align="center">
          <template #default="{ row }">
            <div v-if="row.title" class="cell-title">{{ row.title }}</div>
            <div class="cell-message">{{ row.message || '-' }}</div>
            <div v-if="row.item_id" class="cell-itemid">
              <el-link :href="mercariItemUrl(row.item_id)" target="_blank" type="primary" :underline="false">
                {{ row.item_id }}
              </el-link>
              <span v-if="row.item_name" class="cell-itemname">{{ row.item_name }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="买家" width="160" align="center" header-align="center">
          <template #default="{ row }">
            <div v-if="buyerNameFromMessage(row.message)" class="cell-buyer">{{ buyerNameFromMessage(row.message) }}</div>
            <div v-if="row.sender_id" class="cell-sender-id">ID: {{ row.sender_id }}</div>
            <span v-if="!row.sender_id && !buyerNameFromMessage(row.message)" class="cell-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="时间" width="170" align="center" header-align="center">
          <template #default="{ row }">
            <div>{{ displayTs(row.mercari_updated || row.mercari_created) }}</div>
            <div v-if="row.synced_at" class="cell-muted-sm">同步: {{ displayTs(row.synced_at) }}</div>
          </template>
        </el-table-column>

        <el-table-column label="账号" width="140" align="center" header-align="center">
          <template #default="{ row }">
            <span>{{ row.account_name || `#${row.account_id}` }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="90" align="center" header-align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="onProcess(row)">处理</el-button>
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

<!-- 交易详情面板：通用的「煤炉数据 → 管理软件」表单 -->
    <el-dialog
      v-model="detailDialogVisible"
      :title="`交易详情  ${detail.item_id || ''}`"
      width="1080px"
      :close-on-click-modal="false"
      destroy-on-close
      @close="onDetailDialogClose"
    >
      <template #header="{ titleId, titleClass }">
        <div class="detail-header">
          <span :id="titleId" :class="titleClass">交易详情 <code>{{ detail.item_id || '-' }}</code></span>
          <div class="detail-header-actions">
            <el-button size="small" :loading="detailLoading" @click="onDetailRefresh">刷新抓取</el-button>
            <el-button size="small" type="primary" link @click="onOpenMercariPage">打开煤炉页 ↗</el-button>
          </div>
        </div>
      </template>

      <div v-loading="detailLoading" class="detail-body">
        <!-- 左栏：商品 / 发送元 / 买家 / 发货 -->
        <div class="detail-col detail-col-left">
          <section class="detail-section">
            <div class="detail-section-title">商品</div>
            <div class="detail-row">
              <div class="detail-label">商品名</div>
              <div class="detail-value">
                <el-input
                  v-model="detail.product_name"
                  size="default"
                  placeholder="（待抓取或输入商品名）"
                  clearable
                />
              </div>
            </div>
            <div class="detail-row">
              <div class="detail-label">商品 ID</div>
              <div class="detail-value">
                <el-link :href="mercariItemUrl(detail.item_id)" target="_blank" type="primary" :underline="false">
                  {{ detail.item_id || dash }}
                </el-link>
              </div>
            </div>
            <div v-if="detail.photo_url" class="detail-photo-wrap">
              <el-image
                :src="mercariImageUrl(detail.photo_url)"
                :preview-src-list="[mercariImageUrl(detail.photo_url)]"
                :preview-teleported="true"
                fit="cover"
                referrerpolicy="no-referrer"
                class="detail-photo"
              />
            </div>
          </section>

          <section class="detail-section">
            <div class="detail-section-title">发送元</div>
            <div v-if="detail.sender_address" class="detail-block">{{ detail.sender_address }}</div>
            <div v-else class="detail-empty">待抓取</div>
          </section>

          <section class="detail-section">
            <div class="detail-section-title">买家</div>
            <div class="detail-buyer">
              <div class="detail-buyer-name">{{ detail.buyer_name || dash }}</div>
              <el-tag v-if="detail.buyer_verified" type="success" size="small" effect="light">本人確認済</el-tag>
              <span v-if="detail.sender_id" class="detail-buyer-id">ID: {{ detail.sender_id }}</span>
            </div>
          </section>

          <section v-if="!isReviewedSeller" class="detail-section">
            <div class="detail-section-title">发货</div>
            <div class="detail-shipping-status">
              <span class="detail-label">当前状态</span>
              <span class="detail-value">{{ detail.current_shipping_status || dash }}</span>
            </div>
            <div class="detail-shipping-actions">
              <el-button
                size="default"
                :disabled="!detail.has_size_location_btn"
                @click="onClickShippingSizeLocation"
              >
                选择商品尺寸与发货地
              </el-button>
              <el-button
                size="default"
                :disabled="!detail.has_change_method_btn"
                @click="onClickShippingChangeMethod"
              >
                修改发货方式
              </el-button>
            </div>
            <div class="detail-empty-hint">两个按钮根据煤炉页面实际可见状态启用；抓取前默认禁用。</div>
          </section>
        </div>

        <!-- 右栏：默认是消息/交流；ReviewedSeller 时切换为取引評価表单 -->
        <div class="detail-col detail-col-right">
          <!-- 取引評価（仅 ReviewedSeller） -->
          <section v-if="isReviewedSeller" class="detail-section detail-section-grow">
            <div class="detail-section-title">取引評価</div>
            <div class="detail-empty-hint" style="margin-bottom: 10px">
              煤炉页面 ｢良かった｣ 默认已选中；填写评价后点提交即可（自动点 ｢購入者を評価して取引完了する｣）。
            </div>
            <el-input
              v-model="detail.review_draft"
              type="textarea"
              :autosize="{ minRows: 6, maxRows: 12 }"
              placeholder="例) このたびはお取引ありがとうございました。"
              maxlength="140"
              show-word-limit
            />
            <div class="detail-reply-actions">
              <el-button size="small" @click="onResetReviewDefault">默认评价</el-button>
              <el-button
                size="small"
                type="primary"
                :loading="reviewLoading"
                :disabled="!detail.review_draft || !detail.review_draft.trim()"
                @click="onSubmitReview"
              >
                提交评价并完成取引
              </el-button>
            </div>
          </section>

          <!-- 消息 / 交流（默认） -->
          <section v-else class="detail-section detail-section-grow">
            <div class="detail-section-title">消息 / 交流</div>
            <div v-if="detail.messages && detail.messages.length" class="detail-messages">
              <div
                v-for="(m, i) in detail.messages"
                :key="i"
                :class="['detail-msg', m.is_buyer ? 'detail-msg-buyer' : 'detail-msg-self']"
              >
                <div v-if="m.from" class="detail-msg-from">{{ m.from }}<span v-if="!m.is_buyer" class="detail-msg-tag-self">（卖家）</span></div>
                <div class="detail-msg-text">{{ m.text }}</div>
                <div v-if="m.at" class="detail-msg-at">{{ m.at }}</div>
              </div>
            </div>
            <div v-else class="detail-empty">待抓取</div>

            <div class="detail-reply">
              <el-input
                v-model="detail.reply_draft"
                type="textarea"
                :autosize="{ minRows: 4, maxRows: 8 }"
                placeholder="なにか分からないことがあれば質問してみましょう。"
              />
              <div class="detail-reply-actions">
                <el-button size="small" @click="onResetReplyDefault">默认回复</el-button>
                <el-button
                  size="small"
                  type="primary"
                  :loading="replyLoading"
                  :disabled="!detail.reply_draft || !detail.reply_draft.trim()"
                  @click="onSendReply"
                >
                  发送回复
                </el-button>
              </div>
            </div>
          </section>
        </div>
      </div>

      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
        <el-button type="primary" :disabled="detailLoading" @click="onDetailSubmit">完成处理</el-button>
      </template>
    </el-dialog>

    <!-- 选择商品尺寸：纯前端硬编码列表，按当前配送方式区分 -->
    <el-dialog
      v-model="shippingDialogVisible"
      title="选择商品尺寸"
      width="780px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div class="shipping-dialog-hint">
        当前配送方式：<strong>{{ detail.shipping_method_name || '未识别' }}</strong>
        ；选择尺寸后我们会在浏览器内自动点击对应项 + 「選択して次へ」，发货地请在浏览器内继续选。
      </div>
      <el-radio-group v-if="shippingOptions.length" v-model="shippingPickedIdx" class="ship-radio-group">
        <div
          v-for="(opt, idx) in shippingOptions"
          :key="`${opt.name}-${idx}`"
          :class="['ship-card', shippingPickedIdx === idx ? 'ship-card-active' : '']"
          @click="shippingPickedIdx = idx"
        >
          <el-radio :value="idx" class="ship-card-radio">
            <span class="ship-card-radio-label">{{ opt.name }}</span>
          </el-radio>
          <div class="ship-card-body">
            <div
              v-for="(row, ri) in (opt.rows || [])"
              :key="`row-${ri}`"
              class="ship-card-row"
            >
              <span class="ship-card-label">{{ row[0] }}</span>
              <span :class="['ship-card-value', row[0] === '送料' ? 'ship-card-fee' : '']">{{ row[1] }}</span>
            </div>
            <div
              v-for="(c, ci) in (opt.caveats || [])"
              :key="`cv-${ci}`"
              class="ship-card-caveat"
            >{{ c }}</div>
            <div v-if="opt.auto_finish_no_facility" class="ship-card-note">無需選擇発送地（直接完了）</div>
          </div>
        </div>
      </el-radio-group>
      <div v-else class="detail-empty">无可用尺寸列表</div>

      <div v-if="shippingNeedsFacility" class="ship-facility-section">
        <div class="ship-facility-title">発送地</div>
        <el-radio-group v-model="shippingFacility" class="ship-facility-radio">
          <el-radio value="post_office" border>郵便局</el-radio>
          <el-radio value="lawson" border>ローソン</el-radio>
        </el-radio-group>
      </div>
      <template #footer>
        <el-button @click="shippingDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="shippingPickedIdx == null"
          :loading="shippingConfirmLoading"
          @click="onConfirmShippingSelection"
        >
          确认并发送
        </el-button>
      </template>
    </el-dialog>

    <teleport to="body">
      <div
        v-show="syncOverlayVisible"
        class="todos-sync-overlay todos-sync-overlay--dark"
        :class="{ 'todos-sync-overlay--failed': syncOverlayFailed }"
        role="status"
        aria-live="polite"
      >
        <div class="todos-sync-overlay__box">
          <el-icon class="is-loading todos-sync-overlay__icon" :size="40"><Loading /></el-icon>
          <div class="todos-sync-overlay__title">{{ syncOverlayTitle }}</div>
          <div class="todos-sync-overlay__step">{{ syncProgressLabel || '请稍候…' }}</div>
        </div>
      </div>
    </teleport>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Loading } from '@element-plus/icons-vue'
import { todosApi, meiluAccountApi } from '@/api'
import { useMercariAccountStore } from '@/stores/mercariAccount.js'
import { mercariImageUrl } from '@/utils/mercariImage.js'

const mercariAccountStore = useMercariAccountStore()
const globalAccountId = computed({
  get: () => mercariAccountStore.selectedId,
  set: (v) => mercariAccountStore.setSelected(v),
})

const KIND_LABELS = {
  WaitShippingCard: '待发货',
  WaitShippingPoint: '待发货',
  TransactionWaitShippingFunds: '待发货',
  MerpayRealcardWaitActivation: 'Merpay 卡激活',
  ReviewedSeller: '待评价',
  IncomingMessage: '待回复',
}

const DEFAULT_REPLY = 'ご購入いただきありがとうございます。これから発送の準備をさせていただきます。設定した期日内に発送予定ですので今しばらくお待ちください。取引終了までよろしくお願いいたします。'
const DEFAULT_REVIEW = 'この度はお取引ありがとうございました。また機会がありましたらよろしくお願いします。'

// 发货尺寸硬编码列表，按 shipping_method_name 区分。
// name 字段必须与煤炉 /shipping_class 页 radio 卡片标题文本完全一致（用于 Playwright 文本匹配点击）
const SHIPPING_OPTIONS = {
  'ゆうゆうメルカリ便': [
    {
      name: 'ゆうパケット',
      rows: [
        ['サイズ', '3辺合計60cm以内'],
        ['送料', '¥230'],
        ['厚さ', '3cm以内'],
        ['重さ', '1kg以内'],
      ],
    },
    {
      name: 'ゆうパケットポストmini',
      rows: [
        ['サイズ', '専用封筒 (21cm×17cm)'],
        ['送料', '¥160'],
        ['重さ', '2kg以内'],
        ['発送', '郵便ポストから発送'],
      ],
      caveats: ['※専用封筒(¥20)の購入が必要です'],
      auto_finish_no_facility: true,
    },
    {
      name: 'ゆうパケットポスト',
      rows: [
        ['サイズ', '郵便ポストに投函可能なもの'],
        ['送料', '¥215'],
        ['重さ', '2kg以内'],
        ['発送', '郵便ポストから発送'],
      ],
      caveats: ['※専用箱(¥65)、または発送用シール(20枚入り¥100)の購入が必要です。'],
      auto_finish_no_facility: true,
    },
    {
      name: 'ゆうパケットプラス',
      rows: [
        ['サイズ', '専用箱 (17cm×24cm×7cm)'],
        ['送料', '¥455'],
        ['重さ', '2kg以内'],
      ],
      caveats: ['※専用箱(¥65)の購入が必要です'],
    },
    {
      name: 'ゆうパック60 - 100',
      rows: [
        ['サイズ', '3辺合計100cm以内'],
        ['送料', '¥750 - ¥1,070'],
        ['重さ', '25kg以内'],
      ],
    },
    {
      name: 'ゆうパック120 - 170',
      rows: [
        ['サイズ', '3辺合計170cm以内'],
        ['送料', '¥1,200 - ¥1,900'],
        ['重さ', '25kg以内'],
      ],
    },
  ],
  'らくらくメルカリ便': [
    {
      name: 'ネコポス',
      rows: [
        ['サイズ', '3辺合計60cm以内'],
        ['長辺', '34cm以内'],
        ['最小', '23cm × 11.5cm'],
      ],
    },
    {
      name: '宅急便コンパクト',
      rows: [
        ['サイズ', '専用BOX (20cm×25cm×5cm) / 薄型専用BOX (24.8cm×34cm)'],
        ['送料', '¥450'],
      ],
    },
    {
      name: '宅急便60 - 160',
      rows: [
        ['サイズ', '3辺合計160cm以内'],
        ['送料', '¥750'],
      ],
    },
    {
      name: '宅急便180 - 200',
      rows: [
        ['サイズ', '3辺合計200cm以内'],
      ],
    },
  ],
}

const KIND_TAG_TYPES = {
  WaitShippingCard: 'warning',
  WaitShippingPoint: 'warning',
  TransactionWaitShippingFunds: 'warning',
  MerpayRealcardWaitActivation: 'info',
  ReviewedSeller: 'success',
  IncomingMessage: 'primary',
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
  include_deleted: false,
})

const accountOptions = ref([])
const kindOptions = ref([])

const syncLoading = ref(false)

/** 「从煤炉同步」全屏等待与步骤文案（与后端 progress_job_id 轮询同步） */
const syncOverlayVisible = ref(false)
const syncOverlayTitle = ref('正在从煤炉同步')
const syncOverlayFailed = ref(false)
const syncProgressLabel = ref('')
let syncProgressTimer = null

// ─── 交易详情面板 ───
// 后端抓取接口未接入；先用本地 row 已有字段填充，其他字段留 null 显示占位
const dash = '—'
const detailDialogVisible = ref(false)
const detailLoading = ref(false)
const currentRow = ref(null)
const detail = reactive(createEmptyDetail())

function createEmptyDetail() {
  return {
    // 本地 todo_items 即可得
    item_id: '',
    item_name: '',
    photo_url: '',
    buyer_name: '',
    sender_id: '',
    // 抓取 MITM 才有
    product_name: '',
    shipping_method_name: null,
    sender_address: null,
    current_shipping_status: null,
    shipment_status: null,
    has_size_location_btn: false,
    has_change_method_btn: false,
    messages: [], // [{ from, text, at, is_buyer, user_id }]
    captured: { shipping_info: false, transaction_messages: false },
    // 回复草稿（默认为空，点「默认回复」按钮可一键填入模板）
    reply_draft: '',
    // 评价草稿（仅 ReviewedSeller 用，预填默认评价）
    review_draft: DEFAULT_REVIEW,
  }
}

const replyLoading = ref(false)
const reviewLoading = ref(false)

// 当前待办是否是「评价买家」类型 → 切换为取引評価表单
// 条件：kind === 'ReviewedSeller' 且 title === '評価をしてください'
const isReviewedSeller = computed(() => {
  const kind = (currentRow.value?.kind || '').trim()
  const title = (currentRow.value?.title || '').trim()
  return kind === 'ReviewedSeller' && title === '評価をしてください'
})

// 选择尺寸 dialog（不再走 MITM 抓取，纯前端硬编码列表）
const shippingDialogVisible = ref(false)
const shippingConfirmLoading = ref(false)
const shippingPickedIdx = ref(null)
const shippingFacility = ref(null) // 'post_office' | 'lawson' | null
const shippingOptions = computed(() => {
  const method = (detail.shipping_method_name || '').trim()
  if (SHIPPING_OPTIONS[method]) return SHIPPING_OPTIONS[method]
  // 未识别配送方式时把两套都列出来，让用户自行判断
  return [...(SHIPPING_OPTIONS['ゆうゆうメルカリ便'] || []), ...(SHIPPING_OPTIONS['らくらくメルカリ便'] || [])]
})
const shippingNeedsFacility = computed(() => {
  if (shippingPickedIdx.value == null) return false
  const opt = shippingOptions.value[shippingPickedIdx.value]
  return !!opt && !opt.auto_finish_no_facility
})

function listParams() {
  const p = { page: page.value, page_size: pageSize.value }
  const kw = filters.value.keyword?.trim()
  if (kw) p.keyword = kw
  if (filters.value.account_id) p.account_id = filters.value.account_id
  if (filters.value.kind) p.kind = filters.value.kind
  if (filters.value.include_deleted) p.include_deleted = true
  return p
}

async function load() {
  loading.value = true
  try {
    const res = await todosApi.list(listParams())
    list.value = res?.items || []
    total.value = Number(res?.total || 0)
  } catch (e) {
    ElMessage.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function loadAccountOptions() {
  try {
    const res = await meiluAccountApi.list({ page: 1, page_size: 200 })
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
    const res = await todosApi.kinds()
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
    ElMessage.warning('请先在右上角选择煤炉账号')
    return
  }
  const name = mercariAccountStore.selectedAccountName || `#${aid}`
  try {
    await ElMessageBox.confirm(
      `将使用账号「${name}」从煤炉同步待办事项，是否继续？`,
      '确认同步',
      { type: 'info', confirmButtonText: '开始', cancelButtonText: '取消' },
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
      const pr = await todosApi.getSyncProgress(progressJobId)
      const d = pr?.data
      const zh = d?.label_zh
      if (zh) {
        syncProgressLabel.value = zh
        if (zh !== lastConsoleStep) {
          lastConsoleStep = zh
          console.log('[待办同步]', zh)
        }
      }
    } catch {
      /* 轮询失败忽略 */
    }
  }

  syncOverlayTitle.value = '正在从煤炉同步'
  syncOverlayFailed.value = false
  syncProgressLabel.value = '正在连接服务器…'
  syncOverlayVisible.value = true
  syncLoading.value = true
  await pollSyncProgress()
  syncProgressTimer = setInterval(pollSyncProgress, 400)

  let syncHadError = false
  try {
    const d = (await todosApi.sync({ account_id: aid, progress_job_id: progressJobId })) || {}
    ElMessageBox.alert(
      `账号 #${d.account_id ?? '-'} 同步完成：` +
        `新增 ${d.inserted ?? 0} 条，更新 ${d.updated ?? 0} 条，` +
        `标记完成 ${d.marked_deleted ?? 0} 条，共抓取 ${d.total ?? 0} 条。`,
      '同步结果',
      { type: 'success', confirmButtonText: '确定' },
    )
    await Promise.all([load(), loadKindOptions()])
  } catch (e) {
    syncHadError = true
    syncOverlayTitle.value = '同步失败'
    syncOverlayFailed.value = true
    const msg = e?.response?.data?.detail || e?.message || '同步失败'
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
    syncOverlayTitle.value = '正在从煤炉同步'
    syncOverlayFailed.value = false
    syncProgressLabel.value = ''
    syncLoading.value = false
  }
}

function kindLabel(kind) {
  if (!kind) return '-'
  return KIND_LABELS[kind] || kind
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

function mercariItemUrl(itemId) {
  const s = String(itemId || '').trim()
  if (!s) return '#'
  return `https://jp.mercari.com/item/${s}`
}

function onProcess(row) {
  currentRow.value = row
  Object.assign(detail, createEmptyDetail(), {
    item_id: row.item_id || '',
    item_name: row.item_name || '',
    photo_url: row.photo_url || '',
    buyer_name: buyerNameFromMessage(row.message) || '',
    sender_id: row.sender_id || '',
  })
  detailDialogVisible.value = true
  // 自动启动浏览器抓取真实数据
  onDetailRefresh()
}

async function onDetailRefresh() {
  if (!currentRow.value?.id) return
  if (!currentRow.value?.item_id) {
    ElMessage.warning('该待办无关联 item_id，无法打开交易页')
    return
  }
  detailLoading.value = true
  try {
    const d = await todosApi.fetchTransactionDetail(currentRow.value.id)
    if (!d || typeof d !== 'object') {
      ElMessage.warning('未拿到交易页数据')
      return
    }
    // 合并抓取结果；本地预填的字段（item_id/photo_url 等）保留
    const merged = { ...d }
    // 部分字段可能为 null，避免覆盖本地预填值
    if (merged.buyer_name == null) delete merged.buyer_name
    Object.assign(detail, merged)
    ElMessage.success('交易页数据已抓取')
  } catch (e) {
    // axios 拦截器已弹错误；此处保留兜底
    if (!e?.response) ElMessage.error(e?.message || '抓取失败')
  } finally {
    detailLoading.value = false
  }
}

function onOpenMercariPage() {
  const iid = String(detail.item_id || '').trim()
  if (!iid) {
    ElMessage.warning('无 item_id，无法打开')
    return
  }
  window.open(`https://jp.mercari.com/transaction/${iid}`, '_blank', 'noopener')
}

async function onClickShippingSizeLocation() {
  if (!currentRow.value?.id) return
  // 先点开页面上的「商品サイズと発送場所を選択する」让浏览器跳到尺寸选择页
  try {
    await todosApi.startShippingClass(currentRow.value.id)
  } catch (e) {
    if (!e?.response) ElMessage.error(e?.message || '打开尺寸选择页失败')
    return
  }
  shippingPickedIdx.value = null
  shippingFacility.value = null
  shippingDialogVisible.value = true
}

async function onConfirmShippingSelection() {
  if (!currentRow.value?.id) return
  const idx = shippingPickedIdx.value
  if (idx == null) return
  const opt = shippingOptions.value[idx]
  if (!opt) return
  const classText = opt.name
  const needsFacility = !opt.auto_finish_no_facility
  if (needsFacility && !shippingFacility.value) {
    ElMessage.warning('请选择发货地（郵便局 / ローソン）')
    return
  }
  shippingConfirmLoading.value = true
  try {
    await todosApi.confirmShippingSelection(currentRow.value.id, {
      class_text: classText,
      facility: needsFacility ? shippingFacility.value : null,
    })
    ElMessage.success(`「${classText}」 已完成发货设定`)
    shippingDialogVisible.value = false
    onDetailRefresh()
  } catch (e) {
    if (!e?.response) ElMessage.error(e?.message || '提交失败')
  } finally {
    shippingConfirmLoading.value = false
  }
}

async function onClickShippingChangeMethod() {
  if (!currentRow.value?.id) return
  try {
    await todosApi.changeShippingMethod(currentRow.value.id)
    ElMessage.success('已在浏览器内点击「発送方法を変更する」，请在浏览器页面继续操作')
  } catch (e) {
    if (!e?.response) ElMessage.error(e?.message || '点击失败')
  }
}


function onDetailSubmit() {
  // TODO: 完成处理 → 本地标完成 + 关闭面板（具体动作待定）
  ElMessage.info('完成处理动作待定')
}

function onResetReplyDefault() {
  detail.reply_draft = DEFAULT_REPLY
}

async function onSendReply() {
  if (!currentRow.value?.id) return
  const text = (detail.reply_draft || '').trim()
  if (!text) {
    ElMessage.warning('回复内容不能为空')
    return
  }
  replyLoading.value = true
  try {
    const result = await todosApi.sendTransactionMessage(currentRow.value.id, text)
    if (result?.completed) {
      // 待回复（IncomingMessage）：后端已软删 + 关浏览器，前端关 dialog + 刷列表
      ElMessage.success('已回复，浏览器已关闭，待办已完成')
      detailDialogVisible.value = false
      load()
    } else {
      ElMessage.success('已点击煤炉发送按钮')
      // 普通发送：刷新一次抓取让消息流更新
      onDetailRefresh()
    }
  } catch (e) {
    if (!e?.response) ElMessage.error(e?.message || '发送失败')
  } finally {
    replyLoading.value = false
  }
}

function onResetReviewDefault() {
  detail.review_draft = DEFAULT_REVIEW
}

async function onSubmitReview() {
  if (!currentRow.value?.id) return
  const text = (detail.review_draft || '').trim()
  if (!text) {
    ElMessage.warning('评价内容不能为空')
    return
  }
  reviewLoading.value = true
  try {
    const result = await todosApi.submitTransactionReview(currentRow.value.id, text)
    if (result?.completed) {
      const note = result.order_refresh_error
        ? `（订单信息刷新失败：${result.order_refresh_error}）`
        : ''
      ElMessage.success(`检测到「取引が完了しました」，已关闭浏览器并刷新订单状态${note}`)
      // 浏览器已由后端关闭；这里关 dialog（onDetailDialogClose 里的 closeBrowser 是幂等的）
      detailDialogVisible.value = false
      load() // 刷新待办列表（todo 已软删，列表中应消失）
    } else {
      ElMessage.warning('已提交但未检测到「取引が完了しました」，请在浏览器内手动确认')
    }
  } catch (e) {
    if (!e?.response) ElMessage.error(e?.message || '提交失败')
  } finally {
    reviewLoading.value = false
  }
}

function onDetailDialogClose() {
  // 关 dialog 时同步关掉对应账号的 __auto 浏览器（fire-and-forget）
  const aid = currentRow.value?.account_id
  if (aid) {
    todosApi.closeDetailBrowser(aid).catch(() => { /* 忽略关浏览器失败 */ })
  }
  currentRow.value = null
  replyLoading.value = false
}


function buyerNameFromMessage(msg) {
  const s = String(msg || '')
  // 「<买家名>さんが...」 / 「<买家名>さんに...」
  const m = s.match(/^(.+?)さん[がにへ]/)
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
.todo-thumb {
  width: 56px;
  height: 56px;
  border-radius: 6px;
  display: block;
}
.thumb-fallback {
  color: var(--el-text-color-placeholder);
  font-size: 12px;
}
.cell-title {
  font-weight: 600;
  margin-bottom: 4px;
}
.cell-message {
  color: var(--el-text-color-regular);
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
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
.row-tag-done {
  margin-top: 4px;
  color: var(--el-color-success);
  font-size: 11px;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
  display: flex;
}
/* ─── 交易详情面板 ─── */
.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.detail-header code {
  color: var(--el-color-primary);
  font-weight: 600;
}
.detail-header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.detail-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  min-height: 560px;
  max-height: 70vh;
}
.detail-col {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  min-height: 0;
}
.detail-col-right {
  /* 右栏只放消息，撑满整个 dialog 高度 */
  height: 100%;
}
.detail-section {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  padding: 10px 12px;
  background: var(--el-fill-color-blank);
}
.detail-section-grow {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.detail-section-title {
  font-weight: 600;
  color: var(--el-text-color-primary);
  font-size: 13px;
  border-bottom: 1px dashed var(--el-border-color-lighter);
  padding-bottom: 6px;
  margin-bottom: 8px;
}
.detail-row {
  display: flex;
  gap: 8px;
  align-items: baseline;
  padding: 3px 0;
  font-size: 13px;
}
.detail-label {
  width: 84px;
  flex-shrink: 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.detail-value {
  flex: 1;
  word-break: break-all;
  color: var(--el-text-color-primary);
}
.detail-block {
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.6;
  color: var(--el-text-color-primary);
  padding: 4px 0;
}
.detail-empty {
  color: var(--el-text-color-placeholder);
  font-size: 12px;
  padding: 8px 0;
  text-align: center;
}
.detail-empty-hint {
  color: var(--el-text-color-placeholder);
  font-size: 11px;
  margin-top: 6px;
}
.detail-photo-wrap {
  margin-top: 8px;
}
.detail-photo {
  width: 100%;
  max-width: 200px;
  height: auto;
  border-radius: 6px;
}
.detail-buyer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.detail-buyer-name {
  font-weight: 600;
  font-size: 14px;
}
.detail-buyer-id {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.detail-messages {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}
.detail-msg {
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 13px;
}
.detail-msg-buyer {
  background: var(--el-fill-color);
}
.detail-msg-self {
  background: var(--el-color-primary-light-9);
}
.detail-msg-tag-self {
  color: var(--el-color-primary);
  font-size: 11px;
  margin-left: 4px;
}
.detail-reply {
  margin-top: 12px;
  border-top: 1px dashed var(--el-border-color-lighter);
  padding-top: 10px;
  flex-shrink: 0;
}
.detail-reply-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
.detail-msg-from {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}
.detail-msg-text {
  white-space: pre-wrap;
  line-height: 1.5;
}
.detail-msg-at {
  font-size: 10px;
  color: var(--el-text-color-placeholder);
  margin-top: 4px;
  text-align: right;
}
.detail-shipping-status {
  display: flex;
  gap: 8px;
  align-items: baseline;
  padding: 4px 0 10px;
  font-size: 13px;
}
.detail-shipping-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* ─── 选择尺寸 dialog ─── */
.shipping-dialog-hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.6;
  margin-bottom: 12px;
  padding: 8px 10px;
  background: var(--el-fill-color);
  border-radius: 4px;
}
.ship-radio-group {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  width: 100%;
}
.ship-card {
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  padding: 10px 12px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.ship-card:hover {
  border-color: var(--el-color-primary);
}
.ship-card-active {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.ship-card-radio {
  margin-right: 0;
  margin-bottom: 6px;
}
.ship-card-radio-label {
  font-weight: 600;
  font-size: 14px;
}
.ship-card-body {
  padding-left: 22px;
}
.ship-card-row {
  display: flex;
  font-size: 12px;
  line-height: 1.6;
}
.ship-card-label {
  color: var(--el-text-color-secondary);
  width: 48px;
  flex-shrink: 0;
}
.ship-card-value {
  color: var(--el-text-color-primary);
}
.ship-card-fee {
  color: var(--el-color-success);
  font-weight: 600;
}
.ship-card-caveat {
  margin-top: 4px;
  color: var(--el-color-warning);
  font-size: 11px;
  line-height: 1.4;
}
.ship-card-note {
  margin-top: 4px;
  color: var(--el-color-success);
  font-size: 11px;
}
.ship-facility-section {
  margin-top: 16px;
  padding: 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: var(--el-fill-color);
}
.ship-facility-title {
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 10px;
}
.ship-facility-radio {
  display: flex;
  gap: 12px;
}
</style>

<!-- 「从煤炉同步」全屏等待（teleport 到 body，须无 scoped；黑色主题） -->
<style>
.todos-sync-overlay.todos-sync-overlay--dark {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(6px);
}
.todos-sync-overlay--dark .todos-sync-overlay__box {
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
.todos-sync-overlay--dark .todos-sync-overlay__icon {
  color: #94a3b8;
}
.todos-sync-overlay--dark .todos-sync-overlay__title {
  margin-top: 14px;
  font-size: 17px;
  font-weight: 600;
  color: #f1f5f9;
  letter-spacing: 0.02em;
}
.todos-sync-overlay--dark.todos-sync-overlay--failed .todos-sync-overlay__title {
  color: #f87171;
}
.todos-sync-overlay--dark.todos-sync-overlay--failed .todos-sync-overlay__step {
  color: #cbd5e1;
}
.todos-sync-overlay--dark .todos-sync-overlay__step {
  margin-top: 10px;
  font-size: 14px;
  color: #94a3b8;
  line-height: 1.55;
  word-break: break-word;
}
</style>
