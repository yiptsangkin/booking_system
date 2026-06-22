<template>
  <section>
    <div class="toolbar">
      <h1>商品页</h1>
      <div class="segmented">
        <button
          v-for="option in categoryOptions"
          :key="option.value"
          :class="{ active: category === option.value }"
          @click="category = option.value"
        >
          {{ option.label }}
        </button>
      </div>
    </div>
    <div v-if="error" class="alert">{{ error }}</div>
    <div v-if="loading" class="empty">加载中...</div>
    <div v-else class="grid product-grid">
      <article v-for="group in filteredProductGroups" :key="group.key" class="product-card">
        <div class="product-head">
          <div>
            <h2 class="product-title">{{ group.name }}</h2>
            <div class="muted">{{ categoryLabel(group.category) }} · {{ group.variants.length }} 个色号</div>
          </div>
          <span class="swatch large" :style="{ background: selectedVariant(group).color_hex }" />
        </div>

        <div class="color-picker" role="radiogroup" :aria-label="`${group.name} 色号`">
          <button
            v-for="variant in group.variants"
            :key="variant.id"
            class="color-option"
            :class="{ active: selectedVariant(group).id === variant.id, soldout: variant.stock <= 0 }"
            type="button"
            role="radio"
            :aria-checked="selectedVariant(group).id === variant.id"
            @click="selectVariant(group.key, variant.id)"
          >
            <span class="swatch" :style="{ background: variant.color_hex }" />
            <span>{{ variant.color }}</span>
          </button>
        </div>

        <div class="selected-color">
          <span class="muted">当前色号</span>
          <strong>{{ selectedVariant(group).color }}</strong>
        </div>
        <div class="price-row">
          <strong>¥{{ selectedVariant(group).price }}</strong>
          <span class="tag" :class="selectedVariant(group).stock > 20 ? 'success' : 'warning'">库存 {{ selectedVariant(group).stock }}</span>
        </div>
        <button
          class="primary full-button product-action"
          :disabled="selectedVariant(group).stock <= cartQuantity(selectedVariant(group).id)"
          @click="cart.add(selectedVariant(group))"
        >
          {{ productActionLabel(selectedVariant(group)) }}
        </button>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api, apiError } from '../api/client'
import { useCartStore } from '../stores/cart'

const cart = useCartStore()
const products = ref([])
const category = ref('all')
const selectedVariants = reactive({})
const loading = ref(false)
const error = ref('')
const categoryOptions = [
  { label: '全部', value: 'all' },
  { label: '内墙', value: 'interior' },
  { label: '外墙', value: 'exterior' },
  { label: '工业', value: 'industrial' }
]

const productGroups = computed(() => {
  const groups = new Map()
  products.value.forEach((product) => {
    const key = product.family_id ? `family-${product.family_id}` : product.family_code
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        familyId: product.family_id,
        name: product.family_name || product.name,
        category: product.family_category || product.category,
        variants: []
      })
    }
    groups.get(key).variants.push(product)
  })
  return [...groups.values()].map((group) => ({
    ...group,
    variants: [...group.variants].sort((a, b) => a.color.localeCompare(b.color, 'zh-Hans-CN'))
  }))
})

const filteredProductGroups = computed(() => {
  if (category.value === 'all') return productGroups.value
  return productGroups.value.filter((group) => group.category === category.value)
})

function categoryLabel(value) {
  return categoryOptions.find((item) => item.value === value)?.label || value
}

function selectedVariant(group) {
  const selectedId = selectedVariants[group.key]
  return group.variants.find((variant) => variant.id === selectedId) || group.variants[0]
}

function selectVariant(groupKey, variantId) {
  selectedVariants[groupKey] = variantId
}

function cartQuantity(productId) {
  return cart.items.find((item) => item.product.id === productId)?.quantity || 0
}

function productActionLabel(product) {
  if (product.stock <= 0) return '暂无库存'
  if (product.stock <= cartQuantity(product.id)) return '库存已加满'
  return '加入购物车'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/products')
    products.value = data
    productGroups.value.forEach((group) => {
      selectedVariants[group.key] = selectedVariants[group.key] || group.variants[0]?.id
    })
  } catch (err) {
    error.value = apiError(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.product-grid {
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
}

.swatch.large {
  width: 34px;
  height: 34px;
  flex-basis: 34px;
}

.color-picker {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 16px;
}

.color-option {
  height: 34px;
  min-height: 34px;
  padding: 0 10px 0 8px;
  border-color: var(--border-soft);
  background: var(--surface-soft);
  font-size: 13px;
}

.color-option.active {
  border-color: var(--primary);
  background: var(--primary-soft);
  color: var(--primary-strong);
}

.color-option.soldout {
  opacity: 0.55;
}

.selected-color {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 36px;
  margin-top: 14px;
  padding: 8px 10px;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: var(--surface-soft);
}

.product-action {
  margin-top: 14px;
}
</style>
