const FEATURES = [
  { emoji: '🎼', label: 'Автоматичне аранжування' },
  { emoji: '🎵', label: 'Мелодія + акорди в партитурі' },
  { emoji: '🪗', label: 'Зручно для баяна та акордеона' },
]

export function Hero() {
  return (
    <div className="mx-auto flex max-w-7xl items-center px-4 pb-12 pt-8 sm:px-6 sm:pb-20 sm:pt-12">
      {/* Left: copy */}
      <div className="flex-1">
        <h1 className="font-display text-3xl font-bold leading-[1.18] tracking-tight text-ink sm:text-4xl lg:text-5xl">
          Створюй ноти для баяна
          <span className="block text-accent">автоматично</span>
        </h1>
        <p className="mt-4 max-w-md text-base leading-relaxed text-muted sm:mt-5">
          Завантаж мелодію із акордовою послідовністю — отримай готову
          партитуру для гри на баяні.
        </p>
        <div className="mt-6 flex flex-wrap gap-3 sm:mt-8">
          {FEATURES.map(({ emoji, label }) => (
            <div
              key={label}
              className="flex items-center gap-2 rounded-full border border-ink/10 bg-white/60 px-4 py-2 text-sm text-ink/65 shadow-sm backdrop-blur-sm"
            >
              <span>{emoji}</span>
              <span>{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Right: accordion artwork */}
      <div className="relative ml-16 hidden h-72 w-80 shrink-0 lg:flex">
        {/* warm blob */}
        <div className="absolute inset-0 rounded-[48px] bg-linear-to-br from-accent/12 to-accent/4" />
        {/* scattered musical notes */}
        <span className="absolute right-14 top-5 select-none text-5xl text-accent/20 rotate-12">♩</span>
        <span className="absolute right-4 top-20 select-none text-3xl text-accent/15 -rotate-6">♪</span>
        <span className="absolute bottom-10 left-6 select-none text-4xl text-accent/18 rotate-8">♫</span>
        <span className="absolute left-16 top-7 select-none text-6xl text-accent/10 -rotate-12">♬</span>
        <span className="absolute bottom-5 right-10 select-none text-2xl text-accent/12 rotate-20">♩</span>
        {/* accordion */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="select-none text-[8rem] drop-shadow-md">🪗</span>
        </div>
      </div>
    </div>
  )
}
