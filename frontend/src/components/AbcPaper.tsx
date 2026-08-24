import { useEffect, useId } from 'react'
import abcjs from 'abcjs'

interface Props {
  abc: string
}

/** Read-only abcjs score view — no editing toolbar. */
export function AbcPaper({ abc }: Props) {
  const uid = useId().replace(/:/g, '')
  const paperId = `abc-paper-${uid}`

  useEffect(() => {
    if (!abc) return
    abcjs.renderAbc(paperId, abc, { responsive: 'resize' })
  }, [paperId, abc])

  if (!abc) return null

  return (
    <div className="overflow-auto rounded-lg bg-white p-2">
      <div id={paperId} />
    </div>
  )
}
