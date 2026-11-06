# Report Template (LaTeX)

## Use on Overleaf
1. GitHub → Code → Download ZIP, then Overleaf → New Project → Upload Project
   → choose that zip.
2. Menu → Compiler → **LuaLaTeX** (or XeLaTeX). The Lora fonts in `fonts/` need
   it; pdfLaTeX stops with a message asking you to switch.
3. Press Recompile.

## Build locally
Debian / Ubuntu / Mint, smallest install (about 0.5 GB):
```sh
sudo apt install --no-install-recommends texlive-luatex texlive-latex-extra latexmk
```
`texlive-luatex` gives LuaLaTeX, `texlive-latex-extra` the layout packages
(tabulary, environ, needspace, placeins, mwe ...), `latexmk` the build tool.
Everything else comes in as a dependency. The list was found by building
`main.tex` and `test.tex` with `-recorder` and mapping every file read to its
package (`dpkg -S`).

macOS: MacTeX. Windows: MiKTeX (installs missing packages on first build) or
TeX Live. The fonts in `fonts/` need no installation.

```sh
latexmk -lualatex main.tex
latexmk -lualatex test.tex
latexmk -c            # remove build files
```

## Files
- `main.tex`: title, author, course, list of sections
- `sections/*.tex`: report content, one file per section (no formatting here)
- `style.tex`: all formatting; every value is set once in its SETTINGS block
- `figures/`: your images
- `references.bib`: sources (BibTeX)
- `test.tex` + `tests/*.tex`: layout test document (see below)
- `scripts/check.py`: automatic checks after a change (see below)

## Settings (Google Docs values)
Line spacing 1.15 (the Google Docs default) for all text styles.

| Style | Size | Before | After | Font |
|---|---|---|---|---|
| Title | 18 | 0 | 4 | Lora Medium |
| Heading 1 | 14 | 16 | 4 | Lora SemiBold |
| Heading 2 | 12 | 4 | 4 | Lora SemiBold |
| Heading 3 | 11 | 4 | 4 | Lora SemiBold |
| Normal text | 11 | 0 | 12 | Lora Regular |
| Subtitle (captions, header, page number, footnotes) | 9 | | | Lora Regular, SemiBold label |

Lists: bullet/number at 0.25 in, text at 0.5 in, each level +0.5 in.
Tables: single line spacing, 5 pt cell padding at the edges, 24 pt between
columns, 1.5 pt top/bottom border, 0.75 pt under the header, 0.5 pt `#EFEFEF`
between rows.
Contents and lists of tables/figures: single line spacing, 6 pt before each
section entry, section numbers as in the headings.
Code and URLs: Latin Modern Mono, scaled to Lora's lowercase height.

## Writing content
Content files hold text and structure only. Every spacing, size and alignment
comes from `style.tex`, so never add `\centering`, `\vspace`, `\small` or
placement options like `[h]` / `[t]` (`[H]` only to pin one, see Page
flow).

**Title block** (`main.tex`): `\title{...}`, `\author{...}`, `\course{...}`.
Course and author go top right on page 1. Add a section by creating
`sections/name.tex` and adding `\input{sections/name}` to `main.tex`.

**Headings**: `\section{...}` → "1. Title", `\subsection{...}` → "1.1",
`\subsubsection{...}` → "1.1.1" (three levels). Label them to refer to them:
`\label{sec:name}`.

**Text**: a blank line starts a new paragraph. `\textbf{...}` (SemiBold),
`\textit{...}`, `\texttt{code}`, `\url{https://...}`, `\footnote{...}`.

**References in text**: `\cref{fig:name}` → "Figure 1", also for tables,
sections and equations (`\Cref` at the start of a sentence). Never type
numbers.

**Citations**: add BibTeX entries to `references.bib` and cite with
`\cite{key}` → "[1]". Numbered in order of first citation (IEEE style); the
References list is printed at the end.

**Lists**: `itemize` (• ◦ ▪), `enumerate` (1. a. i.), up to three levels;
`description` for term + definition (`\item[Term] ...`). For a bold lead-in,
start the item with `\textbf{Lead-in.}`.

**Indent**: `\begin{indented} ... \end{indented}` (like "Increase indent"),
`\begin{indented}[2]` for two steps; `quote` uses one step.

**Figure**
```latex
\begin{figure}
  \includegraphics[width=\linewidth]{name}   % or 0.6\linewidth etc.
  \caption{...}  \label{fig:name}
\end{figure}
```
**Sub-figures** ("Figure 2a", "Figure 2b"): side by side, `\subwidth{n}` is
the width of one of n in a row, `\hfill` between them. Add a main caption
after the last sub-figure if the whole figure needs one.
```latex
\begin{figure}
  \begin{subfigure}[t]{\subwidth{2}}
    \includegraphics[width=\linewidth]{left}
    \caption{...}  \label{fig:left}
  \end{subfigure}\hfill
  \begin{subfigure}[t]{\subwidth{2}}
    \includegraphics[width=\linewidth]{right}
    \caption{...}  \label{fig:right}
  \end{subfigure}
  % \caption{Main caption for the whole figure.}
\end{figure}
```
- more rows (a grid): put `\subfiguregap` between the rows
- stacked full-width sub-figures: `\begin{subfigure}{\linewidth}`, with
  `\subfiguregap` between them
- a figure continued on the next page (same number, goes on to c, d): start
  the second `figure` with `\ContinuedFloat`; see `sections/data.tex`

