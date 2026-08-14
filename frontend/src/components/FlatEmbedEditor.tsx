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
    const host = containerRef.current;
    if (!host) return;
    if (!FLAT_APP_ID) {
      console.warn(
        'VITE_FLAT_APP_ID не задано — embed працюватиме лише на localhost без обмежень.'
      );
    }

    // StrictMode (dev) монтує ефект двічі. flat-embed кешує екземпляр за
    // iframe у контейнері й повертає той самий, якщо iframe лишити на місці,
    // тож НЕ чистимо host — інакше щоразу створюється новий iframe і редактор
    // перезавантажується (у консолі видно «JS API enabled» кілька разів).
    let cancelled = false;

    const embed = new Embed(host, {
      score: scoreId,
      embedParams: {
        appId: FLAT_APP_ID,
        controlsPosition: 'bottom',
        mode: 'edit',
      },
    });
    embedRef.current = embed;

    // Flat шле цю подію, коли блокує дію (напр. редагування недоступне для
    // цього appId/домену) — саме тоді ноти «не набираються». Без слухача
    // збій мовчазний; тут він потрапляє в консоль.
    embed.on('restrictedFeatureAttempt', (...info: unknown[]) =>
      console.warn('[flat-embed] дію заблоковано:', ...info),
    );

    embed.ready().then(async () => {
      if (cancelled) return;
      setIsReady(true);
      if (musicXml) {
        await embed.loadMusicXML(musicXml);
      }
      if (cancelled) return;
      // Клавіатурне введення нот (A–G) працює лише коли фокус усередині
      // iframe — після завантаження віддаємо фокус партитурі, щоб можна
      // було одразу набирати з клавіатури, не клікаючи спершу по нотах.
      embed.focusScore().catch(() => {});
      onReady?.(embed);
    });

    return () => {
      cancelled = true;
      embedRef.current = null;
      // host не чистимо: при справжньому демонтажі React сам прибере контейнер,
      // а до того iframe має лишитися, щоб flat-embed повторно використав його.
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