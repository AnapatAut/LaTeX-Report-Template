#!/usr/bin/env python3
"""Check the template after a change.

    python3 scripts/check.py             # builds, content, page flow, spacing (~10 s)
    python3 scripts/check.py --full      # also README examples and the widow test
    python3 scripts/check.py --render    # also page images in build/pages/ to look at
    python3 scripts/check.py --selftest  # prove the checks work: each one must
                                         # catch a deliberately broken copy (~40 s)

Needs: latexmk + LuaLaTeX, poppler-utils (pdftohtml, pdftoppm).
The spacing checks and --render also need Pillow (python3-pil); without it
they are skipped with a note. Builds go to build/ (git-ignored), rebuilt
from scratch on every run and deleted afterwards, except when a check failed
(logs to read) or with --render (page images to look at).
Exit code 0 = all checks passed.
"""
import argparse
import glob
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = ["main", "test"]
PROBLEM = re.compile(r"^! |Warning|Overfull|Underfull|undefined|Missing character", re.M)
# Formatting that belongs in style.tex, never in content files
FORBIDDEN = re.compile(
    r"\\(centering|raggedright|raggedleft|tiny|scriptsize|footnotesize|small|"
    r"normalsize|large|Large|LARGE|huge|vspace|hspace|vskip|hskip|smallskip|"
    r"medskip|bigskip|setlength|addtolength|captionsetup|fontsize|selectfont|"
    r"linespread|noindent|newline|linebreak|quad|qquad|arraystretch|tabcolsep|"
    r"resizebox|scalebox|textcolor|rowcolor)\b"
    r"|\\begin\{(center|flushleft|flushright|minipage|tabular)\}"
    r"|\\begin\{(figure|table)\}\[|\{0\.\d+\\linewidth\}\{|\\\\\[")
NUMBERED = re.compile(r"^\d+(\.\d+)*\.?\s")
FILLER = re.compile(r"^Paragraph [A-Z]\.")    # paragraphs in tests/t7-page-breaks.tex
BODY_TOP, BODY_BOTTOM = 60, 725               # pt; outside = header and page number


# ---------------------------------------------------------------- results
class Results:
    def __init__(self):
        self.failed = []

    def check(self, ok, label, detail=""):
        print(f"  {'ok  ' if ok else 'FAIL'} {label}" + (f": {detail}" if detail else ""))
        if not ok:
            self.failed.append(label)
        return ok


# ---------------------------------------------------------------- building
def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def build(root, doc, outdir, jobname=None, pre=""):
    """Build doc.tex; return (pdf or None, log text). None means the build failed."""
    os.makedirs(outdir, exist_ok=True)
    job = jobname or doc
    pdf = os.path.join(outdir, f"{job}.pdf")
    if os.path.exists(pdf):
        os.remove(pdf)
    if pre:   # extra code before the document (widow control build)
        for _ in range(2):
            p = run(["lualatex", "-interaction=nonstopmode", "-halt-on-error",
                     f"-output-directory={outdir}", f"-jobname={job}",
                     pre + r"\input{" + doc + "}"], root)
    else:
        p = run(["latexmk", "-lualatex", "-interaction=nonstopmode", "-halt-on-error",
                 f"-outdir={outdir}", f"{doc}.tex"], root)
    logf = os.path.join(outdir, f"{job}.log")
    log = open(logf, errors="replace").read() if os.path.exists(logf) else p.stdout
    return (pdf if p.returncode == 0 and os.path.exists(pdf) else None), log


# ---------------------------------------------------------------- reading pages
def read_pages(pdf):
    """Per page: text lines top to bottom as (top pt, size pt, bold, text)."""
    xml = subprocess.run(["pdftohtml", "-xml", "-i", "-fontfullname", "-stdout", pdf],
                         capture_output=True, text=True).stdout
    fonts, pages = {}, []
    for page in re.findall(r"<page .*?</page>", xml, re.S):
        for fid, size, fam in re.findall(r'<fontspec id="(\d+)" size="(\d+)" family="([^"]*)"', page):
            fonts[fid] = (int(size) / 1.5, bool(re.search(r"SemiBold|Bold", fam)))
        chunks = []
        for top, left, fid, inner in re.findall(
                r'<text top="(\d+)" left="(\d+)" width="\d+" height="\d+" font="(\d+)">(.*?)</text>', page):
            text = html.unescape(re.sub(r"<[^>]+>", "", inner)).strip()
            if text:
                chunks.append((int(top) / 1.5, int(left) / 1.5, fid, text))
        lines = []
        for top, left, fid, text in sorted(chunks):
            if lines and abs(lines[-1][0] - top) < 2:
                lines[-1][3].append((left, fid, text))
            else:
                lines.append([top, None, None, [(left, fid, text)]])
        out = []
        for top, _, _, parts in lines:
            parts.sort()
            size, bold = fonts[parts[0][1]]
            if BODY_TOP < top < BODY_BOTTOM:
                out.append((top, size, bold, " ".join(p[2] for p in parts)))
        pages.append(out)
    return pages


