#!/usr/bin/env python3
"""Convert the Mythos Preview System Card PDF to clean markdown.

Uses PyMuPDF's structured text extraction with font metadata.

Font patterns in the Mythos PDF (Google Docs Renderer):
  16.0 Poppins-SemiBold  → # (h1): main sections (1, 2, 3...)
  14.0 Poppins-Medium    → ## (h2): X.Y sections
  13.0 Poppins-Medium    → ### (h3): X.Y.Z sections
  11.0 Lora-Bold         → #### (h4): X.Y.Z.W sections (detected by pattern + bold)
  11.0 Lora-Regular      → body text
   9.0 Lora-Regular      → footnotes and page numbers
"""

import fitz
import re
import os

PDF_PATH = "primary-sources/mythos-preview-system-card/Claude Mythos Preview System Card.pdf"
OUT_PATH = "primary-sources/mythos-preview-system-card/claude-mythos-preview-system-card.md"

# Pages to skip: 0-indexed
TITLE_PAGE = 0
TOC_PAGES = set(range(3, 9))  # pages 4-9 are TOC

# Figure mapping: 1-indexed page number -> list of figure filenames
# Excludes separator images (tiny height)
FIGURE_PAGES = {}

# Separator images removed: fig-015, fig-017, fig-037, fig-040, fig-075
REMOVED_FIGS = {"fig-015.png", "fig-017.png", "fig-037.png", "fig-040.png", "fig-075.png"}


def build_figure_page_map():
    """Build mapping from extraction output."""
    raw_map = {
        1: ["fig-000.png"], 28: ["fig-001.png"], 31: ["fig-002.png"],
        33: ["fig-003.png"], 42: ["fig-004.png"], 43: ["fig-005.png"],
        49: ["fig-006.png"], 50: ["fig-007.png"], 51: ["fig-008.png"],
        52: ["fig-009.png"], 67: ["fig-010.png"], 68: ["fig-011.png"],
        70: ["fig-012.png"],
        76: ["fig-013.png", "fig-014.png", "fig-016.png"],
        77: ["fig-018.png", "fig-019.png", "fig-020.png"],
        78: ["fig-021.png", "fig-022.png", "fig-023.png"],
        79: ["fig-024.png", "fig-025.png", "fig-026.png"],
        80: ["fig-027.png", "fig-028.png"],
        81: ["fig-029.png"], 87: ["fig-030.png"], 88: ["fig-031.png"],
        89: ["fig-032.png"],
        92: ["fig-033.png", "fig-034.png", "fig-035.png", "fig-036.png"],
        93: ["fig-038.png"],
        94: ["fig-039.png"], 95: ["fig-041.png"],
        96: ["fig-042.png"], 97: ["fig-043.png", "fig-044.png"],
        99: ["fig-045.png"], 100: ["fig-046.png"], 101: ["fig-047.png"],
        102: ["fig-048.png"], 107: ["fig-049.png"], 108: ["fig-050.png"],
        109: ["fig-051.png"], 112: ["fig-052.png"],
        115: ["fig-053.png", "fig-054.png"], 116: ["fig-055.png"],
        118: ["fig-056.png"], 120: ["fig-057.png"], 122: ["fig-058.png"],
        123: ["fig-059.png"], 124: ["fig-060.png"], 126: ["fig-061.png"],
        128: ["fig-062.png"], 129: ["fig-063.png"], 130: ["fig-064.png"],
        132: ["fig-065.png"], 134: ["fig-066.png"], 135: ["fig-067.png"],
        136: ["fig-068.png"], 137: ["fig-069.png"], 139: ["fig-070.png"],
        140: ["fig-071.png"], 142: ["fig-072.png"], 144: ["fig-073.png"],
        151: ["fig-074.png"], 152: ["fig-076.png"],
        155: ["fig-077.png"], 156: ["fig-078.png"], 158: ["fig-079.png"],
        159: ["fig-080.png"], 160: ["fig-081.png"], 163: ["fig-082.png"],
        164: ["fig-083.png"], 166: ["fig-084.png"], 167: ["fig-085.png"],
        172: ["fig-086.png"], 174: ["fig-087.png"],
        176: ["fig-088.png", "fig-089.png"],
        178: ["fig-090.png"], 179: ["fig-091.png", "fig-092.png"],
        186: ["fig-093.png"], 187: ["fig-094.png"], 192: ["fig-095.png"],
        194: ["fig-096.png"], 196: ["fig-097.png"], 197: ["fig-098.png"],
        198: ["fig-099.png"], 207: ["fig-100.png"], 208: ["fig-101.png"],
        211: ["fig-102.png"], 224: ["fig-103.png"], 233: ["fig-104.png"],
        242: ["fig-105.png"],
    }
    # Filter out removed separator images
    result = {}
    for page, figs in raw_map.items():
        filtered = [f for f in figs if f not in REMOVED_FIGS]
        if filtered:
            result[page] = filtered
    return result


