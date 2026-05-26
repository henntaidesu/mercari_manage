import { createI18n } from 'vue-i18n'
import { ref, computed } from 'vue'
import zhCN from './locales/zh-CN.js'
import ja from './locales/ja.js'
import en from './locales/en.js'

import elZhCn from 'element-plus/es/locale/lang/zh-cn'
import elJa from 'element-plus/es/locale/lang/ja'
import elEn from 'element-plus/es/locale/lang/en'

export const SUPPORTED_LOCALES = ['zh-CN', 'ja', 'en']
export const LOCALE_STORAGE_KEY = 'app_locale'

export const elementLocales = {
  'zh-CN': elZhCn,
  ja: elJa,
  en: elEn,
}

function detectInitialLocale() {
  try {
    const saved = localStorage.getItem(LOCALE_STORAGE_KEY)
    if (saved && SUPPORTED_LOCALES.includes(saved)) return saved
  } catch {}
  const nav = (typeof navigator !== 'undefined' && navigator.language) || ''
  const lower = String(nav).toLowerCase()
  if (lower.startsWith('zh')) return 'zh-CN'
  if (lower.startsWith('ja')) return 'ja'
  if (lower.startsWith('en')) return 'en'
  return 'zh-CN'
}

const initialLocale = detectInitialLocale()

const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: initialLocale,
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    ja,
    en,
  },
  missingWarn: false,
  fallbackWarn: false,
})

export default i18n

export const currentLocale = ref(initialLocale)

export function setLocale(locale) {
  if (!SUPPORTED_LOCALES.includes(locale)) return
  i18n.global.locale.value = locale
  currentLocale.value = locale
  try { localStorage.setItem(LOCALE_STORAGE_KEY, locale) } catch {}
  try { document.documentElement.setAttribute('lang', locale) } catch {}
}

export const elementLocale = computed(() => elementLocales[currentLocale.value] || elZhCn)

try { document.documentElement.setAttribute('lang', initialLocale) } catch {}
