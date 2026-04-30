<template>
  <div>
    <div class="page-header">
      <span class="page-title">成本记录</span>
      <el-button type="primary" @click="openCreate">新增记录</el-button>
    </div>

    <el-card shadow="never" class="search-card">
      <el-row :gutter="12" align="middle">
        <el-col :xs="24" :sm="8" :md="5">
          <el-select v-model="filters.type" placeholder="成本类型" clearable @change="onFilterChange" style="width: 100%">
            <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-col>
        <el-col :xs="24" :sm="8" :md="5">
          <el-select v-model="filters.warehouse_id" placeholder="选择仓库" clearable @change="onFilterChange" style="width: 100%">
            <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
          </el-select>
        </el-col>
        <el-col :xs="24" :sm="8" :md="8">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
            @change="onFilterChange"
          />
        </el-col>
        <el-col :xs="24" :sm="24" :md="6">
          <el-button @click="resetFilters">重置</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="日期" prop="cost_date" width="120" />
        <el-table-column label="类型" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="typeMap[row.type]?.tag || 'info'" size="small" effect="light">
              {{ typeMap[row.type]?.label || row.type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="金额" width="120" align="right">
          <template #default="{ row }">
            <span class="amount">¥{{ Number(row.amount || 0).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="100" align="center">
          <template #default="{ row }">
            {{ row.quantity || 0 }}
          </template>
        </el-table-column>
        <el-table-column label="仓库" prop="warehouse_name" width="140">
          <template #default="{ row }">
            {{ row.warehouse_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="备注" prop="remark" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作人" prop="operator" width="100" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-popconfirm title="确认删除该记录？" @confirm="remove(row.id)">
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
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

    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? '编辑成本记录' : '新增成本记录'"
      width="520px"
      destroy-on-close
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="78px">
        <el-form-item label="日期" prop="cost_date">
          <el-date-picker v-model="form.cost_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="类型" prop="type">
          <el-select v-model="form.type" placeholder="请选择类型" style="width: 100%">
            <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="金额" prop="amount">
          <el-input-number v-model="form.amount" :min="0.01" :precision="2" :step="10" style="width: 100%" />
        </el-form-item>
        <el-form-item label="数量" prop="quantity">
          <el-input-number v-model="form.quantity" :min="1" :precision="0" :step="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="仓库">
          <el-select v-model="form.warehouse_id" clearable placeholder="可不选" style="width: 100%">
            <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="200" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { costRecordApi, warehouseApi } from '@/api/index.js'

const loading = ref(false)
const submitting = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const warehouses = ref([])
const dateRange = ref([])
const dialogVisible = ref(false)
const formRef = ref()

const filters = ref({
  type: '',
  warehouse_id: null,
})

const typeOptions = [
  { label: '采购成本', value: 'purchase' },
  { label: '物流成本', value: 'shipping' },
  { label: '包装成本', value: 'packaging' },
  { label: '运营成本', value: 'operation' },
  { label: '其他成本', value: 'other' },
]

const typeMap = {
  purchase: { label: '采购成本', tag: 'primary' },
  shipping: { label: '物流成本', tag: 'warning' },
  packaging: { label: '包装成本', tag: 'danger' },
  operation: { label: '运营成本', tag: 'success' },
  other: { label: '其他成本', tag: 'info' },
}

const createDefaultForm = () => ({
  id: null,
  cost_date: new Date().toISOString().slice(0, 10),
  type: 'purchase',
  amount: 0,
  quantity: 1,
  warehouse_id: null,
  remark: '',
})

const form = ref(createDefaultForm())

const rules = {
  cost_date: [{ required: true, message: '请选择日期', trigger: 'change' }],
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  amount: [{ required: true, message: '请输入金额', trigger: 'blur' }],
  quantity: [{ required: true, message: '请输入数量', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  const params = {
    page: page.value,
    page_size: pageSize.value,
  }
  if (filters.value.type) params.type = filters.value.type
  if (filters.value.warehouse_id) params.warehouse_id = filters.value.warehouse_id
  if (dateRange.value?.length === 2) {
    params.start_date = dateRange.value[0]
    params.end_date = dateRange.value[1]
  }
  const res = await costRecordApi.list(params).finally(() => {
    loading.value = false
  })
  list.value = res.items || []
  total.value = res.total || 0
}

function onFilterChange() {
  page.value = 1
  load()
}

function resetFilters() {
  filters.value = { type: '', warehouse_id: null }
  dateRange.value = []
  page.value = 1
  load()
}

function openCreate() {
  form.value = createDefaultForm()
  dialogVisible.value = true
}

function openEdit(row) {
  form.value = {
    id: row.id,
    cost_date: row.cost_date,
    type: row.type,
    amount: Number(row.amount || 0),
    quantity: Number(row.quantity || 1),
    warehouse_id: row.warehouse_id || null,
    remark: row.remark || '',
  }
  dialogVisible.value = true
}

async function submit() {
  await formRef.value?.validate()
  submitting.value = true
  const payload = {
    cost_date: form.value.cost_date,
    type: form.value.type,
    amount: Number(form.value.amount || 0),
    quantity: Number(form.value.quantity || 0),
    warehouse_id: form.value.warehouse_id,
    remark: form.value.remark || null,
  }
  try {
    if (form.value.id) {
      await costRecordApi.update(form.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await costRecordApi.create(payload)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    load()
  } finally {
    submitting.value = false
  }
}

async function remove(id) {
  await costRecordApi.remove(id)
  ElMessage.success('删除成功')
  if (list.value.length === 1 && page.value > 1) page.value -= 1
  load()
}

onMounted(async () => {
  warehouses.value = await warehouseApi.list()
  load()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-title {
  font-size: 20px;
  font-weight: 600;
}
.search-card {
  margin-bottom: 16px;
  border-radius: 8px;
}
.table-card {
  border-radius: 8px;
}
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.amount {
  color: #f56c6c;
  font-weight: 600;
}
</style>
