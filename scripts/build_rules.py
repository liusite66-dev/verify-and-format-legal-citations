from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from docx import Document


MANUALLY_VERIFIED = {22, 24}


def build(source: Path, output: Path, wrapper: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="citation-rules-") as td:
        md_path = Path(td) / "handbook.md"
        subprocess.run([sys.executable, str(wrapper), str(source), "-o", str(md_path)], check=True)
        markdown = md_path.read_text("utf-8")
        if len(markdown) < 50000:
            raise RuntimeError("MarkItDown输出异常，未生成可读的手册文本")
    # MarkItDown is used to validate a readable conversion, while rule boundaries
    # are taken from DOCX paragraphs because links can merge with following
    # headings in Markdown.
    paragraphs = [p.text.strip() for p in Document(source).paragraphs]
    ordered: list[tuple[int, re.Match]] = []
    cursor = 560  # after the table of contents in this edition
    for number in range(1, 151):
        found = None
        pattern = re.compile(rf"^\s*{number}\s*\.\s*(.+?)\s*$")
        for idx in range(cursor, len(paragraphs)):
            match = pattern.match(paragraphs[idx])
            if match:
                found = (idx, match)
                break
        if not found:
            raise RuntimeError(f"规则编号缺失: {number}")
        ordered.append(found)
        cursor = found[0] + 1
    rules = []
    for idx, (paragraph_index, match) in enumerate(ordered):
        if idx + 1 < len(ordered):
            end = ordered[idx + 1][0]
        else:
            end = next((i for i in range(paragraph_index + 1, len(paragraphs))
                        if paragraphs[i].startswith("附录")
                        or paragraphs[i].startswith("《法学引注手册》编写说明")), len(paragraphs))
        body = "\n\n".join(x for x in paragraphs[paragraph_index + 1:end] if x).strip()
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        number = idx + 1
        verified = number in MANUALLY_VERIFIED
        rules.append({"number": number, "title": title, "text": body,
                      "examples": [x.strip() for x in body.splitlines() if x.strip().startswith("〔")][:5],
                      "verified": verified,
                      "verification_note": ("已对照OCR DOCX与原版页面人工核验"
                                            if verified else "待对照原版逐条人工核验")})
    payload = {"manual": "法学引注手册（第二版）", "source_private": True,
               "generated_at": datetime.now(timezone.utc).isoformat(), "rules": rules}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_docx", type=Path)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parents[1] / "references/rules.json")
    parser.add_argument("--markitdown-wrapper", type=Path,
                        default=Path.home() / ".codex/skills/markitdown/scripts/convert.py")
    args = parser.parse_args()
    result = build(args.source_docx, args.output, args.markitdown_wrapper)
    print(f"已生成 {len(result['rules'])} 条规则: {args.output}")
