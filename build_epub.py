"""Build a single EPUB 3 from the forty chapter drafts in drafts/.

Standard library only -- an EPUB is a ZIP of XHTML, and the drafts use a narrow
enough slice of Markdown (headings, paragraphs, scene-break rules, emphasis) that
no Markdown library is needed.

    python build_epub.py
"""

import html
import re
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

TITLE = "KAOS: Season Two"
AUTHOR = "Matthew Farrell"
LANGUAGE = "en-GB"
DESCRIPTION = (
    "A novelization of a non-existent second season of KAOS (Netflix, 2024), "
    "resolving the open threads of Season 1. Forty chapters in three parts."
)
BOOK_URN = "https://github.com/farrellm/kaos/kaos-season-two"

ROOT = Path(__file__).resolve().parent
DRAFTS = ROOT / "drafts"
RECAP = ROOT / "RECAP-SEASON-ONE.md"
OUTPUT = ROOT / "KAOS-Season-Two.epub"

# Front matter: the Season 1 recap, rendered between the title page and Part One.
RECAP_TITLE = "Season One: The Story So Far"

# Chapter ranges per bible/12-S2-OUTLINE.md (invention, not show canon).
PARTS = [
    ("Part One", "The Spare Bed", 1, 13),
    ("Part Two", "The Reservoir", 14, 27),
    ("Part Three", "What the Humans Did", 28, 40),
]

# Deterministic identity, so a rebuild updates the same book rather than minting a new one.
BOOK_ID = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, BOOK_URN)}"

XML_DECL = '<?xml version="1.0" encoding="UTF-8"?>\n'


# --------------------------------------------------------------------------- markdown


def inline(text):
    """Escape XML, then resolve ***bold italic***, **bold**, *italic*."""
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<em><strong>\1</strong></em>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    return text


def parse_chapter(md_text):
    """Return (chapter_number_line, chapter_title, [body html lines])."""
    number = title = None
    body = []
    fresh = True  # next paragraph opens a chapter or follows a scene break

    for block in re.split(r"\n\s*\n", md_text.strip()):
        block = block.strip()
        if not block:
            continue
        if block.startswith("## "):
            title = block[3:].strip()
            body.append(f'<h2 class="chaptitle">{inline(title)}</h2>')
            fresh = True
        elif block.startswith("# "):
            number = block[2:].strip()
            body.append(f'<h1 class="chapnum">{inline(number)}</h1>')
            fresh = True
        elif set(block) == {"-"} and len(block) >= 3:
            body.append('<hr class="scene" />')
            fresh = True
        else:
            # Drafts are hard-wrapped at ~95 columns; unwrap before rendering.
            para = " ".join(line.strip() for line in block.splitlines())
            cls = ' class="first"' if fresh else ""
            body.append(f"<p{cls}>{inline(para)}</p>")
            fresh = False

    return number, title, body


def load_chapters():
    files = sorted(DRAFTS.glob("ch[0-9][0-9]-*.md"))
    if not files:
        raise SystemExit(f"no chapter drafts found in {DRAFTS}")

    chapters = []
    for path in files:
        num = int(path.name[2:4])
        number, title, body = parse_chapter(path.read_text(encoding="utf-8"))
        if number is None or title is None:
            raise SystemExit(f"{path.name}: missing '# Chapter ...' or '## Title' heading")
        chapters.append(
            {
                "num": num,
                "file": f"ch{num:02d}.xhtml",
                "number": number,
                "title": title,
                "body": "\n".join(body),
            }
        )
    return chapters


