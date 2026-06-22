import { defineStore } from 'pinia'
import { api } from '../api/client'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('paint_order_token') || '',
    user: JSON.parse(localStorage.getItem('paint_order_user') || 'null')
  }),
  actions: {
    async login(email, password) {
      const { data } = await api.post('/auth/login', { email, password })
      this.token = data.token
      this.user = data.user
      localStorage.setItem('paint_order_token', data.token)
      localStorage.setItem('paint_order_user', JSON.stringify(data.user))
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('paint_order_token')
      localStorage.removeItem('paint_order_user')
    }
  }
})
