"""
split_variations.py

Розбиває довгі аранжування на окремі "варіації" за подвійними тактовими
рисками, і дублює відповідну (коротку) мелодію під кожну варіацію.

Навіщо:
    Аранжування гімну — це зазвичай коротка мелодія, програна кілька разів
    поспіль з різною гармонізацією/варіацією. Замість того щоб різати
    аранжування довільно по кількості токенів (що ламає музичний сенс),
    ми ріжемо його по музичних межах — там, де в нотах стоїть подвійна
    тактова риска (Double barline), яку користувач сам проставляє в
    редакторі нот на межі кожної варіації.

Як позначити межі перед запуском:
    У MuseScore (або іншому нотному редакторі): клікнути на такт, ПІСЛЯ
    якого закінчується варіація -> палітра "Тактові риски" -> Double.

Очікувана структура датасету (майстер-пул, ДО train/val спліту):
    dataset/melody/song_XXX_melody.mxl (або .xml)
    dataset/arrangement/song_XXX_full.mxl (або .xml)
    (базовий номер song_XXX збігається, суфікси _full/_melody - різні,
     скрипт сам це враховує)

Опція --min-measures N:
    Варіації коротші за N тактів (наприклад, короткий вступ/затакт перед
    основною темою) НЕ залишаються окремою парою, а приєднуються до
    сусідньої варіації - щоб не плодити занадто дрібні, малоінформативні
    приклади для тренування, але й не втрачати сам музичний матеріал.

    Це "сирі" першоджерела. Папки dataset/train, dataset/val,
    dataset/tokenized — похідні, генеруються окремими скриптами
    (split_dataset.py, tokenize_dataset.py) ПІСЛЯ цього кроку і тут
    не чіпаються.

Результат:
    dataset/melody/X_var1.xml, X_var2.xml, ...
    dataset/arrangement/X_var1.xml, X_var2.xml, ...
    (мелодія копіюється незмінною під кожен номер варіації;
     аранжування розбивається на відповідні шматки)

    Пісні без жодної подвійної риски залишаються як є (X.xml),
    і потрапляють у report.csv зі статусом NO_DOUBLE_BARLINE.

Запуск:
    python split_variations.py --dataset-root ./dataset [--dry-run]

Після запуску:
    1. Перевір dataset/split_variations_report.csv
    2. Перегенеруй train/val:      python split_dataset.py
    3. Перетокенізуй:              python tokenize_dataset.py
"""

import argparse
import copy
import csv
import shutil
from pathlib import Path

from music21 import converter
from music21 import stream

from music21_fixes import strip_degenerate_arpeggios

import re

_ALREADY_SPLIT_RE = re.compile(r"_var\d+$")


def find_double_barline_measures(arrangement: "stream.Score") -> list[int]:
    """Повертає номери тактів (1-based), ПІСЛЯ яких стоїть подвійна риска."""
    part = arrangement.parts[0] if arrangement.parts else arrangement
    measures = part.getElementsByClass(stream.Measure)

    boundary_measure_numbers = []
    for m in measures:
        is_double = False
        if m.rightBarline is not None and getattr(m.rightBarline, "type", None) in (
            "double",
            "final",
        ):
            # 'final' (остання риска твору) теж завжди закриває сегмент
            if m.rightBarline.type == "double":
                is_double = True
        if is_double:
            boundary_measure_numbers.append(m.number)
    return boundary_measure_numbers


def _merge_short_ranges(ranges: list[tuple], min_measures: int) -> list[tuple]:
    """
    Приєднує занадто короткі діапазони (< min_measures тактів) до сусіднього,
    щоб не губити музичний матеріал і не створювати штучно дрібних варіацій
    (типове застосування - короткий вступ/затакт перед основною темою).

    Короткий діапазон зливається З НАСТУПНИМ, якщо такий є; якщо короткий
    діапазон - останній у пісні, зливається з ПОПЕРЕДНІМ.
    """
    if min_measures <= 1 or not ranges:
        return ranges

    merged = [list(r) for r in ranges]
    i = 0
    while i < len(merged):
        start, end = merged[i]
        length = end - start + 1
        if length < min_measures:
            if i + 1 < len(merged):
                merged[i + 1][0] = start          # приєднуємо до наступного
                del merged[i]
                continue  # не рухаємо i - перевіряємо новий об'єднаний діапазон
            elif merged:
                merged[i - 1][1] = end            # останній - приєднуємо до попереднього
                del merged[i]
                i -= 1
                continue
        i += 1
    return [tuple(r) for r in merged]


