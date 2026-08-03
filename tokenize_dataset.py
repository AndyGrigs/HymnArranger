"""
tokenize_dataset.py
--------------------
Токенізація датасету HymnArranger у стилі REMI
(Revamped MIDI-derived Events) з додатковими Voice токенами
для баянної фактури (мелодія / бас / акорд).

Структура токенів:
  Спеціальні:  PAD, BOS, EOS, SEP
  Структурні:  Bar, Position_0..Position_15  (сітка 16-х нот)
  Висота:      Pitch_0..Pitch_127            (MIDI ноти)
  Тривалість:  Duration_1..Duration_32       (в одиницях 16-х нот)
  Голос:       Voice_Melody, Voice_Bass, Voice_Chord

Результат:
  dataset/tokenized/
    train/
      song_001.json   ← {"melody": [...], "arrangement": [...]}
      song_002.json
    val/
      ...
    vocabulary.json   ← словник токенів (індекс ↔ назва)

Використання:
  python tokenize_dataset.py
  python tokenize_dataset.py --resolution 8    (8-а нота як одиниця)
  python tokenize_dataset.py --split train
  python tokenize_dataset.py --dry-run
"""

import os
import sys
import json
import argparse
from pathlib import Path
from fractions import Fraction

try:
    import music21
    from music21 import converter, note, chord, stream
except ImportError:
    print("❌ music21 не встановлено. Запусти: pip install music21")
    sys.exit(1)


# ──────────────────────────────────────────────
# Константи
# ──────────────────────────────────────────────

BASE_DIR     = Path(__file__).parent / "dataset"
OUTPUT_DIR   = BASE_DIR / "tokenized"
SPLITS       = ["train", "val"]

# Кількість позицій на такт (16 = сітка 16-х нот)
DEFAULT_RESOLUTION = 16

# Максимальна тривалість у сітці (2 цілих ноти)
MAX_DURATION = 32


# ──────────────────────────────────────────────
# Словник токенів
# ──────────────────────────────────────────────

def build_vocabulary(resolution: int = DEFAULT_RESOLUTION) -> dict:
    """
    Будує словник всіх можливих токенів.
    Повертає: {назва_токена: індекс}
    """
    vocab = {}
    idx = 0

    def add(name: str):
        nonlocal idx
        vocab[name] = idx
        idx += 1

    # Спеціальні токени
    add("PAD")   # заповнення до однакової довжини
    add("BOS")   # початок послідовності
    add("EOS")   # кінець послідовності
    add("SEP")   # роздільник між секціями

    # Структурні токени
    add("Bar")   # початок такту
    for i in range(resolution):
        add(f"Position_{i}")  # позиція в такті

    # Висота ноти (MIDI 0-127)
    for i in range(128):
        add(f"Pitch_{i}")

    # Тривалість (в одиницях сітки)
    for i in range(1, MAX_DURATION + 1):
        add(f"Duration_{i}")

    # Голоси (для аранжування баяна)
    add("Voice_Melody")  # мелодія (права рука)
    add("Voice_Chord")   # акорди (права рука)
    add("Voice_Bass")    # бас (ліва рука)

    return vocab


# ──────────────────────────────────────────────
# Квантизація
# ──────────────────────────────────────────────

def quantize_offset(offset: float, resolution: int) -> int:
    """
    Переводить зміщення в долях (quarterLength) в одиниці сітки.
    offset=0.0 → 0, offset=0.25 → 1 (при resolution=16)
    """
    units_per_quarter = resolution / 4
    return max(0, round(float(offset) * units_per_quarter))


def quantize_duration(duration: float, resolution: int) -> int:
    """
    Переводить тривалість в одиницях сітки.
    Мінімум 1, максимум MAX_DURATION.
    """
    units_per_quarter = resolution / 4
    dur = max(1, round(float(duration) * units_per_quarter))
    return min(dur, MAX_DURATION)


# ──────────────────────────────────────────────
# Витягування подій з партії
# ──────────────────────────────────────────────

def extract_events(part: stream.Part, resolution: int, voice_label: str) -> list[dict]:
    """
    Витягує всі нотні події з однієї партії (Part).
    Повертає список подій, відсортованих за offset:
    [{"offset_units": int, "pitch": int, "duration_units": int, "voice": str}, ...]
    """
    events = []
    flat = part.flatten()

    for element in flat.notesAndRests:
        offset_units = quantize_offset(element.offset, resolution)
        duration_units = quantize_duration(element.duration.quarterLength, resolution)

        if isinstance(element, note.Note):
            events.append({
                "offset_units": offset_units,
                "pitch": element.pitch.midi,
                "duration_units": duration_units,
                "voice": voice_label,
            })

        elif isinstance(element, chord.Chord):
            # Для акорду беремо кожну ноту окремо
            for p in element.pitches:
                events.append({
                    "offset_units": offset_units,
                    "pitch": p.midi,
                    "duration_units": duration_units,
                    "voice": voice_label,
                })

        # Паузи ігноруємо — вони закодовані відсутністю нот

    return sorted(events, key=lambda e: e["offset_units"])


