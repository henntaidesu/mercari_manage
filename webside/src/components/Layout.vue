<template>
  <el-container class="layout-container">
    <!-- 移动端遮罩 -->
    <div v-if="isMobile && sidebarOpen" class="mobile-mask" @click="sidebarOpen = false" />

    <!-- 侧边栏 -->
    <el-aside
      :width="sidebarOpen ? '220px' : (isMobile ? '0px' : '64px')"
      class="sidebar"
      :class="{ 'sidebar-mobile': isMobile, 'sidebar-open': sidebarOpen }"
    >
      <div class="logo-area">
        <img
          class="logo-image"
          src="data:image/png;base64,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"
          alt="mercari 物品管理"
        />
        <span v-if="sidebarOpen" class="logo-text">物品管理</span>
      </div>
      <el-menu
        :default-active="$route.path"
        :collapse="!sidebarOpen && !isMobile"
        router
        background-color="#001529"
        text-color="#a6adb4"
        active-text-color="#ffffff"
        @select="isMobile && (sidebarOpen = false)"
      >
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主体区域 -->
    <el-container direction="vertical" class="main-wrapper">
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="header-left">
          <el-button text @click="sidebarOpen = !sidebarOpen" class="toggle-btn">
            <el-icon size="20"><Expand v-if="!sidebarOpen" /><Fold v-else /></el-icon>
          </el-button>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-tag size="small" effect="plain">{{ userName }}</el-tag>
          <el-tag type="success" size="small" effect="light">
            <el-icon><CircleCheck /></el-icon> 系统正常
          </el-tag>
          <el-button text type="danger" @click="handleLogout">退出</el-button>
        </div>
      </el-header>

      <!-- 内容区域 -->
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const sidebarOpen = ref(true)
const isMobile = ref(false)
const userName = computed(() => {
  try {
    const u = JSON.parse(localStorage.getItem('auth_user') || '{}')
    return u.display_name || u.username || '用户'
  } catch {
    return '用户'
  }
})

const menuItems = [
  { path: '/dashboard', title: '控制台', icon: 'Odometer' },
  { path: '/inventory', title: '库存管理', icon: 'Goods' },
  { path: '/transactions', title: '出入库记录', icon: 'List' },
  { path: '/cost-records', title: '成本记录', icon: 'Money' },
  { path: '/orders', title: '订单管理', icon: 'Tickets' },
  { path: '/meilu-accounts', title: '煤炉账号管理', icon: 'User' },
  { path: '/warehouses', title: '仓库管理', icon: 'OfficeBuilding' },
  { path: '/categories', title: '游戏分类', icon: 'Collection' },
  { path: '/system', title: '系统管理', icon: 'Setting' }
]

const currentTitle = computed(() => {
  const item = menuItems.find((m) => route.path.startsWith(m.path))
  return item?.title || '首页'
})

const checkMobile = () => {
  isMobile.value = window.innerWidth < 768
  if (isMobile.value) sidebarOpen.value = false
  else sidebarOpen.value = true
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})
onUnmounted(() => window.removeEventListener('resize', checkMobile))

const handleLogout = async () => {
  await ElMessageBox.confirm('确认退出当前账号？', '提示', {
    type: 'warning',
    confirmButtonText: '退出',
    cancelButtonText: '取消'
  })
  localStorage.removeItem('auth_token')
  localStorage.removeItem('auth_user')
  router.replace('/login')
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
  overflow: hidden;
  position: relative;
}

.mobile-mask {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  z-index: 99;
}

.sidebar {
  background: #0f1728;
  transition: width 0.25s ease;
  overflow: hidden;
  flex-shrink: 0;
  z-index: 100;
}

.sidebar-mobile {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: 0 !important;
}
.sidebar-mobile.sidebar-open {
  width: 220px !important;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 18px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  white-space: nowrap;
  overflow: hidden;
}

.logo-image {
  width: 80px;
  height: 80px;
  object-fit: contain;
  flex-shrink: 0;
}

.logo-text {
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

:deep(.el-menu) {
  border-right: none;
}

:deep(.el-menu-item.is-active) {
  background-color: #1890ff !important;
  border-radius: 6px;
  margin: 2px 8px;
  width: calc(100% - 16px);
}

:deep(.el-menu-item) {
  border-radius: 6px;
  margin: 2px 8px;
  width: calc(100% - 16px);
}

:deep(.el-menu--collapse .el-menu-item) {
  margin: 2px 4px;
  width: calc(100% - 8px);
}

.main-wrapper {
  flex: 1;
  overflow: hidden;
  min-width: 0;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: #121b2e;
  border-bottom: 1px solid #253149;
  box-shadow: 0 1px 6px rgba(0,0,0,0.25);
  height: 56px !important;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toggle-btn {
  padding: 6px !important;
}

.main-content {
  overflow-y: auto;
  background: #0b1220;
  padding: 20px;
}

@media (max-width: 767px) {
  .main-content {
    padding: 12px;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
