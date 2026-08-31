import { useEffect, useId } from 'react'
import abcjs from 'abcjs'

interface Props {
  abc: string
  staffwidth?: number
  className?: string
}

/** Read-only abcjs score view — no editing toolbar. */
export function AbcPaper({ abc, staffwidth, className }: Props) {
  const uid = useId().replace(/:/g, '')
  const paperId = `abc-paper-${uid}`

  useEffect(() => {
    if (!abc) return
    abcjs.renderAbc(
      paperId,
      abc,
      staffwidth ? { staffwidth } : { responsive: 'resize' },
    )
  }, [paperId, abc, staffwidth])

  if (!abc) return null

  return (
    <div className={className ?? 'overflow-auto rounded-lg bg-white p-2'}>
      <div id={paperId} />
    </div>
  )
}
