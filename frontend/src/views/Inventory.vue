<template>
  <section>
    <div class="toolbar">
      <h1>库存管理</h1>
      <button class="primary" @click="openCreateFamily">新增商品款式</button>
    </div>
    <div v-if="error" class="alert">{{ error }}</div>
    <div v-if="loading" class="empty">加载中...</div>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>商品款式</th>
            <th>分类</th>
            <th>色号库存</th>
            <th>总库存</th>
            <th>价格</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in familyRows" :key="row.family.id">
            <td>
              <strong>{{ row.family.name }}</strong>
            </td>
            <td>{{ categoryLabel(row.family.category) }}</td>
            <td>
              <div class="color-chip-list">
                <span v-for="variant in row.variants" :key="variant.id" class="color-chip">
                  <span class="swatch small" :style="{ background: variant.color_hex }" />
                  {{ variant.color }} {{ variant.stock }}
                </span>
                <span v-if="!row.variants.length" class="muted">未维护色号</span>
              </div>
            </td>
            <td>{{ row.totalStock }}</td>
            <td>{{ row.priceText }}</td>
            <td>
              <button @click="openManageFamily(row.family)">管理色号</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="dialogVisible" class="dialog-backdrop" @click.self="dialogVisible = false">
      <form class="dialog-panel inventory-dialog" @submit.prevent="saveFamilyAndVariants">
        <div class="dialog-heading">
          <div>
            <h2>{{ creatingFamily ? '新增商品款式' : '管理色号' }}</h2>
            <p class="muted">一个商品款式一行，色号在这里集中维护。</p>
          </div>
          <button class="primary" type="button" @click="addVariant">新增色号</button>
        </div>

        <div class="family-card">
          <label>
            商品款式
            <input v-model.trim="familyForm.name" :disabled="!creatingFamily" required />
          </label>
          <label>
            分类
            <select v-model="familyForm.category" :disabled="!creatingFamily">
              <option value="interior">内墙</option>
              <option value="exterior">外墙</option>
              <option value="industrial">工业</option>
            </select>
          </label>
        </div>

        <div class="variant-grid">
          <div v-for="(variant, index) in variantDrafts" :key="variant.localId" class="variant-card">
            <div class="variant-preview">
              <label class="paint-picker" :style="{ background: variant.color_hex }">
                <input v-model="variant.color_hex" type="color" required />
              </label>
              <div>
                <span class="muted">色号 {{ index + 1 }}</span>
                <input v-model.trim="variant.color" list="color-options" placeholder="例如：象牙白" @change="applyKnownColor(variant)" required />
              </div>
            </div>
            <div class="variant-fields">
              <label>
                价格
                <input v-model.number="variant.price" type="number" min="0" step="0.01" required />
              </label>
              <label>
                库存
                <input v-model.number="variant.stock" type="number" min="0" required />
              </label>
            </div>
          </div>
        </div>

        <datalist id="color-options">
          <option v-for="option in colorOptions" :key="option.name" :value="option.name" />
        </datalist>

        <div class="dialog-footer">
          <button type="button" @click="dialogVisible = false">取消</button>
          <button class="primary" type="submit" :disabled="saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api, apiError } from '../api/client'

