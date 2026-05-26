<template>
  <div class="login-page">
    <div class="login-lang-switcher">
      <el-select v-model="locale" size="small" @change="onLocaleChange">
        <el-option
          v-for="lang in localeOptions"
          :key="lang.value"
          :label="lang.label"
          :value="lang.value"
        />
      </el-select>
    </div>
    <el-card class="login-card" shadow="hover">
      <template #header>
        <div class="title-wrap">
          <el-icon size="26"><UserFilled /></el-icon>
          <span>{{ t('login.title') }}</span>
        </div>
      </template>

      <el-form ref="formRef" :model="form" :rules="rules" @keyup.enter="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="form.username" :placeholder="t('login.usernamePlaceholder')" size="large" clearable />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" :placeholder="t('login.passwordPlaceholder')" size="large" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" style="width: 100%" @click="handleLogin">
            {{ t('login.login') }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="tip">{{ t('login.defaultAccount') }}</div>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { authApi } from '@/api'
import { setLocale, SUPPORTED_LOCALES } from '@/i18n'

const router = useRouter()
const formRef = ref()
const loading = ref(false)
const form = reactive({
  username: '',
  password: ''
})
const { t, locale } = useI18n()

const localeOptions = computed(() => SUPPORTED_LOCALES.map(code => ({
  value: code,
  label: t(`lang.${code}`),
})))

function onLocaleChange(val) {
  setLocale(val)
}

const rules = computed(() => ({
  username: [{ required: true, message: t('login.usernameRequired'), trigger: 'blur' }],
  password: [{ required: true, message: t('login.passwordRequired'), trigger: 'blur' }]
}))

const handleLogin = async () => {
  await formRef.value?.validate()
  loading.value = true
  try {
    const res = await authApi.login(form)
    localStorage.setItem('auth_token', res.token)
    localStorage.setItem('auth_user', JSON.stringify(res.user))
    ElMessage.success(t('login.success'))
    router.replace('/dashboard')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at top, #1f2a44 0%, #0b1220 55%);
  padding: 16px;
  position: relative;
}

.login-lang-switcher {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 140px;
}

.login-card {
  width: 100%;
  max-width: 380px;
  border: 1px solid #2a3446;
}

.title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: #b8c4d0;
}

.tip {
  font-size: 12px;
  color: #94a3b8;
  text-align: center;
}
</style>
