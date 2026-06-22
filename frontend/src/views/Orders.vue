<template>
  <section>
    <div class="toolbar">
      <h1>订单列表</h1>
      <button @click="load">刷新</button>
    </div>
    <div v-if="error" class="alert">{{ error }}</div>
    <div v-if="loading" class="empty">加载中...</div>
    <div v-else-if="orders.length === 0" class="empty">暂无订单</div>
    <div v-else class="orders-grid">
      <article v-for="order in orders" :key="order.order_no" class="order-card">
        <div class="order-card-head">
          <div class="order-heading">
            <span class="muted">订单号</span>
            <h2 class="order-title">{{ order.order_no }}</h2>
          </div>
          <span class="tag primary">{{ order.status }}</span>
        </div>
        <div class="order-recipient">
          <div class="recipient-main">
            <strong>{{ order.receiver_name }}</strong>
            <span>{{ order.receiver_phone }}</span>
          </div>
          <span>{{ order.shipping_address }}</span>
        </div>
        <div class="order-meta">
          <strong>¥{{ order.total_price }}</strong>
          <span class="muted">{{ new Date(order.created_at).toLocaleString() }}</span>
        </div>
        <div class="order-actions">
          <button @click="$router.push(`/orders/${order.order_no}`)">详情</button>
          <template v-if="canCreateShipment(order)">
            <select v-model="carrier[order.order_no]" class="carrier-select">
              <option value="sf">顺丰</option>
              <option value="jd">京东</option>
              <option value="yimi">一米滴答</option>
            </select>
            <button class="primary" @click="ship(order)">调用物流</button>
            <button @click="openBind(order)">绑定已有运单</button>
          </template>
        </div>
      </article>
    </div>

    <div v-if="bindDialog" class="dialog-backdrop" @click.self="bindDialog = false">
      <form class="dialog-panel form-grid" @submit.prevent="bindWaybill">
        <h2>绑定已有运单</h2>
        <label>
          订单
          <input :value="bindForm.order_no || ''" disabled />
        </label>
        <label>
          物流公司
          <select v-model="bindForm.carrier">
            <option value="sf">顺丰</option>
            <option value="jd">京东</option>
            <option value="yimi">一米滴答</option>
          </select>
        </label>
        <label>
          运单号
          <input v-model="bindForm.tracking_no" required />
        </label>
        <div class="dialog-footer">
          <button type="button" @click="bindDialog = false">取消</button>
          <button class="primary" type="submit" :disabled="binding">
            {{ binding ? '绑定中...' : '绑定' }}
          </button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api, apiError } from '../api/client'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const orders = ref([])
const loading = ref(false)
const error = ref('')
const carrier = reactive({})
const isAdmin = computed(() => auth.user?.role === 'admin')
const shippableStatuses = new Set(['CREATED', 'ALLOCATED'])
const bindDialog = ref(false)
const binding = ref(false)
const bindForm = reactive({
  order_no: '',
  carrier: 'sf',
  tracking_no: ''
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/orders')
    orders.value = data
    data.forEach((order) => {
      carrier[order.order_no] = carrier[order.order_no] || 'sf'
    })
  } catch (err) {
    error.value = apiError(err)
  } finally {
    loading.value = false
  }
}

async function ship(order) {
  try {
    await api.post('/shipments/create', { order_no: order.order_no, carrier: carrier[order.order_no] })
    await load()
  } catch (err) {
    error.value = apiError(err)
  }
}

function canCreateShipment(order) {
  return isAdmin.value && shippableStatuses.has(order.status_code) && !order.shipments?.length
}

function openBind(order) {
  bindForm.order_no = order.order_no
  bindForm.carrier = carrier[order.order_no] || 'sf'
  bindForm.tracking_no = ''
  bindDialog.value = true
}

async function bindWaybill() {
  bindForm.tracking_no = bindForm.tracking_no.trim()
  if (!bindForm.tracking_no) {
    error.value = '请输入运单号'
    return
  }
  binding.value = true
  error.value = ''
  try {
    await api.post('/shipments/0/bind', { ...bindForm })
    bindDialog.value = false
    await load()
  } catch (err) {
    error.value = apiError(err)
  } finally {
    binding.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.orders-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

.order-card {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.order-card-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}

.order-heading {
  min-width: 0;
}

.order-title {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  color: var(--heading);
  font-size: 16px;
  line-height: 1.25;
  margin: 3px 0 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.order-recipient {
  display: grid;
  gap: 7px;
  min-width: 0;
  padding: 11px 12px;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: var(--surface-soft);
  color: var(--text);
  font-size: 13px;
}

.recipient-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-width: 0;
}

.recipient-main strong {
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recipient-main span {
  flex: 0 0 auto;
  color: var(--text-muted);
}

.order-recipient span {
  color: var(--text-muted);
  overflow-wrap: anywhere;
  line-height: 1.45;
}

.order-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  min-width: 0;
}

.order-meta strong {
  color: var(--heading);
  font-size: 16px;
}

.order-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding-top: 12px;
  border-top: 1px solid var(--border-soft);
}

.order-actions button {
  flex: 0 0 auto;
}

.carrier-select {
  width: 128px;
  flex: 0 0 128px;
  height: var(--control-height);
  min-height: var(--control-height);
}

@media (max-width: 460px) {
  .orders-grid {
    grid-template-columns: 1fr;
  }

  .order-card-head {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .recipient-main {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }

  .order-actions button,
  .carrier-select {
    flex: 1 1 120px;
  }
}
</style>