def parse_recap():
    """Render RECAP-SEASON-ONE.md to body HTML.

    A wider Markdown subset than parse_chapter: three heading levels and plain
    section rules, with no chapter-number/title contract to satisfy.
    """
    if not RECAP.exists():
        raise SystemExit(f"missing front matter: {RECAP}")

    levels = [
        ("### ", "h3", "recap-section"),
        ("## ", "h2", "recap-part"),
        ("# ", "h1", "recap-title"),
    ]
    body = []
    fresh = True

    for block in re.split(r"\n\s*\n", RECAP.read_text(encoding="utf-8").strip()):
        block = block.strip()
        if not block:
            continue
        for prefix, tag, cls in levels:
            if block.startswith(prefix):
                heading = inline(block[len(prefix):].strip())
                body.append(f'<{tag} class="{cls}">{heading}</{tag}>')
                fresh = True
                break
        else:
            if set(block) == {"-"} and len(block) >= 3:
                body.append('<hr class="section" />')
                fresh = True
            else:
                # Hard-wrapped in the source, same as the drafts; unwrap before rendering.
                para = " ".join(line.strip() for line in block.splitlines())
                indent = ' class="first"' if fresh else ""
                body.append(f"<p{indent}>{inline(para)}</p>")
                fresh = False

    return "\n".join(body)


# --------------------------------------------------------------------------- documents


def page(title, body, css="style.css", extra_head=""):
    return (
        XML_DECL
        + f'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{LANGUAGE}" '
        f'lang="{LANGUAGE}">\n'
        "<head>\n"
        '  <meta charset="utf-8" />\n'
        f"  <title>{html.escape(title)}</title>\n"
        f'  <link rel="stylesheet" type="text/css" href="{css}" />\n'
        f"{extra_head}"
        "</head>\n"
        f"<body>\n{body}\n</body>\n</html>\n"
    )


STYLESHEET = """\
@namespace "http://www.w3.org/1999/xhtml";

body {
  font-family: Palatino, "Palatino Linotype", "Book Antiqua", Georgia, serif;
  margin: 0 5%;
  line-height: 1.5;
  text-align: justify;
  hyphens: auto;
  -webkit-hyphens: auto;
  -epub-hyphens: auto;
  widows: 2;
  orphans: 2;
}

p {
  margin: 0;
  text-indent: 1.2em;
}

p.first {
  text-indent: 0;
}

h1.chapnum {
  margin: 3em 0 0.2em;
  font-size: 0.95em;
  font-weight: normal;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  text-align: center;
}

h2.chaptitle {
  margin: 0 0 2em;
  font-size: 1.5em;
  font-weight: normal;
  font-style: italic;
  text-align: center;
  page-break-after: avoid;
}

/* Scene break. The asterisks come from ::after; a reader that ignores generated
   content still gets the blank line, which reads as a break either way. */
hr.scene {
  border: 0;
  height: 1.4em;
  margin: 0.6em 0;
  text-align: center;
  overflow: visible;
  page-break-inside: avoid;
}

hr.scene:after {
  content: "* * *";
  letter-spacing: 0.6em;
  color: #555;
}

/* Cover */
body.cover {
  margin: 0;
  text-align: center;
  background: #12161c;
  color: #f2ede3;
  height: 100%;
}

.cover-wrap {
  padding: 24% 8% 0;
}

.cover-wrap .book-title {
  font-size: 2.6em;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  line-height: 1.15;
  margin: 0;
  font-weight: normal;
  text-align: center;
}

.cover-wrap .rule {
  border-top: 1px solid #b8975a;
  width: 40%;
  margin: 1.4em auto;
}

.cover-wrap .byline {
  font-style: italic;
  font-size: 1.15em;
  letter-spacing: 0.06em;
  text-align: center;
  margin: 0;
}

/* Title page and part dividers */
.titlepage, .part {
  text-align: center;
  margin-top: 25%;
}

.titlepage h1 {
  font-size: 2.1em;
  font-weight: normal;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  margin: 0 0 0.6em;
}

.titlepage .byline {
  font-style: italic;
  font-size: 1.1em;
  margin: 0 0 3em;
}

.titlepage .note {
  font-size: 0.8em;
  color: #666;
  font-style: italic;
  margin: 0;
}

.part .part-label {
  font-size: 0.9em;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  margin: 0 0 0.8em;
  text-align: center;
}

.part .part-title {
  font-size: 1.9em;
  font-weight: normal;
  font-style: italic;
  margin: 0;
  text-align: center;
}

/* Front matter recap */
h1.recap-title {
  margin: 2em 0 1.6em;
  font-size: 1.6em;
  font-weight: normal;
  letter-spacing: 0.06em;
  text-align: center;
  text-wrap: balance;
}

h2.recap-part {
  margin: 2.4em 0 1em;
  font-size: 1.05em;
  font-weight: normal;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  text-align: center;
  page-break-after: avoid;
}

h3.recap-section {
  margin: 1.8em 0 0.6em;
  font-size: 1.1em;
  font-weight: normal;
  font-style: italic;
  text-align: left;
  page-break-after: avoid;
}

hr.section {
  border: 0;
  border-top: 1px solid #ccc;
  width: 30%;
  margin: 2.4em auto;
}

nav ol {
  list-style: none;
  padding-left: 0;
}

nav ol ol {
  padding-left: 1.2em;
}

nav li {
  margin: 0.35em 0;
}
"""


