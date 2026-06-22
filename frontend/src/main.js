import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './styles.css'
import App from './App.vue'
import router from './router'
import { applyStoredTheme } from './stores/theme'

applyStoredTheme()
createApp(App).use(createPinia()).use(router).mount('#app')
