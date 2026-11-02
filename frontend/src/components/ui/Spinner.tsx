import { useTranslation } from 'react-i18next'

export function Spinner({ className = '' }: { className?: string }) {
  const { t } = useTranslation()
  return (
    <span
      role="status"
      aria-label={t('panels.common.loading')}
      className={`inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
    />
  )
}