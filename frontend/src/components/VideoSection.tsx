import { Play } from 'lucide-react'
import { useTranslation } from 'react-i18next'

/**
 * Посилання на відео-інструкцію з YouTube. Поки порожнє — показується
 * заглушка. Підійде будь-яке посилання: youtu.be/…, youtube.com/watch?v=…,
 * youtube.com/embed/… або shorts.
 */
const YOUTUBE_URL = ''

/** Дістає 11-символьний id відео з типових форм YouTube-посилань. */
function youtubeId(url: string): string | null {
  const match = url.match(
    /(?:youtu\.be\/|youtube(?:-nocookie)?\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/|v\/))([\w-]{11})/,
  )
  return match ? match[1] : null
}

export function VideoSection() {
  const { t } = useTranslation()
  const id = youtubeId(YOUTUBE_URL)

  return (
    <section className="mx-auto w-full max-w-4xl px-8 pt-2">
      <div className="text-center">
        <h2 className="font-display text-2xl font-semibold text-ink">{t('home.video.title')}</h2>
        <p className="mt-1.5 text-sm text-[#767c86]">{t('home.video.text')}</p>
      </div>

      <div className="mt-5 aspect-video w-full overflow-hidden rounded-[14px] border border-[#e3e1da] bg-[#f8f7f4]">
        {id ? (
          <iframe
            src={`https://www.youtube-nocookie.com/embed/${id}`}
            title={t('home.video.iframeTitle')}
            loading="lazy"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            referrerPolicy="strict-origin-when-cross-origin"
            allowFullScreen
            className="h-full w-full"
          />
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center gap-3 text-[#8a9099]">
            <span className="flex h-16 w-16 items-center justify-center rounded-full bg-tint">
              <Play className="ml-1 h-7 w-7 text-accent" />
            </span>
            <span className="text-sm">{t('home.video.placeholder')}</span>
          </div>
        )}
      </div>
    </section>
  )
}
