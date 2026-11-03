#!/usr/bin/env python3
"""Builds deck/Cash_Logistics_Demo.pptx from the designed HTML deck.

Rebuilds deck/deck.pdf, renders each page to PNG, places it full-bleed on a
slide, sets a real (searchable) slide title hidden behind the image, and writes
speaker notes: SAY from deck/speaker_notes.json (verbatim), CLICK / CUE and
TIME from docs/demo_spoken_script_v2.md.

The slide count comes from the PDF and must match speaker_notes.json.

Usage: python3 deck/build_pptx.py [output.pptx]   (needs python-pptx and poppler)
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from pptx import Presentation
from pptx.util import Emu, Inches

DECK = Path(__file__).resolve().parent
ROOT = DECK.parent
PDF = DECK / "deck.pdf"
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DECK / "Cash_Logistics_Demo.pptx"
NOTES_JSON = DECK / "speaker_notes.json"
SCRIPT_MD = ROOT / "docs" / "demo_spoken_script_v2.md"

BACKUP_SLIDES = {8, 9}
APPENDIX_SLIDES = {14, 15}
LIVE_DEMO_TIME = "05:00–13:00"
QA_TIME = "18:00–26:00"


def build_pdf():
    subprocess.run(["bash", str(DECK / "build_pdf.sh")], check=True)
    info = subprocess.run(["pdfinfo", str(PDF)], capture_output=True, text=True, check=True).stdout
    return int(re.search(r"Pages:\s+(\d+)", info).group(1))


def render_pngs(tmp, expected):
    subprocess.run(["pdftoppm", "-png", "-r", "200", str(PDF), str(tmp / "p")], check=True)
    pngs = sorted(tmp.glob("p-*.png"), key=lambda p: int(p.stem.split("-")[1]))
    if len(pngs) != expected:
        sys.exit(f"rendered {len(pngs)} PNGs, expected {expected}")
    return pngs


def plain(text):
    text = re.sub(r"\*\*|\*|`|#", "", text)
    return re.sub(r"\s+", " ", text).strip()


def script_cues():
    """Map slide number -> {"cue": [...], "time": str, "heading": str} from the spoken script."""
    md = SCRIPT_MD.read_text()
    parts = re.split(r"^## (\d+)\. (.*)$", md, flags=re.M)
    out = {}
    for i in range(1, len(parts), 3):
        heading, body = parts[i + 1], re.split(r"^## ", parts[i + 2], flags=re.M)[0]
        m = re.search(r"· Slides? (\d+)", heading)
        if not m:
            continue
        slide = int(m.group(1))
        t = re.search(r"\((\d+:\d+)[–-](\d+:\d+)\)", heading)
        cue = []
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("**Click:**"):
                cue.append("Click: " + plain(line[len("**Click:**"):]))
            elif re.fullmatch(r"\*[^*].*[^*]\*", line):
                cue.append(plain(line))
        entry = out.setdefault(slide, {"cue": [], "time": "", "heading": ""})
        if "→ App" in heading:
            entry["cue"] += ["Then leave the slides and run the live app:"] + cue
            entry["app_time"] = f"{t.group(1)}–{t.group(2)}" if t else LIVE_DEMO_TIME
        else:
            entry["cue"] += cue
            entry["heading"] = plain(re.sub(r"\(.*?\)|·.*$", "", heading))
            if t:
                entry["time"] = f"{t.group(1)}–{t.group(2)}"
    return out


def notes_text(n, say, s):
    cue, time = list(s.get("cue", [])), s.get("time", "")
    if n in BACKUP_SLIDES:
        cue.insert(0, "Backup only if the live app fails. Otherwise skip this slide.")
        time = f"only if needed, during the live demo ({LIVE_DEMO_TIME})"
    elif n in APPENDIX_SLIDES:
        cue.insert(0, "Appendix: use in Q&A.")
        time = f"Q&A only, as needed ({QA_TIME} window)"
    if "(pause)" in say:
        cue.append("At each (pause), stop and wait for their answer.")
    if not cue:
        cue = ["No clicks. Stay on this slide."]
    if s.get("app_time"):
        time = f"{time} on this slide, then live app {s['app_time']}"
    lines = ["SAY:", say, "", "CLICK / CUE:"] + [plain(c) for c in cue] + ["", "TIME: " + (time or "as needed")]
    return "\n".join(lines)


def main():
    pages = build_pdf()
    notes = json.loads(NOTES_JSON.read_text())
    if pages != len(notes):
        sys.exit(f"deck.pdf has {pages} pages but speaker_notes.json has {len(notes)} entries")
    if [x["slide"] for x in notes] != list(range(1, pages + 1)):
        sys.exit("speaker_notes.json slide numbers are not 1..N in order")
    cues = script_cues()

    tmp = Path(tempfile.mkdtemp(prefix="pptx_src_"))
    try:
        pngs = render_pngs(tmp, pages)
        prs = Presentation()
        prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
        layout = next(l for l in prs.slide_layouts if l.name == "Title Only")
        for png, entry in zip(pngs, notes):
            slide = prs.slides.add_slide(layout)
            slide.shapes.title.text = entry["title"]
            # Added after the title, so the picture sits on top and hides it.
            slide.shapes.add_picture(str(png), Emu(0), Emu(0), prs.slide_width, prs.slide_height)
            slide.notes_slide.notes_text_frame.text = notes_text(
                entry["slide"], entry["notes"], cues.get(entry["slide"], {}))
        cp = prs.core_properties
        cp.title = "Right cash, right place: cash logistics demo"
        cp.subject = "Cash logistics demo (synthetic data)"
        cp.author = cp.last_modified_by = "Databricks Field Engineering"
        cp.keywords = cp.comments = cp.category = ""
        cp.created = cp.modified = datetime.now()
        prs.save(OUT)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"wrote {OUT} ({pages} slides, {OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
