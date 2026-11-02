import { useEffect, useId, useRef } from 'react'
import abcjs from 'abcjs'
import { Pause, Play, Square } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAbcPlayback } from '../hooks/useAbcPlayback'
import { Spinner } from './ui/Spinner'

interface Props {
  abc: string
  staffwidth?: number
  className?: string
  /** Додає кнопки відтворення й підсвічування нот, що звучать. */
  playable?: boolean
}

/** Abcjs score view; with `playable` it also plays the tune and highlights the sounding notes. */
export function AbcPaper({ abc, staffwidth, className, playable = false }: Props) {
  const { t } = useTranslation()
  const uid = useId().replace(/:/g, '')
  const paperId = `abc-paper-${uid}`

  const visualRef = useRef<abcjs.TuneObject | null>(null)
  const { playState, play, pause, stop } = useAbcPlayback(() => visualRef.current, abc)

  useEffect(() => {
    if (!abc) return
    const tunes = abcjs.renderAbc(
      paperId,
      abc,
      staffwidth ? { staffwidth } : { responsive: 'resize' },
    )
    visualRef.current = tunes[0] ?? null
  }, [paperId, abc, staffwidth])

  if (!abc) return null

  const buttonClass =
    'flex items-center gap-1.5 rounded-full border border-[#dcdad2] bg-white px-3.5 py-1.5 text-[13px] font-medium text-ink transition hover:border-accent hover:text-accent disabled:opacity-50'

  return (
    <div className={className ?? 'overflow-auto rounded-lg bg-white p-2'}>
      {playable && (
        <div className="mb-3 flex items-center gap-2">
          <button
            type="button"
            onClick={playState === 'playing' ? pause : play}
            disabled={playState === 'loading'}
            className={buttonClass}
          >
            {playState === 'loading' ? (
              <Spinner />
            ) : playState === 'playing' ? (
              <Pause className="h-3.5 w-3.5" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            {playState === 'loading'
              ? t('panels.player.preparing')
              : playState === 'playing'
                ? t('panels.player.pause')
                : playState === 'paused'
                  ? t('panels.player.resume')
                  : t('panels.player.play')}
          </button>
          {(playState === 'playing' || playState === 'paused') && (
            <button type="button" onClick={stop} className={buttonClass}>
              <Square className="h-3.5 w-3.5" />
              {t('panels.player.stop')}
            </button>
          )}
        </div>
      )}
      <div id={paperId} />
    </div>
  )
}