# ──────────────────────────────────────────────
# Конвертація подій у токени
# ──────────────────────────────────────────────

def events_to_tokens(
    events: list[dict],
    score: stream.Score,
    resolution: int,
    vocab: dict,
    include_voice: bool = False,
) -> list[int]:
    """
    Перетворює список подій у послідовність токенів.

    Структура такту:
      Bar Position_X [Voice_Y] Pitch_Z Duration_W  ...наступна нота...

    include_voice=True  → для аранжування (є кілька голосів)
    include_voice=False → для мелодії (один голос)
    """
    tokens = [vocab["BOS"]]

    if not events:
        tokens.append(vocab["EOS"])
        return tokens

    # Визначаємо тривалість такту в одиницях сітки
    time_sig = score.recurse().getElementsByClass("TimeSignature").first()
    if time_sig:
        bar_length = quantize_duration(time_sig.barDuration.quarterLength, resolution)
    else:
        bar_length = resolution  # за замовчуванням 4/4

    current_bar = -1
    current_voice = None

    for event in events:
        bar_idx = event["offset_units"] // bar_length
        pos_idx = event["offset_units"] % bar_length

        # Новий такт
        if bar_idx != current_bar:
            tokens.append(vocab["Bar"])
            current_bar = bar_idx
            current_voice = None  # скидаємо голос на початку такту

        # Позиція в такті
        pos_token = f"Position_{min(pos_idx, resolution - 1)}"
        tokens.append(vocab[pos_token])

        # Голос (якщо потрібно і якщо змінився)
        if include_voice:
            voice_token = f"Voice_{event['voice'].replace('Voice_', '')}"
            if voice_token != current_voice and voice_token in vocab:
                tokens.append(vocab[voice_token])
                current_voice = voice_token

        # Висота ноти
        pitch_token = f"Pitch_{event['pitch']}"
        if pitch_token in vocab:
            tokens.append(vocab[pitch_token])

        # Тривалість
        dur_token = f"Duration_{event['duration_units']}"
        if dur_token in vocab:
            tokens.append(vocab[dur_token])

    tokens.append(vocab["EOS"])
    return tokens


# ──────────────────────────────────────────────
# Токенізація одного файлу
# ──────────────────────────────────────────────

def tokenize_melody(filepath: Path, resolution: int, vocab: dict) -> list[int] | None:
    """
    Токенізує файл мелодії.
    Мелодія = один голос, перша партія.
    """
    try:
        score = converter.parse(str(filepath))
        if not score.parts:
            print(f"    ⚠️  Немає партій у {filepath.name}")
            return None

        part = score.parts[0]
        events = extract_events(part, resolution, "Melody")
        tokens = events_to_tokens(events, score, resolution, vocab, include_voice=False)
        return tokens

    except Exception as e:
        print(f"    ❌ Помилка мелодії {filepath.name}: {e}")
        return None


def tokenize_arrangement(filepath: Path, resolution: int, vocab: dict) -> list[int] | None:
    """
    Токенізує файл аранжування для баяна.
    Розподіл голосів:
      Партія 0 (права рука) → Voice_Melody + Voice_Chord
      Партія 1 (ліва рука)  → Voice_Bass
    """
    try:
        score = converter.parse(str(filepath))
        if not score.parts:
            print(f"    ⚠️  Немає партій у {filepath.name}")
            return None

        all_events = []

        for i, part in enumerate(score.parts):
            if i == 0:
                # Права рука: мелодія (верхній голос) і акорди (нижній)
                # Спрощення: все з правої руки → Voice_Melody
                events = extract_events(part, resolution, "Melody")
            elif i == 1:
                # Ліва рука → Voice_Bass
                events = extract_events(part, resolution, "Bass")
            else:
                # Додаткові партії (якщо є) → Voice_Chord
                events = extract_events(part, resolution, "Chord")

            all_events.extend(events)

        # Сортуємо всі події за offset
        all_events.sort(key=lambda e: (e["offset_units"], e["voice"]))

        tokens = events_to_tokens(all_events, score, resolution, vocab, include_voice=True)
        return tokens

    except Exception as e:
        print(f"    ❌ Помилка аранжування {filepath.name}: {e}")
        return None


