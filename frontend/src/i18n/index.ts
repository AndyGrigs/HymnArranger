import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { uk } from './uk'
import { de } from './de'
import { en } from './en'

export const LANGUAGES = ['uk', 'de', 'en'] as const
export type Language = (typeof LANGUAGES)[number]

const STORAGE_KEY = 'hymnarranger_lang'

function isLanguage(value: string | null): value is Language {
  return value !== null && (LANGUAGES as readonly string[]).includes(value)
}

/** Збережена мова → мова браузера (de, en) → українська за замовчуванням. */
function initialLanguage(): Language {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (isLanguage(saved)) return saved
  } catch {
    // localStorage може бути недоступний (приватний режим) — це не критично
  }
  const browser = navigator.language?.toLowerCase() ?? ''
  if (browser.startsWith('de')) return 'de'
  if (browser.startsWith('en')) return 'en'
  return 'uk'
}

void i18n.use(initReactI18next).init({
  resources: {
    uk: { translation: uk },
    de: { translation: de },
    en: { translation: en },
  },
  lng: initialLanguage(),
  fallbackLng: 'uk',
  interpolation: { escapeValue: false },
})

document.documentElement.lang = i18n.language

i18n.on('languageChanged', (lng) => {
  document.documentElement.lang = lng
  try {
    localStorage.setItem(STORAGE_KEY, lng)
  } catch {
    // див. вище
  }
})

export function setLanguage(lng: Language): void {
  void i18n.changeLanguage(lng)
}

/** Локаль для toLocaleString/Intl залежно від поточної мови. */
export function currentLocale(): string {
  return { de: 'de-DE', en: 'en-GB', uk: 'uk-UA' }[i18n.language] ?? 'uk-UA'
}

export default i18n
