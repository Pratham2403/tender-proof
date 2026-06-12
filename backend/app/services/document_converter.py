import io
import subprocess
import tempfile
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image


class DocumentConverter:
    """
    Converts any supported document format into a list of PNG page images.
    Responsibility: format detection and page rendering only. No LLM calls.
    """

    SUPPORTED_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp"}
    MAX_IMAGE_DIM = 2048  # pixels on longest edge — Qwen2.5-VL optimal input size

    def convert(self, file_path: str) -> list[tuple[int, bytes]]:
        """
        Returns: list of (page_number, png_bytes) tuples, 1-indexed.
        Raises: ValueError for unsupported formats.
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return self._pdf_to_images(path)
        elif suffix in {".docx", ".doc"}:
            return self._docx_to_images(path)
        elif suffix in self.SUPPORTED_IMAGE_TYPES:
            return self._image_to_page(path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

    def extract_text(self, file_path: str) -> str:
        """
        Plain-text extraction for digitally-born documents (used by schema
        compilation, which needs text rather than page images).
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            doc = fitz.open(str(path))
            text = "\n\n".join(page.get_text() for page in doc)
            doc.close()
            return text
        elif suffix in {".docx", ".doc"}:
            from docx import Document as DocxDocument
            docx = DocxDocument(str(path))
            return "\n".join(p.text for p in docx.paragraphs)
        else:
            raise ValueError(f"Cannot extract text from file type: {suffix}")

    def _pdf_to_images(self, path: Path) -> list[tuple[int, bytes]]:
        doc = fitz.open(str(path))
        pages = []
        for i, page in enumerate(doc, start=1):
            mat = fitz.Matrix(150 / 72, 150 / 72)  # 150 DPI
            pix = page.get_pixmap(matrix=mat)
            png_bytes = pix.tobytes("png")
            png_bytes = self._resize_if_needed(png_bytes)
            pages.append((i, png_bytes))
        doc.close()
        return pages

    def _docx_to_images(self, path: Path) -> list[tuple[int, bytes]]:
        # LibreOffice headless converts DOCX → PDF, then _pdf_to_images
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                ["libreoffice", "--headless", "--convert-to", "pdf",
                 "--outdir", tmp, str(path)],
                check=True, capture_output=True
            )
            pdf_path = Path(tmp) / (path.stem + ".pdf")
            return self._pdf_to_images(pdf_path)

    def _image_to_page(self, path: Path) -> list[tuple[int, bytes]]:
        # Normalize all image inputs to PNG so the data-URI mime type is correct
        img = Image.open(str(path)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return [(1, self._resize_if_needed(buf.getvalue()))]

    def _resize_if_needed(self, png_bytes: bytes) -> bytes:
        img = Image.open(io.BytesIO(png_bytes))
        w, h = img.size
        if max(w, h) <= self.MAX_IMAGE_DIM:
            return png_bytes
        scale = self.MAX_IMAGE_DIM / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
