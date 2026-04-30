<template>
  <div>
    <div class="page-header">
      <span class="page-title">煤炉账号管理</span>
      <el-button type="primary" @click="openCreate">新增账号</el-button>
    </div>

    <el-card shadow="never" class="search-card">
      <el-row :gutter="12" align="middle">
        <el-col :xs="24" :sm="12" :md="8">
          <el-input
            v-model="filters.keyword"
            placeholder="搜索账号名称/登录账号"
            clearable
            @change="onFilterChange"
          />
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <el-select v-model="filters.status" placeholder="账号状态" clearable style="width: 100%" @change="onFilterChange">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-col>
        <el-col :xs="24" :sm="24" :md="10">
          <el-button @click="resetFilters">重置</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="账号名称" prop="account_name" min-width="140" />
        <el-table-column label="登录账号" prop="login_id" min-width="140" />
        <el-table-column label="登录密码" min-width="140">
          <template #default="{ row }">
            {{ row.login_password || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small" effect="light">
              {{ row.status === 'active' ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="备注" prop="remark" min-width="180" show-overflow-tooltip />
        <el-table-column label="创建时间" prop="created_at" width="170" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-popconfirm title="确认删除该账号？" @confirm="remove(row.id)">
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

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑煤炉账号' : '新增煤炉账号'" width="520px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="86px">
        <el-form-item label="账号名称" prop="account_name">
          <el-input v-model="form.account_name" maxlength="60" clearable />
        </el-form-item>
        <el-form-item label="登录账号" prop="login_id">
          <el-input v-model="form.login_id" maxlength="80" clearable />
        </el-form-item>
        <el-form-item label="登录密码">
          <el-input v-model="form.login_password" maxlength="80" show-password clearable />
        </el-form-item>
        <el-form-item label="账号状态" prop="status">
          <el-select v-model="form.status" style="width: 100%">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
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
import { meiluAccountApi } from '@/api/index.js'

const loading = ref(false)
const submitting = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)
const formRef = ref()

const filters = ref({ keyword: '', status: '' })
const statusOptions = [
  { label: '启用', value: 'active' },
  { label: '停用', value: 'disabled' },
]

const createDefaultForm = () => ({
  id: null,
  account_name: '',
  login_id: '',
  login_password: '',
  status: 'active',
  remark: '',
})
const form = ref(createDefaultForm())

const rules = {
  account_name: [{ required: true, message: '请输入账号名称', trigger: 'blur' }],
  login_id: [{ required: true, message: '请输入登录账号', trigger: 'blur' }],
  status: [{ required: true, message: '请选择账号状态', trigger: 'change' }],
}

async function load() {
  loading.value = true
  const params = { page: page.value, page_size: pageSize.value }
  if (filters.value.keyword) params.keyword = filters.value.keyword
  if (filters.value.status) params.status = filters.value.status
  const res = await meiluAccountApi.list(params).finally(() => {
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
    account_name: row.account_name || '',
    login_id: row.login_id || '',
    login_password: row.login_password || '',
    status: row.status || 'active',
    remark: row.remark || '',
  }
  dialogVisible.value = true
}

async function submit() {
  await formRef.value?.validate()
  submitting.value = true
  const payload = {
    account_name: String(form.value.account_name || '').trim(),
    login_id: String(form.value.login_id || '').trim(),
    login_password: String(form.value.login_password || '').trim() || null,
    status: form.value.status,
    remark: form.value.remark || null,
  }
  try {
    if (form.value.id) {
      await meiluAccountApi.update(form.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await meiluAccountApi.create(payload)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    load()
  } finally {
    submitting.value = false
  }
}

async function remove(id) {
  await meiluAccountApi.remove(id)
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
</style>
