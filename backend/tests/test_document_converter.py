import io

import fitz
import pytest
from PIL import Image

from app.services.document_converter import DocumentConverter


@pytest.fixture
def sample_pdf(tmp_path):
    path = tmp_path / "sample.pdf"
    doc = fitz.open()
    for i in range(2):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1} content")
    doc.save(str(path))
    doc.close()
    return str(path)


def test_pdf_converts_to_one_png_per_page(sample_pdf):
    pages = DocumentConverter().convert(sample_pdf)
    assert [n for n, _ in pages] == [1, 2]
    for _, png in pages:
        img = Image.open(io.BytesIO(png))
        assert img.format == "PNG"


def test_jpg_converts_to_single_png_page(tmp_path):
    path = tmp_path / "photo.jpg"
    Image.new("RGB", (640, 480), "white").save(str(path), "JPEG")
    pages = DocumentConverter().convert(str(path))
    assert len(pages) == 1
    assert pages[0][0] == 1
    assert Image.open(io.BytesIO(pages[0][1])).format == "PNG"


def test_oversized_image_is_resized(tmp_path):
    path = tmp_path / "big.png"
    Image.new("RGB", (4096, 2048), "white").save(str(path), "PNG")
    pages = DocumentConverter().convert(str(path))
    img = Image.open(io.BytesIO(pages[0][1]))
    assert max(img.size) <= DocumentConverter.MAX_IMAGE_DIM


def test_unsupported_format_raises(tmp_path):
    path = tmp_path / "data.xlsx"
    path.write_bytes(b"not a real xlsx")
    with pytest.raises(ValueError, match="Unsupported file type"):
        DocumentConverter().convert(str(path))


def test_extract_text_from_pdf(sample_pdf):
    text = DocumentConverter().extract_text(sample_pdf)
    assert "Page 1 content" in text
    assert "Page 2 content" in text


def test_blank_page_detection(tmp_path):
    path = tmp_path / "mixed.pdf"
    doc = fitz.open()
    doc.new_page()  # blank
    page = doc.new_page()
    page.insert_text((72, 72), "Substantive bid content " * 20)
    doc.save(str(path))
    doc.close()

    pages = DocumentConverter().convert(str(path))
    assert DocumentConverter.is_blank_page(pages[0][1]) is True
    assert DocumentConverter.is_blank_page(pages[1][1]) is False
