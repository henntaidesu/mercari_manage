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

    <el-card shadow="never" class="search-card">
      <template #header>
        <div class="card-title">系统维护</div>
      </template>
      <p class="sys-maint-tip">
        重启将关闭当前后端进程（含煤炉浏览器与 MITM 代理），约数秒后自动拉起新进程。进行中的自动化任务会被中断。
      </p>
      <el-button type="danger" :loading="restarting" @click="confirmRestartSystem">
        <el-icon><RefreshRight /></el-icon> 重启系统
      </el-button>
    </el-card>

    <el-card shadow="never" class="search-card">
      <template #header>
        <div class="card-title">出品默认值</div>
      </template>
      <el-form label-width="132px" class="listing-def-form">
        <el-form-item label="默认发货地址">
          <el-cascader
            v-model="listingDefForm.shipping_from_path"
            :options="shippingFromCascaderOptions"
            :props="shippingFromCascaderProps"
            :show-all-levels="false"
            filterable
            clearable
            placeholder="不设置则出品表单内使用内置默认"
            style="width: 100%; max-width: 520px"
            popper-class="product-type-cascader-popper"
            @change="onShippingFromChange"
          />
        </el-form-item>
        <el-form-item label="默认配送方法">
          <el-select
            v-model="listingDefForm.shipping_method"
            clearable
            placeholder="未设置时出品表单为「未定」"
            style="width: 100%; max-width: 360px"
          >
            <el-option v-for="s in shippingMethodOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="默认快递费负担">
          <el-select v-model="listingDefForm.shipping_payer" clearable style="width: 100%; max-width: 360px">
            <el-option v-for="s in shippingPayerOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="默认最大发货天数">
          <el-select v-model="listingDefForm.shipping_days" clearable style="width: 100%; max-width: 280px">
            <el-option v-for="s in shippingDaysOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="默认出品账号">
          <el-select
            v-model="listingDefForm.meilu_account_id"
            clearable
            filterable
            placeholder="不设置则出品时需手动选择煤炉账号"
            style="width: 100%; max-width: 420px"
            :loading="meiluAccountsLoading"
          >
            <el-option
              v-for="a in meiluAccountOptions"
              :key="a.id"
              :label="meiluAccountOptionLabel(a)"
              :value="a.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="listingDefSaving" @click="saveListingDefaults">保存出品默认值</el-button>
          <el-button :loading="listingDefLoading" @click="loadListingDefaults">重新加载</el-button>
        </el-form-item>
      </el-form>
    </el-card>

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
import { reactive, ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, RefreshRight } from '@element-plus/icons-vue'
import { authApi, configApi, meiluAccountApi, systemApi } from '@/api/index.js'
import {
  MERCARI_AREAS,
  JP_REGION_OPTIONS,
  getRegionIdForAreaId,
  normalizeShippingFromSeed
} from '@/constants/mercariJapanAreas.js'

const SHIPPING_FROM_AREA_PREFIX = 'AREA:'
const SHIPPING_FROM_REGION_PREFIX = 'REGION:'

const shippingFromCascaderProps = {
  value: 'value',
  label: 'label',
  children: 'children',
  emitPath: true,
  checkStrictly: false
}

const shippingFromCascaderOptions = computed(() =>
  JP_REGION_OPTIONS.map((r) => ({
    value: `${SHIPPING_FROM_REGION_PREFIX}${r.id}`,
    label: r.label,
    children: r.areaIds
      .map((aid) => {
        const a = MERCARI_AREAS.find((x) => x.id === aid)
        return a ? { value: `${SHIPPING_FROM_AREA_PREFIX}${a.id}`, label: a.name } : null
      })
      .filter(Boolean)
  }))
)

const shippingPayerOptions = [
  { label: '送料込み(出品者负担)', value: 'seller' },
  { label: '着払い(购买者负担)', value: 'buyer' }
]
const shippingMethodOptions = [
  { label: '未定', value: 'undecided' },
  { label: 'らくらくメルカリ便', value: 'rakuraku' },
  { label: 'ゆうゆうメルカリ便', value: 'yuuyu' },
  { label: '普通邮便(定形、定形外)', value: 'regular_mail' }
]
const shippingDaysOptions = [
  { label: '1~2天', value: '1_2_days' },
  { label: '2~3天', value: '2_3_days' },
  { label: '4~7天', value: '4_7_days' }
]

function buildShippingFromPath(areaId) {
  if (!areaId) return []
  const regionId = getRegionIdForAreaId(areaId)
  if (!regionId) return []
  return [`${SHIPPING_FROM_REGION_PREFIX}${regionId}`, `${SHIPPING_FROM_AREA_PREFIX}${areaId}`]
}

