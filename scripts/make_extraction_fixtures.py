"""Regenerate the extraction fixtures in data/fixtures/extraction.

Needs reportlab + Pillow (dev only, not a runtime dependency):
    pip install reportlab
All people and companies are invented.
"""
from __future__ import annotations

import io
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, os.pardir, "data", "fixtures", "extraction")
os.makedirs(OUT, exist_ok=True)

W, H = A4
BULLET = "•"
NDASH = "–"


def p(name):
    return os.path.join(OUT, name)


# ---------------------------------------------------------------- 1. one column
def one_column():
    c = canvas.Canvas(p("01_simple_1col.pdf"), pagesize=A4)

    def page1():
        y = H - 25 * mm
        c.setFont("Helvetica-Bold", 20)
        c.drawString(25 * mm, y, "Ravi Menon")
        y -= 7 * mm
        c.setFont("Helvetica", 10)
        c.drawString(25 * mm, y, "Backend Engineer  |  Pune, India")
        y -= 5 * mm
        c.drawString(25 * mm, y, "ravi.menon@example.invalid  |  +91 90000 11111  |  github.com/ravimenon-demo")
        y -= 12 * mm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(25 * mm, y, "SUMMARY")
        y -= 6 * mm
        c.setFont("Helvetica", 10)
        for line in [
            "Backend engineer with 6 years building payment and ledger services in Python and Go.",
            "Owned two production migrations and led a team of four for eighteen months.",
        ]:
            c.drawString(25 * mm, y, line)
            y -= 5 * mm
        y -= 6 * mm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(25 * mm, y, "EXPERIENCE")
        y -= 8 * mm
        roles = [
            ("Senior Backend Engineer", "Tavira Payments", f"Mar 2021 {NDASH} Present", [
                "Rebuilt the settlement ledger in Go, cutting end-of-day close from 40 min to 6 min.",
                "Designed an idempotent retry layer over Kafka handling 2.4M events/day.",
                "Mentored three juniors; ran the on-call rotation for the payments pod.",
            ]),
            ("Backend Engineer", "Halden Logistics", f"Jul 2019 {NDASH} Feb 2021", [
                "Built a FastAPI route-planning service used by 300 depot operators.",
                "Moved batch jobs from cron to Airflow, removing 11 hours of manual ops per week.",
            ]),
        ]
        for title, org, dates, bullets in roles:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(25 * mm, y, f"{title}, {org}")
            c.setFont("Helvetica-Oblique", 10)
            c.drawRightString(W - 25 * mm, y, dates)
            y -= 6 * mm
            c.setFont("Helvetica", 10)
            for b in bullets:
                c.drawString(30 * mm, y, f"{BULLET} {b}")
                y -= 5 * mm
            y -= 4 * mm

    page1()
    c.showPage()

    # page 2 — makes this the "typical 2-page resume" timing sample
    y = H - 25 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(25 * mm, y, "EXPERIENCE (continued)")
    y -= 8 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(25 * mm, y, "Junior Developer, Sarath Analytics")
    c.setFont("Helvetica-Oblique", 10)
    c.drawRightString(W - 25 * mm, y, f"Aug 2018 {NDASH} Jun 2019")
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    for b in [
        "Wrote ETL scripts in Python/pandas for a 12-table reporting warehouse.",
        "Added pytest coverage to a legacy Django codebase, 14% to 61%.",
    ]:
        c.drawString(30 * mm, y, f"{BULLET} {b}")
        y -= 5 * mm
    y -= 8 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(25 * mm, y, "EDUCATION")
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    c.drawString(25 * mm, y, f"B.E. Computer Engineering, Deccan Institute of Technology {NDASH} 2018")
    y -= 10 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(25 * mm, y, "SKILLS")
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    c.drawString(25 * mm, y, "Python, Go, FastAPI, Django, PostgreSQL, Kafka, Redis, Docker, AWS, Terraform")
    c.showPage()
    c.save()


# ------------------------------------------------- 2/3. two column (two orders)
_HEADER = [
    ("Helvetica-Bold", 20, "Ananya Kulkarni"),
    ("Helvetica", 10, "Data Platform Engineer  |  Bengaluru, India"),
    ("Helvetica", 10, "ananya.k@example.invalid  |  +91 98888 22222"),
]