def cover_svg():
    esc = html.escape
    return (
        XML_DECL
        + '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1800" '
        'viewBox="0 0 1200 1800" preserveAspectRatio="xMidYMid meet">\n'
        '  <rect width="1200" height="1800" fill="#12161c" />\n'
        '  <rect x="60" y="60" width="1080" height="1680" fill="none" '
        'stroke="#b8975a" stroke-width="3" />\n'
        '  <g font-family="Palatino, Georgia, serif" text-anchor="middle" fill="#f2ede3">\n'
        '    <text x="600" y="640" font-size="150" letter-spacing="14">KAOS</text>\n'
        '    <text x="600" y="790" font-size="82" letter-spacing="12">SEASON TWO</text>\n'
        '    <line x1="420" y1="900" x2="780" y2="900" stroke="#b8975a" stroke-width="2" />\n'
        f'    <text x="600" y="1010" font-size="52" font-style="italic">'
        f"{esc(AUTHOR)}</text>\n"
        '    <text x="600" y="1640" font-size="34" letter-spacing="8" fill="#8a8f98">'
        "A NOVELIZATION</text>\n"
        "  </g>\n"
        "</svg>\n"
    )


def cover_xhtml():
    body = (
        '<div class="cover-wrap">\n'
        f'  <h1 class="book-title">KAOS<br />Season Two</h1>\n'
        '  <div class="rule"></div>\n'
        f'  <p class="byline">{html.escape(AUTHOR)}</p>\n'
        "</div>"
    )
    return page("Cover", body).replace("<body>", '<body class="cover">')


def title_xhtml():
    body = (
        '<div class="titlepage">\n'
        f"  <h1>{html.escape(TITLE)}</h1>\n"
        f'  <p class="byline">{html.escape(AUTHOR)}</p>\n'
        '  <p class="note">A novelization of a second season that does not exist.</p>\n'
        "</div>"
    )
    return page(TITLE, body)


def recap_xhtml():
    return page(RECAP_TITLE, parse_recap())


def part_xhtml(label, name):
    body = (
        '<section class="part" epub:type="part">\n'
        f'  <p class="part-label">{html.escape(label)}</p>\n'
        f'  <h1 class="part-title">{html.escape(name)}</h1>\n'
        "</section>"
    )
    return page(f"{label} — {name}", body).replace(
        '<html xmlns="http://www.w3.org/1999/xhtml"',
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"',
    )


def chapter_xhtml(ch):
    return page(f"{ch['number']} — {ch['title']}", ch["body"])


# --------------------------------------------------------------------------- packaging