def extract_line_info(page):
    """Extract all text lines with font info from a page."""
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
    lines_out = []

    for block in blocks:
        if block["type"] != 0:
            continue
        block_bbox = block["bbox"]

        for line in block["lines"]:
            spans = line["spans"]
            if not spans:
                continue

            # Collect text and font info for the line
            text_parts = []
            fonts = set()
            sizes = []
            for span in spans:
                text_parts.append(span["text"])
                fonts.add(span["font"])
                sizes.append(round(span["size"], 1))

            full_text = "".join(text_parts)
            if not full_text.strip():
                # Empty line within a block = paragraph break
                lines_out.append({
                    "text": "",
                    "size": 11.0,
                    "bold": False,
                    "italic": False,
                    "poppins": False,
                    "left": round(block_bbox[0]),
                    "top": round(line["bbox"][1]),
                    "block_left": round(block_bbox[0]),
                })
                continue

            # Dominant font size (most common)
            avg_size = max(set(sizes), key=sizes.count) if sizes else 11.0

            is_bold = any("Bold" in f or "bold" in f for f in fonts)
            is_poppins = any("Poppins" in f for f in fonts)
            is_italic = any("Italic" in f or "italic" in f for f in fonts)

            # Detect footnote definitions: first span is tiny number, rest is ~10pt
            is_footnote_def = False
            footnote_num = None
            if (len(spans) >= 2
                    and round(spans[0]["size"], 1) < 7
                    and spans[0]["text"].strip().isdigit()):
                footnote_num = int(spans[0]["text"].strip())
                rest_text = "".join(s["text"] for s in spans[1:])
                is_footnote_def = True

            lines_out.append({
                "text": full_text,
                "size": avg_size,
                "bold": is_bold,
                "italic": is_italic,
                "poppins": is_poppins,
                "left": round(block_bbox[0]),
                "top": round(line["bbox"][1]),
                "block_left": round(block_bbox[0]),
                "is_footnote_def": is_footnote_def,
                "footnote_num": footnote_num,
            })

    return lines_out


def classify_line(line, page_num):
    """Classify a line as heading, body, footnote, page_number, etc."""
    text = line["text"].strip()
    size = line["size"]
    poppins = line["poppins"]
    bold = line["bold"]

    # Empty line = paragraph break
    if not text:
        return "para_break", 0

    # Page numbers: small standalone numbers
    if size <= 9.5 and text.isdigit():
        return "page_number", 0

    # Figure/table captions: size 9.0, bold, starts with [Figure or [Table
    if size <= 9.5 and bold and re.match(r'\[?(Figure|Table)\s+\d+', text):
        return "caption", 0

    # Caption continuation: size 9.0, bold (follows a caption)
    if size <= 9.5 and bold:
        return "caption_cont", 0

    # Footnotes: size 9.0, NOT bold, starts with number
    if size <= 9.5 and not bold and re.match(r'^\d+\s', text):
        return "footnote", 0

    # Small text continuation (footnote continuation)
    if size <= 9.5 and not bold:
        return "footnote_cont", 0

    # Footnote definitions: first span is very small (< 7) number, rest is ~10pt
    # These are detected separately in the main loop via span-level analysis

    # Headings by font
    if poppins and size >= 15.5:
        # Main numbered sections are h1, unnumbered (Changelog, Abstract, etc.) are h2
        if re.match(r'^\d+\s', text):
            return "heading", 1  # # Main section
        else:
            return "heading", 2  # ## Changelog, Abstract, Acknowledgments
    if poppins and size >= 13.5:
        return "heading", 2  # ## X.Y
    if poppins and size >= 12.5:
        return "heading", 3  # ### X.Y.Z

    # 4-level and 5-level headings: Lora-Bold with section number pattern
    if bold and size >= 10.5 and re.match(r'^\d+\.\d+\.\d+\.\d+\.\d+', text):
        return "heading", 5
    if bold and size >= 10.5 and re.match(r'^\d+\.\d+\.\d+\.\d+', text):
        return "heading", 4

    # Body text
    return "body", 0


