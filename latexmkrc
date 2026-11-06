# Overleaf: run LuaLaTeX even when the project compiler is set to pdfLaTeX.
# (Overleaf runs latexmk in pdf mode; this replaces the pdflatex command.)
$pdflatex = 'lualatex %O %S';