# (y_offset_mm, left_line, right_line) rows for the body, drawn side by side
_LEFT_X = 22 * mm
_RIGHT_X = 128 * mm
_BODY_ROWS = [
    ("EXPERIENCE", "SKILLS", True),
    ("Data Platform Engineer", "Python, Scala, SQL", False),
    ("Neelkanth Retail Systems", "Apache Spark, Kafka", False),
    (f"Apr 2022 {NDASH} Present", "Airflow, dbt, Snowflake", False),
    (f"{BULLET} Built a Spark pipeline over 9 TB of", "AWS (EMR, S3, Glue)", False),
    ("  clickstream data, 22 min end to end.", "Terraform, Docker", False),
    (f"{BULLET} Cut warehouse spend 34% by moving", "", False),
    ("  cold partitions to S3 + Athena.", "CERTIFICATIONS", True),
    (f"{BULLET} Introduced dbt; 140 models, tested.", "AWS Solutions Architect", False),
    ("", "Associate (2023)", False),
    ("Analytics Engineer", "Databricks Data Engineer", False),
    ("Marisol Consulting", "Professional (2022)", False),
    (f"Jan 2020 {NDASH} Mar 2022", "", False),
    (f"{BULLET} Owned the reporting warehouse for", "EDUCATION", True),
    ("  four retail clients (Redshift).", "M.Tech Data Science", False),
    (f"{BULLET} Automated 31 recurring reports.", "Koregaon University, 2019", False),
    ("", "B.Sc Statistics", False),
    ("PROJECTS", "Koregaon University, 2017", True),
    (f"{BULLET} kafka-lag-exporter fork, 200+ stars.", "", False),
    (f"{BULLET} Wrote a dbt macro pack used in 3 orgs.", "LANGUAGES", True),
    ("", "English, Marathi, Kannada", False),
]


def _two_col_header(c):
    y = H - 22 * mm
    for font, size, text in _HEADER:
        c.setFont(font, size)
        c.drawString(_LEFT_X, y, text)
        y -= (size * 0.45 + 3) * mm / 2.5
    return y - 8 * mm


def two_column(filename, interleaved: bool):
    """interleaved=True  -> content stream emits left/right line by line (Word-table style)
       interleaved=False -> content stream emits the whole left column, then the right."""
    c = canvas.Canvas(p(filename), pagesize=A4)
    top = _two_col_header(c)
    step = 6.2 * mm

    def draw(x, text, bold, i):
        if not text:
            return
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 11 if bold else 9.5)
        c.drawString(x, top - i * step, text)

    if interleaved:
        for i, (l, r, bold) in enumerate(_BODY_ROWS):
            draw(_LEFT_X, l, bold, i)
            draw(_RIGHT_X, r, bold, i)
    else:
        for i, (l, _r, bold) in enumerate(_BODY_ROWS):
            draw(_LEFT_X, l, bold, i)
        for i, (_l, r, bold) in enumerate(_BODY_ROWS):
            draw(_RIGHT_X, r, bold, i)
    c.showPage()
    c.save()


# ------------------------------------------------------------ 4. table + bullets
def table_pdf():
    c = canvas.Canvas(p("04_table_bullets.pdf"), pagesize=A4)
    y = H - 25 * mm
    c.setFont("Helvetica-Bold", 18)
    c.drawString(20 * mm, y, "Farhan Qureshi")
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, "QA Automation Lead  |  Hyderabad, India  |  farhan.q@example.invalid")
    y -= 14 * mm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, "EXPERIENCE")
    y -= 8 * mm

    cols = [20 * mm, 72 * mm, 122 * mm, 160 * mm]
    headers = ["Role", "Company", "Period", "Stack"]
    rows = [
        ["QA Automation Lead", "Vellore Softworks", f"2022{NDASH}Present", "Playwright"],
        ["Senior QA Engineer", "Vellore Softworks", f"2020{NDASH}2022", "Selenium"],
        ["QA Engineer", "Iravati Systems", f"2018{NDASH}2020", "pytest"],
        ["Test Analyst", "Iravati Systems", f"2016{NDASH}2018", "Manual/JIRA"],
    ]
    c.setFont("Helvetica-Bold", 10)
    for x, h in zip(cols, headers):
        c.drawString(x, y, h)
    y -= 2 * mm
    c.line(20 * mm, y, W - 20 * mm, y)
    y -= 5 * mm
    c.setFont("Helvetica", 10)
    for row in rows:
        for x, cell in zip(cols, row):
            c.drawString(x, y, cell)
        y -= 6 * mm
    y -= 2 * mm
    c.line(20 * mm, y, W - 20 * mm, y)
    y -= 12 * mm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, "HIGHLIGHTS")
    y -= 7 * mm
    c.setFont("Helvetica", 10)
    for b in [
        "Reduced regression suite runtime from 3h 10m to 27m via parallel Playwright workers.",
        "Built a flaky-test quarantine bot; false-failure rate fell from 9% to under 1%.",
        "Trained 12 manual testers on Python automation over two quarters.",
    ]:
        c.drawString(24 * mm, y, f"{BULLET} {b}")
        y -= 5.5 * mm
    c.showPage()
    c.save()


