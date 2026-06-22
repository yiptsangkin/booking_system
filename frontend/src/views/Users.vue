<template>
  <section>
    <div class="toolbar">
      <h1>用户与角色</h1>
      <button class="primary" @click="openCreate">新增用户</button>
    </div>

    <div v-if="error" class="alert">{{ error }}</div>
    <div v-if="loading" class="empty">加载中...</div>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>姓名</th>
            <th>邮箱</th>
            <th>角色</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>
              <strong>{{ user.name }}</strong>
            </td>
            <td>{{ user.email }}</td>
            <td>
              <span class="tag" :class="user.role === 'admin' ? 'primary' : 'info'">
                {{ roleLabel(user.role) }}
              </span>
            </td>
            <td>
              <button @click="openEdit(user)">编辑</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="dialogVisible" class="dialog-backdrop" @click.self="dialogVisible = false">
      <form class="dialog-panel user-dialog form-grid" @submit.prevent="saveUser">
        <h2>{{ editingUserId ? '编辑用户' : '新增用户' }}</h2>
        <label>
          姓名
          <input v-model.trim="form.name" required />
        </label>
        <label>
          邮箱
          <input v-model.trim="form.email" autocomplete="off" required />
        </label>
        <label>
          角色
          <select v-model="form.role">
            <option v-for="role in roles" :key="role.code" :value="role.code">
              {{ role.label }}
            </option>
          </select>
        </label>
        <label>
          密码
          <div class="password-field">
            <input
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              autocomplete="new-password"
              :required="!editingUserId"
              :placeholder="editingUserId ? '留空则不修改密码' : ''"
            />
            <button type="button" @click="showPassword = !showPassword">
              {{ showPassword ? '隐藏' : '显示' }}
            </button>
          </div>
        </label>
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
import { onMounted, reactive, ref } from 'vue'
import { api, apiError } from '../api/client'

const users = ref([])
const roles = ref([
  { code: 'admin', label: '管理员' },
  { code: 'dealer', label: '经销商' }
])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const dialogVisible = ref(false)
const editingUserId = ref(null)
const showPassword = ref(false)
const form = reactive({
  name: '',
  email: '',
  role: 'dealer',
  password: ''
})

function roleLabel(role) {
  return roles.value.find((item) => item.code === role)?.label || role
}

function resetForm() {
  form.name = ''
  form.email = ''
  form.role = 'dealer'
  form.password = ''
}

function openCreate() {
  editingUserId.value = null
  resetForm()
  showPassword.value = false
  dialogVisible.value = true
}

function openEdit(user) {
  editingUserId.value = user.id
  form.name = user.name
  form.email = user.email
  form.role = user.role
  form.password = ''
  showPassword.value = false
  dialogVisible.value = true
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [usersRes, rolesRes] = await Promise.all([
      api.get('/users'),
      api.get('/users/roles')
    ])
    users.value = usersRes.data
    roles.value = rolesRes.data
  } catch (err) {
    error.value = apiError(err)
  } finally {
    loading.value = false
  }
}

async function saveUser() {
  error.value = ''
  saving.value = true
  try {
    const payload = {
      name: form.name,
      email: form.email,
      role: form.role
    }
    if (form.password) {
      payload.password = form.password
    }
    if (editingUserId.value) {
      await api.patch(`/users/${editingUserId.value}`, payload)
    } else {
      await api.post('/users', payload)
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
.user-dialog {
  max-width: 520px;
}

.password-field {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
}

.password-field input {
  min-width: 0;
}

.password-field button {
  padding-inline: 14px;
}
</style>
