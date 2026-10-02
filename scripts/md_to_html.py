#!/usr/bin/env python3
"""md_to_html.py - convert a lab .md into a standalone branded HTML page.

Mirrors the house format used by Langchain-Labs:
  * one <style> block (scripts/assets/lab.css)
  * reusable logo-bar header + copyright footer (scripts/assets/header.html, footer.html)
  * every fenced block becomes a macOS-terminal-style window:
        title bar (traffic-light dots + language label) + syntax-highlighted body
  * ```mermaid blocks are rendered to PNG with mermaid-cli and inlined as base64 <img>

Usage:
    python scripts/md_to_html.py <lab.md> [-o out.html] [--cache-dir DIR]

Notes:
  * Code highlighting is Pygments "one-dark" (the theme Langchain-Labs uses).
  * ```mermaid rendering needs node + npx; without it the block degrades to a
    plain code window rather than failing the build.
"""
import argparse, base64, html, re, subprocess, sys, tempfile
from pathlib import Path

from pygments import highlight
from pygments.lexers import BashLexer, TextLexer
from pygments.lexers.python import PythonLexer
from pygments.formatters import HtmlFormatter
from pygments.styles.onedark import OneDarkStyle
from pygments.token import Keyword, Name, Operator

ASSETS_DIR = Path(__file__).resolve().parent / "assets"


class CogOneDark(OneDarkStyle):
    """The house One Dark variant.

    Derived empirically from the Langchain-Labs reference HTML: plain and
    attribute names are left at the default foreground, while function/class/
    builtin names get a uniform blue, and ``None``/``True``/``False`` and the
    word operators (``in``/``not``/``or``/``and``/``is``) are purple. The stock
    one-dark red (#E06C75) and amber (#E5C07B) never appear in the reference.
    """
    styles = dict(OneDarkStyle.styles)
    for _t in (Name, Name.Attribute, Name.Other, Name.Tag, Name.Builtin.Pseudo,
               Name.Variable, Name.Namespace, Name.Constant, Name.Property,
               Name.Label, Name.Entity, Name.Exception):
        styles[_t] = ""
    for _t in (Name.Class, Name.Function, Name.Function.Magic, Name.Builtin,
               Name.Decorator, Keyword.Type):
        styles[_t] = "#61afef"
    styles[Keyword.Constant] = "#c678dd"   # None / True / False
    styles[Operator.Word] = "#c678dd"      # in / not / or / and / is


class CogPythonLexer(PythonLexer):
    """PythonLexer with highlight.js-like naming.

    The reference colours any identifier immediately followed by ``(`` — a call
    or constructor — in blue, regardless of case. Stock Pygments only tags
    ``def``/``class`` names, so promote call targets to ``Name.Function``.
    """
    def get_tokens_unprocessed(self, text):
        toks = list(super().get_tokens_unprocessed(text))
        for i, (pos, tok, val) in enumerate(toks):
            if tok in (Name, Name.Attribute) and val[:1].isalpha():
                j = i + 1
                while j < len(toks) and not toks[j][2].strip():
                    j += 1
                if j < len(toks) and toks[j][2].startswith("("):
                    toks[i] = (pos, Name.Function, val)
        return toks

# Terminal window chrome, copied verbatim from the Langchain-Labs build.
WIN = ('<div style="margin:18px 0;border-radius:8px;overflow:hidden;'
       'border:1px solid #2d3139;box-shadow:0 1px 3px rgba(0,0,0,0.12);">')
BAR = ('<div style="background:#21252b;padding:8px 14px;border-radius:8px 8px 0 0;'
       'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,'
       'sans-serif;display:block;">'
       '<span style="width:10px;height:10px;border-radius:50%;display:inline-block;'
       'background:#ff5f56;margin-right:6px;"></span>'
       '<span style="width:10px;height:10px;border-radius:50%;display:inline-block;'
       'background:#ffbd2e;margin-right:6px;"></span>'
       '<span style="width:10px;height:10px;border-radius:50%;display:inline-block;'
       'background:#27c93f;margin-right:6px;"></span>'
       '<span style="float:right;font-family:\'SFMono-Regular\',Consolas,'
       '\'Liberation Mono\',Menlo,monospace;font-size:11px;color:#9aa0ab;'
       'text-transform:uppercase;letter-spacing:0.06em;">{label}</span></div>')
BODY = ('<div style="background:#282c34;margin:0;padding:16px 18px;overflow-x:auto;'
        'white-space:pre-wrap;overflow-wrap:anywhere;border-radius:0 0 8px 8px;'
        'font-family:\'SFMono-Regular\',Consolas,\'Liberation Mono\',Menlo,monospace;'
        'font-size:13px;line-height:1.55;color:#dcdfe4;">{code}</div>')