def clean_text(text):
    """Clean unicode and formatting in text."""
    # Zero-width chars
    text = text.replace("\u200b", "")
    text = text.replace("\u200c", "")
    text = text.replace("\u00a0", " ")

    # Bullets
    text = re.sub(r'●\s*', "- ", text)
    text = re.sub(r'○\s*', "  - ", text)
    text = re.sub(r'■\s*', "  - ", text)

    # Smart quotes -> ascii
    text = text.replace("\u201c", '"')
    text = text.replace("\u201d", '"')
    text = text.replace("\u2018", "'")
    text = text.replace("\u2019", "'")

    # Dashes
    text = text.replace("\u2014", "---")
    text = text.replace("\u2013", "--")

    # Ellipsis
    text = text.replace("\u2026", "...")

    # Other common unicode
    text = text.replace("\u2022", "- ")  # bullet
    text = text.replace("\u2192", "->")  # arrow

    return text


def is_figure_caption(text):
    """Check if text is a figure or table caption."""
    return bool(re.match(r'\s*\[?(Figure|Table)\s+\d+\.\d+', text))


def get_caption_info(text):
    """Extract caption type and number."""
    m = re.match(r'\s*\[?(Figure|Table)\s+(\d+\.\d+(?:\.\d+)*(?:\.\w+)?)\]?', text)
    if m:
        return m.group(1), m.group(2)
    return None, None


