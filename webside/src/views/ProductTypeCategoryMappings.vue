<template>
  <div>
    <el-card shadow="never" class="search-card">
      <el-row justify="end">
        <el-button type="primary" @click="openDialog()">
          <el-icon><Plus /></el-icon> 新增映射
        </el-button>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="映射ID" prop="mapping_id" min-width="180" />
        <el-table-column label="商品类型" prop="product_type" min-width="180" />
        <el-table-column label="说明" prop="description" show-overflow-tooltip />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除该映射？" @confirm="remove(row.mapping_id)">
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.original_mapping_id ? '编辑映射' : '新增映射'" width="460px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="90px">
        <el-form-item label="商品类型" prop="product_type">
          <el-input v-model="form.product_type" placeholder="请输入商品类型（如：手办、卡牌）" />
        </el-form-item>
        <el-form-item label="映射ID" prop="mapping_id">
          <el-input v-model="form.mapping_id" placeholder="请输入映射ID" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="可选说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { productTypeCategoryMappingApi } from '@/api/index.js'

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref()
const form = ref({ original_mapping_id: null, product_type: '', mapping_id: '', description: '' })
const rules = {
  product_type: [{ required: true, message: '请输入商品类型', trigger: 'blur' }],
  mapping_id: [{ required: true, message: '请输入映射ID', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  list.value = await productTypeCategoryMappingApi.list().finally(() => (loading.value = false))
}

function openDialog(row = null) {
  form.value = row
    ? {
        original_mapping_id: row.mapping_id || null,
        product_type: row.product_type || '',
        mapping_id: row.mapping_id || '',
        description: row.description || ''
      }
    : { original_mapping_id: null, product_type: '', mapping_id: '', description: '' }
  dialogVisible.value = true
}

async function submit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    const payload = {
      product_type: String(form.value.product_type || '').trim(),
      mapping_id: String(form.value.mapping_id || '').trim(),
      description: form.value.description
    }
    if (form.value.original_mapping_id) await productTypeCategoryMappingApi.update(form.value.original_mapping_id, payload)
    else await productTypeCategoryMappingApi.create(payload)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } finally {
    submitting.value = false
  }
}

async function remove(id) {
  await productTypeCategoryMappingApi.remove(id)
  ElMessage.success('删除成功')
  load()
}

onMounted(load)
</script>

<style scoped>
.search-card { margin-bottom: 16px; border-radius: 8px; }
.table-card { border-radius: 8px; }
</style>