# ---------------------------------------------------------------- page-flow detectors
def is_heading(line, body_size=11):
    _, size, bold, text = line
    return bool(bold and size >= body_size - 0.5 and (NUMBERED.match(text) or text == "References"))


def content_pages(pages):
    """Pages from the first numbered Heading 1 on (skips title and contents pages)."""
    for i, lines in enumerate(pages):
        if any(l[2] and l[1] > 12.5 and NUMBERED.match(l[3]) for l in lines):
            return list(enumerate(pages, 1))[i:]
    return []


def stranded_headings(pages):
    return [n for n, lines in content_pages(pages)
            if lines and is_heading([l for l in lines if l[1] > 10][-1])]


def widows_orphans(pages):
    widows, orphans = [], []
    for n, lines in content_pages(pages):
        text = [l[3] for l in lines if l[1] > 10]       # without footnotes
        if len(text) >= 2 and not FILLER.match(text[0]) and FILLER.match(text[1]):
            widows.append(n)        # page starts with the last line of a paragraph
        if text and FILLER.match(text[-1]) and len(text[-1]) > 60:
            orphans.append(n)       # page ends with the first line of a paragraph
    return widows, orphans


# ---------------------------------------------------------------- spacing
def have_pil():
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def ink_gaps(png, top=120, bottom=1450):
    """Gaps (pt) between vertical runs of ink on a 144 dpi grey page image."""
    from PIL import Image
    im = Image.open(png).convert("L")
    w, _ = im.size
    px = im.load()
    rows = [any(px[x, y] < 200 for x in range(144, w - 144, 2)) for y in range(top, bottom)]
    runs, start = [], None
    for i, r in enumerate(rows + [False]):
        if r and start is None:
            start = i
        if not r and start is not None:
            runs.append(((start + top) / 2, (i + top) / 2))
            start = None
    return [b[0] - a[1] for a, b in zip(runs, runs[1:])]


PROBE = r"""\documentclass[11pt]{article}
\input{style}
\begin{document}
\section{Hg One}
Xg text a.

Xg text b.

\begin{figure}\includegraphics[width=\linewidth,height=1.2cm]{example-image}
\caption{Xg cap.}\end{figure}

Xg text c.

\begin{table}\caption{Xg cap.}\begin{autotable}{L R}\toprule A & 1\\\bottomrule
\end{autotable}\end{table}

Xg text d.
\subsection{Hg Two}
Xg text e.
\subsubsection{Hg Three}
Xg text f.
\end{document}
"""
PROBE_GAPS = ["H1-text", "para", "text-fig", "fig-cap", "cap-text", "text-tcap",
              "tcap-table", "rule-row", "row-rule", "table-text", "text-H2",
              "H2-text", "text-H3", "H3-text"]


