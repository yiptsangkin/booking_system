import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import Login from '../views/Login.vue'
import Products from '../views/Products.vue'
import Checkout from '../views/Checkout.vue'
import Orders from '../views/Orders.vue'
import OrderDetail from '../views/OrderDetail.vue'
import Inventory from '../views/Inventory.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/products' },
    { path: '/login', component: Login },
    { path: '/products', component: Products, meta: { auth: true } },
    { path: '/checkout', component: Checkout, meta: { auth: true } },
    { path: '/orders', component: Orders, meta: { auth: true } },
    { path: '/orders/:orderNo', component: OrderDetail, meta: { auth: true } },
    { path: '/inventory', component: Inventory, meta: { auth: true, admin: true } }
  ]
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.auth && !auth.token) return '/login'
  if (to.meta.admin && auth.user?.role !== 'admin') return '/products'
  if (to.path === '/login' && auth.token) return '/products'
})

export default router
