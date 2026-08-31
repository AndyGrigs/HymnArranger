import { lazy, Suspense } from 'react'

const AbcPaper = lazy(() => import('./AbcPaper').then(m => ({ default: m.AbcPaper })))

const HERO_ABC = `X:1
M:3/4
L:1/8
K:F
V:1 clef=treble
V:2 clef=bass
[V:1] "F"f2 c2 A2 | "C7"g2 e2 c2 |
[V:2] F,,2 [A,,C,F,]4 | C,,2 [C,E,G,]4 |`

export function Hero() {
  return (
    <header className="relative overflow-hidden flex items-center" style={{ minHeight: 620 }}>
      {/* Photo background — right 58% */}
      <div
        className="absolute top-0 right-0 bottom-0 w-[58%] overflow-hidden"
        style={{
          WebkitMaskImage:
            'linear-gradient(to right, transparent 0%, black 18%), linear-gradient(to bottom, black 66%, transparent 100%)',
          WebkitMaskComposite: 'source-in',
          maskImage:
            'linear-gradient(to right, transparent 0%, black 18%), linear-gradient(to bottom, black 66%, transparent 100%)',
          maskComposite: 'intersect',
        }}
      >
        <img
          src="/bayan.jpg"
          alt="Баян на столі"
          className="h-full w-full object-cover"
          style={{
            objectPosition: '48% 57%',
            transform: 'scale(1.28)',
            filter: 'saturate(.86) contrast(.97)',
          }}
        />
      </div>

      {/* Horizontal gradient — text side fade */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'linear-gradient(96deg,#f6f5f1 0%,#f6f5f1 30%,rgba(246,245,241,.82) 40%,rgba(246,245,241,.4) 52%,rgba(246,245,241,.12) 62%,transparent 72%)',
        }}
      />
      {/* Vertical gradient — top/bottom fade */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'linear-gradient(to bottom,rgba(246,245,241,.7) 0%,rgba(246,245,241,0) 20%,rgba(246,245,241,0) 66%,#f6f5f1 100%)',
        }}
      />

      {/* Content */}
      <div className="relative mx-auto w-full max-w-7xl px-8" style={{ padding: '56px 32px 44px' }}>
        <div className="grid items-center gap-16" style={{ gridTemplateColumns: '1fr 420px' }}>

          {/* Left: copy */}
          <div>
            <p className="font-mono text-[11px] font-medium uppercase text-accent" style={{ letterSpacing: '.18em' }}>
              Аранжування для баяна
            </p>
            <h1
              className="mt-4.5 font-display font-medium text-ink"
              style={{ fontSize: 60, lineHeight: 1.06, letterSpacing: '-.015em', textWrap: 'pretty' } as React.CSSProperties}
            >
              Мелодія гімну —<br />
              <span className="italic text-accent">повна партитура</span> для баяна
            </h1>
            <p
              className="mt-5.5 text-base leading-[1.7] text-muted"
              style={{ maxWidth: 470, textWrap: 'pretty' } as React.CSSProperties}
            >
              Завантаж мелодію з акордовою послідовністю або набери її в редакторі ABC — і отримай готову дворучну партитуру з фігурацією та басом Страделла.
            </p>
            <div
              className="mt-7.5 flex flex-wrap items-center gap-3.5 font-mono uppercase text-[#767c86]"
              style={{ fontSize: '11.5px', letterSpacing: '.1em' }}
            >
              <span>Автоматичне аранжування</span>
              <span className="text-[#c9ccd1]">·</span>
              <span>Мелодія + акорди</span>
              <span className="text-[#c9ccd1]">·</span>
              <span>Баян та акордеон</span>
            </div>
          </div>

          {/* Right: score preview card */}
          <div
            className="self-end rounded-[14px] border border-parchment-edge bg-parchment"
            style={{
              padding: '20px 20px 12px',
              boxShadow: '0 1px 2px rgba(28,30,34,.05),0 24px 48px -28px rgba(28,30,34,.5)',
            }}
          >
            <p
              className="mb-2.75 flex justify-between font-mono uppercase text-[#8b8371]"
              style={{ fontSize: '10.5px', letterSpacing: '.14em' }}
            >
              <span>Приклад · Suite</span>
              <span>3/4 · F</span>
            </p>
            <div className="ha-score">
              <Suspense fallback={<div className="h-24" />}>
                <AbcPaper abc={HERO_ABC} staffwidth={340} className="" />
              </Suspense>
            </div>
          </div>
        </div>

        {/* Decorative staff lines */}
        <div className="mt-14 flex flex-col gap-1.5 opacity-50">
          <span className="block h-px bg-[#cfcdc4]" />
          <span className="block h-px bg-[#cfcdc4]" />
          <span className="block h-px bg-[#cfcdc4]" />
        </div>
      </div>
    </header>
  )
}