def spacing_checks(root, build_dir, res):
    path = os.path.join(root, "probe-check.tex")
    open(path, "w").write(PROBE)
    try:
        pdf, log = build(root, "probe-check", os.path.join(build_dir, "probe"))
    finally:
        os.remove(path)
    if not res.check(pdf is not None and not PROBLEM.search(log), "spacing probe builds"):
        return
    prefix = os.path.join(build_dir, "probe", "p")
    run(["pdftoppm", "-r", "144", "-gray", "-png", "-f", "1", "-l", "1", pdf, prefix], root)
    g = ink_gaps(glob.glob(prefix + "-*.png")[0])
    if not res.check(len(g) == len(PROBE_GAPS), "spacing probe layout as expected",
                     "" if len(g) == len(PROBE_GAPS) else
                     f"{len(g)} gaps, expected {len(PROBE_GAPS)}; update PROBE_GAPS"):
        return
    m = dict(zip(PROBE_GAPS, g))
    print("  gaps (pt): " + ", ".join(f"{k} {v:.1f}" for k, v in m.items()))
    cap = float(re.search(r"\\newcommand\{\\CaptionGap\}\{([\d.]+)\}",
                          open(os.path.join(root, "style.tex")).read()).group(1))
    for k in ("fig-cap", "tcap-table"):
        res.check(abs(m[k] - cap) <= 1.5, f"{k} matches \\CaptionGap ({cap:g} pt)", f"{m[k]:.1f}")
    for k in ("text-fig", "cap-text", "text-tcap", "table-text"):
        res.check(m["para"] - 2 <= m[k] <= m["para"] + 10,
                  f"{k} close to the paragraph gap ({m['para']:.1f})", f"{m[k]:.1f}")
    h = [m["H1-text"], m["H2-text"], m["H3-text"]]
    res.check(max(h) - min(h) <= 2.5, "heading-to-text gaps alike", " / ".join(f"{x:.1f}" for x in h))
    res.check(min(h) > m["para"] / 3, "headings set apart from their text", f"{min(h):.1f}")
    res.check(abs(m["rule-row"] - m["row-rule"]) <= 1, "table cell padding even",
              f"{m['rule-row']:.1f} / {m['row-rule']:.1f}")


# ---------------------------------------------------------------- README
def readme_examples(root, build_dir, res):
    blocks = re.findall(r"```latex\n(.*?)```", open(os.path.join(root, "README.md")).read(), re.S)
    parts = []
    for b in blocks:
        b = (b.replace("{name}", "{example-image}").replace("{left}", "{example-image-a}")
             .replace("{right}", "{example-image-b}").replace("...", "Text"))
        if b.lstrip().startswith(r"\begin{autotable}"):
            b = "\\begin{table}\\caption{Example.}\n" + b + "\\end{table}\n"
        parts.append(b)
    doc = (r"\documentclass[11pt]{article}\input{style}\title{T}\author{A}\course{C}"
           "\n\\begin{document}\\maketitle\n\\section{S}\n" + "\n\nText.\n\n".join(parts) +
           "\n\\cref{fig:name}, \\cref{tab:name}, \\cref{eq:name}.\n\\end{document}\n")
    path = os.path.join(root, "readme-check.tex")
    open(path, "w").write(doc)
    try:
        pdf, log = build(root, "readme-check", os.path.join(build_dir, "readme"))
    finally:
        os.remove(path)
    found = PROBLEM.findall(log)
    res.check(pdf is not None and not found, f"README examples compile ({len(blocks)} blocks)",
              "see build/readme/readme-check.log" if pdf is None or found else "")