def spine_documents(chapters):
    """[(id, href, title, is_part)] in reading order, after cover and title page."""
    items = []
    for index, (label, name, lo, hi) in enumerate(PARTS, start=1):
        items.append((f"part{index}", f"part{index}.xhtml", f"{label}: {name}", True))
        for ch in chapters:
            if lo <= ch["num"] <= hi:
                items.append(
                    (f"ch{ch['num']:02d}", ch["file"], f"{ch['number']} — {ch['title']}", False)
                )
    covered = sum(1 for i in items if not i[3])
    if covered != len(chapters):
        raise SystemExit(
            f"PARTS covers {covered} chapters but {len(chapters)} drafts exist -- "
            "update PARTS in build_epub.py"
        )
    return items


def content_opf(docs):
    modified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = [
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav" />',
        '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml" />',
        '<item id="css" href="style.css" media-type="text/css" />',
        '<item id="cover-image" href="images/cover.svg" media-type="image/svg+xml" '
        'properties="cover-image" />',
        '<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml" />',
        '<item id="titlepage" href="title.xhtml" media-type="application/xhtml+xml" />',
        '<item id="recap" href="recap.xhtml" media-type="application/xhtml+xml" />',
    ]
    spine = [
        '<itemref idref="cover" linear="yes" />',
        '<itemref idref="titlepage" linear="yes" />',
        '<itemref idref="recap" linear="yes" />',
    ]
    for doc_id, href, _title, _is_part in docs:
        manifest.append(
            f'<item id="{doc_id}" href="{href}" media-type="application/xhtml+xml" />'
        )
        spine.append(f'<itemref idref="{doc_id}" />')

    indent = "\n    "
    return (
        XML_DECL
        + '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
        'unique-identifier="book-id" xml:lang="' + LANGUAGE + '">\n'
        '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        f'    <dc:identifier id="book-id">{BOOK_ID}</dc:identifier>\n'
        f"    <dc:title>{html.escape(TITLE)}</dc:title>\n"
        f'    <dc:creator id="author">{html.escape(AUTHOR)}</dc:creator>\n'
        '    <meta refines="#author" property="role" scheme="marc:relators">aut</meta>\n'
        f"    <dc:language>{LANGUAGE}</dc:language>\n"
        f"    <dc:description>{html.escape(DESCRIPTION)}</dc:description>\n"
        "    <dc:subject>Fiction</dc:subject>\n"
        f'    <meta property="dcterms:modified">{modified}</meta>\n'
        '    <meta name="cover" content="cover-image" />\n'
        "  </metadata>\n"
        f"  <manifest>{indent}{indent.join(manifest)}\n  </manifest>\n"
        f'  <spine toc="ncx">{indent}{indent.join(spine)}\n  </spine>\n'
        "</package>\n"
    )


def nav_xhtml(docs):
    lines = [
        '<nav epub:type="toc" id="toc">',
        "  <h1>Contents</h1>",
        "  <ol>",
        '    <li><a href="title.xhtml">Title Page</a></li>',
        f'    <li><a href="recap.xhtml">{html.escape(RECAP_TITLE)}</a></li>',
    ]
    open_part = False
    for _doc_id, href, title, is_part in docs:
        if is_part:
            if open_part:
                lines.append("      </ol>")
                lines.append("    </li>")
            lines.append(f'    <li><a href="{href}">{html.escape(title)}</a>')
            lines.append("      <ol>")
            open_part = True
        else:
            lines.append(f'        <li><a href="{href}">{html.escape(title)}</a></li>')
    if open_part:
        lines.append("      </ol>")
        lines.append("    </li>")
    lines.append("  </ol>")
    lines.append("</nav>")

    doc = page("Contents", "\n".join(lines))
    return doc.replace(
        '<html xmlns="http://www.w3.org/1999/xhtml"',
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"',
    )


