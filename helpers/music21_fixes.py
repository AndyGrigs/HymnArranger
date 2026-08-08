"""
music21_fixes.py

Обхідні шляхи для відомих багів music21 (версія 10.5.0), які ламають
запис .mxl/.musicxml для файлів нашого датасету.
"""

from music21 import chord, expressions, stream


def strip_degenerate_arpeggios(score: "stream.Score") -> int:
    """
    Прибирає ArpeggioMarkSpanner, що обгортає лише ОДНУ звичайну ноту
    (не акорд).

    Навіщо: music21.musicxml.m21ToXml.appendArpeggioMarkSpannersToNotations
    викликає len(ams[0]), очікуючи Chord (в нього є len() - кількість нот).
    Якщо єдиний елемент спанера - Note (без len()), запис у MusicXML/.mxl
    падає з `TypeError: object of type 'Note' has no len()`.

    Такий одно-нотний "арпеджіо"-спанер і музично беззмістовний (нема що
    "розкладати"), тому просто видаляємо його, не чіпаючи саму ноту.

    Повертає кількість видалених спанерів.
    """
    removed = 0
    for ams in list(score.recurse().getElementsByClass(expressions.ArpeggioMarkSpanner)):
        spanned = ams.getSpannedElements()
        if len(spanned) == 1 and not isinstance(spanned[0], chord.Chord):
            score.remove(ams, recurse=True)
            removed += 1
    return removed
