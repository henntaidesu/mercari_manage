<template>
  <div>
    <el-card shadow="never" class="search-card">
      <div class="sys-top-actions">
        <el-button type="danger" :loading="restarting" @click="confirmRestartSystem">
          <el-icon><RefreshRight /></el-icon> {{ t('system.restartSystem') }}
        </el-button>
        <el-button type="primary" @click="openUserDialog">
          <el-icon><Plus /></el-icon> {{ t('system.addUser') }}
        </el-button>
      </div>
    </el-card>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="14">
        <el-card shadow="never" class="table-card">
          <template #header>
            <div class="card-title">{{ t('system.userList') }}</div>
          </template>
          <el-table :data="users" v-loading="loading" stripe>
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="username" :label="t('system.username')" min-width="120" />
            <el-table-column prop="display_name" :label="t('system.displayName')" min-width="140" />
            <el-table-column :label="t('common.status')" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
                  {{ row.is_active ? t('common.enabled') : t('common.disabled') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="last_login_at" :label="t('system.lastLoginAt')" min-width="160" />
            <el-table-column prop="created_at" :label="t('common.createdAt')" min-width="160" />
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="10">
        <el-card shadow="never" class="table-card">
          <template #header>
            <div class="card-title">{{ t('system.changeMyPassword') }}</div>
          </template>
          <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="90px">
            <el-form-item :label="t('system.oldPassword')" prop="old_password">
              <el-input v-model="pwdForm.old_password" type="password" show-password />
            </el-form-item>
            <el-form-item :label="t('system.newPassword')" prop="new_password">
              <el-input v-model="pwdForm.new_password" type="password" show-password />
            </el-form-item>
            <el-form-item :label="t('system.confirmPassword')" prop="confirm_password">
              <el-input v-model="pwdForm.confirm_password" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="pwdSubmitting" @click="submitPassword">{{ t('system.changePassword') }}</el-button>
            </el-form-item>
          </el-form>
          <div class="pwd-tip">{{ t('system.pwdTip') }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="search-card">
      <template #header>
        <div class="card-title">{{ t('system.listingDefaults') }}</div>
      </template>
      <el-form label-width="132px" class="listing-def-form">
        <el-form-item :label="t('system.defaultShippingFrom')">
          <el-cascader
            v-model="listingDefForm.shipping_from_path"
            :options="shippingFromCascaderOptions"
            :props="shippingFromCascaderProps"
            :show-all-levels="false"
            filterable
            clearable
            :placeholder="t('system.shippingFromPlaceholder')"
            style="width: 100%; max-width: 520px"
            popper-class="product-type-cascader-popper"
            @change="onShippingFromChange"
          />
        </el-form-item>
        <el-form-item :label="t('system.defaultShippingMethod')">
          <el-select
            v-model="listingDefForm.shipping_method"
            clearable
            :placeholder="t('system.shippingMethodPlaceholder')"
            style="width: 100%; max-width: 360px"
          >
            <el-option v-for="s in shippingMethodOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('system.defaultShippingPayer')">
          <el-select v-model="listingDefForm.shipping_payer" clearable style="width: 100%; max-width: 360px">
            <el-option v-for="s in shippingPayerOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('system.defaultShippingDays')">
          <el-select v-model="listingDefForm.shipping_days" clearable style="width: 100%; max-width: 280px">
            <el-option v-for="s in shippingDaysOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('system.defaultListingAccount')">
          <el-select
            v-model="listingDefForm.mercari_account_id"
            clearable
            filterable
            :placeholder="t('system.listingAccountPlaceholder')"
            style="width: 100%; max-width: 420px"
            :loading="mercariAccountsLoading"
          >
            <el-option
              v-for="a in mercariAccountOptions"
              :key="a.id"
              :label="mercariAccountOptionLabel(a)"
              :value="a.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="listingDefSaving" @click="saveListingDefaults">{{ t('system.saveListingDefaults') }}</el-button>
          <el-button :loading="listingDefLoading" @click="loadListingDefaults">{{ t('system.reload') }}</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-dialog v-model="userDialogVisible" :title="t('system.addUser')" width="420px" destroy-on-close>
      <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="90px">
        <el-form-item :label="t('system.username')" prop="username">
          <el-input v-model="userForm.username" />
        </el-form-item>
        <el-form-item :label="t('system.displayName')">
          <el-input v-model="userForm.display_name" />
        </el-form-item>
        <el-form-item :label="t('system.password')" prop="password">
          <el-input v-model="userForm.password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="userSubmitting" @click="submitUser">{{ t('common.create') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, RefreshRight } from '@element-plus/icons-vue'
import { authApi, configApi, mercariAccountApi, systemApi } from '@/api/index.js'
import {
  MERCARI_AREAS,
  JP_REGION_OPTIONS,
  getRegionIdForAreaId,
  normalizeShippingFromSeed
} from '@/constants/mercariJapanAreas.js'

const { t } = useI18n()

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

const shippingPayerOptions = computed(() => [
  { label: t('system.shippingPayerSeller'), value: 'seller' },
  { label: t('system.shippingPayerBuyer'), value: 'buyer' }
])
const shippingMethodOptions = computed(() => [
  { label: t('system.shippingMethodUndecided'), value: 'undecided' },
  { label: 'らくらくメルカリ便', value: 'rakuraku' },
  { label: 'ゆうゆうメルカリ便', value: 'yuuyu' },
  { label: t('system.shippingMethodRegularMail'), value: 'regular_mail' }
])
const shippingDaysOptions = computed(() => [
  { label: t('system.shippingDays12'), value: '1_2_days' },
  { label: t('system.shippingDays23'), value: '2_3_days' },
  { label: t('system.shippingDays47'), value: '4_7_days' }
])

function buildShippingFromPath(areaId) {
  if (!areaId) return []
  const regionId = getRegionIdForAreaId(areaId)
  if (!regionId) return []
  return [`${SHIPPING_FROM_REGION_PREFIX}${regionId}`, `${SHIPPING_FROM_AREA_PREFIX}${areaId}`]
}

function mercariAccountOptionLabel(a) {
  const name = (a?.account_name || '').trim() || `ID ${a?.id}`
  const sid = String(a?.seller_id || '').trim()
  const tail = sid ? ` · ${t('system.seller')} ${sid}` : ''
  const inactive = a?.status === 'disabled' ? `（${t('system.inactive')}）` : ''
  return `${name}${tail}${inactive}`
}

const listingDefForm = reactive({
  shipping_from_path: [],
  shipping_method: null,
  shipping_payer: null,
  shipping_days: null,
  mercari_account_id: null
})

const listingDefLoading = ref(false)
const listingDefSaving = ref(false)
const mercariAccountOptions = ref([])
const mercariAccountsLoading = ref(false)

function onShippingFromChange(path) {
  const picked = Array.isArray(path) ? path[path.length - 1] : null
  if (!picked || !String(picked).startsWith(SHIPPING_FROM_AREA_PREFIX)) {
    listingDefForm.shipping_from_path = []
  }
}

async function fetchMercariAccounts() {
  mercariAccountsLoading.value = true
  try {
    const res = await mercariAccountApi.list({ page: 1, page_size: 500 })
    mercariAccountOptions.value = Array.isArray(res?.items) ? res.items : []
  } catch {
    mercariAccountOptions.value = []
  } finally {
    mercariAccountsLoading.value = false
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
    await fetchMercariAccounts()
    const d = await configApi.getListingDefaults()
    const area = normalizeShippingFromSeed(d?.shipping_from_area_id)
    listingDefForm.shipping_from_path = buildShippingFromPath(area)
    listingDefForm.shipping_method = d?.shipping_method ?? null
    listingDefForm.shipping_payer = d?.shipping_payer ?? null
    listingDefForm.shipping_days = d?.shipping_days ?? null
    listingDefForm.mercari_account_id =
      d?.mercari_account_id != null && Number.isFinite(Number(d.mercari_account_id)) && Number(d.mercari_account_id) > 0
        ? Number(d.mercari_account_id)
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
      mercari_account_id: listingDefForm.mercari_account_id
    })
    ElMessage.success(t('system.listingDefaultsSaved'))
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
      t('system.restartConfirmMsg'),
      t('system.restartSystem'),
      { type: 'warning', confirmButtonText: t('system.confirmRestart'), cancelButtonText: t('common.cancel') }
    )
  } catch {
    return
  }
  restarting.value = true
  try {
    const res = await systemApi.restart()
    ElMessage.success(res?.message || t('system.restartingMsg'))
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
  username: [{ required: true, message: t('login.usernameRequired'), trigger: 'blur' }],
  password: [{ required: true, message: t('login.passwordRequired'), trigger: 'blur' }, { min: 6, message: t('system.passwordMin6'), trigger: 'blur' }]
}

const pwdSubmitting = ref(false)
const pwdFormRef = ref()
const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})
const pwdRules = {
  old_password: [{ required: true, message: t('system.oldPasswordRequired'), trigger: 'blur' }],
  new_password: [{ required: true, message: t('system.newPasswordRequired'), trigger: 'blur' }, { min: 6, message: t('system.newPasswordMin6'), trigger: 'blur' }],
  confirm_password: [
    { required: true, message: t('system.confirmPasswordRequired'), trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== pwdForm.new_password) callback(new Error(t('validation.passwordMismatch')))
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
    ElMessage.success(t('system.userCreatedSuccess'))
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
    ElMessage.success(t('system.passwordChangedSuccess'))
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
.sys-top-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  flex-wrap: nowrap;
  gap: 12px;
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
</style>
