# System Card PDF-to-Markdown Conversion Style Guide

Style guide for converting Anthropic system card PDFs to agent-readable markdown. Based on the conventions established in the Opus 4.6 and Mythos Preview conversions.

## Setup

- Python venv with `pymupdf` (PyMuPDF/fitz) for PDF processing
- Conversion scripts live in `scripts/`
- Each system card gets its own directory under `primary-sources/`

## Output structure

```
primary-sources/<card-name>/
  <card-name>.md          # The converted markdown
  figures/
    fig-000.png           # Extracted figures, zero-padded 3-digit index
    fig-001.png
    ...
  <original>.pdf          # Keep the original PDF
```

## Font patterns (Anthropic system cards from Google Docs Renderer)

These may vary between cards but have been consistent so far:

| Font | Size | Markdown |
|------|------|----------|
| Poppins-SemiBold | 16.0 | `#` for numbered sections, `##` for unnumbered (Changelog, Abstract) |
| Poppins-Medium | 14.0 | `##` for X.Y sections |
| Poppins-Medium | 13.0 | `###` for X.Y.Z sections |
| Lora-Bold | 11.0 | `####` for X.Y.Z.W sections (detected by bold + section number pattern) |
| Lora-Regular | 11.0 | Body text |
| Lora-Bold | 9.0 | Figure/table captions |
| Superscript (6.0) + Lora-Regular (10.0) | Mixed | Footnote definitions |
| Lora-Regular | 9.0 | Page numbers (standalone digits) |

## Title block format

```markdown
# System Card: <Model Name>

**<Date>**

[anthropic.com](https://anthropic.com)

---
```

## Heading conventions

- `#` (h1): Main numbered sections: `# 1 Introduction`, `# 2 RSP evaluations`
- `##` (h2): Unnumbered standalone sections (Changelog, Abstract) AND X.Y subsections
- `###` (h3): X.Y.Z sub-subsections
- `####` (h4): X.Y.Z.W sub-sub-subsections
- `#####` (h5): X.Y.Z.W.V (rare)
- Preserve section numbers in headings (e.g., `## 1.1 Model training and characteristics`)

## Figure references

```markdown
![[Figure X.Y.Z.A] Caption text describing the figure.](figures/fig-NNN.png)
```

- Multi-panel figures: When a single logical figure spans multiple pages or has sub-panels, reference them sequentially with panel annotations:
  ```markdown
  ![[Figure X.Y.Z.A] Full caption text (Panel 1/N)](figures/fig-NNN.png)
  
  ![[Figure X.Y.Z.A] (Panel 2/N)](figures/fig-NNN.png)
  ```
- Skip decorative images (separators, logos, tiny graphics < ~200x200px)
- Figure numbering (fig-NNN) is sequential by extraction order, not by figure number in the document

## Table references

Tables without embedded images are formatted as bold caption text:

```markdown
**[Table X.Y.Z.A] Caption text describing the table.**
```

If a table is rendered as an image, use the figure reference format instead.

Markdown tables should be used where the PDF table can be cleanly converted:

```markdown
| Column 1 | Column 2 | Column 3 |
|---|---|---|
| data | data | data |
```

## Footnotes

Footnote references in body text use markdown superscript syntax. Footnote definitions go at the end of the document:

```markdown
[^1]: Footnote text here.

[^2]: Another footnote.
```

