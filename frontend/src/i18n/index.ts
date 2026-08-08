import { createI18n } from 'vue-i18n'
import en from './en.json'

// Persian UI strings (fa.json) exist but are not loaded until translations are improved.
// export type Locale = 'en' | 'fa'
export type Locale = 'en'

export const i18n = createI18n({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  messages: { en },
})

export function applyDocumentLocale(locale: Locale = 'en') {
  document.documentElement.lang = locale
  document.documentElement.dir = 'ltr'
}
