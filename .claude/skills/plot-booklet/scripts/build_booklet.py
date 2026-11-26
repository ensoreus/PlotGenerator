#!/usr/bin/env python3
"""Зібрати дво-згинний буклет (A4 landscape, 2 сторінки) з plot.json у PDF.

    python3 build_booklet.py plot.json --out ЛігвоЯщірки
        -> ЛігвоЯщірки.html, ЛігвоЯщірки.pdf, palette.json

Палітра: якщо в plot.json немає "palette", вона виводиться з cover_image
(scripts/palette.py). Для genre="christian" завжди береться фіксована палітра.

Рендер: Google Chrome --headless --print-to-pdf. Лише stdlib.
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
CSS = os.path.join(SKILL, "assets", "booklet.css")
LOGOS = os.path.join(SKILL, "assets", "logos")

sys.path.insert(0, HERE)
import palette as palette_mod  # noqa: E402

GENRE_LOGO = {
    "romantic":  "romantic_plot_logo.png",
    "detective": "detective_plot_logo.png",
    "drama":     "drama_plot_logo.png",
    "christian": "christian_plot_logo.png",
}

GENRE_ALIASES = {
    "романтичний": "romantic", "romance": "romantic", "romantic": "romantic",
    "детективний": "detective", "detective": "detective",
    "драматичний": "drama", "драма": "drama", "drama": "drama",
    "християнський": "christian", "christian": "christian",
}

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
]


def e(s):
    return html.escape(str(s or ""), quote=False)


def norm_genre(g):
    key = (g or "").strip().lower()
    if key not in GENRE_ALIASES:
        raise SystemExit("невідомий жанр: %r (очікую: %s)" % (g, ", ".join(sorted(set(GENRE_ALIASES)))))
    return GENRE_ALIASES[key]


def file_url(path):
    return "file://" + os.path.abspath(path).replace(" ", "%20")


# ------------------------------------------------------------------- секції

# Підгонка кегля відбувається просто на сторінці, до того як Chrome друкує PDF:
# так вистачає одного запуску браузера. Звіт вилітає у console.log, а той —
# у stderr Chrome (--enable-logging=stderr), звідки його читає to_pdf().
FIT_SCRIPT = """
<script>
(function () {
  var FLOOR = %(floor)s;
  var VARS = {facts: '--facts-scale', characters: '--chars-scale',
              conflicts: '--conflicts-scale', story: '--story-scale',
              title: '--title-scale'};
  // scrollHeight не годиться: він ніколи не менший за clientHeight, тож недобір
  // тексту з нього не видно. Міряємо по реальному низу дітей.
  function fillOf(p) {
    var cs = getComputedStyle(p), pr = p.getBoundingClientRect();
    var top = pr.top + parseFloat(cs.paddingTop);
    var avail = pr.height - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
    var bottom = top;
    [].forEach.call(p.children, function (c) {
      if (c.dataset.nofill === undefined) bottom = Math.max(bottom, c.getBoundingClientRect().bottom);
    });
    return avail > 0 ? (bottom - top) / avail : 1;
  }
  function overflows(p) { return fillOf(p) > 1.002; }
  function shrink(p, v, from) {
    var root = document.documentElement, s = from;
    for (var i = 0; i < 16 && overflows(p) && s > FLOOR; i++) {
      s = Math.max(FLOOR, s - 0.02);
      root.style.setProperty(v, s.toFixed(3));
      void p.offsetHeight;
    }
    return s;
  }
  function fit() {
    var root = document.documentElement, report = {};
    document.querySelectorAll('.panel').forEach(function (p) {
      var id = p.dataset.id, v = VARS[id], s = 1, dropped = false;
      if (v && %(enabled)s) {
        s = shrink(p, v, 1);
        // ілюстрація конфліктів — «якщо є місце»: коли навіть на мінімальному
        // кеглі не влазить, знімаємо картинку і повертаємо нормальний кегль
        if (overflows(p) && p.querySelector('.inner-figure')) {
          p.classList.add('no-figure');
          dropped = true;
          root.style.setProperty(v, '1');
          void p.offsetHeight;
          s = shrink(p, v, 1);
        }
      }
      report[id] = {fill: +fillOf(p).toFixed(3), scale: +s.toFixed(3)};
      if (dropped) report[id].figure = 'dropped';
    });
    console.log('FIT' + JSON.stringify(report) + 'FIT');
  }
  if (document.readyState === 'complete') fit();
  else window.addEventListener('load', fit);
})();
</script>
"""


def render_title(plot, genre, base):
    t = plot["title"].upper()
    cls = "plot-title"
    if len(t) > 26:
        cls += " is-xlong"
    elif len(t) > 15:
        cls += " is-long"

    cover = plot.get("cover_image")
    fig = ""
    if cover:
        fig = '<figure class="cover-figure"><img src="%s" alt=""></figure>' % e(file_url(_rel(cover, base)))

    logo = os.path.join(LOGOS, GENRE_LOGO[genre])
    return f"""<section class="panel panel--title" data-id="title">
  <div class="char-count">{e(plot["characters_count"])}</div>
  <hr class="rule-thin">
  <h1 class="{cls}">{e(t)}</h1>
  <hr class="rule-thick">
  {fig}
  <p class="logline">{e(plot.get("logline", ""))}</p>
  <div class="genre-logo" data-nofill><img src="{e(file_url(logo))}" alt=""></div>
