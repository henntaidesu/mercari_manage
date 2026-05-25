<template>
  <el-container class="layout-container" direction="horizontal" :class="{ 'layout--mobile': isMobile }">
    <!-- 手机：遮罩 / 菜单按钮挂到 body，避免父级 transform 导致 fixed 失效、被内容盖住 -->
    <Teleport to="body">
      <div
        v-if="isMobile && mobileDrawerOpen"
        class="layout-mobile-mask"
        @click="mobileDrawerOpen = false"
      />
    </Teleport>
    <Teleport to="body">
      <button
        v-if="isMobile && !mobileDrawerOpen"
        type="button"
        class="layout-mobile-fab"
        aria-label="打开菜单"
        aria-expanded="false"
        @click="mobileDrawerOpen = true"
      >
        <el-icon :size="22"><Menu /></el-icon>
      </button>
    </Teleport>

    <!-- 主侧边栏（一级菜单） -->
    <Teleport to="body" :disabled="!isMobile">
      <el-aside
        width="220px"
        class="sidebar"
        :class="{
          'sidebar--mobile': isMobile,
          'sidebar--drawer-open': isMobile && mobileDrawerOpen,
        }"
      >
      <div class="sidebar-inner">
        <div class="logo-area">
          <img
            class="logo-image"
            src="/static/mercari.png"
            alt="mercari 订单管理"
          />
          <span class="logo-text">mercari 订单管理</span>
          <el-button
            v-if="isMobile"
            text
            class="sidebar-close-btn"
            @click="mobileDrawerOpen = false"
          >
            <el-icon :size="18"><Close /></el-icon>
          </el-button>
        </div>
        <div class="sidebar-menu-wrap">
          <el-menu
            :default-active="activePrimary"
            :collapse="false"
            background-color="#001529"
            text-color="#a6adb4"
            active-text-color="#ffffff"
            @select="onPrimarySelect"
          >
            <el-menu-item
              v-for="item in menuItems"
              :key="item.path"
              :index="item.path"
              :class="{ 'has-children': !!item.children }"
            >
              <el-icon><component :is="item.icon" /></el-icon>
              <template #title>
                <span class="menu-title">{{ item.title }}</span>
                <el-icon
                  v-if="item.children"
                  class="menu-arrow"
                  :class="{ 'menu-arrow--open': secondaryOpen && activeWithChildren === item.path }"
                >
                  <ArrowRight />
                </el-icon>
              </template>
            </el-menu-item>
          </el-menu>
        </div>
        <div class="sidebar-footer">
          <div class="sidebar-footer-row">
            <div class="sidebar-footer-user" :title="userName">{{ userName }}</div>
            <el-button class="sidebar-logout-btn" type="danger" plain size="small" @click="handleLogout">
              退出
            </el-button>
          </div>
        </div>
      </div>
    </el-aside>
    </Teleport>

    <!-- 二级侧边栏（位于一级右侧；选中后自动收缩） -->
    <transition name="slide-secondary">
      <el-aside
        v-if="secondaryOpen && currentSecondaryItems.length > 0"
        width="200px"
        class="secondary-sidebar"
      >
        <div class="secondary-header">
          <span class="secondary-title">{{ activePrimaryTitle }}</span>
          <el-button text class="secondary-close" @click="closeSecondary">
            <el-icon :size="16"><Close /></el-icon>
          </el-button>
        </div>
        <div class="secondary-menu-wrap">
          <el-menu
            :default-active="$route.path"
            background-color="#0e1830"
            text-color="#a6adb4"
            active-text-color="#ffffff"
            @select="onSecondarySelect"
          >
            <el-menu-item v-for="c in currentSecondaryItems" :key="c.path" :index="c.path">
              <el-icon><component :is="c.icon" /></el-icon>
              <template #title>{{ c.title }}</template>
            </el-menu-item>
          </el-menu>
        </div>
      </el-aside>
    </transition>

    <el-main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </el-main>
  </el-container>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { Menu, Close, ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()

const isMobile = ref(false)
/** 仅手机端：抽屉侧栏是否打开；电脑端忽略 */
const mobileDrawerOpen = ref(false)

/** 二级菜单是否展开 */
const secondaryOpen = ref(false)
/** 当前正在展开二级面板的一级菜单 path（仅对带 children 的一级有意义） */
const activeWithChildren = ref(null)

/** 与库存页等一致：(max-width: 768px) */
let mqMobile = null

function syncMobileFromMedia() {
  if (typeof window === 'undefined' || !mqMobile) return
  const next = mqMobile.matches
  isMobile.value = next
  if (!next) {
    mobileDrawerOpen.value = false
  }
}

onMounted(() => {
  mqMobile = window.matchMedia('(max-width: 768px)')
  syncMobileFromMedia()
  mqMobile.addEventListener('change', syncMobileFromMedia)
})
onUnmounted(() => {
  mqMobile?.removeEventListener('change', syncMobileFromMedia)
})

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
  { path: '/orders', title: '订单管理', icon: 'Tickets' },
  { path: '/on-sale-items', title: '在售商品', icon: 'ShoppingBag' },
  { path: '/todos', title: '待办事项', icon: 'BellFilled' },
  { path: '/notifications', title: '煤炉通知', icon: 'Bell' },
  { path: '/meilu-accounts', title: '煤炉账号', icon: 'User' },
  {
    path: '/system',
    title: '系统管理',
    icon: 'Setting',
    children: [
      { path: '/system', title: '系统总览', icon: 'Setting' },
      { path: '/system/transactions', title: '库存记录', icon: 'List' },
      { path: '/system/cost-records', title: '库存包材', icon: 'Money' },
      { path: '/system/cost-expenses', title: '包材使用记录', icon: 'Wallet' },
      { path: '/system/warehouses', title: '仓库管理', icon: 'OfficeBuilding' },
      { path: '/system/categories', title: '游戏分类', icon: 'Collection' },
      { path: '/system/product-type-category-mappings', title: '商品类型映射', icon: 'Connection' }
    ]
  }
]

