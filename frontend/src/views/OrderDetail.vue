<template>
  <section class="detail-panel">
    <div class="toolbar">
      <h1>订单详情 {{ order?.order_no }}</h1>
      <div class="nav-links">
        <button @click="load">刷新</button>
        <button v-if="auth.user?.role === 'admin' && order?.shipments?.length && order?.status_code !== 'COMPLETED'" @click="syncTracking">同步轨迹</button>
        <button v-if="auth.user?.role === 'dealer' && order?.status_code === 'DELIVERED'" class="primary" @click="complete">确认完成</button>
      </div>
    </div>
    <div v-if="error" class="alert">{{ error }}</div>
    <div v-if="loading" class="empty">加载中...</div>
    <template v-else-if="order">
      <div class="status-track">
        <span v-for="status in statuses" :key="status.code" class="tag" :class="statusType(status)">
          {{ status.label }}
        </span>
      </div>
      <hr class="divider" />
      <h2 class="product-title">商品</h2>
      <div class="cart-list">
        <div v-for="item in order.items" :key="item.id" class="cart-item">
          <div>
            <strong>{{ item.product.name }}</strong>
            <div class="muted">色号 {{ item.product.color }} · 数量 {{ item.quantity }}</div>
          </div>
          <strong>¥{{ item.price }}</strong>
        </div>
      </div>
      <hr class="divider" />
      <div class="toolbar">
        <h2>物流轨迹</h2>
        <div class="shipping-actions">
          <strong>{{ order.shipments?.[0]?.tracking_no || '未生成运单' }}</strong>
          <template v-if="canBindWaybill">
            <select v-model="carrier" class="carrier-select" aria-label="物流公司">
              <option value="sf">顺丰</option>
              <option value="jd">京东</option>
              <option value="yimi">一米滴答</option>
            </select>
            <button class="primary" @click="ship">调用物流</button>
            <button @click="openBind">绑定已有运单</button>
          </template>
        </div>
      </div>
      <div v-if="!order.shipments.length" class="empty">暂无物流单</div>
      <div v-for="shipment in order.shipments" :key="shipment.id" class="shipment-row">
        <div>
          <strong>{{ carrierName(shipment.carrier) }} · {{ shipment.tracking_no }}</strong>
          <div class="timeline">
            <div v-for="event in shipment.events" :key="event.id" class="timeline-item">
              <div>{{ event.status }} {{ event.location }}</div>
              <div class="muted">{{ new Date(event.time).toLocaleString() }}</div>
            </div>
          </div>
        </div>
        <div v-if="shipment.proof">
          <img class="pod-image" :src="shipment.proof.image_url" alt="签收照片" />
          <div class="muted">{{ shipment.proof.gps_location }} · {{ new Date(shipment.proof.signed_at).toLocaleString() }}</div>
        </div>
      </div>
      <template v-if="auth.user?.role === 'admin' && order.shipments?.length && canUpdateLogistics">
        <hr class="divider" />
        <h2 class="product-title">签收回传</h2>
        <form class="pod-form form-grid" @submit.prevent="submitStatus">
          <label>
            轨迹状态
            <select v-model="podForm.status">
              <option value="IN_TRANSIT">运输中</option>
              <option value="DELIVERED">已签收</option>
            </select>
          </label>
          <label>
            位置/GPS
            <input v-model="podForm.location" />
          </label>
          <label>
            POD 图片 OSS URL
            <input v-model="podForm.image_url" placeholder="https://oss.example.com/pod/order.jpg" />
          </label>
          <div class="nav-links">
            <button type="submit">写入轨迹</button>
            <button type="button" class="primary" @click="submitPod">回传签收POD</button>
          </div>
        </form>
      </template>
    </template>

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
import { useRoute } from 'vue-router'
import { api, apiError } from '../api/client'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()
const order = ref(null)
const loading = ref(false)
const error = ref('')
const carrier = ref('sf')
const bindDialog = ref(false)
const binding = ref(false)
const bindForm = reactive({
  order_no: '',
  carrier: 'sf',
  tracking_no: ''
})
const statuses = [
  { code: 'CREATED', label: '已创建' },
  { code: 'ALLOCATED', label: '待发货' },
  { code: 'SHIPPED', label: '已发货' },
  { code: 'IN_TRANSIT', label: '运输中' },
  { code: 'DELIVERED', label: '已签收' },
  { code: 'COMPLETED', label: '已完成' }
]
const activeIndex = computed(() => statuses.findIndex((item) => item.code === order.value?.status_code))
const canUpdateLogistics = computed(() => ['SHIPPED', 'IN_TRANSIT', 'DELIVERED'].includes(order.value?.status_code))
const canBindWaybill = computed(() => auth.user?.role === 'admin' && ['CREATED', 'ALLOCATED'].includes(order.value?.status_code) && !order.value?.shipments?.length)
const podForm = ref({
  status: 'IN_TRANSIT',
  location: '上海分拨中心',
  image_url: ''
})

