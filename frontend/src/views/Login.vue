<template>
  <section class="login-wrap">
    <form class="login-panel form-grid" @submit.prevent="submit">
      <h1>经销商登录</h1>
      <label>
        邮箱
        <input v-model="form.email" autocomplete="username" />
      </label>
      <label>
        密码
        <input v-model="form.password" type="password" autocomplete="current-password" />
      </label>
      <div v-if="error" class="alert">{{ error }}</div>
      <button class="primary full-button" type="submit" :disabled="loading">
        {{ loading ? '登录中...' : '登录' }}
      </button>
    </form>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiError } from '../api/client'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const error = ref('')
const form = reactive({
  email: '',
  password: ''
})

async function submit() {
  loading.value = true
  error.value = ''
  try {
    await auth.login(form.email, form.password)
    router.push('/products')
  } catch (err) {
    error.value = apiError(err)
  } finally {
    loading.value = false
  }
}
</script>