/** 当前路由所属的一级菜单 path（用于一级 active 高亮） */
const activePrimary = computed(() => {
  for (const item of menuItems) {
    if (item.children) {
      if (item.children.some(c => c.path === route.path)) return item.path
      if (item.path === route.path) return item.path
    } else if (item.path === route.path) {
      return item.path
    }
  }
  return route.path
})

/** 当前展开的二级菜单项列表 */
const currentSecondaryItems = computed(() => {
  if (!activeWithChildren.value) return []
  const found = menuItems.find(m => m.path === activeWithChildren.value)
  return found?.children || []
})

const activePrimaryTitle = computed(() => {
  const found = menuItems.find(m => m.path === activeWithChildren.value)
  return found?.title || ''
})

function onPrimarySelect(path) {
  const item = menuItems.find(m => m.path === path)
  if (!item) return

  if (item.children) {
    // 一级带 children：切换二级面板展开状态，不跳路由
    if (activeWithChildren.value === path) {
      secondaryOpen.value = !secondaryOpen.value
    } else {
      activeWithChildren.value = path
      secondaryOpen.value = true
    }
  } else {
    // 普通一级菜单：关闭二级，跳转
    secondaryOpen.value = false
    activeWithChildren.value = null
    if (route.path !== path) router.push(path)
    if (isMobile.value) mobileDrawerOpen.value = false
  }
}

function onSecondarySelect(path) {
  if (route.path !== path) router.push(path)
  // 选中二级后自动收缩
  secondaryOpen.value = false
  if (isMobile.value) mobileDrawerOpen.value = false
}

function closeSecondary() {
  secondaryOpen.value = false
}