def convert():
    doc = fitz.open(PDF_PATH)
    fig_map = build_figure_page_map()
    output = []

    # Title
    output.append("# System Card: Claude Mythos Preview\n")
    output.append("**April 7, 2026**\n")
    output.append("[anthropic.com](https://anthropic.com)\n")
    output.append("---\n")

    # State machine for building paragraphs
    current_paragraph = []
    current_type = None  # 'body', 'footnote', 'bullet', 'quote', 'heading'
    footnotes = []
    current_footnote = []
    current_caption = []
    current_caption_page = None
    in_footnote_def = False
    pending_para_break = False  # defer para_break until we see the next line

    def flush_paragraph():
        nonlocal current_paragraph, current_type
        if not current_paragraph:
            return
        text = " ".join(current_paragraph)
        text = clean_text(text)
        # Clean up double spaces
        text = re.sub(r'  +', ' ', text)
        output.append(text + "\n")
        current_paragraph = []
        current_type = None

    def flush_caption(page_figs_override=None, fig_used_override=None):
        """Flush accumulated caption text, placing figure if available."""
        nonlocal current_caption, current_caption_page
        if not current_caption:
            return 0
        caption_text = " ".join(current_caption)
        caption_text = clean_text(caption_text)
        caption_text = re.sub(r'  +', ' ', caption_text)

        cap_type, cap_num = get_caption_info(caption_text)
        figs_for_page = fig_map.get(current_caption_page, [])

        if cap_type == "Figure" and figs_for_page:
            # Find next unused figure for this page
            # We track usage via a page-level counter stored in fig_usage
            used = fig_usage.get(current_caption_page, 0)
            if used < len(figs_for_page):
                fig_file = figs_for_page[used]
                fig_usage[current_caption_page] = used + 1
                output.append(f"\n![{caption_text}](figures/{fig_file})\n")
            else:
                output.append(f"\n**{caption_text}**\n")
        else:
            output.append(f"\n**{caption_text}**\n")

        current_caption = []
        current_caption_page = None
        return 0

    def flush_footnote():
        nonlocal current_footnote
        if current_footnote:
            text = " ".join(current_footnote)
            text = clean_text(text)
            text = re.sub(r'  +', ' ', text)
            # Convert "1 text" to "[^1]: text"
            m = re.match(r'^(\d+)\s+(.*)', text)
            if m:
                footnotes.append(f"[^{m.group(1)}]: {m.group(2)}")
            else:
                # Continuation - append to last footnote
                if footnotes:
                    footnotes[-1] += " " + text
                else:
                    footnotes.append(text)
            current_footnote = []

    fig_usage = {}  # page_num -> count of figures used on that page

    for page_idx in range(len(doc)):
        human_page = page_idx + 1

        # Skip title and TOC
        if page_idx == TITLE_PAGE or page_idx in TOC_PAGES:
            continue

        page = doc[page_idx]
        lines = extract_line_info(page)

        # Merge split headings: consecutive Poppins lines at the same size
        # where the second doesn't start with a section number
        merged_lines = []
        for line in lines:
            if (merged_lines
                    and line["poppins"] and merged_lines[-1]["poppins"]
                    and line["size"] == merged_lines[-1]["size"]
                    and line["text"].strip()
                    and not re.match(r'^\d', line["text"].strip())):
                # Continuation of a split heading — merge
                merged_lines[-1]["text"] = (
                    merged_lines[-1]["text"].rstrip() + " " + line["text"].strip()
                )
            else:
                merged_lines.append(line)
        lines = merged_lines

        for line in lines:
            text = line["text"].rstrip()

            # Handle footnote definitions (detected at span level)
            # Don't flush paragraph here — footnotes appear at page bottom
            # and the paragraph may continue on the next page.
            if line.get("is_footnote_def") and line.get("footnote_num"):
                flush_caption()
                flush_footnote()
                fn_num = line["footnote_num"]
                # Strip the leading number from the text
                fn_text = re.sub(r'^\d+\s*', '', text.strip())
                current_footnote = [f"{fn_num} {fn_text}"]
                in_footnote_def = True
                continue

            # Continuation of a footnote definition (size ~10, after a footnote_def)
            if in_footnote_def and line["size"] <= 10.5 and not line["poppins"] and current_footnote:
                current_footnote.append(text.strip())
                continue
            elif in_footnote_def:
                in_footnote_def = False

            line_type, heading_level = classify_line(line, human_page)

            if line_type == "page_number":
                continue

            if line_type == "para_break":
                # Defer the break — only flush if the next line isn't a
                # lowercase continuation of the current paragraph.
                pending_para_break = True
                continue

            if line_type == "caption":
                pending_para_break = False
                flush_paragraph()
                flush_footnote()
                flush_caption()
                current_caption = [text.strip()]
                current_caption_page = human_page
                continue

            if line_type == "caption_cont":
                if current_caption:
                    current_caption.append(text.strip())
                else:
                    # Stray bold small text - treat as footnote continuation
                    if current_footnote:
                        current_footnote.append(text.strip())
                continue

            if line_type == "footnote":
                pending_para_break = False
                flush_paragraph()
                flush_caption()
                flush_footnote()
                current_footnote = [text.strip()]
                continue

            if line_type == "footnote_cont":
                if current_footnote:
                    current_footnote.append(text.strip())
                continue

            # Flush any pending footnote/caption when we hit non-footnote content
            flush_footnote()
            flush_caption()

            if line_type == "heading":
                pending_para_break = False
                flush_paragraph()
                heading_text = clean_text(text.strip())
                prefix = "#" * heading_level
                output.append(f"\n{prefix} {heading_text}\n")
                continue

            # Body text
            stripped = text.strip()
            if not stripped:
                flush_paragraph()
                pending_para_break = False
                continue

            # Resolve deferred para_break: if the next text starts lowercase
            # and we're mid-paragraph, it's a continuation, not a new paragraph.
            cleaned = clean_text(stripped)
            if pending_para_break:
                pending_para_break = False
                if current_paragraph and stripped and stripped[0].islower():
                    # Continuation — append directly and skip bullet/body checks
                    current_paragraph.append(stripped)
                    continue
                else:
                    # Real paragraph break
                    flush_paragraph()

            # Check if this is a bullet point
            if cleaned.startswith("- ") or cleaned.startswith("  - "):
                flush_paragraph()
                current_type = "bullet"
                current_paragraph = [cleaned]
                continue

            # Continuation of bullet: if we're in a bullet and this line
            # starts lowercase, it's a wrapped continuation, not a new paragraph.
            if current_type == "bullet":
                if stripped[0].islower():
                    current_paragraph.append(stripped)
                    continue
                else:
                    # New sentence or structure — flush the bullet
                    text = " ".join(current_paragraph)
                    text = re.sub(r'  +', ' ', text)
                    output.append(text + "\n")
                    current_paragraph = []
                    current_type = None

            # Check for blockquote-like indentation (left > 120 and not a bullet)
            if line["block_left"] > 120 and not stripped.startswith("-"):
                if current_type != "quote":
                    flush_paragraph()
                    current_type = "quote"
                current_paragraph.append(stripped)
                continue

            if current_type == "quote":
                # Flush quote block and switch to body
                text_to_output = " ".join(current_paragraph)
                text_to_output = clean_text(text_to_output)
                text_to_output = re.sub(r'  +', ' ', text_to_output)
                output.append("\n> " + text_to_output + "\n")
                current_paragraph = []
                current_type = None

            # Regular body text - accumulate into paragraph
            if current_type == "body":
                current_paragraph.append(stripped)
            else:
                current_type = "body"
                current_paragraph.append(stripped)

        # End of page: don't flush paragraph (it may continue on next page)
        # But flush footnotes
        flush_footnote()

    # Flush any remaining
    if current_type == "quote" and current_paragraph:
        text_to_output = " ".join(current_paragraph)
        text_to_output = clean_text(text_to_output)
        text_to_output = re.sub(r'  +', ' ', text_to_output)
        output.append("\n> " + text_to_output + "\n")
        current_paragraph = []
    elif current_type == "bullet" and current_paragraph:
        text = " ".join(current_paragraph)
        text = re.sub(r'  +', ' ', text)
        output.append(text + "\n")
        current_paragraph = []
    else:
        flush_paragraph()

    # Clean and sort footnotes
    cleaned_footnotes = []
    for fn in footnotes:
        # Remove stray page numbers at the end of footnote text
        fn = re.sub(r'\s+\d{1,3}$', '', fn)
        # Parse the footnote number for sorting
        m = re.match(r'\[\^(\d+)\]:', fn)
        if m:
            fn_num = int(m.group(1))
            # Skip false positives (very high numbers)
            if fn_num > 100:
                continue
            cleaned_footnotes.append((fn_num, fn))

    # Sort by footnote number
    cleaned_footnotes.sort(key=lambda x: x[0])

    if cleaned_footnotes:
        for _, fn in cleaned_footnotes:
            output.append(fn + "\n")

    # Write output
    content = "\n".join(output)
    # Clean excessive blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)
    # Clean trailing whitespace on lines
    content = re.sub(r'[ \t]+\n', '\n', content)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        f.write(content)

    line_count = content.count('\n')
    fig_count = sum(1 for line in content.split('\n') if line.startswith('!['))
    fn_count = len(footnotes)
    print(f"Written to {OUT_PATH}")
    print(f"Lines: {line_count}, Figures placed: {fig_count}, Footnotes: {fn_count}")


if __name__ == "__main__":
    convert()
