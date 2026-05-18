#!/usr/bin/env python3
import argparse
import base64
import logging
import os
import shutil
import subprocess
import tempfile

import markdown
from pathlib import Path

preamble = """\
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
{css}
</style>
</head>
<body>
<div id="resume">
"""

postamble = """\
</div>
</body>
</html>
"""

CHROME_DEFAULT = os.path.expandvars(
    r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"
)


def title(md: str) -> str:
    for line in md.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.strip("#").strip()
    raise ValueError("Cannot find any markdown headings")


def make_html(md: str, prefix: str = "resume") -> str:
    try:
        with open(prefix + ".css", encoding="utf-8") as cssfp:
            css = cssfp.read()
    except FileNotFoundError:
        logging.warning(f"{prefix}.css not found. Output will be unstyled.")
        css = ""

    return "".join(
        (
            preamble.format(title=title(md), css=css),
            markdown.markdown(
                md,
                extensions=["smarty", "tables", "fenced_code", "attr_list"],
            ),
            postamble,
        )
    )


def write_pdf(
    html: str,
    prefix: str = "resume",
    chrome_path: str = CHROME_DEFAULT,
) -> None:
    if not os.path.exists(chrome_path):
        raise FileNotFoundError(f"Chrome not found: {chrome_path}")

    html64 = base64.b64encode(html.encode("utf-8")).decode("utf-8")

    options = [
        "--headless=new",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        "--enable-logging=stderr",
        "--log-level=2",
        "--disable-gpu",
    ]

    tmpdir = tempfile.TemporaryDirectory(prefix="resume.md_")
    options.append(f"--crash-dumps-dir={tmpdir.name}")
    options.append(f"--user-data-dir={tmpdir.name}")

    output_pdf = Path(f"{prefix}.pdf").resolve()

    if output_pdf.exists():
        output_pdf.unlink()

    try:
        subprocess.run(
            [
                chrome_path,
                *options,
                f"--print-to-pdf={output_pdf}",
                "data:text/html;base64," + html64,
            ],
            check=True,
        )
        if output_pdf.exists():
            logging.info(f"Wrote {output_pdf}")
        else:
            raise RuntimeError(f"Chrome did not create PDF: {output_pdf}")
        
    finally:
        try:
            shutil.rmtree(tmpdir.name)
        except PermissionError as exc:
            logging.warning(f"Could not delete {tmpdir.name}")
            logging.info(exc)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "file",
        help="markdown input file [resume.md]",
        default="resume.md",
        nargs="?",
    )
    parser.add_argument(
        "--no-html",
        help="Do not write html output",
        action="store_true",
    )
    parser.add_argument(
        "--no-pdf",
        help="Do not write pdf output",
        action="store_true",
    )
    parser.add_argument(
        "--chrome-path",
        default=CHROME_DEFAULT,
        help="Path to chrome.exe",
    )
    parser.add_argument("-q", "--quiet", action="store_true")

    args = parser.parse_args()

    if args.quiet:
        logging.basicConfig(level=logging.WARN, format="%(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    prefix, _ = os.path.splitext(args.file)

    with open(args.file, encoding="utf-8") as mdfp:
        md = mdfp.read()

    html = make_html(md, prefix=prefix)

    if not args.no_html:
        with open(prefix + ".html", "w", encoding="utf-8") as htmlfp:
            htmlfp.write(html)
            logging.info(f"Wrote {htmlfp.name}")

    if not args.no_pdf:
        write_pdf(html, prefix=prefix, chrome_path=args.chrome_path)