# ---------------------------------------------------------------- page images
def render(root, build_dir, pdfs):
    from PIL import Image
    out = os.path.join(build_dir, "pages")
    os.makedirs(out, exist_ok=True)
    for pdf in pdfs:
        name = os.path.splitext(os.path.basename(pdf))[0]
        run(["pdftoppm", "-r", "60", "-png", pdf, os.path.join(out, name)], root)
        files = sorted(glob.glob(os.path.join(out, name + "-*.png")))
        for k in range(0, len(files), 6):
            ims = [Image.open(f) for f in files[k:k + 6]]
            w, h = ims[0].size
            sheet = Image.new("RGB", (3 * (w + 8), 2 * (h + 8)), "grey")
            for j, im in enumerate(ims):
                sheet.paste(im, ((j % 3) * (w + 8), (j // 3) * (h + 8)))
            sheet.save(os.path.join(out, f"{name}-sheet{k // 6 + 1}.png"))
        for f in files:
            os.remove(f)
    print(f"  page images: {out}/")


# ---------------------------------------------------------------- all checks
def check_all(root, full=False, images=False):
    res = Results()
    build_dir = os.path.join(root, "build")
    shutil.rmtree(build_dir, ignore_errors=True)

    print("Build")
    pdfs = {}
    for doc in DOCS:
        pdf, log = build(root, doc, build_dir)
        found = PROBLEM.findall(log)
        if res.check(pdf is not None and not found, f"{doc}.tex builds with no errors or warnings",
                     "" if pdf and not found else
                     f"{'build failed' if pdf is None else f'{len(found)} problems'}, see build/{doc}.log"):
            pdfs[doc] = pdf
        elif pdf is not None:
            pdfs[doc] = pdf          # warnings only: the layout can still be checked

    print("Content files")
    hits = []
    for f in sorted(glob.glob(os.path.join(root, "sections", "*.tex")) +
                    glob.glob(os.path.join(root, "tests", "*.tex"))):
        for i, line in enumerate(open(f), 1):
            if FORBIDDEN.search(line.split("%")[0]):
                hits.append(f"{os.path.relpath(f, root)}:{i}")
    res.check(not hits, "no manual formatting in sections/ and tests/", ", ".join(hits[:5]))

    print("Page flow")
    for doc in DOCS:
        if doc not in pdfs:
            res.check(False, f"{doc}: page flow", "skipped, no PDF")
            continue
        pages = read_pages(pdfs[doc])
        found = sum(is_heading(l) for _, lines in content_pages(pages) for l in lines)
        if not res.check(found > 0, f"{doc}: headings found in the PDF text",
                         "" if found else "PDF text not readable; page-flow checks skipped"):
            continue
        s = stranded_headings(pages)
        res.check(not s, f"{doc}: no page ends with a heading", f"pages {s}" if s else "")
        w, o = widows_orphans(pages)
        res.check(not w and not o, f"{doc}: no widows or orphans",
                  f"widows on pages {w}, orphans on pages {o}" if w or o else "")
    if full:
        pdf, _ = build(root, "test", os.path.join(build_dir, "control"), jobname="control",
                       pre=r"\AtBeginDocument{\clubpenalty=0 \widowpenalty=0 \displaywidowpenalty=0}")
        w, o = widows_orphans(read_pages(pdf)) if pdf else ([], [])
        res.check(bool(w and o), "page-break test makes a widow and an orphan with the penalties off",
                  "" if w and o else "retune paragraph lengths in tests/t7-page-breaks.tex")

    print("Spacing")
    if not have_pil():
        print("  skip (needs Pillow: sudo apt install python3-pil)")
    else:
        spacing_checks(root, build_dir, res)
        for doc, pdf in pdfs.items():
            d = os.path.join(build_dir, "gaps", doc)
            os.makedirs(d)
            run(["pdftoppm", "-r", "144", "-gray", "-png", pdf, os.path.join(d, "p")], root)
            worst = max(g for f in glob.glob(os.path.join(d, "*.png")) for g in ink_gaps(f))
            res.check(worst <= 32, f"{doc}: no gap between blocks over 32 pt", f"largest {worst:.1f}")

    if full:
        print("README")
        readme_examples(root, build_dir, res)
    if images:
        print("Render")
        if have_pil():
            render(root, build_dir, list(pdfs.values()))
        else:
            print("  skip (needs Pillow)")

    print(f"\n{'All checks passed.' if not res.failed else f'{len(res.failed)} check(s) failed.'}")
    if res.failed or images:
        print(f"Build files kept in {build_dir}/")
    else:
        shutil.rmtree(build_dir, ignore_errors=True)
    return res.failed


# ---------------------------------------------------------------- self-test
def unit_tests():
    """Page-flow detectors on made-up pages: (top, size, bold, text).
    Sizes as pdftohtml reports them: 11 pt body text reads as 10.67."""
    h1 = (100, 14, True, "1. Introduction")
    text = (120, 11, False, "Some text.")
    cases = [
        ("heading at page end is found",
         stranded_headings([[h1, text, (700, 12, True, "2.1 Data")]]), [1]),
        ("Heading 3 (body size, bold) at page end is found",
         stranded_headings([[h1, text, (700, 10.67, True, "2.1.1 Rules")]]), [1]),
        ("numbered list item at page end is not a heading",
         stranded_headings([[h1, text, (700, 10.67, False, "1. First step.")]]), []),
        ("bold lead-in list item at page end is not a heading",
         stranded_headings([[h1, text, (700, 11, False, "2. Limitation two. Why.")]]), []),
        ("footnote under a final paragraph is ignored",
         stranded_headings([[h1, (690, 12, True, "2.1 Data"), (700, 11, False, "Text."),
                             (715, 8.67, False, "1 A footnote.")]]), []),
        ("contents pages are skipped",
         stranded_headings([[(100, 14, True, "Contents"), (700, 11, True, "7. Equations")],
                            [h1, text]]), []),
        ("widow is found",
         widows_orphans([[h1, text], [(80, 11, False, "end of a paragraph."),
                                      (100, 11, False, "Paragraph B. Starts here and goes on.")]])[0], [2]),
        ("orphan is found",
         widows_orphans([[h1, text, (700, 11, False,
                                     "Paragraph C. This sentence is filler for the page break test.")]])[1], [1]),
        ("page starting with a whole paragraph is not a widow",
         widows_orphans([[h1, text], [(80, 11, False, "Paragraph B. One line."),
                                      (100, 11, False, "Paragraph C. Next.")]])[0], []),
    ]
    ok = True
    for label, got, want in cases:
        good = got == want
        ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} {label}" + ("" if good else f": got {got}, want {want}"))
    return ok


def edit(path, old, new):
    s = open(path).read()
    assert old in s, f"self-test edit target not found in {path}: {old!r}"
    open(path, "w").write(s.replace(old, new, 1))


# (name, edits [(file, old, new)], text that must appear in a FAIL line)
MUTATIONS = [
    ("build error", [("sections/introduction.tex", "State the goal", r"\undefinedmacro State the goal")],
     "main.tex builds"),
    ("undefined reference", [("sections/introduction.tex", "State the goal", r"See \cref{nolabel}. State the goal")],
     "main.tex builds"),
    ("manual formatting in a test file", [("tests/t1-text.tex", "A second paragraph", r"\small A second paragraph")],
     "no manual formatting"),
    ("figures far from the text", [("style.tex", r"\newcommand{\FloatGap}{18}", r"\newcommand{\FloatGap}{40}")],
     "close to the paragraph gap"),
    ("Heading 3 with no space after", [("style.tex", r"\newcommand{\HeadingThree}{{11}{4}{4}}",
                                        r"\newcommand{\HeadingThree}{{11}{4}{0}}")],
     "heading-to-text gaps alike"),
    ("caption offset wrong", [("style.tex", r"\fpeval{5.5+0.69", r"\fpeval{1.5+0.69")],
     r"fig-cap matches"),
    ("uneven table cell padding", [("style.tex", r"\newcommand{\CellBelow}{\fpeval{\CellEdge+",
                                    r"\newcommand{\CellBelow}{\fpeval{4+\CellEdge+")],
     "table cell padding even"),
    ("widow control off", [("style.tex", r"\widowpenalty=10000", r"\widowpenalty=0")],
     "test: no widows or orphans"),
    ("broken README example", [("README.md", r"\begin{autotable}{L RR RR}", r"\begin{autotabel}{L RR RR}")],
     "README examples compile"),
]


def copy_repo(dst):
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "build")]
        rel = os.path.relpath(dirpath, ROOT)
        os.makedirs(os.path.join(dst, rel), exist_ok=True)
        for f in filenames:
            shutil.copy2(os.path.join(dirpath, f), os.path.join(dst, rel, f))


