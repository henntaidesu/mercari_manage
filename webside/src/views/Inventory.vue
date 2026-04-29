<template>
  <div>
    <div class="page-header">
      <span class="page-title">库存管理</span>
      <div class="header-actions">
        <el-button type="success" @click="openTxDialog('in')">
          <el-icon><Top /></el-icon> 入库
        </el-button>
        <el-button type="danger" plain @click="openTxDialog('out')">
          <el-icon><Bottom /></el-icon> 出库
        </el-button>
        <el-button type="warning" plain @click="openTxDialog('transfer')">
          <el-icon><Switch /></el-icon> 调拨
        </el-button>
      </div>
    </div>

    <!-- 筛选 -->
    <el-card shadow="never" class="search-card">
      <el-row :gutter="12">
        <el-col :xs="24" :sm="12" :md="6">
          <el-select v-model="filterWarehouse" placeholder="选择仓库" clearable @change="load" style="width:100%">
            <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
          </el-select>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <el-checkbox v-model="filterLow" @change="load" border>仅显示低库存</el-checkbox>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="图片" width="60" align="center">
          <template #default="{ row }">
            <el-image v-if="row.image" :src="row.image" style="width:36px;height:36px;border-radius:4px" fit="cover" />
            <el-icon v-else color="#ddd" size="28"><Picture /></el-icon>
          </template>
        </el-table-column>
        <el-table-column label="商品名称" prop="product_name" min-width="120" />
        <el-table-column label="SKU" prop="sku" width="110" />
        <el-table-column label="分类" prop="category_name" width="100" />
        <el-table-column label="仓库" prop="warehouse_name" width="110" />
        <el-table-column label="库存数量" prop="quantity" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="row.quantity <= row.min_quantity && row.min_quantity > 0 ? 'danger' : 'success'" size="small">
              {{ row.quantity }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最低库存" width="110" align="center">
          <template #default="{ row }">
            <el-input-number
              v-model="row.min_quantity"
              :min="0"
              size="small"
              style="width:80px"
              @change="updateMinQty(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="单位" prop="unit" width="70" align="center" />
        <el-table-column label="更新时间" prop="updated_at" width="155" />
      </el-table>
    </el-card>

    <!-- 出入库弹窗 -->
    <el-dialog v-model="txDialogVisible" :title="txTitles[txForm.type]" width="460px" destroy-on-close>
      <el-form :model="txForm" :rules="txRules" ref="txFormRef" label-width="90px">
        <el-form-item label="商品" prop="product_id">
          <el-select v-model="txForm.product_id" placeholder="选择商品" filterable style="width:100%">
            <el-option v-for="p in products" :key="p.id" :label="`${p.name}${p.sku ? ' ['+p.sku+']' : ''}`" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="仓库" prop="warehouse_id">
          <el-select v-model="txForm.warehouse_id" placeholder="选择仓库" style="width:100%">
            <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="txForm.type === 'transfer'" label="目标仓库" prop="target_warehouse_id">
          <el-select v-model="txForm.target_warehouse_id" placeholder="选择目标仓库" style="width:100%">
            <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="数量" prop="quantity">
          <el-input-number v-model="txForm.quantity" :min="1" style="width:100%" />
        </el-form-item>
        <el-form-item label="操作人">
          <el-input v-model="txForm.operator" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="txForm.remark" type="textarea" :rows="2" placeholder="可选备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="txDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitTx" :loading="txSubmitting">确认提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { inventoryApi, warehouseApi, productApi, transactionApi } from '@/api/index.js'

const list = ref([])
const loading = ref(false)
const warehouses = ref([])
const products = ref([])
const filterWarehouse = ref(null)
const filterLow = ref(false)

const txDialogVisible = ref(false)
const txSubmitting = ref(false)
const txFormRef = ref()
const txForm = ref({ type: 'in', product_id: null, warehouse_id: null, target_warehouse_id: null, quantity: 1, operator: '管理员', remark: '' })
const txTitles = { in: '商品入库', out: '商品出库', transfer: '库存调拨' }
const txRules = {
  product_id: [{ required: true, message: '请选择商品', trigger: 'change' }],
  warehouse_id: [{ required: true, message: '请选择仓库', trigger: 'change' }],
  target_warehouse_id: [{ required: true, message: '请选择目标仓库', trigger: 'change' }],
  quantity: [{ required: true, message: '请填写数量', trigger: 'blur' }]
}

async function load() {
  loading.value = true
  const params = {}
  if (filterWarehouse.value) params.warehouse_id = filterWarehouse.value
  if (filterLow.value) params.low_stock = true
  list.value = await inventoryApi.list(params).finally(() => (loading.value = false))
}

async function updateMinQty(row) {
  await inventoryApi.update(row.id, { min_quantity: row.min_quantity })
  ElMessage.success('最低库存已更新')
}

function openTxDialog(type) {
  txForm.value = { type, product_id: null, warehouse_id: null, target_warehouse_id: null, quantity: 1, operator: '管理员', remark: '' }
  txDialogVisible.value = true
}

async function submitTx() {
  await txFormRef.value.validate()
  txSubmitting.value = true
  try {
    await transactionApi.create(txForm.value)
    ElMessage.success('操作成功')
    txDialogVisible.value = false
    load()
  } finally {
    txSubmitting.value = false
  }
}

onMounted(async () => {
  const [w, p] = await Promise.all([warehouseApi.list(), productApi.list()])
  warehouses.value = w
  products.value = p
  load()
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 10px; }
.page-title { font-size: 20px; font-weight: 600; }
.header-actions { display: flex; gap: 8px; }
.search-card { margin-bottom: 16px; border-radius: 8px; }
.table-card { border-radius: 8px; }
</style>
