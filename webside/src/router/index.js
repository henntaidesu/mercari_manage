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
      { path: 'inventory', name: 'Inventory', component: () => import('@/views/Products.vue'), meta: { title: '库存管理', icon: 'Goods' } },
      { path: 'transactions', name: 'Transactions', component: () => import('@/views/Transactions.vue'), meta: { title: '出入库记录', icon: 'List' } },
      { path: 'warehouses', name: 'Warehouses', component: () => import('@/views/Warehouses.vue'), meta: { title: '仓库管理', icon: 'OfficeBuilding' } },
      { path: 'categories', name: 'Categories', component: () => import('@/views/Categories.vue'), meta: { title: '分类管理', icon: 'Collection' } },
      { path: 'system', name: 'System', component: () => import('@/views/System.vue'), meta: { title: '系统管理', icon: 'Setting' } }
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
