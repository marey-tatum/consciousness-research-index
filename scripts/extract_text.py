#!/usr/bin/env python3
"""Extract raw text from the Mythos Preview System Card PDF.

Outputs page-delimited text to stdout for further processing.
"""

import fitz
import sys

PDF_PATH = "primary-sources/mythos-preview-system-card/Claude Mythos Preview System Card.pdf"


def extract_text():
    doc = fitz.open(PDF_PATH)

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        # Mark page boundaries for later processing
        print(f"<<<PAGE {page_num + 1}>>>")
        print(text)

    doc.close()


if __name__ == "__main__":
    extract_text()
