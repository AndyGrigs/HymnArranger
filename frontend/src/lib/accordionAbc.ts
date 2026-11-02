import type { AccordionHands } from '../api'

/** Порожні такти 4/4 по вісім вісімок — заготовка для кожної руки. */
export const EMPTY_HAND = 'z8 | z8 | z8 | z8 |]'

/**
 * Збирає одну ABC-партитуру з двох рук. Рядки рук чергуємо (V:R, V:L, V:R, …),
 * щоб abcjs вирівняв системи, а ліву руку виводимо в басовому ключі.
 */
export function composeAccordionAbc({ right, left, key, meter }: AccordionHands, title = ''): string {
  const r = right.split('\n')
  const l = left.split('\n')
  const body: string[] = []
  for (let i = 0; i < Math.max(r.length, l.length); i++) {
    body.push('V:R', r[i] ?? 'z8 |', 'V:L', l[i] ?? 'z8 |')
  }
  return [
    'X:1',
    `T:${title}`,
    `M:${meter}`,
    'L:1/8',
    '%%staves {R L}',
    'V:R clef=treble name="Права"',
    'V:L clef=bass name="Ліва"',
    `K:${key}`,
    ...body,
  ].join('\n')
}

/** Чи є в тексті руки хоч одна нота (а не самі паузи й риски). */
export function hasNotes(hand: string): boolean {
  return /[A-Ga-g]/.test(hand.replace(/"[^"]*"/g, ''))
}
