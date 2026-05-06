<template>
  <div>
    <el-card shadow="never" class="search-card">
      <el-row :gutter="0" align="middle" class="search-row">
        <el-col :xs="24" :md="16" class="search-left-group">
          <el-select v-model="filters.type" placeholder="成本类型" clearable @change="onFilterChange" style="width: 100%">
            <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-select v-model="filters.warehouse_id" placeholder="选择仓库" clearable @change="onFilterChange" style="width: 100%">
            <el-option v-for="w in warehouses" :key="w.id" :label="warehouseShelfLabel(w)" :value="w.id" />
          </el-select>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            @change="onFilterChange"
          />
        </el-col>
        <el-col :xs="24" :md="8" class="search-actions">
          <el-button type="primary" @click="openCreate">新增记录</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="物品图" width="90" align="center">
          <template #default="{ row }">
            <el-image
              v-if="row.item_image"
              :src="row.item_image"
              :preview-src-list="[row.item_image]"
              :hide-on-click-modal="true"
              :preview-teleported="true"
              :z-index="4000"
              style="width:40px;height:40px;border-radius:4px;object-fit:cover"
              fit="cover"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="typeMap[row.type]?.tag || 'info'" size="small" effect="light">
              {{ typeMap[row.type]?.label || row.type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="物品名称" prop="item_name" min-width="140" />
        <el-table-column label="金额" width="120" align="right">
          <template #default="{ row }">
            <span class="amount">¥{{ Math.round(row.amount || 0) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="100" align="center">
          <template #default="{ row }">
            {{ row.quantity || 0 }}
          </template>
        </el-table-column>
        <el-table-column label="总价" width="120" align="right">
          <template #default="{ row }">
            <span class="amount">¥{{ Math.round((row.amount || 0) * (row.quantity || 0)) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="仓库" prop="warehouse_name" width="140">
          <template #default="{ row }">
            {{ row.warehouse_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="备注" prop="remark" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作人" prop="operator" width="100" />
        <el-table-column label="记录时间" width="175">
          <template #default="{ row }">
            {{ formatTs(row.cost_date) }}
          </template>
        </el-table-column>
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
        <el-form-item label="记录时间" prop="cost_date">
          <el-date-picker
            v-model="form.cost_date"
            type="datetime"
            value-format="x"
            placeholder="请选择记录时间"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="类型" prop="type">
          <el-select v-model="form.type" placeholder="请选择类型" style="width: 100%">
            <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="物品名称" prop="item_name">
          <el-input v-model="form.item_name" placeholder="请输入物品名称" maxlength="60" clearable />
        </el-form-item>
        <el-form-item label="物品图">
          <div class="image-row">
            <div class="image-upload-box" @click="fileInputRef?.click()">
              <img v-if="form.item_image" :src="form.item_image" class="image-preview" />
              <span v-else class="image-placeholder">点击上传</span>
            </div>
            <div class="image-actions">
              <el-button size="small" @click="fileInputRef?.click()" :loading="uploadingImage">选择图片</el-button>
              <el-button size="small" type="danger" text @click="clearImage" :disabled="!form.item_image">移除</el-button>
            </div>
          </div>
          <input ref="fileInputRef" type="file" accept="image/*" style="display:none" @change="handleImageUpload" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="单价" prop="amount">
              <el-input-number
                v-model="form.amount"
                :min="1"
                :precision="0"
                :controls="false"
                placeholder="请输入单价"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数量" prop="quantity">
              <el-input-number
                v-model="form.quantity"
                :min="1"
                :precision="0"
                :controls="false"
                placeholder="请输入数量"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="仓库">
          <el-select v-model="form.warehouse_id" clearable placeholder="可不选" style="width: 100%">
            <el-option v-for="w in warehouses" :key="w.id" :label="warehouseShelfLabel(w)" :value="w.id" />
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
import { warehouseShelfLabel } from '@/utils/warehouseLabel.js'

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
const fileInputRef = ref()
const uploadingImage = ref(false)

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
  cost_date: Date.now(),
  type: 'purchase',
  item_name: '',
  item_image: '',
  amount: null,
  quantity: 1,
  warehouse_id: null,
  remark: '',
})

const form = ref(createDefaultForm())

function formatTs(ts) {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleString()
}

const rules = {
  cost_date: [{ required: true, message: '请选择记录时间', trigger: 'change' }],
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  item_name: [{ required: true, message: '请输入物品名称', trigger: 'blur' }],
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
    cost_date: (row.cost_date || 0) * 1000,
    type: row.type,
    item_name: row.item_name || '',
    item_image: row.item_image || '',
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
    cost_date: Math.floor((form.value.cost_date || Date.now()) / 1000),
    type: form.value.type,
    item_name: String(form.value.item_name || '').trim(),
    item_image: form.value.item_image || null,
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

async function handleImageUpload(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.warning('图片不能超过5MB')
    return
  }
  uploadingImage.value = true
  try {
    const res = await costRecordApi.uploadImage(file)
    form.value.item_image = res.path || ''
    ElMessage.success('图片上传成功')
  } finally {
    uploadingImage.value = false
  }
}

function clearImage() {
  form.value.item_image = ''
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
  gap: 20px;
}
.search-actions {
  display: flex;
  justify-content: flex-end;
  gap: 20px;
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
.image-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.image-upload-box {
  width: 64px;
  height: 64px;
  border: 1px dashed #4b5f7d;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  cursor: pointer;
}
.image-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.image-placeholder {
  font-size: 12px;
  color: #8ea2c0;
}
.image-actions {
  display: flex;
  gap: 8px;
}
</style>
