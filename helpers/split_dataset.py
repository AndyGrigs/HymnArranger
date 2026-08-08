"""
split_dataset.py
----------------
Розділяє датасет HymnArranger на train/ і val/.

Логіка розділення:
  songs 001-035  →  val/   (оригінальні унікальні пісні)
  songs 036-214  →  train/ (аугментовані дані)

Це гарантує що val містить тільки реальні пісні
і немає витоку даних між train і val.

Використання:
  python split_dataset.py
  python split_dataset.py --dry-run
"""

import shutil
import argparse
from pathlib import Path


# ──────────────────────────────────────────────
# Налаштування
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).parent / "dataset"

# Оригінальні пісні (001-035) → val
# Аугментовані (036+)         → train
VAL_RANGE = range(1, 36)    # 1..35 включно


# ──────────────────────────────────────────────
# Головна функція
# ──────────────────────────────────────────────

def split_dataset(dry_run: bool = False):

    arrangement_dir = BASE_DIR / "arrangement"
    melody_dir      = BASE_DIR / "melody"

    if not arrangement_dir.exists() or not melody_dir.exists():
        print("❌ Папки dataset/arrangement/ або dataset/melody/ не знайдені.")
        return

    # Збираємо всі пари
    def get_files(folder):
        files = {}
        for ext in ("*.mxl", "*.xml"):
            for f in folder.glob(ext):
                stem = f.stem.replace("_full", "").replace("_melody", "")
                files[stem] = f
        return files

    arrangement_files = get_files(arrangement_dir)
    melody_files      = get_files(melody_dir)

    paired_stems = sorted(
        stem for stem in arrangement_files if stem in melody_files
    )

    print(f"\n🎵 HymnArranger — Розділення датасету")
    print(f"   Всього пар:    {len(paired_stems)}")
    print(f"   Val:           songs 001-035 (оригінальні)")
    print(f"   Train:         songs 036+ (аугментовані)")
    if dry_run:
        print(f"   Режим:         DRY-RUN\n")

    train_stems = []
    val_stems   = []

    for stem in paired_stems:
        # Витягуємо номер пісні з імені (song_001 → 1)
        try:
            number = int(stem.split("_")[1])
        except (IndexError, ValueError):
            print(f"  ⚠️  Не вдалось визначити номер для: {stem} → train")
            train_stems.append(stem)
            continue

        if number in VAL_RANGE:
            val_stems.append(stem)
        else:
            train_stems.append(stem)

    print(f"\n   Train: {len(train_stems)} пісень")
    print(f"   Val:   {len(val_stems)} пісень")

    # Копіюємо файли
    for split_name, stems in [("train", train_stems), ("val", val_stems)]:
        arr_out = BASE_DIR / split_name / "arrangement"
        mel_out = BASE_DIR / split_name / "melody"

        print(f"\n{'='*50}")
        print(f"  📂 {split_name.upper()} ({len(stems)} пісень)")
        print(f"{'='*50}")

        if not dry_run:
            arr_out.mkdir(parents=True, exist_ok=True)
            mel_out.mkdir(parents=True, exist_ok=True)

        for stem in stems:
            arr_src = arrangement_files[stem]
            mel_src = melody_files[stem]

            if dry_run:
                print(f"  → {stem}")
            else:
                shutil.copy2(arr_src, arr_out / arr_src.name)
                shutil.copy2(mel_src, mel_out / mel_src.name)
                print(f"  ✅ {stem}")

    print(f"\n{'='*50}")
    if dry_run:
        print(f"  DRY-RUN завершено. Запусти без --dry-run щоб застосувати.")
    else:
        print(f"  🎉 Готово!")
        print(f"  Train: {BASE_DIR / 'train'}")
        print(f"  Val:   {BASE_DIR / 'val'}")
    print()


# ──────────────────────────────────────────────
# Аргументи
# ──────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Розділення датасету HymnArranger на train/val"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Показати результат без копіювання файлів",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    split_dataset(dry_run=args.dry_run)