function statusType(status) {
  const index = statuses.findIndex((item) => item.code === status.code)
  if (index < activeIndex.value) return 'success'
  if (index === activeIndex.value) return 'primary'
  return 'info'
}

function carrierName(code) {
  return { sf: '顺丰', jd: '京东', yimi: '一米滴答' }[code] || code
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get(`/orders/${route.params.orderNo}`)
    order.value = data
  } catch (err) {
    error.value = apiError(err)
  } finally {
    loading.value = false
  }
}

async function ship() {
  if (!order.value) return
  error.value = ''
  try {
    await api.post('/shipments/create', { order_no: order.value.order_no, carrier: carrier.value })
    await load()
  } catch (err) {
    error.value = apiError(err)
  }
}

function openBind() {
  if (!order.value) return
  bindForm.order_no = order.value.order_no
  bindForm.carrier = carrier.value
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
    carrier.value = bindForm.carrier
    bindDialog.value = false
    await load()
  } catch (err) {
    error.value = apiError(err)
  } finally {
    binding.value = false
  }
}

async function syncTracking() {
  error.value = ''
  try {
    await api.get(`/tracking/${order.value.order_no}?sync=true`)
    await load()
  } catch (err) {
    error.value = apiError(err)
  }
}

async function complete() {
  error.value = ''
  try {
    const { data } = await api.post(`/orders/${order.value.order_no}/complete`, { order_no: order.value.order_no })
    order.value = data
  } catch (err) {
    error.value = apiError(err)
  }
}

function firstShipment() {
  return order.value?.shipments?.[0]
}

async function submitStatus() {
  const shipment = firstShipment()
  if (!shipment) return
  error.value = ''
  try {
    await api.post(`/shipments/${shipment.id}/status`, {
      status: podForm.value.status,
      location: podForm.value.location,
      time: new Date().toISOString(),
      raw: { source: 'admin-ui' }
    })
    await load()
  } catch (err) {
    error.value = apiError(err)
  }
}

async function submitPod() {
  const shipment = firstShipment()
  if (!shipment) return
  if (!podForm.value.image_url) {
    error.value = '请输入 POD 图片 OSS URL'
    return
  }
  error.value = ''
  try {
    await api.post(`/shipments/${shipment.id}/pod`, {
      image_url: podForm.value.image_url,
      signed_at: new Date().toISOString(),
      gps_location: podForm.value.location,
      raw: { source: 'admin-ui' }
    })
    await load()
  } catch (err) {
    error.value = apiError(err)
  }
}

onMounted(load)
</script>

<style scoped>
.pod-form {
  max-width: 560px;
}

.shipping-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}

.shipping-actions strong {
  color: var(--heading);
  font-size: 14px;
  overflow-wrap: anywhere;
}

.carrier-select {
  width: 128px;
  flex: 0 0 128px;
  height: var(--control-height);
  min-height: var(--control-height);
}

@media (max-width: 560px) {
  .shipping-actions {
    justify-content: flex-start;
    width: 100%;
  }

  .carrier-select {
    flex: 1 1 140px;
  }
}
</style>