# --------------------------------------------------------------- 5. DOCX resume
def docx_resume():
    import docx
    from docx.shared import Pt

    d = docx.Document()
    d.add_heading("Sneha Ravindran", level=0)
    d.add_paragraph("Product Designer  |  Kochi, India  |  sneha.r@example.invalid  |  +91 97777 33333")

    d.add_heading("Summary", level=1)
    d.add_paragraph(
        "Product designer with 7 years across fintech and health apps. "
        "Leads design systems work and hands-on prototyping."
    )

    d.add_heading("Experience", level=1)
    t = d.add_table(rows=1, cols=3)
    t.style = "Table Grid"
    hdr = t.rows[0].cells
    hdr[0].text = "Role"
    hdr[1].text = "Company"
    hdr[2].text = "Period"
    for role, org, period in [
        ("Lead Product Designer", "Palani Health", f"Feb 2022 {NDASH} Present"),
        ("Product Designer", "Cheruvu Fintech", f"Jun 2019 {NDASH} Jan 2022"),
        ("UX Designer", "Ambalika Labs", f"Aug 2017 {NDASH} May 2019"),
    ]:
        cells = t.add_row().cells
        cells[0].text = role
        cells[1].text = org
        cells[2].text = period

    d.add_heading("Selected work", level=1)
    for b in [
        "Rebuilt the Palani Health onboarding; drop-off fell from 48% to 19%.",
        "Owned a 60-component design system shipped in Figma and React.",
        "Ran 40+ moderated usability sessions across three markets.",
    ]:
        d.add_paragraph(b, style="List Bullet")

    d.add_heading("Skills", level=1)
    para = d.add_paragraph()
    run = para.add_run("Figma, Framer, React, Storybook, user research, accessibility (WCAG 2.2)")
    run.font.size = Pt(10)

    d.add_heading("Education", level=1)
    d.add_paragraph(f"B.Des Communication Design, Trivandrum Design School {NDASH} 2017")
    d.save(p("05_resume.docx"))


# ------------------------------------------------------- 6. image-only (scanned)
def scanned_pdf():
    img = Image.new("RGB", (1240, 1754), "white")
    dr = ImageDraw.Draw(img)
    lines = [
        "Imran Sheikh",
        "Site Reliability Engineer  |  Nagpur, India",
        "imran.sheikh@example.invalid",
        "",
        "EXPERIENCE",
        "SRE, Bhandara Cloud Services, 2021 - Present",
        "- Ran a 180-node Kubernetes estate across three regions.",
        "- Cut p99 latency 38% by reworking the ingress tier.",
        "",
        "SKILLS",
        "Kubernetes, Prometheus, Go, Terraform, Linux",
    ]
    y = 120
    for line in lines:
        dr.text((110, y), line, fill="black")
        y += 46
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    c = canvas.Canvas(p("06_scanned_image_only.pdf"), pagesize=A4)
    c.drawImage(ImageReader(buf), 0, 0, width=W, height=H)
    c.showPage()
    c.save()