def run_copy(name, edits):
    with tempfile.TemporaryDirectory(prefix="template-selftest-") as tmp:
        copy_repo(tmp)
        for f, old, new in edits:
            edit(os.path.join(tmp, f), old, new)
        p = subprocess.run([sys.executable, os.path.join(tmp, "scripts", "check.py"), "--full"],
                           cwd=tmp, capture_output=True, text=True)
        crash = p.stderr.strip().splitlines()[-1:] if p.returncode not in (0, 1) else []
        return name, p.returncode, p.stdout + "".join(f"\nFAIL crashed: {c}" for c in crash)


def selftest():
    print("Detectors on made-up pages")
    ok = unit_tests()
    print("Clean copy must pass; each broken copy must fail the right check")
    jobs = [("clean copy", [])] + [(n, e) for n, e, _ in MUTATIONS]
    expect = {n: want for n, _, want in MUTATIONS}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for name, code, out in pool.map(lambda j: run_copy(*j), jobs):
            fails = [l.strip() for l in out.splitlines() if l.strip().startswith("FAIL")]
            if name == "clean copy":
                good = code == 0
                detail = "" if good else "; ".join(fails[:3])
            else:
                good = code != 0 and any(expect[name] in l for l in fails)
                detail = f"expected a FAIL containing {expect[name]!r}, got {fails[:3] or 'none'}" if not good else ""
            ok &= good
            print(f"  {'ok  ' if good else 'FAIL'} {name}" + (f": {detail}" if detail else ""))
    print(f"\n{'Self-test passed.' if ok else 'Self-test FAILED.'}")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full", action="store_true", help="also README examples and the widow test")
    ap.add_argument("--render", action="store_true", help="also page images to look at")
    ap.add_argument("--selftest", action="store_true", help="prove each check catches a broken copy")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(0 if selftest() else 1)
    sys.exit(1 if check_all(ROOT, args.full, args.render) else 0)


if __name__ == "__main__":
    main()
