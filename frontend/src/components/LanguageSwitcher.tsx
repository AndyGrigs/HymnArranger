import { useTranslation } from 'react-i18next'
import { LANGUAGES, setLanguage, type Language } from '../i18n'

const SHORT: Record<Language, string> = { uk: 'UA', de: 'DE', en: 'EN' }

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation()

  return (
    <div
      role="group"
      aria-label={t('nav.language')}
      className="flex rounded-full border border-[#dcdad2] bg-white p-0.5 text-xs font-medium"
    >
      {LANGUAGES.map((lng) => (
        <button
          key={lng}
          type="button"
          onClick={() => setLanguage(lng)}
          aria-pressed={i18n.language === lng}
          className={`rounded-full px-2.5 py-1 transition ${
            i18n.language === lng ? 'bg-tint text-accent' : 'text-[#767c86] hover:text-ink'
          }`}
        >
          {SHORT[lng]}
        </button>
      ))}
    </div>
  )
}
