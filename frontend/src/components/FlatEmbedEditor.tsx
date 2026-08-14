import { useEffect, useRef, useState } from 'react';
import Embed from 'flat-embed';

const FLAT_APP_ID = import.meta.env.VITE_FLAT_APP_ID;

interface FlatEmbedEditorProps {
  musicXml?: string;              // якщо завантажуємо власний MusicXML
  scoreId?: string;               // якщо відкриваємо існуючу ноту на Flat
  onReady?: (embed: Embed) => void;
  height?: string;
}

export function FlatEmbedEditor({
  musicXml,
  scoreId,
  onReady,
  height = '600px',
}: FlatEmbedEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const embedRef = useRef<Embed | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;
    if (!FLAT_APP_ID) {
      console.warn(
        'VITE_FLAT_APP_ID не задано — embed працюватиме лише на localhost без обмежень.'
      );
    }

    const embed = new Embed(containerRef.current, {
      score: scoreId,
      embedParams: {
        appId: FLAT_APP_ID,
        controlsPosition: 'bottom',
        mode: 'edit',
      },
    });
    embedRef.current = embed;

    embed.ready().then(async () => {
      setIsReady(true);
      if (musicXml) {
        await embed.loadMusicXML(musicXml);
      }
      onReady?.(embed);
    });

    return () => {
      if (containerRef.current) containerRef.current.innerHTML = '';
      embedRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Метод для отримання відредагованого MusicXML назад в арранжер
//   async function exportMusicXml(): Promise<string | null> {
//     if (!embedRef.current) return null;
//     return embedRef.current.getMusicXML();
//   }

  return (
    <div>
      <div ref={containerRef} style={{ width: '100%', height }} />
      {!isReady && <p>Завантаження редактора нот…</p>}
    </div>
  );
}