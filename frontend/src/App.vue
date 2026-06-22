<template>
  <div class="app-shell">
    <AppNav v-if="auth.token" />
    <main class="page">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { useAuthStore } from './stores/auth'
import AppNav from './components/AppNav.vue'

const auth = useAuthStore()
</script>
