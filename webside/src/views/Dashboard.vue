<template>
  <div class="dashboard">
    <div class="page-title">控制台</div>

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

    <!-- 低库存预警 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon color="#f56c6c"><Warning /></el-icon>
          <span>库存预警</span>
          <el-badge :value="lowStockList.length" type="danger" />
        </div>
      </template>
      <el-table :data="lowStockList" size="small" stripe>
        <el-table-column label="商品" prop="product_name" />
        <el-table-column label="SKU" prop="sku" width="120" />
        <el-table-column label="仓库" prop="warehouse_name" width="120" />
        <el-table-column label="当前库存" prop="quantity" width="100" align="center">
          <template #default="{ row }">
            <el-tag type="danger" size="small">{{ row.quantity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最低库存" prop="min_quantity" width="100" align="center" />
        <el-table-column label="单位" prop="unit" width="70" align="center" />
      </el-table>
      <div v-if="lowStockList.length === 0" class="empty-tip">
        <el-icon color="#67c23a" size="20"><CircleCheck /></el-icon> 暂无库存预警
      </div>
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
const lowStockList = ref([])
const recentTx = ref([])

const statCards = [
  { key: 'total_products', label: '商品种类', icon: 'Goods', color: '#409EFF' },
  { key: 'total_warehouses', label: '仓库数量', icon: 'OfficeBuilding', color: '#67C23A' },
  { key: 'total_stock', label: '总库存量', icon: 'Box', color: '#E6A23C' },
  { key: 'low_stock_count', label: '低库存预警', icon: 'Warning', color: '#F56C6C' },
  { key: 'today_in', label: '今日入库', icon: 'Top', color: '#67C23A' },
  { key: 'today_out', label: '今日出库', icon: 'Bottom', color: '#F56C6C' }
]

async function load() {
  const [s, inv, tx] = await Promise.all([
    inventoryApi.summary(),
    inventoryApi.list({ low_stock: true }),
    transactionApi.list({ page_size: 10 })
  ])
  summary.value = s
  lowStockList.value = inv
  recentTx.value = tx.items
}

onMounted(load)
</script>

<style scoped>
.dashboard { max-width: 1400px; }
.page-title { font-size: 20px; font-weight: 600; color: #1a1a1a; margin-bottom: 20px; }
.stat-row { margin-bottom: 20px; }
.stat-row .el-col { margin-bottom: 16px; }
.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  border-top: 3px solid;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
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
.stat-value { font-size: 22px; font-weight: 700; color: #1a1a1a; }
.stat-label { font-size: 12px; color: #888; margin-top: 2px; }
.section-card { margin-bottom: 20px; border-radius: 8px; }
.card-header { display: flex; align-items: center; gap: 8px; font-weight: 600; }
.empty-tip { text-align: center; padding: 20px; color: #67c23a; display: flex; align-items: center; justify-content: center; gap: 6px; }
</style>
