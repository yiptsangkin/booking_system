import { defineStore } from 'pinia'

export const useCartStore = defineStore('cart', {
  state: () => ({
    items: JSON.parse(localStorage.getItem('paint_cart') || '[]')
  }),
  getters: {
    totalQuantity: (state) => state.items.reduce((sum, item) => sum + item.quantity, 0),
    totalPrice: (state) => state.items.reduce((sum, item) => sum + Number(item.product.price) * item.quantity, 0)
  },
  actions: {
    add(product) {
      const stock = Number(product.stock) || 0
      if (stock <= 0) return
      const existing = this.items.find((item) => item.product.id === product.id)
      if (existing) {
        existing.product = product
        existing.quantity = Math.min(existing.quantity + 1, stock)
      } else {
        this.items.push({ product, quantity: 1 })
      }
      this.persist()
    },
    update(productId, quantity) {
      const item = this.items.find((entry) => entry.product.id === productId)
      if (!item) return
      const stock = Math.max(1, Number(item.product.stock) || 1)
      item.quantity = Math.min(Math.max(1, quantity), stock)
      this.persist()
    },
    remove(productId) {
      this.items = this.items.filter((item) => item.product.id !== productId)
      this.persist()
    },
    clear() {
      this.items = []
      this.persist()
    },
    persist() {
      localStorage.setItem('paint_cart', JSON.stringify(this.items))
    }
  }
})