# ------------------------------------------------- 9. tight inter-word spacing
# Regression fixture for the x_tolerance bug (app/extraction.py `_TOLERANCE`).
#
# Real PDFs frequently store NO space characters: the producer positions each
# word with a text-matrix move, and pdfplumber has to infer the break from the
# horizontal gap. reportlab's drawString always writes a real space glyph, which
# pdfplumber splits on unconditionally, so a normal drawString CANNOT reproduce
# the bug. This page therefore places every glyph itself and never emits a
# space, exactly as a tight-tracking Word/InDesign export does.
#
# The two gaps are chosen to straddle the thresholds:
#   body    10 pt, word gap 2.2 pt -> old default (3 pt) FUSES the words;
#                                     ratio 0.15 (= 1.5 pt) splits them.
#   heading 20 pt, letter gap 2.0 pt, word gap 4.4 pt
#                                  -> ratio 0.15 (= 3.0 pt) keeps the letters
#                                     together; a FLAT 1.5 pt would shatter the
#                                     name into single letters.
_TIGHT_WORD_GAP_RATIO = 0.22   # word gap as a fraction of font size
_TIGHT_HEAD_CHAR_GAP = 2.0     # pt of tracking inside the big heading


def _place_glyphs(c, x, y, text, font, size, char_gap=0.0):
    """Draw one line glyph by glyph, with no space character anywhere."""
    c.setFont(font, size)
    word_gap = _TIGHT_WORD_GAP_RATIO * size
    for i, wordtext in enumerate(text.split(" ")):
        if i:
            x += word_gap
        for ch in wordtext:
            c.drawString(x, y, ch)
            x += c.stringWidth(ch, font, size) + char_gap
        x -= char_gap


def tight_spacing():
    c = canvas.Canvas(p("09_tight_spacing.pdf"), pagesize=A4)
    y = H - 25 * mm
    _place_glyphs(c, 22 * mm, y, "Priya Deshmukh", "Helvetica-Bold", 20,
                  char_gap=_TIGHT_HEAD_CHAR_GAP)
    y -= 8 * mm
    for line, font, size in [
        ("Software Engineer | Nashik, India | priya.deshmukh@example.invalid", "Helvetica", 10),
        ("", "Helvetica", 10),
        ("EXPERIENCE", "Helvetica-Bold", 11),
        ("Solvent Labs India, Software Engineer", "Helvetica-Bold", 10),
        (f"Jun 2021 {NDASH} Present", "Helvetica-Oblique", 10),
        ("Strong focus on system optimization, profiling and release hygiene.", "Helvetica", 10),
        ("Rewrote the invoice reconciler and cut the nightly run from 90 to 12 minutes.", "Helvetica", 10),
        ("Owned the release checklist for a team of five engineers.", "Helvetica", 10),
        ("", "Helvetica", 10),
        ("Kavira Systems, Associate Engineer", "Helvetica-Bold", 10),
        (f"Aug 2019 {NDASH} May 2021", "Helvetica-Oblique", 10),
        ("Maintained a Django billing service used by two hundred branch offices.", "Helvetica", 10),
        ("", "Helvetica", 10),
        ("EDUCATION", "Helvetica-Bold", 11),
        ("Bachelor of Engineering, Ghatkopar Institute of Technology, 2019", "Helvetica", 10),
        ("", "Helvetica", 10),
        ("SKILLS", "Helvetica-Bold", 11),
        ("Python, Django, PostgreSQL, Redis, Docker, JavaScript, GraphQL", "Helvetica", 10),
    ]:
        if line:
            _place_glyphs(c, 22 * mm, y, line, font, size)
        y -= 6 * mm
    c.showPage()
    c.save()



# ---------------------------------------------------------------- 7. corrupt pdf
def corrupt_pdf():
    raw = open(p("01_simple_1col.pdf"), "rb").read()
    open(p("07_truncated.pdf"), "wb").write(raw[: int(len(raw) * 0.4)])
    # and a file that is simply not a PDF at all, named .pdf
    open(p("08_not_a_pdf.pdf"), "wb").write(b"Dear hiring manager,\nI am not a PDF.\n" * 5)


if __name__ == "__main__":
    one_column()
    two_column("02_two_col_interleaved.pdf", interleaved=True)
    two_column("03_two_col_by_column.pdf", interleaved=False)
    table_pdf()
    docx_resume()
    scanned_pdf()
    corrupt_pdf()
    tight_spacing()
    for f in sorted(os.listdir(OUT)):
        print(f, os.path.getsize(os.path.join(OUT, f)), "bytes")