</section>"""


def render_characters(plot):
    items = "\n".join(
        '  <p class="character"><span class="name">%s</span> — %s</p>' % (e(c["name"]), e(c["bio"]))
        for c in plot["characters"]
    )
    return f"""<section class="panel panel--characters" data-id="characters">
  <hr class="rule-thin">
  <h2 class="section-title">ПЕРСОНАЖІ</h2>
{items}
</section>"""


def render_facts(plot):
    groups = []
    for g in plot["facts"]:
        rows = "\n".join(
            '    <p class="fact"><span class="key">%s</span> — %s</p>' % (e(f["fact"]), e(f["text"]))
            for f in g["items"]
        )
        groups.append('  <div class="fact-group">\n    <p class="owner">%s</p>\n%s\n  </div>'
                      % (e(g["character"]), rows))
    return """<section class="panel panel--facts" data-id="facts">
  <hr class="rule-thin">
  <h2 class="section-title">ФАКТИ</h2>
%s
</section>""" % "\n".join(groups)


def render_conflicts(plot, base):
    inner = plot.get("inner_image")
    fig = ""
    if inner:
        fig = '  <figure class="inner-figure"><img src="%s" alt=""></figure>' % e(file_url(_rel(inner, base)))

    blocks = []
    for c in plot["conflicts"]:
        sides = ['    <p class="side"><span class="who">%s</span> %s</p>' % (e(c["a"]), e(c["a_wants"]))]
        if c.get("b_wants"):
            sides.append('    <p class="side"><span class="who">%s</span> %s</p>' % (e(c["b"]), e(c["b_wants"])))
        blocks.append('  <div class="conflict">\n    <p class="pair">%s : %s</p>\n%s\n  </div>'
                      % (e(c["a"]), e(c["b"]), "\n".join(sides)))

    heading = "КОНФЛІКТ" if len(plot["conflicts"]) == 1 else "КОНФЛІКТИ"
    return """<section class="panel panel--conflicts" data-id="conflicts">
%s  <h2 class="section-title">%s</h2>
  <hr class="rule-thin">
%s
</section>""" % (fig, heading, "\n".join(blocks))


DIALOGUE = re.compile(r"^\s*[—–\-«\"]")


def render_story(plot):
    paras = [p.strip() for p in plot["story"].split("\n") if p.strip()]
    body = "\n".join(
        '  <p class="%s">%s</p>' % ("dialogue" if DIALOGUE.match(p) else "", e(p))
        for p in paras
    )
    return '<section class="panel panel--story" data-id="story">\n%s\n</section>' % body


def _rel(path, base):
    return path if os.path.isabs(path) else os.path.join(base, path)


# --------------------------------------------------------------------- HTML

SCALE_VAR = {"facts": "--facts-scale", "characters": "--chars-scale",
             "conflicts": "--conflicts-scale", "story": "--story-scale"}


def build_html(plot, genre, pal, base, fit=True, floor=0.78):
    css = open(CSS, encoding="utf-8").read()
    overrides = "\n".join(
        "  --%s: %s;" % (k.replace("_", "-"), v)
        for k, v in pal.items()
        if k in ("page_bg", "panel_bg", "ink", "heading", "rule", "frame", "muted")
    )
    sizes = ""
    if plot.get("story_size"):
        sizes += "  --story-size: %s;\n" % plot["story_size"]
    if plot.get("body_size"):
        sizes += "  --body-size: %s;\n" % plot["body_size"]
    for panel, val in (plot.get("scales") or {}).items():
        if panel in SCALE_VAR:
            sizes += "  %s: %.4f;\n" % (SCALE_VAR[panel], float(val))

    fit_script = FIT_SCRIPT % {"floor": floor, "enabled": "true" if fit else "false"}

    return f"""<!DOCTYPE html>