const products = ref([])
const families = ref([])
const colorOptions = ref([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const dialogVisible = ref(false)
const creatingFamily = ref(false)
const activeFamilyId = ref(null)
const familyForm = reactive({
  name: '',
  category: 'interior'
})
const variantDrafts = ref([])
const familyRows = computed(() =>
  families.value.map((family) => {
    const variants = products.value
      .filter((product) => product.family_id === family.id)
      .sort((a, b) => a.color.localeCompare(b.color, 'zh-Hans-CN'))
    return {
      family,
      variants,
      totalStock: variants.reduce((sum, variant) => sum + Number(variant.stock || 0), 0),
      priceText: priceRange(variants)
    }
  })
)

function categoryLabel(value) {
  return { interior: '内墙', exterior: '外墙', industrial: '工业' }[value] || value
}

function priceRange(variants) {
  if (!variants.length) return '-'
  const prices = variants.map((variant) => Number(variant.price))
  const min = Math.min(...prices).toFixed(2)
  const max = Math.max(...prices).toFixed(2)
  return min === max ? `¥${min}` : `¥${min} - ¥${max}`
}

function openCreateFamily() {
  creatingFamily.value = true
  activeFamilyId.value = null
  familyForm.name = ''
  familyForm.category = 'interior'
  variantDrafts.value = [newVariantDraft()]
  dialogVisible.value = true
}

function openManageFamily(family) {
  creatingFamily.value = false
  activeFamilyId.value = family.id
  familyForm.name = family.name
  familyForm.category = family.category
  const variants = products.value.filter((product) => product.family_id === family.id)
  variantDrafts.value = variants.length ? variants.map(toDraft) : [newVariantDraft()]
  dialogVisible.value = true
}

function newVariantDraft() {
  return {
    localId: `new-${Date.now()}-${Math.random()}`,
    id: null,
    color: '',
    color_hex: '#d5dde2',
    price: 0,
    stock: 0
  }
}

function toDraft(product) {
  return {
    localId: `sku-${product.id}`,
    id: product.id,
    color: product.color,
    color_hex: product.color_hex || '#d5dde2',
    price: Number(product.price),
    stock: product.stock
  }
}

function addVariant() {
  variantDrafts.value.push(newVariantDraft())
}

function applyKnownColor(variant) {
  const option = colorOptions.value.find((item) => item.name === variant.color)
  if (option) {
    variant.color_hex = option.hex
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [productRes, familyRes, colorRes] = await Promise.all([
      api.get('/products'),
      api.get('/products/families'),
      api.get('/products/colors')
    ])
    products.value = productRes.data
    families.value = familyRes.data
    colorOptions.value = colorRes.data
  } catch (err) {
    error.value = apiError(err)
  } finally {
    loading.value = false
  }
}

async function saveFamilyAndVariants() {
  error.value = ''
  const drafts = variantDrafts.value.filter((variant) => variant.color)
  if (!familyForm.name) {
    error.value = '请输入商品款式名称'
    return
  }
  if (!drafts.length) {
    error.value = '至少维护一个色号'
    return
  }
  saving.value = true
  try {
    let family = families.value.find((item) => item.id === activeFamilyId.value)
    if (creatingFamily.value) {
      const { data } = await api.post('/products/families', { ...familyForm })
      family = data
    }
    for (const variant of drafts) {
      const payload = {
        family_id: family.id,
        name: family.name,
        category: family.category,
        color: variant.color,
        color_hex: variant.color_hex,
        price: variant.price,
        stock: variant.stock
      }
      if (variant.id) {
        await api.patch(`/products/${variant.id}`, payload)
      } else {
        await api.post('/products', payload)
      }
    }
    dialogVisible.value = false
    await load()
  } catch (err) {
    error.value = apiError(err)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.color-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-width: 520px;
}

.color-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  padding: 0 9px;
  border: 1px solid var(--border-soft);
  border-radius: 999px;
  background: var(--surface-soft);
  white-space: nowrap;
}

.swatch.small {
  width: 18px;
  height: 18px;
  flex: 0 0 18px;
}

.inventory-dialog {
  width: min(860px, 100%);
  display: grid;
  gap: 16px;
}

.dialog-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.dialog-heading h2 {
  margin: 0 0 4px;
}

.family-card {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(160px, 0.6fr);
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: var(--surface-soft);
}

.variant-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}

.variant-card {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
}

.variant-preview {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr);
  gap: 10px;
  align-items: end;
}

.paint-picker {
  display: block;
  width: 54px;
  height: 54px;
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
}

.paint-picker input {
  width: 80px;
  height: 80px;
  margin: -12px;
  padding: 0;
  border: 0;
  cursor: pointer;
}

.variant-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

@media (max-width: 680px) {
  .family-card,
  .variant-fields {
    grid-template-columns: 1fr;
  }
}
</style>
