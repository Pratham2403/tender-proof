"""
Generates mock seed documents using PyMuPDF and Pillow:
    1 demo tender PDF + 3 bidder submission packages of varying quality.

Run:  cd backend && python -m seed.generate_data
"""

import io
from pathlib import Path

import fitz
from PIL import Image, ImageFilter

DATA_DIR = Path(__file__).parent / "data"

TENDER_TEXT = """GOVERNMENT OF INDIA
CENTRAL RESERVE POLICE FORCE

NOTICE INVITING TENDER
Tender No: CRPF/2025/CONST/017

Subject: Construction of Administrative Block and Barracks at CRPF Group Centre

1. ELIGIBILITY CRITERIA

1.1 The bidder must have a minimum average annual turnover of Rs. 5.00 Crore
    during the last three financial years, supported by audited balance sheets
    or a certificate from a Chartered Accountant. (Mandatory)

1.2 The bidder must have successfully completed at least 3 similar construction
    projects within the last 5 years. Work completion certificates from the
    client must be furnished. (Mandatory)

1.3 The bidder must possess a valid GST registration certificate (GSTIN).
    (Mandatory)

1.4 The bidder must hold a valid ISO 9001 quality management certification,
    not expired as of 31 March 2025. (Mandatory)

1.5 The bidder should have prior experience executing projects of a similar
    nature (construction of institutional or government buildings). A work
    portfolio demonstrating similar project experience must be enclosed.
    (Mandatory)

1.6 The bidder may optionally furnish an MSME / Udyam registration certificate
    for fee exemption. (Optional)

2. SUBMISSION
Bids must be submitted before 1700 hrs on the closing date along with all
supporting documents listed in Section 1.
"""

BIDDER_A_PAGES = [
    """APEX CONSTRUCTIONS PVT LTD
Audited Financial Summary — FY 2022-2025

Certified by M/s Rao & Associates, Chartered Accountants

Average Annual Turnover (3 years): Rs. 8.45 Crore
FY 2022-23: Rs. 7.90 Crore
FY 2023-24: Rs. 8.30 Crore
FY 2024-25: Rs. 9.15 Crore

This is to certify that the above figures are drawn from the audited
balance sheets of Apex Constructions Pvt Ltd.
""",
    """APEX CONSTRUCTIONS PVT LTD
Work Experience Summary

Completed similar construction projects in the last 5 years: 5

1. District Court Building, Nagpur — completed 2021
2. Police Housing Complex, Pune — completed 2022
3. Government School Block, Amravati — completed 2023
4. CRPF Barracks Renovation, Nagpur — completed 2024
5. Municipal Office Building, Akola — completed 2024

All work completion certificates enclosed. These projects demonstrate
extensive experience in construction of institutional and government
buildings of a similar nature to the tendered work.
""",
    """APEX CONSTRUCTIONS PVT LTD
Statutory Registrations and Certifications

GST Registration: GSTIN 27AAACA1234F1Z5 (Valid)

ISO 9001:2015 Quality Management Certification
Certificate No: QMS/IN/44821
Valid until: 2026-08-14

MSME / Udyam Registration: UDYAM-MH-04-0012345
""",
]

BIDDER_B_PAGES = [
    """BUILDRIGHT ENGINEERS
Financial Statement Extract (scanned copy)

Average annual turnover for last three years: Rs. 3.20 Crore
FY 2022-23: Rs. 2.95 Crore
FY 2023-24: Rs. 3.10 Crore
FY 2024-25: Rs. 3.55 Crore

CA certificate attached separately.
""",
    """BUILDRIGHT ENGINEERS
Experience Certificate Summary

Similar projects completed in last 5 years: 2
1. Commercial Complex, Indore — completed 2022
2. Warehouse Construction, Bhopal — completed 2024

GST Registration: GSTIN 23AABCB9876K2Z1
ISO 9001 certificate: expired on 2024-11-30
""",
]

BIDDER_C_PAGES = [
    """GREENFORM INFRASTRUCTURE
Consolidated Bid Summary

Average Annual Turnover (FY 2022-2025): Rs. 6.10 Crore
(audited balance sheets enclosed)

Similar government building projects completed in last 5 years: 4
- State Archives Building, Jaipur (2021)
- Forest Department Office, Udaipur (2022)
- Police Training Hall, Kota (2023)
- Govt. Polytechnic Block, Ajmer (2025)

Our portfolio demonstrates strong experience in institutional and
government building construction of a similar nature.
""",
    """GREENFORM INFRASTRUCTURE
Registrations

GST Registration: GSTIN 08AAGCG4567L1Z9 (Valid)
ISO 9001:2015 — Certificate No. QMS/IN/77342
Valid until: 2027-01-20

(see attached photo of certificate)
""",
]

BIDDER_C_CERT_TEXT = """ISO 9001:2015
CERTIFICATE OF QUALITY MANAGEMENT

Awarded to: GREENFORM INFRASTRUCTURE
Certificate No: QMS/IN/77342
Valid until: 2027-01-20
"""


def _text_pdf(pages: list[str], out_path: Path, blur: bool = False):
    """Render text pages into a PDF. blur=True simulates a low-quality scan."""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page(width=595, height=842)  # A4
        page.insert_textbox(fitz.Rect(50, 50, 545, 792), text, fontsize=11,
                            fontname="helv")
    if not blur:
        doc.save(str(out_path))
        doc.close()
        return

    # Rasterize each page, blur + downsample it, and rebuild a scanned-looking PDF
    scanned = fitz.open()
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(100 / 72, 100 / 72))
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
        img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=45)
        new_page = scanned.new_page(width=595, height=842)
        new_page.insert_image(fitz.Rect(0, 0, 595, 842), stream=buf.getvalue())
    scanned.save(str(out_path))
    scanned.close()
    doc.close()


def _cert_photo(text: str, out_path: Path):
    """Render a certificate as a slightly imperfect JPG photo."""
    doc = fitz.open()
    page = doc.new_page(width=500, height=380)
    page.draw_rect(fitz.Rect(10, 10, 490, 370), color=(0.2, 0.3, 0.5), width=3)
    page.insert_textbox(fitz.Rect(40, 60, 460, 340), text, fontsize=14,
                        fontname="helv", align=fitz.TEXT_ALIGN_CENTER)
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    img = img.rotate(-1.5, fillcolor=(235, 232, 225), expand=True)
    img.save(str(out_path), format="JPEG", quality=70)
    doc.close()


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _text_pdf([TENDER_TEXT], DATA_DIR / "tender_demo.pdf")
    _text_pdf(BIDDER_A_PAGES, DATA_DIR / "bidder_a_typed.pdf")
    _text_pdf(BIDDER_B_PAGES, DATA_DIR / "bidder_b_scanned.pdf", blur=True)
    _text_pdf(BIDDER_C_PAGES, DATA_DIR / "bidder_c_mixed.pdf")
    _cert_photo(BIDDER_C_CERT_TEXT, DATA_DIR / "bidder_c_cert_photo.jpg")
    print(f"Generated seed documents in {DATA_DIR}")


if __name__ == "__main__":
    main()