<html lang="uk"><head><meta charset="utf-8"><title>{e(plot['title'])}</title>
<style>
{css}
:root {{
{overrides}
{sizes}}}
</style></head>
<body>
<div class="sheet sheet--outer">
{render_facts(plot)}
{render_characters(plot)}
{render_title(plot, genre, base)}
</div>
<div class="sheet sheet--inner">
{render_conflicts(plot, base)}
{render_story(plot)}
</div>
{fit_script}</body></html>
"""


# --------------------------------------------------------------------- Chrome

def find_chrome():
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    p = shutil.which("chromium") or shutil.which("google-chrome")
    if p:
        return p
    raise SystemExit("не знайдено Chrome/Chromium — встанови або передай --chrome")


FIT_RE = re.compile(r"FIT(\{.*?\})FIT", re.S)


def to_pdf(html_path, pdf_path, chrome, timeout=90):
    """Один запуск Chrome: сторінка сама підганяє кегль на `load`, потім друкується.

    Chrome headless на macOS часто не завершується сам після --print-to-pdf,
    тож чекаємо на готовий файл і гасимо процес власноруч. Звіт про
    заповненість панелей приходить через console.log -> stderr.
    Повертає {panel_id: {"fill": float, "scale": float}}.
    """
    pdf_path = os.path.abspath(pdf_path)
    if os.path.exists(pdf_path):
        os.unlink(pdf_path)
    profile = os.path.join(os.path.dirname(pdf_path), ".chrome-profile")
    shutil.rmtree(profile, ignore_errors=True)
    cmd = [
        chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--no-first-run", "--no-default-browser-check", "--disable-extensions",
        "--enable-logging=stderr", "--v=0",
        "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=15000", "--user-data-dir=" + profile,
        "--print-to-pdf=" + pdf_path,
        file_url(html_path),
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    deadline = time.time() + timeout
    stable, last = 0, -1
    try:
        while time.time() < deadline:
            if os.path.exists(pdf_path):
                size = os.path.getsize(pdf_path)
                stable = stable + 1 if size == last and size > 0 else 0
                last = size
                if stable >= 2:
                    break
            if proc.poll() is not None:
                break
            time.sleep(0.4)
    finally:
        if proc.poll() is None:
            proc.terminate()
    try:
        err = proc.communicate(timeout=10)[1]
    except subprocess.TimeoutExpired:
        proc.kill()
        err = proc.communicate()[1]
    shutil.rmtree(profile, ignore_errors=True)
    err = (err or b"").decode("utf-8", "replace")

    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
        sys.stderr.write(err[-4000:])
        raise SystemExit("Chrome не створив PDF")

    m = FIT_RE.search(err)
    if not m:
        return {}
    try:
        return json.loads(m.group(1).replace('\\"', '"'))
    except ValueError:
        return {}


def preview(pdf_path, out_prefix, dpi=90):
    """Відрендерити PDF у PNG для візуальної перевірки (потрібен ghostscript)."""
    gs = shutil.which("gs")
    if not gs:
        return []
    subprocess.run([gs, "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=png16m", "-r%d" % dpi,
                    "-sOutputFile=%s_%%d.png" % out_prefix, pdf_path],
                   check=True, capture_output=True)
    return sorted(p for p in
                  (["%s_%d.png" % (out_prefix, i) for i in (1, 2)])
                  if os.path.exists(p))


# ---------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plot", help="шлях до plot.json")
    ap.add_argument("--out", help="префікс вихідних файлів (типово — назва сюжету)")
    ap.add_argument("--chrome")
    ap.add_argument("--no-preview", action="store_true")
    ap.add_argument("--no-fit", action="store_true",
                    help="не підганяти кегль автоматично під висоту панелей")
    a = ap.parse_args()

    plot = json.load(open(a.plot, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(a.plot))
    genre = norm_genre(plot.get("genre"))

    if plot.get("palette"):
        pal = plot["palette"]
    elif genre == "christian":
        pal = dict(palette_mod.CHRISTIAN)
    elif plot.get("cover_image"):
        pal = palette_mod.build_palette(_rel(plot["cover_image"], base))
    else:
        raise SystemExit("немає ні palette, ні cover_image — нема з чого брати кольори")

    # --out трактуємо відносно поточної теки (як будь-який шлях у команді),
    # а типову назву з title — відносно теки самого plot.json
    if a.out:
        out = os.path.abspath(a.out)
    else:
        out = os.path.join(base, re.sub(r"[^\w\-]+", "_", plot["title"]))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    with open(out + ".palette.json", "w", encoding="utf-8") as f:
        json.dump(pal, f, ensure_ascii=False, indent=2)

    chrome = a.chrome or find_chrome()
    html_path = out + ".html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(build_html(plot, genre, pal, base, fit=not a.no_fit))

    report = to_pdf(html_path, out + ".pdf", chrome)

    print(out + ".pdf")
    print(out + ".html")
    print(out + ".palette.json")
    if not a.no_preview:
        for p in preview(out + ".pdf", out + "_preview"):
            print(p)

    if not report:
        sys.stderr.write("! не вдалось прочитати звіт про заповненість — перевір прев'ю очима\n")
        return
    sys.stderr.write("панелі (заповненість / кегль): %s\n" % ", ".join(
        "%s %d%%/%d%%" % (k, round(v["fill"] * 100), round(v["scale"] * 100))
        for k, v in sorted(report.items())))
    for k, v in sorted(report.items()):
        if v["fill"] > 1.005:
            sys.stderr.write("  !! %s: текст обрізано (%d%%) — скороти\n" % (k, round(v["fill"] * 100)))
        elif v["scale"] < 0.999:
            sys.stderr.write("  ! %s: кегль стиснуто до %d%% — краще скоротити текст\n"
                             % (k, round(v["scale"] * 100)))
        if v.get("figure") == "dropped":
            sys.stderr.write("  ~ %s: ілюстрацію знято — не було місця\n" % k)
    if report.get("story", {}).get("fill", 1) < 0.55:
        sys.stderr.write("  ~ story: заповнено лише %d%% блоку — сюжет варто розширити\n"
                         % round(report["story"]["fill"] * 100))


if __name__ == "__main__":
    main()
