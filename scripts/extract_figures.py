#!/usr/bin/env python3
"""Extract figures from the Mythos Preview System Card PDF.

Extracts embedded images and renders pages with figures as high-quality PNGs.
Filters out tiny images (logos, icons) and keeps substantial figures.
"""

import fitz
import os
import sys

PDF_PATH = "primary-sources/mythos-preview-system-card/Claude Mythos Preview System Card.pdf"
OUT_DIR = "primary-sources/mythos-preview-system-card/figures"

MIN_IMAGE_AREA = 40000  # Skip images smaller than ~200x200


def extract_figures():
    doc = fitz.open(PDF_PATH)
    os.makedirs(OUT_DIR, exist_ok=True)

    fig_index = 0
    seen_xrefs = set()

    for page_num in range(len(doc)):
        page = doc[page_num]
        images = page.get_images(full=True)

        for img_info in images:
            xref = img_info[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            # Extract the image
            try:
                base_image = doc.extract_image(xref)
            except Exception as e:
                print(f"  Warning: Could not extract xref {xref} on page {page_num+1}: {e}")
                continue

            width = base_image["width"]
            height = base_image["height"]
            area = width * height

            if area < MIN_IMAGE_AREA:
                continue

            ext = base_image["ext"]
            image_bytes = base_image["image"]

            out_name = f"fig-{fig_index:03d}.png"
            out_path = os.path.join(OUT_DIR, out_name)

            if ext == "png":
                with open(out_path, "wb") as f:
                    f.write(image_bytes)
            else:
                # Convert to PNG via pixmap
                pix = fitz.Pixmap(image_bytes)
                if pix.n > 4:  # CMYK or similar
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                pix.save(out_path)

            print(f"  fig-{fig_index:03d}.png  page={page_num+1}  {width}x{height}  (xref={xref})")
            fig_index += 1

    print(f"\nExtracted {fig_index} figures to {OUT_DIR}/")
    doc.close()


if __name__ == "__main__":
    extract_figures()
