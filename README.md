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
- `references.bib`: sources, cited with `\cite{key}`
- `test.tex` + `tests/*.tex`: layout test document (see below)

## Settings (Google Docs values)
Line spacing 1.5 for all text styles.

| Style | Size | Before | After | Font |
|---|---|---|---|---|
| Title | 18 | 0 | 4 | Lora Medium |
| Heading 1 | 14 | 16 | 4 | Lora SemiBold |
| Heading 2 | 12 | 4 | 4 | Lora SemiBold |
| Heading 3 | 11 | 4 | 0 | Lora SemiBold |
| Normal text | 11 | 0 | 12 | Lora Regular |
| Subtitle (captions, header, page number, footnotes) | 9 | | | Lora Regular, SemiBold label |

Lists: bullet/number at 0.25 in, text at 0.5 in, each level +0.5 in.
Tables: single line spacing, 5 pt cell padding, 1.5 pt top/bottom border,
0.75 pt under the header, 0.5 pt `#EFEFEF` between rows.
Contents and lists of tables/figures (uncomment in `main.tex`): single line
spacing, 6 pt before each section entry, section numbers as in the headings.

## Writing content
**Figure**
```latex
\begin{figure}
  \includegraphics[width=\linewidth]{name}   % or 0.6\linewidth etc.
  \caption{...}  \label{fig:name}
\end{figure}
```
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
- content longer than the line → full width; text (`L`) columns wrap and get
  width in proportion to their text; number (`R`) columns stay narrow
- content wider than 60% of the line → full width, no wrapping
- narrower than 40% → widened to 40%; otherwise natural width

Choosing column types:
- text, or a mix like "0.869, but slow" → `L`
- numbers → `R`; better still, put a number and its note in separate columns
  so the numbers line up
- grouped values like `194/0/42` → one `R` column per value under a grouped
  header (`\multicolumn` + `\cmidrule`), so every part lines up; see
  `tests/t3-tables.tex`

**References in text**: `\cref{fig:name}` → "Figure 1". Never type numbers.
**Indent**: `\begin{indented} ... \end{indented}` (like "Increase indent").

## Captions (IEEE / NeurIPS / ICML convention)
Table captions above, figure captions below, 10 pt from the table/figure.
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