**Table**: the width is chosen from the content
```latex
\begin{table}
  \caption{...}  \label{tab:name}
  \begin{autotable}{L R R}          % L = text, R = numbers, C = centred
    \toprule
    \textbf{Head} & \textbf{Head} & \textbf{Head} \\
    \midrule
    row \\ \rowline                  % \rowline = light line between rows
    row \\
    \bottomrule
  \end{autotable}
\end{table}
```
- the table is as wide as its content, with 24 pt between the content of
  neighbouring columns (`\TableColumnGap`), and centred
- content longer than the line → full width; text (`L`) columns wrap and get
  width in proportion to their text; number (`R`) columns stay narrow

Choosing column types:
- text, or a mix like "0.869, but slow" → `L`
- numbers → `R`; better still, put a number and its note in separate columns
  so the numbers line up
- a total or best row: `\textbf{...}` in each cell
- grouped values like `194/0/42` → one `R` column per value under a grouped
  header, so every part lines up:
```latex
  \begin{autotable}{L RR RR}
    \toprule
    & \multicolumn{2}{c}{\textbf{Day}} & \multicolumn{2}{c}{\textbf{Night}} \\
    \cmidrule(lr){2-3}\cmidrule(lr){4-5}
    \textbf{Model} & \textbf{Found} & \textbf{Missed} & \textbf{Found} & \textbf{Missed} \\
    \midrule
    A & 194 & 42 & 31 & 5 \\ \rowline
    B & 189 & 47 & 15 & 21 \\
    \bottomrule
  \end{autotable}
```

**Equations**: numbered on the right, "(1)".
```latex
\begin{equation}
  c = \frac{a + b}{2}  \label{eq:name}
\end{equation}
```
Several lines aligned at `&`: `\begin{align} P &= ... \\ R &= ... \end{align}`.
Inline: `$F_1 = 2PR/(P+R)$`.

**Code block**: `\begin{verbatim} ... \end{verbatim}`, printed as typed.

**Contents, list of tables, list of figures**: uncomment the four lines after
`\maketitle` in `main.tex` (useful from about 10 pages).

## Changing the look
All values are in the SETTINGS block at the top of `style.tex`, in Google Docs
terms. Common changes:
- line spacing: `\DocsLineSpacing` (1.15; use 1.5 if a course asks for it).
  Headings, captions and figure gaps follow it; table cells and the contents
  keep their own spacing
- A4 paper: in `\PageSetup`, change `letterpaper` to `a4paper`
- justified text: delete the `\AtBeginDocument{\raggedright}` line
- caption alignment: `\CaptionStyle` (see Captions below)
- bold weight: `\BoldWeight` (`SemiBold` or `Bold`)

## Captions (IEEE / NeurIPS / ICML convention)
Table captions above, figure captions below, 8 pt from the table/figure.
Figures and tables sit 18 pt from the text above and below (`\FloatGap`).
Narrow tables and figures are centred. A one-line caption is centred; a longer
one is justified across the full text width. `\CaptionStyle` also offers
`centered` (all centred) and `left` (all at the left margin).

## Page flow and page breaks
- A figure/table goes where it is written if it fits, otherwise to the top of
  the next page while the text fills the gap. It never appears before the place
  it is written, and never moves past the next numbered section.
- A figure/table and its caption are never split.
- A heading is never left alone at the bottom of a page (keep with next), and a
  figure/table written directly after a heading stays attached to it.
- A paragraph never leaves a single line alone at the bottom or top of a page.
- A list's intro line stays with its first item; text stays with a following
  equation.

Manual tools: `\newpage` (new page), `\clearpage` (new page, place pending
figures first), `\begin{figure}[H]` (pin a figure exactly where it is written).

## Layout test
`test.tex` uses the same `style.tex` and shows every pattern: headings,
indents, lists, tables, figures, combinations, equations, code, page breaks.
On Overleaf: Menu → Main document → `test.tex`; switch back to `main.tex` for
the report.

## Checking changes
After changing `style.tex` or the tests, run:
```sh
python3 scripts/check.py             # about 10 s
python3 scripts/check.py --full      # also README examples and the widow test
python3 scripts/check.py --render    # also page images in build/pages/
python3 scripts/check.py --selftest  # proves the checks work (about 40 s)
```
It rebuilds both documents from scratch into `build/` and checks:
- no errors, warnings or overfull/underfull boxes;
- no manual formatting in `sections/` and `tests/`;
- no page ends with a heading, no widows or orphans;
- spacing measured on the page: captions at `\CaptionGap`, figures and
  tables about one paragraph gap from the text, all three heading levels the
  same distance from their text, even table cell padding, no gap over 32 pt.

`--selftest` runs the page-flow detectors on made-up pages, then runs the
checks on temporary copies of the repo: the clean copy must pass, and each
copy with one deliberate fault (build error, `\small` in a test file, wide
figure gap, Heading 3 with no space after, wrong caption offset, uneven cell
padding, widow control off, broken README example) must fail the matching
check. Run it after changing `scripts/check.py`.

Exit code 0 means all passed. Needs poppler-utils (`pdftohtml`, `pdftoppm`);
the spacing checks and page images also need Pillow (`python3-pil`). Look at
the page images before committing a visual change.

## Limitations
- A table cannot continue on the next page. A table taller than the page
  runs off the bottom with the warning "Float too large for page"; split it
  into two tables.
- Equations use Latin Modern (Lora has no math font).
- XeLaTeX should work (same font loading), but only LuaLaTeX is tested.
