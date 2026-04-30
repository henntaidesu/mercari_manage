<template>
  <div>
    <el-card shadow="never" class="search-card">
      <el-row justify="end">
        <el-button type="primary" @click="openUserDialog">
          <el-icon><Plus /></el-icon> 新增用户
        </el-button>
      </el-row>
    </el-card>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="14">
        <el-card shadow="never" class="table-card">
          <template #header>
            <div class="card-title">用户列表</div>
          </template>
          <el-table :data="users" v-loading="loading" stripe>
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="username" label="用户名" min-width="120" />
            <el-table-column prop="display_name" label="显示名" min-width="140" />
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
                  {{ row.is_active ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="last_login_at" label="最近登录" min-width="160" />
            <el-table-column prop="created_at" label="创建时间" min-width="160" />
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="10">
        <el-card shadow="never" class="table-card">
          <template #header>
            <div class="card-title">修改我的密码</div>
          </template>
          <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="90px">
            <el-form-item label="原密码" prop="old_password">
              <el-input v-model="pwdForm.old_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input v-model="pwdForm.new_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirm_password">
              <el-input v-model="pwdForm.confirm_password" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="pwdSubmitting" @click="submitPassword">修改密码</el-button>
            </el-form-item>
          </el-form>
          <div class="pwd-tip">仅支持修改当前登录用户自己的密码。</div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="userDialogVisible" title="新增用户" width="420px" destroy-on-close>
      <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="userForm.username" />
        </el-form-item>
        <el-form-item label="显示名">
          <el-input v-model="userForm.display_name" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="userForm.password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="userSubmitting" @click="submitUser">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api/index.js'

const users = ref([])
const loading = ref(false)

const userDialogVisible = ref(false)
const userSubmitting = ref(false)
const userFormRef = ref()
const userForm = reactive({
  username: '',
  display_name: '',
  password: ''
})
const userRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '密码至少6位', trigger: 'blur' }]
}

const pwdSubmitting = ref(false)
const pwdFormRef = ref()
const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})
const pwdRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 6, message: '新密码至少6位', trigger: 'blur' }],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== pwdForm.new_password) callback(new Error('两次输入的新密码不一致'))
        else callback()
      },
      trigger: 'blur'
    }
  ]
}

async function loadUsers() {
  loading.value = true
  try {
    users.value = await authApi.listUsers()
  } finally {
    loading.value = false
  }
}

function openUserDialog() {
  userForm.username = ''
  userForm.display_name = ''
  userForm.password = ''
  userDialogVisible.value = true
}

async function submitUser() {
  await userFormRef.value.validate()
  userSubmitting.value = true
  try {
    await authApi.createUser(userForm)
    ElMessage.success('用户创建成功')
    userDialogVisible.value = false
    await loadUsers()
  } finally {
    userSubmitting.value = false
  }
}

async function submitPassword() {
  await pwdFormRef.value.validate()
  pwdSubmitting.value = true
  try {
    await authApi.changePassword({
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password
    })
    ElMessage.success('密码修改成功，请重新登录')
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    window.location.hash = '#/login'
  } finally {
    pwdSubmitting.value = false
  }
}

onMounted(loadUsers)
</script>

<style scoped>
.search-card { margin-bottom: 16px; border-radius: 8px; }
.table-card { border-radius: 8px; margin-bottom: 16px; }
.card-title { font-weight: 600; }
.pwd-tip { font-size: 12px; color: #94a3b8; margin-top: 8px; }
</style>