def _drop_short_ranges(ranges: list[tuple], min_measures: int) -> list[tuple]:
    """Просто прибирає діапазони коротші за min_measures тактів (без злиття)."""
    if min_measures <= 1:
        return ranges
    return [r for r in ranges if (r[1] - r[0] + 1) >= min_measures]


def split_into_segments(
    arrangement: "stream.Score",
    boundaries: list[int],
    min_measures: int = 1,
    drop_short: bool = False,
):
    """Ріже партитуру на сегменти [1..b1], [b1+1..b2], ... за номерами тактів."""
    part = arrangement.parts[0] if arrangement.parts else arrangement
    measures = part.getElementsByClass(stream.Measure)
    last_measure_num = max(m.number for m in measures)

    all_bounds = sorted(set(boundaries))
    if not all_bounds or all_bounds[-1] != last_measure_num:
        all_bounds.append(last_measure_num)

    ranges = []
    start = 1
    for end in all_bounds:
        if end < start:
            continue
        ranges.append((start, end))
        start = end + 1

    ranges = _drop_short_ranges(ranges, min_measures) if drop_short else _merge_short_ranges(ranges, min_measures)

    # measures() коректно підтягує діючий ключ/розмір/clef на початок сегмента
    return [arrangement.measures(s, e) for s, e in ranges]


