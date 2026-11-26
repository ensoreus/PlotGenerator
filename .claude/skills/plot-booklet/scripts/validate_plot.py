#!/usr/bin/env python3
"""Перевірити plot.json на правила жанру до того, як збирати PDF.

    python3 validate_plot.py plot.json

Помилки (exit 1) — те, що ламає правила гри. Попередження — те, що варто
поправити, але буклет усе одно збереться.
"""

import argparse
import itertools
import json
import sys

FACT_VOCAB = [
    "Дім", "Кохання", "Свобода", "Жертва", "Мир", "Святість", "Зброя", "Кар'єра",
    "Алібі", "Насильство", "Експеримент", "Зневіра", "Турбота", "Звільнення",
    "Гріх", "Друг", "Вагітність", "Зрада", "Шлюб", "Батьківщина", "Документ",
    "Суд", "Речовий доказ", "Дитина", "Борг", "Проект", "Смерть", "Традиція",
    "Закон", "Християнство",
]

GENRES = {"romantic", "detective", "drama", "christian"}
ALIASES = {"романтичний": "romantic", "детективний": "detective",
           "драматичний": "drama", "християнський": "christian"}


def check(plot):
    err, warn = [], []
    genre = ALIASES.get(str(plot.get("genre", "")).lower(), str(plot.get("genre", "")).lower())
    if genre not in GENRES:
        err.append("невідомий жанр: %r" % plot.get("genre"))

    chars = plot.get("characters") or []
    names = [c["name"] for c in chars]
    n = len(chars)

    if plot.get("characters_count") != n:
        err.append("characters_count=%r, а персонажів у списку %d"
                   % (plot.get("characters_count"), n))

    initials = [x[:1].upper() for x in names]
    dupes = {i for i in initials if initials.count(i) > 1}
    if dupes:
        warn.append("імена починаються на ту саму літеру: %s" % ", ".join(sorted(dupes)))

    # ---- факти: рівно два на персонажа
    fact_owners = [g["character"] for g in plot.get("facts", [])]
    if sorted(fact_owners) != sorted(names):
        err.append("блоки фактів не збігаються зі списком персонажів: %s проти %s"
                   % (fact_owners, names))
    for g in plot.get("facts", []):
        k = len(g.get("items", []))
        if k != 2:
            err.append("%s: фактів %d, а має бути 2" % (g["character"], k))
        for f in g.get("items", []):
            if f["fact"] not in FACT_VOCAB:
                warn.append("%s: факт «%s» поза рекомендованим списком" % (g["character"], f["fact"]))
            if len(f["fact"].split()) > 2:
                warn.append("%s: факт «%s» — має бути одне слово" % (g["character"], f["fact"]))

    # ---- конфлікти
    conflicts = plot.get("conflicts") or []
    pairs = [(c["a"], c["b"]) for c in conflicts]
    outsiders = sorted({b for _a, b in pairs if b not in names})

    if genre == "detective":
        if len(outsiders) > 1:
            err.append("у детективі має бути одна жертва поза грою, а знайдено: %s" % outsiders)
        victim = outsiders[0] if outsiders else None
        if not victim:
            err.append("у детективі бракує жертви — персонажа, згаданого в конфліктах, але не в списку гравців")
        else:
            missing = [x for x in names if (x, victim) not in pairs]
            if missing:
                err.append("немає мотиву проти жертви «%s» у: %s" % (victim, ", ".join(missing)))
        ring = [(a, b) for a, b in pairs if b in names]
        if n > 2:
            # кожен має рівно один конфлікт із іншим гравцем, і всі — по колу
            src = [a for a, _b in ring]
            dst = [b for _a, b in ring]
            if len(ring) != n or sorted(src) != sorted(names) or sorted(dst) != sorted(names):
                err.append("міжгравцеві конфлікти не утворюють коло: очікую %d штук, "
                           "кожен персонаж один раз як ініціатор і один раз як опонент; маю %s"
                           % (n, ring))
        elif n == 2 and len(ring) != 1:
            err.append("на двох персонажів очікую один конфлікт між ними, маю %d" % len(ring))
    else:
        if outsiders:
            err.append("поза детективом усі конфлікти мають бути між гравцями, а тут згадано: %s" % outsiders)
        want = {frozenset(p) for p in itertools.combinations(names, 2)}
        have = {frozenset(p) for p in pairs}
        if want - have:
            err.append("бракує конфліктів між: %s"
                       % "; ".join(" : ".join(sorted(p)) for p in sorted(want - have, key=sorted)))
        if have - want:
            err.append("зайві конфлікти: %s"
                       % "; ".join(" : ".join(sorted(p)) for p in sorted(have - want, key=sorted)))
        for c in conflicts:
            if not c.get("b_wants"):
                warn.append("%s : %s — вказано позицію лише одного боку" % (c["a"], c["b"]))

    # ---- тексти
    if not plot.get("logline"):
        err.append("немає logline")
    elif plot["logline"].count(".") > 1:
        warn.append("logline має бути одним реченням")

    story = plot.get("story", "")
    if not story:
        err.append("немає story")
    elif len(story) > 4200:
        warn.append("story %d символів — може не влізти навіть після підгонки" % len(story))

    if genre != "christian" and not plot.get("cover_image") and not plot.get("palette"):
        err.append("немає cover_image — нема з чого брати палітру")

    return err, warn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plot")
    a = ap.parse_args()
    err, warn = check(json.load(open(a.plot, encoding="utf-8")))
    for w in warn:
        print("warn: " + w)
    for x in err:
        print("ПОМИЛКА: " + x)
    if err:
        sys.exit(1)
    print("ok" + (" (%d попереджень)" % len(warn) if warn else ""))


if __name__ == "__main__":
    main()