LABEL = {"python": "python", "bash": "bash", "sh": "bash", "shell": "bash"}


def window(label, inner):
    return f'{WIN}{BAR.format(label=label)}{BODY.format(code=inner)}</div>'


def highlight_code(code, lang):
    """Pygments one-dark, normalized to the house inline-style format.

    The reference build emits ``style="color:#98c379;"`` (lowercase hex, no
    space, trailing semicolon) and renders comments in italic, whereas raw
    Pygments emits ``style="color: #98C379"``. Normalize so the two match
    byte-for-byte.
    """
    lexer = {"python": CogPythonLexer, "bash": BashLexer}.get(lang, TextLexer)()
    out = highlight(code, lexer, HtmlFormatter(style=CogOneDark, noclasses=True))
    m = re.search(r"<pre[^>]*>(.*)</pre>", out, re.S)
    out = m.group(1) if m else html.escape(code)

    out = re.sub(r"<span></span>", "", out)  # Pygments' leading empty span

    def fix_style(match):
        colour = match.group(1).lower()
        style = f"color:{colour};"
        if colour == "#7f848e":            # one-dark comment -> italic
            style += "font-style:italic;"
        return f'<span style="{style}"'

    out = re.sub(r'<span style="color:\s*(#[0-9A-Fa-f]{6})"', fix_style, out)

    # The reference never wraps default-foreground text or bare operators in a
    # span — it lets them inherit the window's #dcdfe4 body colour. Pygments'
    # one-dark emits #abb2bf (default fg) and #56b6c2 (operator) spans, so
    # unwrap them to match.
    return re.sub(
        r'<span style="color:#(?:abb2bf|56b6c2|dcdfe4);[^"]*">(.*?)</span>',
        r"\1", out, flags=re.S,
    )


