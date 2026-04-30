<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-row">
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

    <!-- 最近交易 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon color="#409EFF"><List /></el-icon>
          <span>最近出入库</span>
        </div>
      </template>
      <el-table :data="recentTx" size="small" stripe>
        <el-table-column label="时间" prop="created_at" width="160" />
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
import { ref, onMounted } from 'vue'
import { inventoryApi, transactionApi } from '@/api/index.js'

const summary = ref({})
const recentTx = ref([])

const statCards = [
  { key: 'total_inventory', label: '库存条目', icon: 'Goods', color: '#409EFF' },
  { key: 'total_quantity', label: '总库存量', icon: 'Box', color: '#E6A23C' },
  { key: 'today_in', label: '今日入库', icon: 'Top', color: '#67C23A' },
  { key: 'today_out', label: '今日出库', icon: 'Bottom', color: '#F56C6C' }
]

async function load() {
  const [inventoryItems, tx] = await Promise.all([
    inventoryApi.list(),
    transactionApi.list({ page_size: 10 })
  ])
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
.dashboard { max-width: 1400px; }
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
.stat-value { font-size: 22px; font-weight: 700; color: #ecf2ff; }
.stat-label { font-size: 12px; color: #9ba8bf; margin-top: 2px; }
.section-card { margin-bottom: 20px; border-radius: 8px; }
.card-header { display: flex; align-items: center; gap: 8px; font-weight: 600; }
</style>
