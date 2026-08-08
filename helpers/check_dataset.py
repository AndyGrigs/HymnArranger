#!/usr/bin/env python3
"""
check_dataset_pairs.py

Перевіряє датасет HymnArranger (dataset/{train,val}/{melody,arrangement}/*.xml):
  1. Чи для кожної мелодії є відповідне аранжування (і навпаки).
  2. Чи обидва файли коректно парситься music21 (не биті/порожні).
  3. Чи мелодія та аранжування мають однакову тональність (key).
  4. Базові sanity-перевірки: чи є ноти, чи аранжування має >1 партії
     (мелодія + бас/акорди), чи довжина аранжування не сильно коротша за мелодію.

Використання:
    python check_dataset_pairs.py --dataset dataset --report report.csv

Вимагає: pip install music21
"""

import argparse
import csv
import re
import sys
from pathlib import Path

from music21 import converter, key as m21key

SONG_ID_RE = re.compile(r"(\d+)")


def get_key(score):
    """
    Повертає тональність партитури.
    Спочатку шукає явний об'єкт Key/KeySignature у нотах (найнадійніше,
    бо наш датасет уже транспонований у явні тональності).
    Якщо явного знака немає — використовує аналіз Кростел-Кулі (analyze('key')).
    """
    explicit = score.flatten().getElementsByClass(m21key.Key)
    if len(explicit) > 0:
        k = explicit[0]
        return k.tonic.name, k.mode
    explicit_sig = score.flatten().getElementsByClass(m21key.KeySignature)
    if len(explicit_sig) > 0:
        k = explicit_sig[0].asKey()
        return k.tonic.name, k.mode
    analyzed = score.analyze('key')
    return analyzed.tonic.name, analyzed.mode


def _collect(dir_path: Path):
    """Збирає файли *.xml/*.musicxml/*.mxl у папці, ключ — номер пісні (song id)."""
    files = {}
    for pattern in ("*.xml", "*.musicxml", "*.mxl"):
        for p in dir_path.glob(pattern):
            m = SONG_ID_RE.search(p.stem)
            key = m.group(1) if m else p.stem
            files[key] = p
    return files


def find_pairs(dataset_root: Path):
    """Знаходить пари (melody_path, arrangement_path).

    Підтримує як плоску структуру dataset/{melody,arrangement}/*,
    так і поділ на сплити dataset/{train,val}/{melody,arrangement}/*.
    """
    pairs = []

    split_dirs = [
        (split, dataset_root / split)
        for split in ("train", "val")
        if (dataset_root / split / "melody").exists() and (dataset_root / split / "arrangement").exists()
    ]
    if not split_dirs:
        split_dirs = [("all", dataset_root)]

    for split, base in split_dirs:
        melody_dir = base / "melody"
        arr_dir = base / "arrangement"
        if not melody_dir.exists() or not arr_dir.exists():
            continue

        melody_files = _collect(melody_dir)
        arr_files = _collect(arr_dir)

        common = set(melody_files) & set(arr_files)
        for name in sorted(common):
            pairs.append((split, name, melody_files[name], arr_files[name]))

        for name in sorted(set(melody_files) - set(arr_files)):
            pairs.append((split, name, melody_files[name], None))
        for name in sorted(set(arr_files) - set(melody_files)):
            pairs.append((split, name, None, arr_files[name]))

    return pairs


def check_pair(split, name, melody_path, arr_path):
    """Повертає dict з результатом перевірки однієї пари."""
    row = {
        "split": split,
        "name": name,
        "status": "OK",
        "issue": "",
        "melody_key": "",
        "arrangement_key": "",
    }

    if melody_path is None:
        row["status"] = "MISSING_MELODY"
        row["issue"] = "Немає файлу мелодії для цього аранжування"
        return row
    if arr_path is None:
        row["status"] = "MISSING_ARRANGEMENT"
        row["issue"] = "Немає файлу аранжування для цієї мелодії"
        return row

    try:
        melody_score = converter.parse(melody_path)
    except Exception as e:
        row["status"] = "CORRUPT_MELODY"
        row["issue"] = f"Помилка парсингу мелодії: {e}"
        return row

    try:
        arr_score = converter.parse(arr_path)
    except Exception as e:
        row["status"] = "CORRUPT_ARRANGEMENT"
        row["issue"] = f"Помилка парсингу аранжування: {e}"
        return row

    if len(melody_score.flatten().notes) == 0:
        row["status"] = "EMPTY_MELODY"
        row["issue"] = "У мелодії немає нот"
        return row
    if len(arr_score.flatten().notes) == 0:
        row["status"] = "EMPTY_ARRANGEMENT"
        row["issue"] = "В аранжуванні немає нот"
        return row

    n_parts = len(arr_score.parts) if arr_score.parts else 1
    if n_parts < 2:
        row["status"] = "SINGLE_VOICE_ARRANGEMENT"
        row["issue"] = "Аранжування містить лише одну партію (очікується мелодія + бас/акорди)"

    try:
        m_tonic, m_mode = get_key(melody_score)
        a_tonic, a_mode = get_key(arr_score)
    except Exception as e:
        row["status"] = "KEY_DETECTION_FAILED"
        row["issue"] = f"Не вдалося визначити тональність: {e}"
        return row

    row["melody_key"] = f"{m_tonic} {m_mode}"
    row["arrangement_key"] = f"{a_tonic} {a_mode}"

    if (m_tonic, m_mode) != (a_tonic, a_mode):
        row["status"] = "KEY_MISMATCH"
        row["issue"] = (
            f"Тональності не збігаються: мелодія={m_tonic} {m_mode}, "
            f"аранжування={a_tonic} {a_mode}"
        )
        return row

    m_len = melody_score.duration.quarterLength
    a_len = arr_score.duration.quarterLength
    if m_len > 0 and a_len < m_len * 0.6:
        row["status"] = "LENGTH_MISMATCH"
        row["issue"] = (
            f"Аранжування суттєво коротше за мелодію "
            f"({a_len:.1f} vs {m_len:.1f} чвертей)"
        )

    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="dataset", help="Шлях до кореня dataset/")
    parser.add_argument("--report", default="dataset_check_report.csv", help="Куди зберегти CSV-звіт")
    args = parser.parse_args()

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    dataset_root = Path(args.dataset)
    if not dataset_root.exists():
        print(f"Не знайдено директорію датасету: {dataset_root}", file=sys.stderr)
        sys.exit(1)

    pairs = find_pairs(dataset_root)
    if not pairs:
        print("Пари melody/arrangement не знайдено. Перевір структуру папок.", file=sys.stderr)
        sys.exit(1)

    results = []
    for i, (split, name, melody_path, arr_path) in enumerate(pairs, 1):
        print(f"[{i}/{len(pairs)}] Перевіряю {split}/{name} ...")
        results.append(check_pair(split, name, melody_path, arr_path))

    with open(args.report, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["split", "name", "status", "melody_key", "arrangement_key", "issue"]
        )
        writer.writeheader()
        writer.writerows(results)

    ok = sum(1 for r in results if r["status"] == "OK")
    bad = [r for r in results if r["status"] != "OK"]

    print("\n=== ПІДСУМОК ===")
    print(f"Всього пар: {len(results)}")
    print(f"Без проблем: {ok}")
    print(f"З проблемами: {len(bad)}")

    if bad:
        counts = {}
        for r in bad:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        print("\nЗа типом проблеми:")
        for status, count in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {status}: {count}")

    print(f"\nПовний звіт збережено у {args.report}")


if __name__ == "__main__":
    main()