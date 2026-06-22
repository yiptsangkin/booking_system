<template>
  <section class="checkout-panel">
    <div class="toolbar">
      <h1>下单页</h1>
      <strong>合计 ¥{{ cart.totalPrice.toFixed(2) }}</strong>
    </div>
    <div class="cart-list">
      <div v-for="item in cart.items" :key="item.product.id" class="cart-item">
        <div>
          <strong>{{ item.product.name }}</strong>
          <div class="muted">色号 {{ item.product.color }} · ¥{{ item.product.price }}</div>
        </div>
        <div class="nav-links">
          <input
            class="qty-input"
            type="number"
            min="1"
            :max="item.product.stock"
            :value="item.quantity"
            @input="cart.update(item.product.id, Number($event.target.value || 1))"
          />
          <button class="danger" @click="cart.remove(item.product.id)">删除</button>
        </div>
      </div>
    </div>
    <div v-if="cart.items.length === 0" class="empty">购物车为空</div>
    <form v-else class="form-grid" @submit.prevent="submit">
      <div v-if="invalidItems.length" class="alert">
        库存不足：{{ invalidItems.map((item) => `${item.product.name} 当前库存 ${item.product.stock}`).join('；') }}
      </div>
      <label>
        收货人
        <input v-model="form.receiver_name" required />
      </label>
      <label>
        联系电话
        <input v-model="form.receiver_phone" required />
      </label>
      <label>
        收货地址
        <textarea v-model="form.shipping_address" rows="3" required />
      </label>
      <div v-if="error" class="alert">{{ error }}</div>
      <button class="primary" type="submit" :disabled="loading || !canSubmit">
        {{ loading ? '提交中...' : '提交订单' }}
      </button>
    </form>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, apiError } from '../api/client'
import { useCartStore } from '../stores/cart'

const router = useRouter()
const cart = useCartStore()
const loading = ref(false)
const error = ref('')
const form = reactive({
  receiver_name: '',
  receiver_phone: '',
  shipping_address: ''
})
const invalidItems = computed(() =>
  cart.items.filter((item) => {
    const stock = Number(item.product.stock) || 0
    return stock <= 0 || item.quantity > stock
  })
)
const canSubmit = computed(() => cart.items.length > 0 && invalidItems.value.length === 0)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await refreshCartProducts()
    if (!canSubmit.value) {
      error.value = '请先调整超出库存的商品数量'
      return
    }
    const payload = {
      receiver_name: form.receiver_name.trim(),
      receiver_phone: form.receiver_phone.trim(),
      shipping_address: form.shipping_address.trim(),
      items: cart.items.map((item) => ({ product_id: item.product.id, quantity: item.quantity }))
    }
    const { data } = await api.post('/orders', payload)
    cart.clear()
    router.push(`/orders/${data.order_no}`)
  } catch (err) {
    error.value = apiError(err)
  } finally {
    loading.value = false
  }
}

async function refreshCartProducts() {
  const { data } = await api.get('/products')
  const productMap = new Map(data.map((product) => [product.id, product]))
  cart.items.forEach((item) => {
    item.product = productMap.get(item.product.id) || { ...item.product, stock: 0 }
  })
  cart.persist()
}
</script>

<style scoped>
.qty-input {
  width: 88px;
}
</style>
