<template>
  <div class="dashboard">
    <!-- 库存管理统计 -->
    <el-card class="section-card inventory-stats-wrap" shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon color="#409EFF"><Goods /></el-icon>
          <span>库存管理</span>
        </div>
      </template>
      <el-row :gutter="16" class="stat-row inventory-stat-row">
        <el-col :xs="12" :sm="12" :md="8" :lg="4" v-for="card in statCards" :key="card.label">
          <div class="stat-card" :style="{ borderTopColor: card.color }">
            <div class="stat-icon" :style="{ background: card.color + '20', color: card.color }">
              <el-icon size="22"><component :is="card.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ summary[card.key] ?? '-' }}</div>
              <div class="stat-label">{{ card.label }}</div>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 订单汇总：近 30 天本地自然日（Unix 秒区间），与订单页 /orders/stats 口径一致（COALESCE 购入/下单时间） -->
    <el-card class="section-card order-stats-wrap" shadow="never" v-loading="orderStatsLoading">
      <template #header>
        <div class="card-header">
          <el-icon color="#67C23A"><Tickets /></el-icon>
          <span>订单统计（近30天）</span>
        </div>
      </template>
      <el-row :gutter="16" class="stat-row order-stat-row">
        <el-col :xs="12" :sm="12" :md="8" :lg="4" v-for="card in orderStatCards" :key="card.label">
          <div
            class="stat-card order-stat-card"
            :class="card.cardClass"
            :style="{ borderTopColor: card.color }"
          >
            <div class="stat-icon" :style="{ background: card.color + '20', color: card.color }">
              <el-icon size="22"><component :is="card.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value-row">
                <span class="stat-value" :class="card.valueClass">{{ card.display }}</span>
                <span class="stat-today">（今日新增 {{ card.todayDisplay }}）</span>
              </div>
              <div class="stat-label">{{ card.label }}</div>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 最近交易 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon color="#409EFF"><List /></el-icon>
          <span>最近出入库</span>
        </div>
      </template>
      <el-table :data="recentTx" size="small" stripe>
        <el-table-column label="时间" width="160">
          <template #default="{ row }">{{ formatUnixSecLocal(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="类型" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.type === 'in' ? 'success' : row.type === 'out' ? 'danger' : 'warning'" size="small">
              {{ { in: '入库', out: '出库', transfer: '调拨' }[row.type] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="商品" prop="product_name" />
        <el-table-column label="仓库" prop="warehouse_name" />
        <el-table-column label="数量" prop="quantity" width="80" align="center" />
        <el-table-column label="操作人" prop="operator" width="90" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { inventoryApi, transactionApi, orderApi } from '@/api/index.js'
import { rollingLocalDayRangeTs, localTodayRangeTs } from '@/utils/orderStatsTime.js'
import { formatUnixSecLocal } from '@/utils/timeDisplay.js'

const summary = ref({})
const recentTx = ref([])
const orderStatsLoading = ref(false)
const orderStats = ref({
  total_count: 0,
  sum_amount: 0,
  sum_service_fee: 0,
  sum_shipping_fee: 0,
  sum_net_income: 0,
  today_total_count: 0,
  today_sum_amount: 0,
  today_sum_service_fee: 0,
  today_sum_shipping_fee: 0,
  today_sum_net_income: 0,
})

const statCards = [
  { key: 'total_inventory', label: '库存条目', icon: 'Goods', color: '#409EFF' },
  { key: 'total_quantity', label: '总库存量', icon: 'Box', color: '#E6A23C' },
  { key: 'today_in', label: '今日入库', icon: 'Top', color: '#67C23A' },
  { key: 'today_out', label: '今日出库', icon: 'Bottom', color: '#F56C6C' }
]

const orderStatCards = computed(() => {
  const o = orderStats.value
  return [
    {
      label: '订单笔数',
      display: o.total_count ?? 0,
      todayDisplay: o.today_total_count ?? 0,
      icon: 'Document',
      color: '#409EFF',
      cardClass: '',
      valueClass: '',
    },
    {
      label: '金额合计',
      display: Math.round(Number(o.sum_amount || 0)),
      todayDisplay: Math.round(Number(o.today_sum_amount || 0)),
      icon: 'Money',
      color: '#E6A23C',
      cardClass: '',
      valueClass: '',
    },
    {
      label: '手续费合计',
      display: Math.round(Number(o.sum_service_fee || 0)),
      todayDisplay: Math.round(Number(o.today_sum_service_fee || 0)),
      icon: 'Histogram',
      color: '#F56C6C',
      cardClass: '',
      valueClass: '',
    },
    {
      label: '快递费合计',
      display: Math.round(Number(o.sum_shipping_fee || 0)),
      todayDisplay: Math.round(Number(o.today_sum_shipping_fee || 0)),
      icon: 'Box',
      color: '#F56C6C',
      cardClass: '',
      valueClass: '',
    },
    {
      label: '净收益合计',
      display: Math.round(Number(o.sum_net_income || 0)),
      todayDisplay: Math.round(Number(o.today_sum_net_income || 0)),
      icon: 'TrendCharts',
      color: '#67C23A',
      cardClass: '',
      valueClass: '',
    },
  ]
})

async function loadOrderStats() {
  orderStatsLoading.value = true
  try {
    const range = rollingLocalDayRangeTs(30)
    const today = localTodayRangeTs()
    const res = await orderApi.stats({
      ...range,
      ...today,
    })
    orderStats.value = {
      total_count: res.total_count ?? 0,
      sum_amount: res.sum_amount ?? 0,
      sum_service_fee: res.sum_service_fee ?? 0,
      sum_shipping_fee: res.sum_shipping_fee ?? 0,
      sum_net_income: res.sum_net_income ?? 0,
      today_total_count: res.today_total_count ?? 0,
      today_sum_amount: res.today_sum_amount ?? 0,
      today_sum_service_fee: res.today_sum_service_fee ?? 0,
      today_sum_shipping_fee: res.today_sum_shipping_fee ?? 0,
      today_sum_net_income: res.today_sum_net_income ?? 0,
    }
  } finally {
    orderStatsLoading.value = false
  }
}

async function load() {
  const [inventoryItems, tx] = await Promise.all([
    inventoryApi.list(),
    transactionApi.list({ page_size: 10 }),
  ])
  await loadOrderStats()
  const totalQuantity = inventoryItems.reduce((sum, p) => sum + (p.quantity || 0), 0)
  summary.value = {
    total_inventory: inventoryItems.length,
    total_quantity: totalQuantity,
    today_in: tx.today_in ?? '-',
    today_out: tx.today_out ?? '-'
  }
  recentTx.value = tx.items
}

onMounted(load)
</script>

<style scoped>
.dashboard { max-width: none; width: auto; }
.stat-row { margin-bottom: 20px; }
.stat-row .el-col { margin-bottom: 16px; }
.stat-card {
  background: #131c2f;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  border-top: 3px solid;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  border: 1px solid #2a3446;
}
.stat-icon {
  width: 46px;
  height: 46px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-value-row {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 2px;
  line-height: 1.25;
}
.stat-value { font-size: 22px; font-weight: 700; color: #ecf2ff; }
.stat-today {
  font-size: 13px;
  color: #7dd87a;
  font-weight: 500;
  white-space: nowrap;
}
.stat-label { font-size: 12px; color: #9ba8bf; margin-top: 4px; }
.section-card { margin-bottom: 20px; border-radius: 8px; }
.inventory-stats-wrap,
.order-stats-wrap { margin-bottom: 20px; }
.inventory-stat-row { margin-bottom: 0; }
.card-header { display: flex; align-items: center; gap: 8px; font-weight: 600; }
</style>
