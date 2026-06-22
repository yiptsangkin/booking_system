import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('paint_order_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export function apiError(error) {
  const detail = error?.response?.data?.detail
  if (Array.isArray(detail)) {
    return detail.map(formatValidationIssue).join('；')
  }
  if (typeof detail === 'string') {
    return translateMessage(detail)
  }
  if (detail?.msg) {
    return translateMessage(detail.msg)
  }
  return translateMessage(error?.message) || '请求失败'
}

function formatValidationIssue(issue) {
  const field = fieldName(issue?.loc)
  const message = translateMessage(issue?.msg || '参数校验失败')
  return field ? `${field}：${message}` : message
}

function fieldName(loc = []) {
  const key = Array.isArray(loc) ? loc[loc.length - 1] : loc
  return {
    email: '账号',
    password: '密码',
    order_no: '订单号',
    carrier: '物流公司',
    tracking_no: '运单号',
    receiver_name: '收货人',
    receiver_phone: '联系电话',
    shipping_address: '收货地址',
    items: '商品',
    product_id: '商品',
    quantity: '数量',
    name: '名称',
    color: '色号',
    color_hex: '色值',
    category: '分类',
    price: '价格',
    stock: '库存',
    delta: '库存调整数量',
    status: '状态',
    location: '位置',
    time: '时间',
    image_url: '图片地址',
    gps_location: '签收位置'
  }[key] || ''
}

function translateMessage(message) {
  const text = String(message || '')
  const exact = {
    'Dealer role required': '需要经销商账号操作',
    'Admin role required': '需要管理员权限',
    'Missing bearer token': '请先登录',
    'User not found': '登录用户不存在',
    'Invalid token': '登录已失效，请重新登录',
    'Token expired': '登录已过期，请重新登录',
    'Invalid email or password': '账号或密码错误',
    'Network Error': '网络异常，请检查后端服务是否已启动',
    timeout: '请求超时，请稍后重试',
    'Request failed with status code 403': '无权执行该操作',
    'Request failed with status code 401': '请先登录',
    'Request failed with status code 404': '请求的数据不存在',
    'Request failed with status code 409': '当前状态不允许执行该操作',
    'Request failed with status code 422': '提交内容格式不正确'
  }[text]
  if (exact) return exact
  if (text.includes('Field required')) return '必填项不能为空'
  if (text.includes('String should have at least')) return '内容不能为空'
  if (text.includes('String should have at most')) return '内容过长'
  if (text.includes('Input should be greater than or equal to')) return '数值不能小于 0'
  if (text.includes('Input should be greater than')) return '数值必须大于 0'
  if (text.includes('Input should be')) return '取值不符合要求'
  return text || '请求失败'
}
