<template>
  <div>
    <div class="page-header">
      <span class="page-title">订单管理</span>
      <el-button type="primary" @click="openCreate">新增订单</el-button>
    </div>

    <el-card shadow="never" class="search-card">
      <el-row :gutter="12" align="middle">
        <el-col :xs="24" :sm="8" :md="6">
          <el-input
            v-model="filters.keyword"
            placeholder="搜索订单号/客户"
            clearable
            @change="onFilterChange"
          />
        </el-col>
        <el-col :xs="24" :sm="8" :md="6">
          <el-select v-model="filters.status" placeholder="订单状态" clearable style="width: 100%" @change="onFilterChange">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
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
        <el-col :xs="24" :sm="24" :md="4">
          <el-button @click="resetFilters">重置</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="订单号" prop="order_no" min-width="150" />
        <el-table-column label="日期" prop="order_date" width="120" />
        <el-table-column label="客户" prop="customer_name" width="140">
          <template #default="{ row }">{{ row.customer_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]?.tag || 'info'" size="small" effect="light">
              {{ statusMap[row.status]?.label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="金额" width="120" align="right">
          <template #default="{ row }">
            <span class="amount">¥{{ Number(row.amount || 0).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="备注" prop="remark" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-popconfirm title="确认删除该订单？" @confirm="remove(row.id)">
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

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑订单' : '新增订单'" width="520px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="86px">
        <el-form-item label="订单号" prop="order_no">
          <el-input v-model="form.order_no" placeholder="请输入订单号" maxlength="60" clearable />
        </el-form-item>
        <el-form-item label="订单日期" prop="order_date">
          <el-date-picker v-model="form.order_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="客户名称">
          <el-input v-model="form.customer_name" placeholder="请输入客户名称" maxlength="60" clearable />
        </el-form-item>
        <el-form-item label="订单状态" prop="status">
          <el-select v-model="form.status" style="width: 100%">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="订单金额" prop="amount">
          <el-input-number v-model="form.amount" :min="0.01" :precision="2" :controls="false" style="width: 100%" />
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
import { orderApi } from '@/api/index.js'

const loading = ref(false)
const submitting = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dateRange = ref([])
const dialogVisible = ref(false)
const formRef = ref()

const filters = ref({ keyword: '', status: '' })

const statusOptions = [
  { label: '待包装', value: 'to_pack' },
  { label: '待发货', value: 'to_ship' },
  { label: '已发送', value: 'sent' },
  { label: '已签收', value: 'signed' },
  { label: '已确认', value: 'confirmed' },
]

const statusMap = {
  to_pack: { label: '待包装', tag: 'info' },
  to_ship: { label: '待发货', tag: 'warning' },
  sent: { label: '已发送', tag: 'primary' },
  signed: { label: '已签收', tag: 'success' },
  confirmed: { label: '已确认', tag: 'danger' },
}

const createDefaultForm = () => ({
  id: null,
  order_no: '',
  order_date: new Date().toISOString().slice(0, 10),
  customer_name: '',
  status: 'to_pack',
  amount: null,
  remark: '',
})

const form = ref(createDefaultForm())

const rules = {
  order_no: [{ required: true, message: '请输入订单号', trigger: 'blur' }],
  order_date: [{ required: true, message: '请选择订单日期', trigger: 'change' }],
  status: [{ required: true, message: '请选择订单状态', trigger: 'change' }],
  amount: [{ required: true, message: '请输入订单金额', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  const params = { page: page.value, page_size: pageSize.value }
  if (filters.value.keyword) params.keyword = filters.value.keyword
  if (filters.value.status) params.status = filters.value.status
  if (dateRange.value?.length === 2) {
    params.start_date = dateRange.value[0]
    params.end_date = dateRange.value[1]
  }
  const res = await orderApi.list(params).finally(() => {
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
  filters.value = { keyword: '', status: '' }
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
    order_no: row.order_no || '',
    order_date: row.order_date,
    customer_name: row.customer_name || '',
    status: row.status || 'to_pack',
    amount: Number(row.amount || 0),
    remark: row.remark || '',
  }
  dialogVisible.value = true
}

async function submit() {
  await formRef.value?.validate()
  submitting.value = true
  const payload = {
    order_no: String(form.value.order_no || '').trim(),
    order_date: form.value.order_date,
    customer_name: String(form.value.customer_name || '').trim() || null,
    status: form.value.status,
    amount: Number(form.value.amount || 0),
    remark: form.value.remark || null,
  }
  try {
    if (form.value.id) {
      await orderApi.update(form.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await orderApi.create(payload)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    load()
  } finally {
    submitting.value = false
  }
}

async function remove(id) {
  await orderApi.remove(id)
  ElMessage.success('删除成功')
  if (list.value.length === 1 && page.value > 1) page.value -= 1
  load()
}

onMounted(() => {
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
