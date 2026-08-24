from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from docx_io import DocumentRejected, extract_entries, preflight, sha256, write_output


RUNTIME_ROOT = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node"
DEFAULT_NODE = RUNTIME_ROOT / "bin/node"
DEFAULT_MODULES = RUNTIME_ROOT / "node_modules"
RULES_PATH = Path(__file__).resolve().parents[1] / "references/rules.json"


def build_report(json_path: Path, xlsx_path: Path, preview_dir: Path | None = None) -> None:
    node = Path(os.environ.get("CITATION_NODE", str(DEFAULT_NODE)))
    modules = Path(os.environ.get("CITATION_NODE_MODULES", str(DEFAULT_MODULES)))
    if not node.exists() or not modules.exists():
        raise RuntimeError("缺少Codex工作区Node或@oai/artifact-tool运行时")
    source = Path(__file__).with_name("build_report.mjs")
    with tempfile.TemporaryDirectory(prefix="citation-report-") as td:
        work = Path(td)
        runner = work / "build_report.mjs"
        shutil.copy2(source, runner)
        (work / "node_modules").symlink_to(modules, target_is_directory=True)
        cmd = [str(node), str(runner), str(json_path), str(xlsx_path)]
        if preview_dir:
            cmd.append(str(preview_dir))
        subprocess.run(cmd, check=True, cwd=work)


def verified_rule_numbers() -> set[int]:
    data = json.loads(RULES_PATH.read_text("utf-8"))
    return {int(rule["number"]) for rule in data.get("rules", []) if rule.get("verified") is True}


def main() -> int:
    parser = argparse.ArgumentParser(description="按《法学引注手册（第二版）》格式化DOCX中的脚注和参考文献")
    parser.add_argument("input_docx", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--preview-dir", type=Path, help="可选：输出XLSX预览PNG供QA")
    args = parser.parse_args()
    input_path = args.input_docx.resolve()
    output_dir = (args.output_dir or input_path.with_name(input_path.stem + "_引注格式化结果")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    original_hash = sha256(input_path)
    try:
        preflight(input_path)
    except DocumentRejected as exc:
        print(f"拒绝处理：{exc}", file=sys.stderr)
        return 2
    located, trees = extract_entries(input_path)
    verified_rules = verified_rule_numbers()
    for item in located:
        if item.entry.auto_changes and not verified_rules.intersection(item.entry.rule_numbers):
            item.entry.normalized = item.entry.original
            item.entry.auto_changes = ""
            note = "适用规则尚未人工核验，未自动改写"
            item.entry.review_note = (item.entry.review_note + "；" if item.entry.review_note else "") + note
            item.entry.format_status = "未格式化（规则未核验）"

    output_docx = output_dir / f"{input_path.stem}_引注规范化.docx"
    output_xlsx = output_dir / f"{input_path.stem}_引注格式化报告.xlsx"
    json_path = output_dir / "citation_formatting_data.json"
    write_output(input_path, output_docx, located, trees)
    payload = {"input_file": str(input_path), "input_sha256": original_hash,
               "processing_scope": "仅格式化脚注和参考文献；未进行真实性核验",
               "entries": [x.entry.to_dict() for x in located]}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
    build_report(json_path, output_xlsx, args.preview_dir)
    Path(str(output_xlsx) + ".inspect.ndjson").unlink(missing_ok=True)
    if sha256(input_path) != original_hash:
        raise RuntimeError("输入文件哈希发生变化，已停止交付")
    json_path.unlink(missing_ok=True)
    print(json.dumps({"docx": str(output_docx), "xlsx": str(output_xlsx),
                      "footnotes": sum(x.entry.location == "脚注" for x in located),
                      "references": sum(x.entry.location == "参考文献" for x in located)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
