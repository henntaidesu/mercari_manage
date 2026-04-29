import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('@/components/Layout.vue'),
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '控制台', icon: 'Odometer' } },
      { path: 'products', name: 'Products', component: () => import('@/views/Products.vue'), meta: { title: '商品管理', icon: 'Goods' } },
      { path: 'inventory', name: 'Inventory', component: () => import('@/views/Inventory.vue'), meta: { title: '库存管理', icon: 'Box' } },
      { path: 'transactions', name: 'Transactions', component: () => import('@/views/Transactions.vue'), meta: { title: '出入库记录', icon: 'List' } },
      { path: 'warehouses', name: 'Warehouses', component: () => import('@/views/Warehouses.vue'), meta: { title: '仓库管理', icon: 'OfficeBuilding' } },
      { path: 'categories', name: 'Categories', component: () => import('@/views/Categories.vue'), meta: { title: '分类管理', icon: 'Collection' } }
    ]
  }
]

export default createRouter({
  history: createWebHashHistory(),
  routes
})
