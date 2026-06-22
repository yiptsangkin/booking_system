<template>
  <header class="nav">
    <div class="nav-inner">
      <div class="brand">经销商油漆下单系统</div>
      <nav class="nav-links">
        <button class="ghost" @click="$router.push('/products')">商品</button>
        <button class="ghost" @click="$router.push('/checkout')">购物车 {{ cart.totalQuantity }}</button>
        <button class="ghost" @click="$router.push('/orders')">订单</button>
        <button v-if="auth.user?.role === 'admin'" class="ghost" @click="$router.push('/inventory')">库存</button>
        <select class="theme-select" v-model="theme.active" @change="theme.setTheme(theme.active)">
          <option v-for="preset in themePresets" :key="preset.id" :value="preset.id">{{ preset.label }}</option>
        </select>
        <span class="tag">{{ roleLabel }}</span>
        <button class="ghost" @click="logout">退出</button>
      </nav>
    </div>
  </header>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useCartStore } from '../stores/cart'
import { themePresets, useThemeStore } from '../stores/theme'
import { computed } from 'vue'

const router = useRouter()
const auth = useAuthStore()
const cart = useCartStore()
const theme = useThemeStore()
const roleLabel = computed(() => ({ admin: '管理员', dealer: '经销商' }[auth.user?.role] || auth.user?.role || '未登录'))

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.theme-select {
  width: 86px;
  height: 34px;
  min-height: 34px;
  padding-left: 10px;
  font-size: 13px;
}
</style>