def render_mermaid(code, cache_dir, diagram_index):
    """Render a mermaid block to a base64 <img>. Returns None on failure."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = str(abs(hash(code.strip())))
    png = cache_dir / f"mermaid-{key}.png"
    if not png.exists():
        mmd = png.with_suffix(".mmd")
        mmd.write_text(code, encoding="utf-8")
        try:
            subprocess.run(
                ["npx", "-y", "@mermaid-js/mermaid-cli@11",
                 "-i", str(mmd), "-o", str(png), "-b", "white", "-s", "2"],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=300,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return None
    b64 = base64.b64encode(png.read_bytes()).decode("ascii")
    return (f'<img alt="diagram {diagram_index}" src="data:image/png;base64,{b64}" '
            f'style="max-width:100%;height:auto;display:block;margin:0 auto;'
            f'border:1px solid #e2e5ea;border-radius:8px;padding:12px;'
            f'background:#ffffff;">')


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_divider(line):
    return bool(re.fullmatch(r"\|[\s:|-]+\|", line.strip()))


def inline(text):
    """Markdown inline -> HTML. Inline code is stashed so it wins over emphasis."""
    stash = []

    def keep(m):
        stash.append(m.group(1))
        return f"\x00{len(stash) - 1}\x00"

    text = re.sub(r"`([^`]+)`", keep, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", text)
    for i, code in enumerate(stash):
        text = text.replace(f"\x00{i}\x00", f"<code>{html.escape(code)}</code>")
    return text


def convert(md_path, out_path, cache_dir):
    css = (ASSETS_DIR / "lab.css").read_text(encoding="utf-8")
    footer = (ASSETS_DIR / "footer.html").read_text(encoding="utf-8")

    lines = md_path.read_text(encoding="utf-8").splitlines()

    # The first H1 is the lab title: it stays in the body as the page's <h1>
    # (the header bar repeats it in plain text) and also fills DOC_TITLE.
    doc_title = md_path.stem
    title_idx = None
    for idx, ln in enumerate(lines):
        if ln.startswith("```"):
            break
        m = re.match(r"^#\s+(.+)$", ln.strip())
        if m:
            doc_title = m.group(1).strip()
            title_idx = idx
            break

    # Rank the section-heading levels actually used (ignoring the title line),
    # then map the shallowest to <h2> and any deeper level to <h3>. Some labs
    # mark sections with "#" and subsections with "###"; others use "##"/"###".
    # Collapsing to the reference's two-level hierarchy avoids ten <h1>s per
    # file and keeps every heading inside the styled h1–h3 range.
    _in_fence = False
    _levels = set()
    for _idx, _ln in enumerate(lines):
        if _ln.strip().startswith("```"):
            _in_fence = not _in_fence
            continue
        if not _in_fence and _idx != title_idx:
            _m = re.match(r"^(#{1,6})\s+", _ln.strip())
            if _m:
                _levels.add(len(_m.group(1)))
    _sorted = sorted(_levels)
    level_map = {lvl: (2 if r == 0 else 3) for r, lvl in enumerate(_sorted)}

    out, i, n = [], 0, len(lines)
    diagram_index = 0
    while i < n:
        line = lines[i]
        stripped = line.strip()

        # ---- fenced block -------------------------------------------------
        if stripped.startswith("```"):
            lang = stripped[3:].strip().lower()
            i += 1
            body = []
            while i < n and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1
            code = "\n".join(body)
            if lang == "mermaid":
                img = render_mermaid(code, cache_dir, diagram_index)
                diagram_index += 1
                out.append(img if img else window("mermaid", html.escape(code)))
            else:
                out.append(window(LABEL.get(lang, "output"), highlight_code(code, lang)))
            continue

        # ---- blank --------------------------------------------------------
        if not stripped:
            i += 1
            continue

        # ---- horizontal rule ----------------------------------------------
        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", stripped):
            out.append("<hr/>")
            i += 1
            continue

        # ---- heading -------------------------------------------------------
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level, text = len(m.group(1)), m.group(2)
            level = 1 if i == title_idx else level_map.get(level, level)
            out.append(f"<h{level}>{inline(text)}</h{level}>")
            i += 1
            continue

        # ---- table ---------------------------------------------------------
        if stripped.startswith("|") and i + 1 < n and is_divider(lines[i + 1]):
            head = split_row(stripped)
            i += 2
            body_rows = []
            while i < n and lines[i].strip().startswith("|"):
                body_rows.append(split_row(lines[i].strip()))
                i += 1
            parts = ["<table>", "<thead><tr>"]
            parts += [f"<th>{inline(c)}</th>" for c in head]
            parts += ["</tr></thead>", "<tbody>"]
            for row in body_rows:
                parts.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>")
            parts += ["</tbody>", "</table>"]
            out.append("".join(parts))
            continue

        # ---- blockquote -----------------------------------------------------
        if stripped.startswith(">"):
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append(f"<blockquote>{inline(' '.join(quote))}</blockquote>")
            continue

        # ---- lists ----------------------------------------------------------
        if re.match(r"^([-*+]|\d+\.)\s+", stripped):
            ordered = bool(re.match(r"^\d+\.\s", stripped))
            tag = "ol" if ordered else "ul"
            items = []
            while i < n:
                s = lines[i].strip()
                mm = re.match(r"^([-*+]|\d+\.)\s+(.*)$", s)
                if mm:
                    items.append(f"<li>{inline(mm.group(2))}</li>")
                    i += 1
                elif s and not s.startswith("```") and not re.match(r"^#{1,6}\s", s):
                    # lazy continuation of the previous item
                    items[-1] = items[-1][: -len("</li>")] + " " + inline(s) + "</li>"
                    i += 1
                else:
                    break
            out.append(f"<{tag}>" + "".join(items) + f"</{tag}>")
            continue

        # ---- paragraph ------------------------------------------------------
        para = []
        while i < n and lines[i].strip() and not lines[i].strip().startswith("```"):
            s = lines[i].strip()
            if re.match(r"^#{1,6}\s", s) or s.startswith("|") or s.startswith(">"):
                break
            if re.match(r"^([-*+]|\d+\.)\s", s):
                break
            if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", s):
                break
            para.append(s)
            i += 1
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")

    # The header's DOC_TITLE is the HTML-escaped doc title: it sits in a text
    # node, so an unescaped "&" would swallow the following tag.
    header = (ASSETS_DIR / "header.html").read_text(encoding="utf-8").replace(
        "{{DOC_TITLE}}", html.escape(doc_title, quote=False)
    )
    body_html = "\n".join(out)
    page = (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8"/>\n'
        f"<title>{html.escape(doc_title)}</title>\n<style>\n{css}\n</style>\n"
        f"</head>\n<body>\n{header}\n{body_html}\n{footer}\n\n</body>\n</html>\n"
    )
    out_path.write_text(page, encoding="utf-8")
    return page


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("md", type=Path)
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--cache-dir", type=Path,
                    default=Path(".html-cache"),
                    help="where rendered mermaid PNGs are cached")
    args = ap.parse_args()
    out = args.out or args.md.with_suffix(".html")
    page = convert(args.md, out, args.cache_dir)
    print(f"Wrote {out}  ({len(page):,} chars)")


if __name__ == "__main__":
    main()
