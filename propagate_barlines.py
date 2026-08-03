"""
propagate_barlines.py

Функція, яка бере ОРИГІНАЛ аранжування і автоматично розставляє
подвійні риски в тих самих номерах тактів у всіх його ТРАНСПОНОВАНИХ копіях.

Чому це працює:
    Транспозиція міняє висоту нот, але не змінює кількість тактів і їх
    порядок. Тому якщо в оригіналі подвійна риска стоїть після такту №8,
    то в транспонованій копії тієї самої пісні межа варіації теж на
    такті №8 — просто там інша тональність.

Формат файлів (як у dataset/arrangement):
    song_089_full.mxl   (id завжди 3 цифри, з нулями попереду)

Використання:
    from propagate_barlines import propagate_double_barlines

    # приклад: пісня 014 - оригінал, транспонована в 4 копії
    report = propagate_double_barlines(
        original_arrangement="dataset/arrangement/song_014_full.mxl",
        transposed_song_numbers={"D major": 89, "A major": 90, "e minor": 91, "G major": 92},
        dataset_root="dataset",
    )

    Другий аргумент може бути словником у БУДЬ-ЯКОМУ напрямку
    (тональність -> номер, або номер -> тональність) — функція сама
    визначає, де там номери партитур, а де тональності, і бере номери.
    Також підійде просто список номерів: [89, 90, 91, 92].

Безпека:
    - Функція звіряє кількість тактів оригіналу й кожної транспонованої
      копії. Якщо вони не збігаються — файл ПРОПУСКАЄТЬСЯ (не псується),
      і це потрапляє у звіт зі статусом MEASURE_COUNT_MISMATCH.
    - Останній такт партитури не чіпається (там зазвичай вже стоїть
      фінальна риска 'final' — її переписувати не потрібно), навіть якщо
      межа варіації випадково збіглася з кінцем твору.
    - Спочатку запускай з dry_run=True, щоб побачити звіт і нічого не
      записати на диск.
"""

from pathlib import Path
from typing import Union

from music21 import bar, converter, stream


def _find_double_barline_measures(score: "stream.Score") -> list[int]:
    """Номери тактів (1-based), ПІСЛЯ яких в партитурі стоїть подвійна риска."""
    part = score.parts[0] if score.parts else score
    measures = part.getElementsByClass(stream.Measure)
    return [
        m.number for m in measures
        if m.rightBarline is not None and getattr(m.rightBarline, "type", None) == "double"
    ]


def _extract_song_ids(transposed_song_numbers: Union[dict, list, tuple]) -> list[str]:
    """
    Дістає номери партитур (як рядки без provided формату) незалежно від того,
    чи це список номерів, чи словник {тональність: номер} / {номер: тональність}.
    """
    if isinstance(transposed_song_numbers, (list, tuple, set)):
        raw_values = list(transposed_song_numbers)
    else:
        # словник: перевіряємо, де саме лежать номери - в ключах чи в значеннях
        keys = list(transposed_song_numbers.keys())
        values = list(transposed_song_numbers.values())

        def looks_numeric(v):
            return str(v).strip().isdigit()

        if all(looks_numeric(v) for v in values):
            raw_values = values
        elif all(looks_numeric(k) for k in keys):
            raw_values = keys
        else:
            raise ValueError(
                "Не вдалось визначити, де в словнику номери партитур — "
                "ані ключі, ані значення не виглядають як числа. "
                "Передай явно список номерів, наприклад [89, 90, 91]."
            )

    return [str(v).strip() for v in raw_values]


def propagate_double_barlines(
    original_arrangement: Union[str, Path, "stream.Score"],
    transposed_song_numbers: Union[dict, list, tuple],
    dataset_root: Union[str, Path] = "dataset",
    filename_pattern: str = "song_{id}_full.mxl",
    id_width: int = 3,
    dry_run: bool = False,
) -> list[dict]:
    """
    Розставляє подвійні тактові риски в транспонованих копіях за зразком оригіналу.

    Аргументи:
        original_arrangement:      шлях до оригінальної партитури (.mxl/.xml)
                                    з уже проставленими подвійними рисками,
                                    або вже завантажений music21 Score.
        transposed_song_numbers:   номери партитур-транспозицій - список
                                    [89, 90, 91] або словник у будь-якому
                                    напрямку {тональність: номер}/{номер: тональність}.
        dataset_root:               корінь датасету (де лежить папка arrangement/).
        filename_pattern:           шаблон імені файлу, {id} буде замінено
                                    на номер, доповнений нулями до id_width.
        dry_run:                    True -> нічого не записувати, тільки звіт.

    Повертає:
        список словників-звітів по кожній транспонованій партитурі.
    """
    dataset_root = Path(dataset_root)
    arrangement_dir = dataset_root / "arrangement"

    original_score = (
        original_arrangement
        if isinstance(original_arrangement, stream.Score)
        else converter.parse(str(original_arrangement))
    )

    boundaries = _find_double_barline_measures(original_score)
    if not boundaries:
        print("⚠️  В оригіналі не знайдено жодної подвійної риски — "
              "спершу проستав їх у MuseScore і збережи файл.")
        return []

    orig_part = original_score.parts[0] if original_score.parts else original_score
    orig_measure_count = len(orig_part.getElementsByClass(stream.Measure))

    song_ids = _extract_song_ids(transposed_song_numbers)
    report = []

    for song_id in song_ids:
        padded_id = song_id.zfill(id_width)
        target_path = arrangement_dir / filename_pattern.format(id=padded_id)

        if not target_path.exists():
            report.append({"song_id": padded_id, "status": "FILE_NOT_FOUND", "detail": str(target_path)})
            continue

        try:
            target_score = converter.parse(str(target_path))
        except Exception as e:
            report.append({"song_id": padded_id, "status": "CORRUPT_FILE", "detail": str(e)})
            continue

        target_part = target_score.parts[0] if target_score.parts else target_score
        target_measures = target_part.getElementsByClass(stream.Measure)

        if len(target_measures) != orig_measure_count:
            report.append({
                "song_id": padded_id, "status": "MEASURE_COUNT_MISMATCH",
                "detail": f"оригінал: {orig_measure_count} тактів, "
                          f"{padded_id}: {len(target_measures)} тактів - файл пропущено",
            })
            continue

        last_measure_num = max(m.number for m in target_measures)
        applied = []
        for m in target_measures:
            if m.number in boundaries and m.number != last_measure_num:
                m.rightBarline = bar.Barline("double")
                applied.append(m.number)

        if not dry_run:
            target_score.write("mxl", fp=str(target_path))

        report.append({
            "song_id": padded_id, "status": "OK",
            "detail": f"проставлено подвійні риски на тактах: {applied}",
        })

    n_ok = sum(1 for r in report if r["status"] == "OK")
    n_problems = len(report) - n_ok
    print(f"Готово{' (dry-run)' if dry_run else ''}: {n_ok} партитур оброблено успішно, "
          f"{n_problems} з проблемами (див. звіт).")
    for r in report:
        if r["status"] != "OK":
            print(f"  ⚠️  {r['song_id']}: {r['status']} — {r['detail']}")

    return report


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("original", help="Шлях до оригінальної партитури з проставленими рисками")
    ap.add_argument("transposed_numbers", help="JSON-список або словник номерів, напр. '[89,90,91]'")
    ap.add_argument("--dataset-root", default="dataset")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    numbers = json.loads(args.transposed_numbers)
    propagate_double_barlines(
        original_arrangement=args.original,
        transposed_song_numbers=numbers,
        dataset_root=args.dataset_root,
        dry_run=args.dry_run,
    )