# ──────────────────────────────────────────────
# Головна функція токенізації
# ──────────────────────────────────────────────

def tokenize_split(
    split: str,
    resolution: int,
    vocab: dict,
    dry_run: bool = False,
) -> dict:
    """
    Токенізує всі пари в одному split.
    """
    melody_dir      = BASE_DIR / split / "melody"
    arrangement_dir = BASE_DIR / split / "arrangement"
    out_dir         = OUTPUT_DIR / split

    stats = {"total": 0, "success": 0, "errors": 0}

    if not melody_dir.exists() or not arrangement_dir.exists():
        print(f"  ⚠️  Папки не знайдені для {split}/")
        return stats

    melody_files = {
        f.stem.replace("_melody", ""): f
        for ext in ("*.xml", "*.musicxml", "*.mxl")
        for f in melody_dir.glob(ext)
    }
    arrangement_files = {
        f.stem.replace("_full", ""): f
        for ext in ("*.xml", "*.musicxml", "*.mxl")
        for f in arrangement_dir.glob(ext)
    }

    pairs = [s for s in melody_files if s in arrangement_files]
    stats["total"] = len(pairs)

    print(f"\n{'='*55}")
    print(f"  📂 {split.upper()} — {len(pairs)} пар")
    print(f"{'='*55}")

    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    for stem in sorted(pairs):
        print(f"  🎵 {stem}...", end=" ")

        melody_tokens = tokenize_melody(melody_files[stem], resolution, vocab)
        arrangement_tokens = tokenize_arrangement(arrangement_files[stem], resolution, vocab)

        if melody_tokens is None or arrangement_tokens is None:
            print("❌ пропущено")
            stats["errors"] += 1
            continue

        result = {
            "id": stem,
            "melody_length": len(melody_tokens),
            "arrangement_length": len(arrangement_tokens),
            "melody": melody_tokens,
            "arrangement": arrangement_tokens,
        }

        if not dry_run:
            out_path = out_dir / f"{stem}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f)

        print(f"✅ мелодія={len(melody_tokens)} токенів, "
              f"аранжування={len(arrangement_tokens)} токенів")
        stats["success"] += 1

    return stats


# ──────────────────────────────────────────────
# Аргументи
# ──────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Токенізація датасету HymnArranger (REMI-стиль)"
    )
    parser.add_argument(
        "--resolution",
        type=int,
        default=DEFAULT_RESOLUTION,
        help=f"Позицій на такт (за замовчуванням: {DEFAULT_RESOLUTION})",
    )
    parser.add_argument(
        "--split",
        choices=["train", "val", "both"],
        default="both",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Показати результат без збереження файлів",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    splits = SPLITS if args.split == "both" else [args.split]

    print(f"\n🎵 HymnArranger — Токенізація датасету")
    print(f"   Шлях:       {BASE_DIR.resolve()}")
    print(f"   Resolution: {args.resolution} позицій/такт")
    print(f"   Splits:     {splits}")
    if args.dry_run:
        print(f"   Режим:      DRY-RUN")

    # Будуємо словник
    vocab = build_vocabulary(args.resolution)
    print(f"\n📚 Словник: {len(vocab)} токенів")

    # Зберігаємо словник
    if not args.dry_run:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        vocab_path = OUTPUT_DIR / "vocabulary.json"
        # Зворотній словник теж зберігаємо (індекс → назва)
        idx_to_token = {str(v): k for k, v in vocab.items()}
        full_vocab = {"token_to_idx": vocab, "idx_to_token": idx_to_token}
        with open(vocab_path, "w", encoding="utf-8") as f:
            json.dump(full_vocab, f, ensure_ascii=False, indent=2)
        print(f"   Збережено: {vocab_path}")

    # Токенізуємо
    total_success = 0
    total_errors = 0

    for split in splits:
        stats = tokenize_split(split, args.resolution, vocab, args.dry_run)
        total_success += stats["success"]
        total_errors += stats["errors"]

    # Підсумок
    print(f"\n{'='*55}")
    print(f"  📊 ПІДСУМОК")
    print(f"{'='*55}")
    print(f"  Успішно токенізовано: {total_success} пар")
    print(f"  Помилок:              {total_errors}")

    if not args.dry_run and total_success > 0:
        print(f"\n  📁 Результати збережено: {OUTPUT_DIR.resolve()}")
        print(f"  📚 Словник збережено:    {OUTPUT_DIR / 'vocabulary.json'}")

    print(f"\n  🎉 Готово до тренування!\n")


if __name__ == "__main__":
    main()