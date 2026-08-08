import { createI18n } from 'vue-i18n'
import en from './en.json'
import fa from './fa.json'

export type Locale = 'en' | 'fa'

export const i18n = createI18n({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  messages: { en, fa },
})

export function applyDocumentLocale(locale: Locale) {
  const dir = locale === 'fa' ? 'rtl' : 'ltr'
  document.documentElement.lang = locale
  document.documentElement.dir = dir
}
