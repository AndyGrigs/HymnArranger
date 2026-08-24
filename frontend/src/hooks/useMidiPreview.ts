import { useEffect, useRef, useState } from 'react'
import { api } from '../api'

const SOUNDFONT = 'https://storage.googleapis.com/magentadata/js/soundfonts/sgm_plus'

let midiRegistered = false
async function ensureMidiPlayer() {
  if (!midiRegistered) {
    await import('html-midi-player')
    midiRegistered = true
  }
}

export function useMidiPreview(musicxml: string | undefined) {
  const midiHostRef = useRef<HTMLDivElement>(null)
  const midiUrlRef  = useRef<string | null>(null)
  const [midiLoading, setMidiLoading] = useState(false)
  const [midiReady,   setMidiReady]   = useState(false)

  useEffect(() => {
    if (midiUrlRef.current) {
      URL.revokeObjectURL(midiUrlRef.current)
      midiUrlRef.current = null
    }
    if (midiHostRef.current) midiHostRef.current.innerHTML = ''
    setMidiReady(false)
    setMidiLoading(false)
  }, [musicxml])

  async function handlePlayMidi() {
    if (!musicxml || midiLoading || midiReady) return
    setMidiLoading(true)
    try {
      await ensureMidiPlayer()
      const blob = await api.midi({ musicxml })
      if (midiUrlRef.current) URL.revokeObjectURL(midiUrlRef.current)
      const url = URL.createObjectURL(blob)
      midiUrlRef.current = url
      const player = document.createElement('midi-player')
      player.setAttribute('sound-font', SOUNDFONT)
      player.setAttribute('src', url)
      player.style.width = '100%'
      if (midiHostRef.current) {
        midiHostRef.current.innerHTML = ''
        midiHostRef.current.appendChild(player)
      }
      setMidiReady(true)
    } catch {
      // user can fall back to Export tab
    } finally {
      setMidiLoading(false)
    }
  }

  return { midiHostRef, midiLoading, midiReady, handlePlayMidi }
}
