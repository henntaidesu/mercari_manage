<template>
  <div>
    <!-- 筛选 -->
    <el-card shadow="never" class="search-card">
      <el-row :gutter="0" align="middle" class="search-row">
        <el-col :xs="24" :md="16" class="search-left-group">
          <el-select v-model="filters.type" placeholder="操作类型" clearable @change="load" style="width:100%">
            <el-option label="入库" value="in" />
            <el-option label="出库" value="out" />
            <el-option label="调拨" value="transfer" />
          </el-select>
          <el-select v-model="filters.warehouse_id" placeholder="选择仓库" clearable @change="load" style="width:100%">
            <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
          </el-select>
        </el-col>
        <el-col :xs="24" :md="8" class="search-actions">
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="时间" width="160">
          <template #default="{ row }">{{ formatUnixSecLocal(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="类型" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="typeConfig[row.type]?.tag" size="small" effect="light">
              {{ typeConfig[row.type]?.label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="商品" prop="product_name" min-width="120" />
        <el-table-column label="来源仓库" prop="warehouse_name" width="120" />
        <el-table-column label="目标仓库" prop="target_warehouse_name" width="120">
          <template #default="{ row }">
            {{ row.target_warehouse_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="数量" width="90" align="center">
          <template #default="{ row }">
            <span :class="row.type === 'in' ? 'text-green' : row.type === 'out' ? 'text-red' : 'text-orange'">
              {{ row.type === 'in' ? '+' : row.type === 'out' ? '-' : '⇄' }}{{ row.quantity }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作人" prop="operator" width="90" />
        <el-table-column label="备注" prop="remark" show-overflow-tooltip />
      </el-table>

      <!-- 分页 -->
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { transactionApi, warehouseApi } from '@/api/index.js'
import { formatUnixSecLocal } from '@/utils/timeDisplay.js'

const list = ref([])
const loading = ref(false)
const warehouses = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filters = ref({ type: '', warehouse_id: null })

const typeConfig = {
  in: { label: '入库', tag: 'success' },
  out: { label: '出库', tag: 'danger' },
  transfer: { label: '调拨', tag: 'warning' }
}

async function load() {
  loading.value = true
  const params = { page: page.value, page_size: pageSize.value }
  if (filters.value.type) params.type = filters.value.type
  if (filters.value.warehouse_id) params.warehouse_id = filters.value.warehouse_id
  const res = await transactionApi.list(params).finally(() => (loading.value = false))
  list.value = res.items
  total.value = res.total
}

function resetFilters() {
  filters.value = { type: '', warehouse_id: null }
  page.value = 1
  load()
}

onMounted(async () => {
  warehouses.value = await warehouseApi.list()
  load()
})
</script>

<style scoped>
.search-card { margin-bottom: 16px; border-radius: 8px; }
.search-row { justify-content: space-between; }
.search-left-group { display: flex; align-items: center; gap: 20px; }
.search-actions { display: flex; justify-content: flex-end; }
.table-card { border-radius: 8px; }
.pagination { margin-top: 16px; display: flex; justify-content: flex-end; }
.text-green { color: #67c23a; font-weight: 600; }
.text-red { color: #f56c6c; font-weight: 600; }
.text-orange { color: #e6a23c; font-weight: 600; }
</style>
