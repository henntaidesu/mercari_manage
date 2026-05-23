import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true, title: '登录' }
  },
  {
    path: '/',
    component: () => import('@/components/Layout.vue'),
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '控制台', icon: 'Odometer' } },
      { path: 'inventory', name: 'Inventory', component: () => import('@/views/Inventory.vue'), meta: { title: '库存管理', icon: 'Goods' } },
      { path: 'orders', name: 'Orders', component: () => import('@/views/Orders.vue'), meta: { title: '订单管理', icon: 'Tickets' } },
      { path: 'on-sale-items', name: 'OnSaleItems', component: () => import('@/views/OnSaleItems.vue'), meta: { title: '在售商品', icon: 'ShoppingBag' } },
      { path: 'meilu-accounts', name: 'MeiluAccounts', component: () => import('@/views/MeiluAccounts.vue'), meta: { title: '煤炉账号', icon: 'User' } },
      // 系统管理（一级，二级菜单由 Layout 侧边栏右侧弹出，URL 嵌套到 /system/*）
      { path: 'system', name: 'System', component: () => import('@/views/system/System.vue'), meta: { title: '系统总览', icon: 'Setting' } },
      { path: 'system/transactions', name: 'Transactions', component: () => import('@/views/system/Transactions.vue'), meta: { title: '库存记录', icon: 'List' } },
      { path: 'system/cost-records', name: 'CostRecords', component: () => import('@/views/system/CostRecords.vue'), meta: { title: '库存包材', icon: 'Money' } },
      { path: 'system/cost-expenses', name: 'CostExpenses', component: () => import('@/views/system/CostExpenses.vue'), meta: { title: '包材使用记录', icon: 'Wallet' } },
      { path: 'system/warehouses', name: 'Warehouses', component: () => import('@/views/system/Warehouses.vue'), meta: { title: '仓库管理', icon: 'OfficeBuilding' } },
      { path: 'system/categories', name: 'Categories', component: () => import('@/views/system/Categories.vue'), meta: { title: '游戏分类', icon: 'Collection' } },
      { path: 'system/product-type-category-mappings', name: 'ProductTypeCategoryMappings', component: () => import('@/views/system/ProductTypeCategoryMappings.vue'), meta: { title: '商品类型映射', icon: 'Connection' } }
    ]
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const isPublic = Boolean(to.meta?.public)
  const token = localStorage.getItem('auth_token')

  if (!isPublic && !token) {
    next('/login')
    return
  }

  if (to.path === '/login' && token) {
    next('/dashboard')
    return
  }

  next()
})

export default router