- Sort by footnote number
- Strip stray page numbers from the end of footnote text
- Filter out false positives (e.g., numbers > 100 that aren't real footnotes)

## Text formatting

- Bullets: `- ` for top-level, `  - ` for sub-bullets
- Smart quotes: Convert to ASCII (`"` and `'`)
- Em dashes: `---`
- En dashes: `--`
- Zero-width characters: Strip (`\u200b`, `\u200c`)
- Non-breaking spaces: Convert to regular spaces

## Paragraph handling

- Join lines that are part of the same paragraph (PDF wraps at page width)
- Paragraph breaks are indicated by empty lines within text blocks
- Paragraphs may continue across page boundaries
- Do NOT join across heading boundaries, bullet points, or figure captions

## Blockquotes

Indented text (left margin > ~120px) that doesn't start with a bullet is treated as a blockquote:

```markdown
> Quoted text here.
```

## Known challenges

1. **Multi-line headings**: Long section titles that wrap to a second line may produce a split heading (`## first part` / `## second part`). The script has a pre-processing merger for consecutive Poppins-font lines at the same size, but edge cases may remain.
2. **Bullet continuation**: Bullets that wrap across PDF lines may produce extra blank lines. The script uses a content-based heuristic (lowercase first character → continuation), which handles most cases but misses continuations starting with proper nouns.
3. **Tables**: Multi-column PDF tables extract as garbled text (columns interleaved). Must be manually reformatted as markdown tables using PDF source data. See "Manual table conversion" below.
4. **Code blocks in transcripts**: Model output transcripts embedded in the document need manual formatting with code fences.
5. **Footnote definitions at size 10.0**: These are at a different size than expected (not 9.0) and use a superscript number (size 6.0) as the first span.
6. **Cross-page paragraph breaks**: Paragraphs spanning page boundaries can get false breaks, especially when footnote definitions appear at the bottom of the first page. The script uses a deferred `pending_para_break` mechanism to handle most cases, but breaks before uppercase-starting text (proper nouns like "Claude", "Sonnet") still need post-processing.
7. **Merged numbered lists**: When the converter joins lines aggressively, sequential numbered list items can end up on one line (e.g., `1. First thing 2. Second thing`). Split with a regex for patterns like `. N. [A-Z]` where N > 1.
8. **Merged subheadings**: Short bold subheadings in the PDF (e.g., "Details", "Results", "Methodology", "Benchmark of notable capability") extract as plain text merged into the preceding or following paragraph. These need manual separation onto their own line and wrapping in `**bold**`.
9. **Table caption run-ons**: Table caption text (bold `**[Table X.X]...**`) sometimes merges with the following paragraph onto the same line. Insert a line break after the closing `**`.
10. **Multi-panel figures**: Figures that span multiple PDF pages need manual placement after automated extraction. The script extracts them sequentially but can't determine which logical figure they belong to.
11. **Out-of-order blocks (misplaced blockquotes)**: PyMuPDF sometimes returns blocks in internal storage order rather than visual (y-position) order. Indented blockquotes (x~82 vs body text at x~72) can appear after the page number block in extraction order, causing them to be placed in the wrong section of the output. Check for blockquote text that appears *after* a heading when visually it belongs *before* it.
12. **Flattened conversation transcripts**: Multi-turn conversation transcripts (`User:`, `Assistant:`, stage directions like `[Opening turn]`) extract as plain body text. They need manual formatting as blockquotes with bold labels (`> **User:**`, `> **Assistant:**`), and `<thinking>` blocks need code fences.
13. **Missing transcript captions**: `[Transcript X.Y.Z.A]` captions (bold 9pt) often get stripped or merged into surrounding text. Search the PDF for all `[Transcript` occurrences and verify each has a corresponding caption in the markdown.
14. **Inline blockquotes merged into body text**: Indented quotes from the PDF (x~82) that appear mid-paragraph get joined into the surrounding body text instead of being extracted as `>` blockquotes. These are common in qualitative assessment sections where model output is quoted inline.
15. **Content in out-of-order PDF blocks**: Some content (like blocklists, test file lists, or code-formatted text) lives in PDF blocks that the text extractor places at the wrong position or skips entirely. If a section says "the following:" and is immediately followed by a heading, the "following" content is likely in an out-of-order block. Use the dict extractor to find it by y-position.

## Manual table conversion

PDF tables with 3+ columns reliably extract as garbled text. To fix:

1. **Extract table data from PDF**: Use a script like this to get x-positions and text for each table page:
   ```python
   import fitz
   doc = fitz.open("path/to/card.pdf")
   for page_num in [220, 221, ...]:  # 0-indexed
       page = doc[page_num]
       blocks = page.get_text("dict")["blocks"]
       for block in blocks:
           for line in block.get("lines", []):
               for span in line["spans"]:
                   print(f"  x={int(span['origin'][0]):3d}: {span['text']}")
   ```
2. **Identify columns** by x-position clusters. Each distinct x-position is a column.
3. **Reconstruct the table** as a markdown table, matching values to columns by their x-position.
4. **Restore truncated captions** from the PDF source text — the converter often cuts them off.

For tables with very long text cells (e.g., the welfare interview summary), consider structured list format instead of a markdown table:
```markdown
**Category name**

*Concern description*
- Response: Claude's answer summary
- Intervention: Suggested intervention
```

## Conversation transcript formatting

The system card includes multi-turn conversation transcripts (model outputs, user inputs, thinking blocks). These extract as plain text merged into body paragraphs. To fix:

1. **Identify transcripts**: Search the PDF for `[Transcript` captions (bold 9pt). Each caption corresponds to a preceding transcript block at x~82 (indented from body text at x~72).
2. **Format turn labels**: Wrap `User:` and `Assistant:` labels in bold within blockquotes:
   ```markdown
   > **User:** question text
   >
   > **Assistant:** response text
   ```
3. **Stage directions**: Labels like `[Opening turn]`, `[Early conversation]`, etc. should be bold within the blockquote:
   ```markdown
   > **[Opening turn]** transcript text...
   ```
4. **Thinking blocks**: `<thinking>` content (usually in `RobotoMono-Regular` 9pt) should be wrapped in code fences within the blockquote:
   ```markdown
   > **Assistant:**
   > ```
   > <thinking>
   > reasoning text...
   > </thinking>
   > ```
   ```
5. **Action lines**: Tool use descriptions like `[greps the code, finds...]` should also use code fences.
6. **Caption placement**: The `[Transcript X.Y.Z.A]` caption goes immediately after the blockquoted transcript, as bold text:
   ```markdown
   **[Transcript X.Y.Z.A]** Caption describing what the transcript shows.
   ```

## Quality checklist

After automated conversion:

- [ ] All headings present and at correct levels (compare against PDF TOC)
- [ ] No split headings (single heading broken across two `##` lines)
- [ ] Figures placed near their captions (check multi-panel figures especially)
- [ ] Footnotes sorted, cleaned of stray page numbers, no false positives
- [ ] Bullet items properly joined (no mid-item blank lines)
- [ ] Blockquotes properly formatted
- [ ] No raw page numbers remaining in body text
- [ ] Title block matches the standard format
- [ ] All tables formatted as markdown tables (not garbled column text)
- [ ] Table captions on their own line (not merged with following paragraph)
- [ ] Bold subheadings separated from surrounding text (search for short capitalized phrases at line starts)
- [ ] Numbered lists not merged onto single lines
- [ ] All `[Transcript X.Y.Z.A]` captions present (compare count against PDF)
- [ ] Conversation transcripts properly blockquoted with bold `**User:**`/`**Assistant:**` labels
- [ ] `<thinking>` blocks and action lines (e.g., `[greps the code...]`) preserved in code fences
- [ ] Inline model quotes extracted from body text into `>` blockquotes
- [ ] No "the following:" lines immediately followed by a heading (indicates missing content)
- [ ] Blocklists, test lists, and other structured content not dropped by the extractor