def toc_ncx(docs):
    points = []
    order = 1

    def nav_point(nav_id, href, title, depth):
        pad = "  " * depth
        return (
            f'{pad}<navPoint id="{nav_id}" playOrder="{order}">\n'
            f"{pad}  <navLabel><text>{html.escape(title)}</text></navLabel>\n"
            f'{pad}  <content src="{href}" />\n'
        )

    points.append(nav_point("nav-title", "title.xhtml", "Title Page", 2))
    points.append("    </navPoint>\n")
    order += 1

    points.append(nav_point("nav-recap", "recap.xhtml", RECAP_TITLE, 2))
    points.append("    </navPoint>\n")
    order += 1

    open_part = False
    for doc_id, href, title, is_part in docs:
        if is_part:
            if open_part:
                points.append("    </navPoint>\n")
            points.append(nav_point(f"nav-{doc_id}", href, title, 2))
            order += 1
            open_part = True
        else:
            points.append(nav_point(f"nav-{doc_id}", href, title, 3))
            points.append("      </navPoint>\n")
            order += 1
    if open_part:
        points.append("    </navPoint>\n")

    return (
        XML_DECL
        + '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" '
        f'xml:lang="{LANGUAGE}">\n'
        "  <head>\n"
        f'    <meta name="dtb:uid" content="{BOOK_ID}" />\n'
        '    <meta name="dtb:depth" content="2" />\n'
        '    <meta name="dtb:totalPageCount" content="0" />\n'
        '    <meta name="dtb:maxPageNumber" content="0" />\n'
        "  </head>\n"
        f"  <docTitle><text>{html.escape(TITLE)}</text></docTitle>\n"
        f"  <docAuthor><text>{html.escape(AUTHOR)}</text></docAuthor>\n"
        "  <navMap>\n" + "".join(points) + "  </navMap>\n"
        "</ncx>\n"
    )


CONTAINER_XML = (
    XML_DECL
    + '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
    "  <rootfiles>\n"
    '    <rootfile full-path="OEBPS/content.opf" '
    'media-type="application/oebps-package+xml" />\n'
    "  </rootfiles>\n"
    "</container>\n"
)


def build():
    chapters = load_chapters()
    docs = spine_documents(chapters)
    by_file = {ch["file"]: ch for ch in chapters}
    # Render front matter before the archive is opened, so a missing or malformed
    # recap fails without leaving a truncated .epub behind.
    recap = recap_xhtml()

    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as z:
        # The mimetype entry must come first and be stored uncompressed.
        info = zipfile.ZipInfo("mimetype")
        info.compress_type = zipfile.ZIP_STORED
        z.writestr(info, "application/epub+zip")

        z.writestr("META-INF/container.xml", CONTAINER_XML)
        z.writestr("OEBPS/content.opf", content_opf(docs))
        z.writestr("OEBPS/nav.xhtml", nav_xhtml(docs))
        z.writestr("OEBPS/toc.ncx", toc_ncx(docs))
        z.writestr("OEBPS/style.css", STYLESHEET)
        z.writestr("OEBPS/images/cover.svg", cover_svg())
        z.writestr("OEBPS/cover.xhtml", cover_xhtml())
        z.writestr("OEBPS/title.xhtml", title_xhtml())
        z.writestr("OEBPS/recap.xhtml", recap)

        for index, (label, name, _lo, _hi) in enumerate(PARTS, start=1):
            z.writestr(f"OEBPS/part{index}.xhtml", part_xhtml(label, name))

        for _doc_id, href, _title, is_part in docs:
            if not is_part:
                z.writestr(f"OEBPS/{href}", chapter_xhtml(by_file[href]))

    words = sum(len(re.sub(r"<[^>]+>", " ", ch["body"]).split()) for ch in chapters)
    size_kb = OUTPUT.stat().st_size / 1024
    print(f"Wrote {OUTPUT.name} -- {len(chapters)} chapters, ~{words:,} words, {size_kb:.0f} KB")


if __name__ == "__main__":
    build()
