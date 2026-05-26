<template>
  <div>
    <el-card shadow="never" class="search-card">
      <el-row :gutter="0" align="middle" class="search-row">
        <el-col :xs="24" :md="16" class="search-left-group">
          <el-select v-model="filters.type" :placeholder="t('system.costRecordTypeFilter')" clearable @change="onFilterChange" style="width: 100%">
            <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-select v-model="filters.warehouse_id" :placeholder="t('system.costRecordSelectWarehouse')" clearable @change="onFilterChange" style="width: 100%">
            <el-option v-for="w in warehouses" :key="w.id" :label="warehouseShelfLabel(w)" :value="w.id" />
          </el-select>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            :range-separator="t('common.to')"
            :start-placeholder="t('common.startDate')"
            :end-placeholder="t('common.endDate')"
            value-format="YYYY-MM-DD"
            @change="onFilterChange"
          />
        </el-col>
        <el-col :xs="24" :md="8" class="search-actions">
          <el-button type="primary" @click="openCreate">{{ t('system.costRecordCreate') }}</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column :label="t('system.costRecordItemImage')" width="90" align="center">
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
        <el-table-column :label="t('common.type')" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="typeMap[row.type]?.tag || 'info'" size="small" effect="light">
              {{ typeMap[row.type]?.label || row.type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('system.costRecordItemName')" prop="item_name" min-width="140" />
        <el-table-column :label="t('common.amount')" width="120" align="right">
          <template #default="{ row }">
            <span class="amount">¥{{ Math.round(row.amount || 0) }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('common.quantity')" width="100" align="center">
          <template #default="{ row }">
            {{ row.quantity || 0 }}
          </template>
        </el-table-column>
        <el-table-column :label="t('system.costRecordTotalAmount')" width="120" align="right">
          <template #default="{ row }">
            <span class="amount">¥{{ Math.round((row.amount || 0) * (row.quantity || 0)) }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('inventory.warehouse')" prop="warehouse_name" width="140">
          <template #default="{ row }">
            {{ row.warehouse_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column :label="t('common.remark')" prop="remark" min-width="180" show-overflow-tooltip />
        <el-table-column :label="t('common.operator')" prop="operator" width="100" />
        <el-table-column :label="t('system.costRecordRecordTime')" width="175">
          <template #default="{ row }">
            {{ formatTs(row.cost_date) }}
          </template>
        </el-table-column>
        <el-table-column :label="t('common.actions')" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
            <el-popconfirm :title="t('system.costRecordDeleteConfirm')" @confirm="remove(row.id)">
              <template #reference>
                <el-button size="small" type="danger">{{ t('common.delete') }}</el-button>
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
          size="small"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? t('system.costRecordEdit') : t('system.costRecordCreate')"
      width="520px"
      destroy-on-close
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="78px">
        <el-form-item :label="t('system.costRecordRecordTime')" prop="cost_date">
          <el-date-picker
            v-model="form.cost_date"
            type="datetime"
            value-format="x"
            :placeholder="t('system.costRecordSelectRecordTime')"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item :label="t('common.type')" prop="type">
          <el-select v-model="form.type" :placeholder="t('system.costRecordSelectType')" style="width: 100%">
            <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('system.costRecordItemName')" prop="item_name">
          <el-input v-model="form.item_name" :placeholder="t('system.costRecordInputItemName')" maxlength="60" clearable />
        </el-form-item>
        <el-form-item :label="t('system.costRecordItemImage')">
          <div class="image-row">
            <div class="image-upload-box" @click="fileInputRef?.click()">
              <img v-if="form.item_image" :src="form.item_image" class="image-preview" />
              <span v-else class="image-placeholder">{{ t('system.costRecordClickUpload') }}</span>
            </div>
            <div class="image-actions">
              <el-button size="small" @click="fileInputRef?.click()" :loading="uploadingImage">{{ t('system.costRecordSelectImage') }}</el-button>
              <el-button size="small" type="danger" text @click="clearImage" :disabled="!form.item_image">{{ t('system.costRecordRemove') }}</el-button>
            </div>
          </div>
          <input ref="fileInputRef" type="file" accept="image/*" style="display:none" @change="handleImageUpload" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item :label="t('system.costRecordUnitPrice')" prop="amount">
              <el-input-number
                v-model="form.amount"
                :min="1"
                :precision="0"
                :controls="false"
                :placeholder="t('system.costRecordInputUnitPrice')"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="t('common.quantity')" prop="quantity">
              <el-input-number
                v-model="form.quantity"
                :min="1"
                :precision="0"
                :controls="false"
                :placeholder="t('system.costRecordInputQuantity')"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item :label="t('inventory.warehouse')">
          <el-select v-model="form.warehouse_id" clearable :placeholder="t('system.costRecordWarehouseOptional')" style="width: 100%">
            <el-option v-for="w in warehouses" :key="w.id" :label="warehouseShelfLabel(w)" :value="w.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('common.remark')">
          <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="200" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { costRecordApi, warehouseApi } from '@/api/index.js'
import { warehouseShelfLabel } from '@/utils/warehouseLabel.js'

const { t } = useI18n()

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

const typeOptions = computed(() => [
  { label: t('system.costRecordTypePurchase'), value: 'purchase' },
  { label: t('system.costRecordTypeShipping'), value: 'shipping' },
  { label: t('system.costRecordTypePackaging'), value: 'packaging' },
  { label: t('system.costRecordTypeOperation'), value: 'operation' },
  { label: t('system.costRecordTypeOther'), value: 'other' },
])

const typeMap = computed(() => ({
  purchase: { label: t('system.costRecordTypePurchase'), tag: 'primary' },
  shipping: { label: t('system.costRecordTypeShipping'), tag: 'warning' },
  packaging: { label: t('system.costRecordTypePackaging'), tag: 'danger' },
  operation: { label: t('system.costRecordTypeOperation'), tag: 'success' },
  other: { label: t('system.costRecordTypeOther'), tag: 'info' },
}))

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

const rules = computed(() => ({
  cost_date: [{ required: true, message: t('system.costRecordSelectRecordTime'), trigger: 'change' }],
  type: [{ required: true, message: t('system.costRecordSelectType'), trigger: 'change' }],
  item_name: [{ required: true, message: t('system.costRecordInputItemName'), trigger: 'blur' }],
  amount: [{ required: true, message: t('system.costRecordInputAmount'), trigger: 'blur' }],
  quantity: [{ required: true, message: t('system.costRecordInputQuantity'), trigger: 'blur' }],
}))

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
      ElMessage.success(t('system.costRecordUpdateSuccess'))
    } else {
      await costRecordApi.create(payload)
      ElMessage.success(t('system.costRecordCreateSuccess'))
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
  if (file.size > 25 * 1024 * 1024) {
    ElMessage.warning(t('system.costRecordImageSizeLimit'))
    return
  }
  uploadingImage.value = true
  try {
    const res = await costRecordApi.uploadImage(file)
    form.value.item_image = res.path || ''
    ElMessage.success(t('system.costRecordImageUploadSuccess'))
  } finally {
    uploadingImage.value = false
  }
}

function clearImage() {
  form.value.item_image = ''
}

async function remove(id) {
  await costRecordApi.remove(id)
  ElMessage.success(t('system.costRecordDeleteSuccess'))
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