function meiluAccountOptionLabel(a) {
  const name = (a?.account_name || '').trim() || `ID ${a?.id}`
  const sid = String(a?.seller_id || '').trim()
  const tail = sid ? ` · 卖家 ${sid}` : ''
  const inactive = a?.status === 'disabled' ? '（停用）' : ''
  return `${name}${tail}${inactive}`
}

const listingDefForm = reactive({
  shipping_from_path: [],
  shipping_method: null,
  shipping_payer: null,
  shipping_days: null,
  meilu_account_id: null
})

const listingDefLoading = ref(false)
const listingDefSaving = ref(false)
const meiluAccountOptions = ref([])
const meiluAccountsLoading = ref(false)

function onShippingFromChange(path) {
  const picked = Array.isArray(path) ? path[path.length - 1] : null
  if (!picked || !String(picked).startsWith(SHIPPING_FROM_AREA_PREFIX)) {
    listingDefForm.shipping_from_path = []
  }
}

async function fetchMeiluAccounts() {
  meiluAccountsLoading.value = true
  try {
    const res = await meiluAccountApi.list({ page: 1, page_size: 500 })
    meiluAccountOptions.value = Array.isArray(res?.items) ? res.items : []
  } catch {
    meiluAccountOptions.value = []
  } finally {
    meiluAccountsLoading.value = false
  }
}

function pathToAreaId(path) {
  const picked = Array.isArray(path) ? path[path.length - 1] : null
  if (!picked || !String(picked).startsWith(SHIPPING_FROM_AREA_PREFIX)) return null
  const id = String(picked).slice(SHIPPING_FROM_AREA_PREFIX.length).trim()
  return id || null
}

async function loadListingDefaults() {
  listingDefLoading.value = true
  try {
    await fetchMeiluAccounts()
    const d = await configApi.getListingDefaults()
    const area = normalizeShippingFromSeed(d?.shipping_from_area_id)
    listingDefForm.shipping_from_path = buildShippingFromPath(area)
    listingDefForm.shipping_method = d?.shipping_method ?? null
    listingDefForm.shipping_payer = d?.shipping_payer ?? null
    listingDefForm.shipping_days = d?.shipping_days ?? null
    listingDefForm.meilu_account_id =
      d?.meilu_account_id != null && Number.isFinite(Number(d.meilu_account_id)) && Number(d.meilu_account_id) > 0
        ? Number(d.meilu_account_id)
        : null
  } catch {
    /* 拦截器已提示 */
  } finally {
    listingDefLoading.value = false
  }
}

async function saveListingDefaults() {
  listingDefSaving.value = true
  try {
    const areaId = pathToAreaId(listingDefForm.shipping_from_path)
    await configApi.putListingDefaults({
      shipping_from_area_id: areaId,
      shipping_method: listingDefForm.shipping_method,
      shipping_payer: listingDefForm.shipping_payer,
      shipping_days: listingDefForm.shipping_days,
      meilu_account_id: listingDefForm.meilu_account_id
    })
    ElMessage.success('出品默认值已保存')
    await loadListingDefaults()
  } catch {
    /* 拦截器 */
  } finally {
    listingDefSaving.value = false
  }
}

const users = ref([])
const loading = ref(false)
const restarting = ref(false)

async function confirmRestartSystem() {
  try {
    await ElMessageBox.confirm(
      '将重启 mercari 后端服务（浏览器与 MITM 会一并关闭）。约 10 秒后请刷新页面。是否继续？',
      '重启系统',
      { type: 'warning', confirmButtonText: '确认重启', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  restarting.value = true
  try {
    const res = await systemApi.restart()
    ElMessage.success(res?.message || '系统正在重启，请稍后刷新页面')
  } catch {
    /* 拦截器已提示；进程退出时也可能出现网络错误，仍提示用户稍后刷新 */
  } finally {
    restarting.value = false
  }
}

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

onMounted(async () => {
  await Promise.all([loadUsers(), loadListingDefaults()])
})
</script>

<style scoped>
.search-card {
  margin-bottom: 16px;
  border-radius: 8px;
}
.table-card {
  border-radius: 8px;
  margin-bottom: 16px;
}
.card-title {
  font-weight: 600;
}
.pwd-tip {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 8px;
}
.listing-def-form {
  max-width: 720px;
}
.sys-maint-tip {
  margin: 0 0 16px;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
  max-width: 640px;
}
</style>
