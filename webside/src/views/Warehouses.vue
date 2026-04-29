<template>
  <div>
    <div class="page-header">
      <span class="page-title">仓库管理</span>
      <el-button type="primary" @click="openDialog()">
        <el-icon><Plus /></el-icon> 新增仓库
      </el-button>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="w in list" :key="w.id">
        <el-card shadow="hover" class="warehouse-card">
          <div class="wh-icon">
            <el-icon size="32" color="#409EFF"><OfficeBuilding /></el-icon>
          </div>
          <div class="wh-name">{{ w.name }}</div>
          <div class="wh-loc" v-if="w.location">
            <el-icon size="12"><Location /></el-icon> {{ w.location }}
          </div>
          <div class="wh-desc" v-if="w.description">{{ w.description }}</div>
          <el-divider />
          <div class="wh-stats">
            <div class="wh-stat">
              <div class="wh-stat-val">{{ w.product_types }}</div>
              <div class="wh-stat-label">商品种类</div>
            </div>
            <div class="wh-stat">
              <div class="wh-stat-val">{{ w.total_quantity }}</div>
              <div class="wh-stat-label">总库存量</div>
            </div>
          </div>
          <div class="wh-actions">
            <el-button size="small" @click="openDialog(w)">编辑</el-button>
            <el-popconfirm title="确认删除该仓库？" @confirm="remove(w.id)">
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑仓库' : '新增仓库'" width="440px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="仓库名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入仓库名称" />
        </el-form-item>
        <el-form-item label="位置">
          <el-input v-model="form.location" placeholder="如：1号楼A区" />
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { warehouseApi } from '@/api/index.js'

const list = ref([])
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref()
const form = ref({ id: null, name: '', location: '', description: '' })
const rules = { name: [{ required: true, message: '请输入仓库名称', trigger: 'blur' }] }

async function load() {
  list.value = await warehouseApi.list()
}

function openDialog(row = null) {
  form.value = row ? { ...row } : { id: null, name: '', location: '', description: '' }
  dialogVisible.value = true
}

async function submit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (form.value.id) await warehouseApi.update(form.value.id, form.value)
    else await warehouseApi.create(form.value)
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
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-title { font-size: 20px; font-weight: 600; }
.warehouse-card { border-radius: 10px; text-align: center; margin-bottom: 16px; }
.wh-icon { margin-bottom: 10px; }
.wh-name { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.wh-loc { font-size: 12px; color: #95a1b7; margin-bottom: 4px; display: flex; align-items: center; justify-content: center; gap: 4px; }
.wh-desc { font-size: 12px; color: #7f8aa1; margin-bottom: 4px; }
.wh-stats { display: flex; justify-content: space-around; }
.wh-stat-val { font-size: 20px; font-weight: 700; color: #409EFF; }
.wh-stat-label { font-size: 12px; color: #95a1b7; }
.wh-actions { display: flex; justify-content: center; gap: 8px; margin-top: 12px; }
</style>
