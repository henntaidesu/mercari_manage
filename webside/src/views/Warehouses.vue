<template>
  <div>
    <el-card shadow="never" class="search-card">
      <div class="warehouse-head">
        <div>
          <div class="warehouse-title">仓库管理（按仓库区分货架）</div>
          <div class="warehouse-subtitle">支持按仓库筛选，历史空值默认归入“默认仓库”</div>
        </div>
        <div class="warehouse-actions">
          <el-select v-model="selectedWarehouse" placeholder="选择仓库" style="width: 180px">
            <el-option label="全部仓库" value="" />
            <el-option
              v-for="w in warehouseOptions"
              :key="w"
              :label="w"
              :value="w"
            />
          </el-select>
          <el-button @click="openWarehouseDialog">新建仓库</el-button>
          <el-button type="primary" @click="openDialog()">
            <el-icon><Plus /></el-icon> 新增货架
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card shadow="hover" class="overview-card">
      <div class="overview-grid">
        <div class="overview-item">
          <div class="overview-value">{{ mergedWarehouse.shelf_count }}</div>
          <div class="overview-label">货架数量</div>
        </div>
        <div class="overview-item">
          <div class="overview-value">{{ mergedWarehouse.product_types }}</div>
          <div class="overview-label">商品种类</div>
        </div>
        <div class="overview-item">
          <div class="overview-value">{{ mergedWarehouse.total_quantity }}</div>
          <div class="overview-label">总库存量</div>
        </div>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-table :data="filteredList" border stripe>
        <el-table-column label="仓库" prop="warehouse" min-width="140" />
        <el-table-column label="货架名称" prop="name" min-width="180" />
        <el-table-column label="位置" prop="location" min-width="140" />
        <el-table-column label="描述" prop="description" min-width="180" show-overflow-tooltip />
        <el-table-column label="商品种类" prop="product_types" width="110" />
        <el-table-column label="总库存量" prop="total_quantity" width="110" />
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除该货架？" @confirm="remove(row.id)">
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑货架' : '新增货架'" width="440px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="仓库" prop="warehouse">
          <el-input v-model="form.warehouse" placeholder="请输入仓库名称（如 1号仓）" />
        </el-form-item>
        <el-form-item v-if="form.id" label="货架名称" prop="name">
          <el-select v-model="form.name" filterable allow-create default-first-option placeholder="请选择或输入货架名称">
            <el-option
              v-for="name in shelfNameOptionsForEdit"
              :key="name"
              :label="name"
              :value="name"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-else label="货架名称" prop="names">
          <el-select
            v-model="form.names"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="请选择或输入货架名称（可多选）"
          >
            <el-option
              v-for="name in shelfNameOptionsForCreate"
              :key="name"
              :label="name"
              :value="name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="位置">
          <el-input v-model="form.location" placeholder="如：1号仓库1排左侧" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="可选描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="warehouseDialogVisible" title="新建仓库" width="420px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="仓库名称" required>
          <el-input v-model="newWarehouseName" placeholder="请输入仓库名称（如 2号仓）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="warehouseDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmCreateWarehouse">下一步</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { warehouseApi } from '@/api/index.js'

const list = ref([])
const selectedWarehouse = ref('')
const dialogVisible = ref(false)
const warehouseDialogVisible = ref(false)
const newWarehouseName = ref('')
const submitting = ref(false)
const formRef = ref()
const form = ref({ id: null, warehouse: '默认仓库', name: '', names: [], location: '', description: '' })
const rules = {
  warehouse: [{ required: true, message: '请输入仓库名称', trigger: 'blur' }],
  name: [{ required: true, message: '请输入货架名称', trigger: 'blur' }],
  names: [{
    validator: (_, value, callback) => {
      if (!Array.isArray(value) || value.length === 0) {
        callback(new Error('请选择至少一个货架名称'))
        return
      }
      callback()
    },
    trigger: 'change'
  }]
}

const warehouseOptions = computed(() => {
  const all = list.value.map((item) => item.warehouse || '默认仓库')
  return [...new Set(all)]
})

const filteredList = computed(() => {
  if (!selectedWarehouse.value) {
    return list.value
  }
  return list.value.filter((item) => (item.warehouse || '默认仓库') === selectedWarehouse.value)
})