def process_song(
    melody_path: Path,
    arrangement_path: Path,
    dry_run: bool,
    min_measures: int = 1,
    drop_short: bool = False,
) -> list[dict]:
    rows = []
    try:
        arrangement = converter.parse(str(arrangement_path))
    except Exception as e:
        rows.append({
            "song": arrangement_path.stem, "status": "CORRUPT_ARRANGEMENT",
            "detail": str(e), "n_variations": 0,
        })
        return rows

    boundaries = find_double_barline_measures(arrangement)

    if not boundaries:
        rows.append({
            "song": arrangement_path.stem, "status": "NO_DOUBLE_BARLINE",
            "detail": "залишено без змін (одна пара)", "n_variations": 1,
        })
        return rows

    segments = split_into_segments(arrangement, boundaries, min_measures=min_measures, drop_short=drop_short)

    if not segments:
        rows.append({
            "song": arrangement_path.stem, "status": "ALL_VARIATIONS_TOO_SHORT",
            "detail": f"усі варіації коротші за --min-measures {min_measures} - "
                      f"оригінал залишено без змін, щоб пісня не зникла з датасету",
            "n_variations": 0,
        })
        return rows

    stem = arrangement_path.stem
    ext = arrangement_path.suffix  # .mxl або .xml - зберігаємо той самий формат
    write_format = "mxl" if ext == ".mxl" else "musicxml"

    for i, segment in enumerate(segments, start=1):
        var_arrangement_out = arrangement_path.parent / f"{stem}_var{i}{ext}"
        var_melody_out = melody_path.parent / f"{stem}_var{i}{melody_path.suffix}"

        if not dry_run:
            strip_degenerate_arpeggios(segment)
            segment.write(write_format, fp=str(var_arrangement_out))
            shutil.copyfile(melody_path, var_melody_out)

        rows.append({
            "song": stem, "status": "SPLIT_OK",
            "detail": f"var{i}: такти {segment.parts[0].getElementsByClass(stream.Measure)[0].number}"
                       f"-{segment.parts[0].getElementsByClass(stream.Measure)[-1].number}"
                       if segment.parts else "var range n/a",
            "n_variations": len(segments),
        })

    if not dry_run:
        # прибираємо оригінали, щоб не тренуватись і на цілій пісні, і на варіаціях одночасно
        arrangement_path.unlink()
        melody_path.unlink()

    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset-root", type=Path, default=Path("dataset"))
    ap.add_argument("--dry-run", action="store_true",
                     help="Тільки показати, що буде зроблено, нічого не записувати/видаляти")
    ap.add_argument("--min-measures", type=int, default=1,
                     help="Мінімальна довжина варіації в тактах. Коротші варіації "
                          "(напр. короткі вступи/затакти) приєднуються до сусідньої "
                          "(або, з --drop-short, видаляються повністю). "
                          "За замовчуванням 1 = без фільтрації.")
    ap.add_argument("--drop-short", action="store_true",
                     help="Замість злиття коротких варіацій із сусідньою - "
                          "просто видаляти їх (втрата цих тактів).")
    args = ap.parse_args()

    all_rows = []
    melody_dir = args.dataset_root / "melody"
    arrangement_dir = args.dataset_root / "arrangement"

    if not melody_dir.exists() or not arrangement_dir.exists():
        print(f"❌ Не знайдено {melody_dir} або {arrangement_dir}. "
              f"Перевір --dataset-root (очікується dataset/melody і dataset/arrangement).")
        return

    arrangement_files = sorted(
        list(arrangement_dir.glob("*.mxl")) + list(arrangement_dir.glob("*.xml"))
    )

    for arrangement_path in arrangement_files:
        stem = arrangement_path.stem

        if _ALREADY_SPLIT_RE.search(stem):
            # файл вже є результатом попереднього розрізання (напр. попередній
            # запуск перервався на половині датасету) - не чіпаємо повторно
            all_rows.append({
                "song": stem, "status": "ALREADY_SPLIT",
                "detail": "файл вже містить _varN у назві, пропущено", "n_variations": 1,
            })
            continue

        base_id = stem.replace("_full", "")
        # мелодія зазвичай називається {base_id}_melody.mxl, але якщо скрипт
        # запускають ПОВТОРНО на вже розрізаному датасеті (напр. переривання
        # попереднього запуску), копія мелодії для варіації лежить під тим
        # самим іменем, що й файл аранжування - враховуємо і цей випадок,
        # щоб повторний запуск не губив уже готові пари
        melody_candidates = (
            list(melody_dir.glob(f"{base_id}_melody.*"))
            or list(melody_dir.glob(f"{base_id}.*"))
            or list(melody_dir.glob(f"{stem}.*"))
        )
        if not melody_candidates:
            all_rows.append({
                "song": stem, "status": "MISSING_MELODY",
                "detail": str(melody_dir / f"{base_id}_melody.*"), "n_variations": 0,
            })
            continue
        melody_path = melody_candidates[0]

        rows = process_song(
            melody_path, arrangement_path, args.dry_run,
            min_measures=args.min_measures, drop_short=args.drop_short,
        )
        all_rows.extend(rows)

    report_path = args.dataset_root / "split_variations_report.csv"
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["song", "status", "n_variations", "detail"])
        writer.writeheader()
        writer.writerows(all_rows)

    n_split = sum(1 for r in all_rows if r["status"] == "SPLIT_OK")
    n_no_boundary = sum(1 for r in all_rows if r["status"] == "NO_DOUBLE_BARLINE")
    n_missing = sum(1 for r in all_rows if r["status"] == "MISSING_MELODY")
    n_corrupt = sum(1 for r in all_rows if r["status"] == "CORRUPT_ARRANGEMENT")
    n_all_too_short = sum(1 for r in all_rows if r["status"] == "ALL_VARIATIONS_TOO_SHORT")
    n_already_split = sum(1 for r in all_rows if r["status"] == "ALREADY_SPLIT")

    print(f"Готово{' (dry-run, нічого не записано)' if args.dry_run else ''}.")
    print(f"  Розрізано сегментів (SPLIT_OK):      {n_split}")
    print(f"  Пісень без подвійної риски:          {n_no_boundary}  <- перевір їх вручну")
    print(f"  Відсутня мелодія:                    {n_missing}")
    print(f"  Пошкоджені файли аранжування:         {n_corrupt}")
    print(f"  Усі варіації занадто короткі:        {n_all_too_short}  <- пісня залишена цілою, перевір вручну")
    print(f"  Вже було розрізано раніше (пропущено): {n_already_split}")
    print(f"  Повний звіт: {report_path}")


if __name__ == "__main__":
    main()
