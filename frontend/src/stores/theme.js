import { defineStore } from 'pinia'

export const themePresets = [
  { id: 'emerald', label: '翡翠', swatch: '#0f766e' },
  { id: 'marine', label: '海蓝', swatch: '#2563eb' },
  { id: 'terracotta', label: '赤陶', swatch: '#b45309' },
  { id: 'graphite', label: '石墨', swatch: '#475569' }
]

const STORAGE_KEY = 'paint_order_theme'
const DEFAULT_THEME = 'emerald'

export function applyTheme(themeId) {
  const id = themePresets.some((theme) => theme.id === themeId) ? themeId : DEFAULT_THEME
  document.documentElement.dataset.theme = id
  localStorage.setItem(STORAGE_KEY, id)
  return id
}

export function applyStoredTheme() {
  return applyTheme(localStorage.getItem(STORAGE_KEY) || DEFAULT_THEME)
}

export const useThemeStore = defineStore('theme', {
  state: () => ({
    active: document.documentElement.dataset.theme || localStorage.getItem(STORAGE_KEY) || DEFAULT_THEME
  }),
  actions: {
    setTheme(themeId) {
      this.active = applyTheme(themeId)
    }
  }
})