/** 直接通过 URL 进入二级页时：高亮一级 + 初始化 activeWithChildren（但不展开二级面板） */
watch(
  () => route.path,
  (p) => {
    const owner = menuItems.find(item => item.children && item.children.some(c => c.path === p))
    if (owner) {
      activeWithChildren.value = owner.path
    }
  },
  { immediate: true }
)

const handleLogout = async () => {
  await ElMessageBox.confirm('确认退出当前账号？', '提示', {
    type: 'warning',
    confirmButtonText: '退出',
    cancelButtonText: '取消',
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
}

.sidebar {
  background: #0f1728;
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* 二级侧边栏：位于主侧边栏右侧，深色稍浅，with 200px */
.secondary-sidebar {
  background: #0e1830;
  border-left: 1px solid rgba(255, 255, 255, 0.06);
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.secondary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  color: #b8c4d0;
  font-size: 14px;
  font-weight: 600;
}

.secondary-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.secondary-close {
  color: #a6adb4 !important;
  padding: 4px !important;
  flex-shrink: 0;
}

.secondary-menu-wrap {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

/* 二级菜单滑入/滑出动画 */
.slide-secondary-enter-active,
.slide-secondary-leave-active {
  transition: width 0.22s cubic-bezier(0.32, 0.72, 0, 1), opacity 0.18s ease;
}
.slide-secondary-enter-from,
.slide-secondary-leave-to {
  width: 0 !important;
  opacity: 0;
}

/* 手机：抽屉侧栏从左侧滑入 */
.sidebar--mobile {
  position: fixed !important;
  left: 0;
  top: 0;
  bottom: 0;
  width: min(220px, 85vw) !important;
  max-width: 220px;
  z-index: 5010;
  transform: translate3d(-100%, 0, 0);
  transition: transform 0.3s cubic-bezier(0.32, 0.72, 0, 1);
  box-shadow: none;
  will-change: transform;
}

.sidebar--mobile.sidebar--drawer-open {
  transform: translate3d(0, 0, 0);
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.45);
}

.sidebar-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.sidebar-menu-wrap {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-footer {
  flex-shrink: 0;
  padding: 12px 14px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.sidebar-footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
}

.sidebar-footer-user {
  flex: 1;
  min-width: 0;
  font-size: 12px;
  color: #9ba8bf;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-logout-btn {
  flex-shrink: 0;
  margin: 0 !important;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  white-space: nowrap;
  overflow: hidden;
}

.logo-image {
  width: 40px;
  height: 40px;
  object-fit: contain;
  flex-shrink: 0;
}

.logo-text {
  flex: 1;
  min-width: 0;
  color: #b8c4d0;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.5px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-close-btn {
  flex-shrink: 0;
  color: #a6adb4 !important;
  padding: 4px !important;
  margin-left: auto;
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

/* 一级菜单中带 children 的项：在 title 右侧显示箭头 */
:deep(.el-menu-item.has-children .el-tooltip__trigger),
:deep(.el-menu-item.has-children) {
  position: relative;
}

.menu-title {
  flex: 1;
  min-width: 0;
}

.menu-arrow {
  margin-left: auto;
  font-size: 12px;
  transition: transform 0.2s ease;
  color: #9ba8bf;
}

.menu-arrow--open {
  transform: rotate(90deg);
}

.main-content {
  flex: 1;
  overflow-y: auto;
  background: #0b1220;
  padding: 20px;
  min-width: 0;
}

@media (max-width: 767px) {
  .main-content {
    padding: 12px;
    padding-top: 56px;
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

<!-- Teleport 到 body，不能用 scoped，单独挂类名 -->
<style>
.layout-mobile-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 5000;
}
.layout-mobile-fab {
  position: fixed;
  left: max(12px, env(safe-area-inset-left, 0px));
  top: max(12px, env(safe-area-inset-top, 0px));
  z-index: 5020;
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: #121b2e;
  border: 1px solid #253149;
  color: #ecf2ff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.45);
  padding: 0;
}
.layout-mobile-fab:active {
  opacity: 0.92;
}
</style>
