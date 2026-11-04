#!/usr/bin/env python3
"""Offline conversion benchmarks for JustConvertIt Phase 1.

Generates deterministic fixtures, runs registry.convert(), and prints JSON +
markdown-friendly rows. No network. Optional ops skip when engines missing.

Usage (from repo root, venv active):
  python scripts/benchmarks/run_benchmarks.py
  python scripts/benchmarks/run_benchmarks.py --json-out /tmp/bench.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import resource
import shutil
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from omniconvert.core.registry import build_default_registry  # noqa: E402
from omniconvert.services.dependencies import get_dependency_service  # noqa: E402


@dataclass
class BenchRow:
    name: str
    operation_id: str
    status: str  # ok | skip | fail
    input_bytes: int = 0
    output_bytes: int = 0
    wall_ms: float = 0.0
    peak_rss_mb: float = 0.0
    detail: str = ""
    meta: str = ""


def _rss_mb() -> float:
    # Linux: ru_maxrss is KiB; macOS: bytes. Detect via platform.
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return usage / (1024 * 1024)
    return usage / 1024.0


def _write_png(path: Path, w: int, h: int, color: tuple[int, int, int] = (40, 80, 120)) -> None:
    from PIL import Image

    Image.new("RGB", (w, h), color).save(path, format="PNG")


def _write_jpeg(path: Path, w: int, h: int) -> None:
    from PIL import Image

    Image.new("RGB", (w, h), (200, 100, 50)).save(path, format="JPEG", quality=85)


def _write_pdf(path: Path, pages: int = 2) -> None:
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path))
    for i in range(pages):
        c.drawString(72, 720, f"Benchmark page {i + 1}")
        c.showPage()
    c.save()


def _write_csv(path: Path, rows: int, cols: int = 8) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([f"col{i}" for i in range(cols)])
        for r in range(rows):
            w.writerow([f"v{r}_{c}" for c in range(cols)])


def _write_docx(path: Path) -> None:
    from docx import Document

    doc = Document()
    doc.add_heading("Benchmark DOCX", level=1)
    doc.add_paragraph("Phase 1 performance fixture.")
    doc.save(str(path))


def _write_wav(path: Path, seconds: float = 0.5) -> None:
    """Minimal PCM WAV (no FFmpeg needed to create)."""
    import struct
    import wave

    rate = 16000
    n = int(rate * seconds)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        for i in range(n):
            # quiet sine-ish
            val = int(1000 * ((i % 40) / 40.0 - 0.5))
            w.writeframes(struct.pack("<h", val))


def make_fixtures(base: Path) -> dict[str, Path]:
    base.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    paths["png_small"] = base / "small.png"
    paths["png_large"] = base / "large.png"
    paths["jpeg_med"] = base / "med.jpg"
    paths["pdf"] = base / "doc.pdf"
    paths["csv_small"] = base / "small.csv"
    paths["csv_large"] = base / "large.csv"
    paths["docx"] = base / "sample.docx"
    paths["wav"] = base / "tone.wav"

    _write_png(paths["png_small"], 64, 64)
    _write_png(paths["png_large"], 2400, 1800)
    _write_jpeg(paths["jpeg_med"], 1200, 900)
    _write_pdf(paths["pdf"], pages=3)
    _write_csv(paths["csv_small"], 50)
    _write_csv(paths["csv_large"], 5000)
    _write_docx(paths["docx"])
    _write_wav(paths["wav"], 0.4)
    return paths


def _run_one(
    registry,
    *,
    name: str,
    operation_id: str,
    source: Path,
    dest: Path,
    settings: dict | None = None,
    require_available: bool = True,
) -> BenchRow:
    try:
        converter, op = registry._ops[operation_id]
    except KeyError:
        return BenchRow(name=name, operation_id=operation_id, status="fail", detail="unknown op")

    if require_available and not converter.is_available():
        return BenchRow(
            name=name,
            operation_id=operation_id,
            status="skip",
            detail="converter unavailable",
            meta=op.requires_external and ",".join(op.requires_external) or "",
        )

    if dest.exists():
        dest.unlink()
    before_rss = _rss_mb()
    t0 = time.perf_counter()
    try:
        result = registry.convert(
            operation_id=operation_id,
            source=source,
            destination=dest,
            settings=settings or {},
        )
        wall_ms = (time.perf_counter() - t0) * 1000.0
        after_rss = _rss_mb()
        out_size = result.output_path.stat().st_size if result.output_path.exists() else 0
        return BenchRow(
            name=name,
            operation_id=operation_id,
            status="ok",
            input_bytes=source.stat().st_size,
            output_bytes=out_size,
            wall_ms=round(wall_ms, 2),
            peak_rss_mb=round(max(before_rss, after_rss), 2),
            detail="ok",
            meta="",
        )
    except Exception as exc:  # noqa: BLE001
        wall_ms = (time.perf_counter() - t0) * 1000.0
        return BenchRow(
            name=name,
            operation_id=operation_id,
            status="fail",
            input_bytes=source.stat().st_size if source.exists() else 0,
            wall_ms=round(wall_ms, 2),
            peak_rss_mb=round(_rss_mb(), 2),
            detail=str(exc)[:200],
        )


def measure_import_startup() -> BenchRow:
    """Time a fresh subprocess importing registry build (approx startup cost without Qt)."""
    import subprocess

    code = (
        "import time; t=time.perf_counter(); "
        "from omniconvert.core.registry import build_default_registry; "
        "build_default_registry(); "
        "print((time.perf_counter()-t)*1000)"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    outer_ms = (time.perf_counter() - t0) * 1000.0
    if proc.returncode != 0:
        return BenchRow(
            name="startup_registry_import",
            operation_id="-",
            status="fail",
            wall_ms=round(outer_ms, 2),
            detail=(proc.stderr or proc.stdout)[:200],
        )
    try:
        inner_ms = float((proc.stdout or "").strip().splitlines()[-1])
    except ValueError:
        inner_ms = outer_ms
    return BenchRow(
        name="startup_registry_import",
        operation_id="-",
        status="ok",
        wall_ms=round(inner_ms, 2),
        peak_rss_mb=round(_rss_mb(), 2),
        detail=f"subprocess_wall_ms={outer_ms:.1f}",
    )


def run_suite(out_dir: Path) -> list[BenchRow]:
    fixtures = make_fixtures(out_dir / "fixtures")
    work = out_dir / "out"
    work.mkdir(parents=True, exist_ok=True)
    registry = build_default_registry()
    deps = get_dependency_service()
    rows: list[BenchRow] = [measure_import_startup()]

    cases = [
        ("png_to_jpeg_small", "image.png_to_jpeg", fixtures["png_small"], work / "s.jpg", {"jpeg_quality": 85}),
        ("png_to_jpeg_large", "image.png_to_jpeg", fixtures["png_large"], work / "l.jpg", {"jpeg_quality": 85}),
        ("jpeg_to_webp", "image.jpeg_to_webp", fixtures["jpeg_med"], work / "m.webp", {"jpeg_quality": 85}),
        (
            "image_crop",
            "image.crop",
            fixtures["png_large"],
            work / "crop.png",
            {"left_pct": 10, "right_pct": 10, "top_pct": 10, "bottom_pct": 10},
        ),
        ("pdf_extract_text", "pdf.extract_text", fixtures["pdf"], work / "doc.txt", {}),
        ("pdf_to_png", "pdf.to_png", fixtures["pdf"], work / "page.png", {}),
        ("pdf_compress", "pdf.compress", fixtures["pdf"], work / "doc_c.pdf", {}),
        ("csv_to_xlsx_small", "data.csv_to_xlsx", fixtures["csv_small"], work / "s.xlsx", {}),
        ("csv_to_xlsx_large", "data.csv_to_xlsx", fixtures["csv_large"], work / "l.xlsx", {}),
        ("docx_to_pdf_text", "office.docx_to_pdf_text", fixtures["docx"], work / "d_text.pdf", {}),
    ]

    # Prefer LO high-fidelity when available (may still fail on Snap sandbox — record result).
    if deps.libreoffice.available:
        cases.append(
            ("docx_to_pdf_lo", "office.docx_to_pdf", fixtures["docx"], work / "d_lo.pdf", {})
        )
    else:
        rows.append(
            BenchRow(
                name="docx_to_pdf_lo",
                operation_id="office.docx_to_pdf",
                status="skip",
                detail="LibreOffice not available",
            )
        )

    if deps.ffmpeg.available:
        cases.append(
            ("wav_to_mp3", "media.wav_to_mp3", fixtures["wav"], work / "tone.mp3", {})
        )
    else:
        rows.append(
            BenchRow(
                name="wav_to_mp3",
                operation_id="media.wav_to_mp3",
                status="skip",
                detail="FFmpeg not available",
            )
        )

    for name, op_id, src, dest, settings in cases:
        rows.append(
            _run_one(
                registry,
                name=name,
                operation_id=op_id,
                source=src,
                dest=dest,
                settings=settings,
            )
        )
    return rows


def rows_to_markdown(rows: list[BenchRow]) -> str:
    lines = [
        "| Name | Op | Status | In (KiB) | Out (KiB) | Wall (ms) | Peak RSS (MiB) | Detail |",
        "|------|----|--------|----------|-----------|-----------|----------------|--------|",
    ]
    for r in rows:
        lines.append(
            f"| {r.name} | `{r.operation_id}` | {r.status} | "
            f"{r.input_bytes / 1024:.1f} | {r.output_bytes / 1024:.1f} | "
            f"{r.wall_ms:.1f} | {r.peak_rss_mb:.1f} | {r.detail.replace('|', '/')} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="JustConvertIt offline benchmarks")
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="Working directory (default: temp under /tmp)",
    )
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--md-out", type=Path, default=None)
    args = parser.parse_args()

    work = args.work_dir or Path(tempfile.mkdtemp(prefix="justconvertit-bench-"))
    work.mkdir(parents=True, exist_ok=True)
    rows = run_suite(work)
    payload = {
        "work_dir": str(work),
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "rows": [asdict(r) for r in rows],
    }
    print(rows_to_markdown(rows))
    print(f"\n# work_dir={work}")
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"# wrote {args.json_out}")
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(rows_to_markdown(rows) + "\n", encoding="utf-8")
        print(f"# wrote {args.md_out}")
    # Soft LO failures on Snap-only hosts are environment limits, not harness bugs.
    hard_fails = [
        r
        for r in rows
        if r.status == "fail"
        and r.operation_id not in {"office.docx_to_pdf", "office.pptx_to_pdf"}
    ]
    return 1 if hard_fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