const shelfNameOptionsForEdit = computed(() => {
  const warehouseName = form.value.warehouse || '默认仓库'
  const names = list.value
    .filter((item) => (item.warehouse || '默认仓库') === warehouseName)
    .map((item) => item.name)
  return [...new Set(names)]
})

const DEFAULT_WAREHOUSE = '默认仓库'

const shelfNameOptionsForCreate = computed(() => {
  const targetWh = form.value.warehouse || DEFAULT_WAREHOUSE
  const selectedNames = new Set((form.value.names || []).map((v) => String(v).trim()).filter(Boolean))

  const normWh = (w) => w || DEFAULT_WAREHOUSE

  const namesFromDefault = list.value
    .filter((item) => normWh(item.warehouse) === DEFAULT_WAREHOUSE)
    .map((item) => item.name)
    .filter(Boolean)

  const namesInTarget = list.value
    .filter((item) => normWh(item.warehouse) === targetWh)
    .map((item) => item.name)
    .filter(Boolean)

  const pool = new Set([...namesFromDefault, ...namesInTarget])
  let options = [...pool].filter((name) => !selectedNames.has(name))

  if (targetWh !== DEFAULT_WAREHOUSE) {
    const existingInTarget = new Set(namesInTarget)
    options = options.filter((name) => !existingInTarget.has(name))
  }

  return [...new Set(options)]
})

const mergedWarehouse = computed(() => {
  const productTypes = filteredList.value.reduce((sum, item) => sum + Number(item.product_types || 0), 0)
  const totalQuantity = filteredList.value.reduce((sum, item) => sum + Number(item.total_quantity || 0), 0)
  return {
    shelf_count: filteredList.value.length,
    product_types: productTypes,
    total_quantity: totalQuantity
  }
})

async function load() {
  const rows = await warehouseApi.list()
  list.value = rows.map((item) => ({ ...item, warehouse: item.warehouse || '默认仓库' }))
}

function openDialog(row = null) {
  form.value = row
    ? { ...row, warehouse: row.warehouse || '默认仓库', names: [] }
    : { id: null, warehouse: selectedWarehouse.value || '默认仓库', name: '', names: [], location: '', description: '' }
  dialogVisible.value = true
}

function openWarehouseDialog() {
  newWarehouseName.value = ''
  warehouseDialogVisible.value = true
}

function confirmCreateWarehouse() {
  const name = (newWarehouseName.value || '').trim()
  if (!name) {
    ElMessage.warning('请输入仓库名称')
    return
  }
  selectedWarehouse.value = name
  warehouseDialogVisible.value = false
  openDialog()
  ElMessage.success('已创建仓库名，请继续新增该仓库下的货架')
}

async function submit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (form.value.id) await warehouseApi.update(form.value.id, form.value)
    else {
      const names = [...new Set((form.value.names || []).map((v) => String(v).trim()).filter(Boolean))]
      for (const shelfName of names) {
        await warehouseApi.create({
          warehouse: form.value.warehouse,
          name: shelfName,
          location: form.value.location,
          description: form.value.description
        })
      }
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } finally {
    submitting.value = false
  }
}

async function remove(id) {
  await warehouseApi.remove(id)
  ElMessage.success('删除成功')
  load()
}

onMounted(load)
</script>

<style scoped>
.search-card { margin-bottom: 16px; border-radius: 8px; }
.warehouse-head { display: flex; justify-content: space-between; gap: 16px; align-items: center; }
.warehouse-actions { display: flex; align-items: center; gap: 10px; }
.warehouse-title { font-size: 18px; font-weight: 600; color: #e6edf7; }
.warehouse-subtitle { font-size: 12px; color: #9ba8bf; margin-top: 4px; }
.overview-card {
  border-radius: 10px;
  margin-bottom: 16px;
  background: #131c2f !important;
  border: 1px solid #28354a !important;
}
.overview-card :deep(.el-card__body) {
  padding: 16px;
  background: transparent !important;
}
.overview-grid { display: grid; grid-template-columns: repeat(3, minmax(100px, 1fr)); gap: 12px; }
.overview-item {
  background: #161f33;
  border-radius: 8px;
  text-align: center;
  padding: 14px 10px;
  border: 1px solid #2a3446;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}
.overview-value { font-size: 24px; font-weight: 700; color: #409eff; line-height: 1.2; }
.overview-label { font-size: 12px; color: #9ba8bf; margin-top: 4px; }
</style>
