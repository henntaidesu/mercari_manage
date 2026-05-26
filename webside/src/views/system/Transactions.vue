<template>
  <div>
    <!-- 筛选 -->
    <el-card shadow="never" class="search-card">
      <el-row :gutter="0" align="middle" class="search-row">
        <el-col :xs="24" :md="16" class="search-left-group">
          <el-select v-model="filters.type" :placeholder="t('system.txTypeFilter')" clearable @change="load" style="width:100%">
            <el-option :label="t('system.txIn')" value="in" />
            <el-option :label="t('system.txOut')" value="out" />
            <el-option :label="t('system.txTransfer')" value="transfer" />
          </el-select>
          <el-select v-model="filters.warehouse_id" :placeholder="t('system.txWarehousePick')" clearable @change="load" style="width:100%">
            <el-option v-for="w in warehouses" :key="w.id" :label="warehouseShelfLabel(w)" :value="w.id" />
          </el-select>
        </el-col>
        <el-col :xs="24" :md="8" class="search-actions">
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column :label="t('system.txTime')" width="160">
          <template #default="{ row }">{{ formatUnixSecLocal(row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="t('system.txType')" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="typeConfig[row.type]?.tag" size="small" effect="light">
              {{ typeConfig[row.type]?.label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('system.txInventory')" prop="inventory_name" min-width="120" />
        <el-table-column :label="t('system.txSourceWarehouse')" prop="warehouse_name" width="120" />
        <el-table-column :label="t('system.txTargetWarehouse')" prop="target_warehouse_name" width="120">
          <template #default="{ row }">
            {{ row.target_warehouse_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column :label="t('system.txQuantity')" width="90" align="center">
          <template #default="{ row }">
            <span :class="row.type === 'in' ? 'text-green' : row.type === 'out' ? 'text-red' : 'text-orange'">
              {{ row.type === 'in' ? '+' : row.type === 'out' ? '-' : '⇄' }}{{ row.quantity }}
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="t('system.txOperator')" prop="operator" width="90" />
        <el-table-column :label="t('common.remark')" prop="remark" show-overflow-tooltip />
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
          size="small"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { transactionApi, warehouseApi } from '@/api/index.js'
import { warehouseShelfLabel } from '@/utils/warehouseLabel.js'
import { formatUnixSecLocal } from '@/utils/timeDisplay.js'

const { t } = useI18n()

const list = ref([])
const loading = ref(false)
const warehouses = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filters = ref({ type: '', warehouse_id: null })

const typeConfig = computed(() => ({
  in: { label: t('system.txIn'), tag: 'success' },
  out: { label: t('system.txOut'), tag: 'danger' },
  transfer: { label: t('system.txTransfer'), tag: 'warning' }
}))

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
