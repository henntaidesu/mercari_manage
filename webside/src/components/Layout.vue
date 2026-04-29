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
        <el-icon size="28" color="#409EFF"><Box /></el-icon>
        <span v-if="sidebarOpen" class="logo-text">仓储管理系统</span>
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
          <el-tag type="success" size="small" effect="light">
            <el-icon><CircleCheck /></el-icon> 系统正常
          </el-tag>
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
import { useRoute } from 'vue-router'

const route = useRoute()
const sidebarOpen = ref(true)
const isMobile = ref(false)

const menuItems = [
  { path: '/dashboard', title: '控制台', icon: 'Odometer' },
  { path: '/products', title: '商品管理', icon: 'Goods' },
  { path: '/transactions', title: '出入库记录', icon: 'List' },
  { path: '/warehouses', title: '仓库管理', icon: 'OfficeBuilding' },
  { path: '/categories', title: '分类管理', icon: 'Collection' }
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
