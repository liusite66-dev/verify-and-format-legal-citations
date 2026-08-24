from __future__ import annotations

import hashlib
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from citation_core import CitationEntry, classify_and_parse

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
ET.register_namespace("w", W)


class DocumentRejected(RuntimeError):
    pass


@dataclass
class LocatedNode:
    entry: CitationEntry
    part: str
    node_id: str


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _text(node: ET.Element) -> str:
    return "".join(t.text or "" for t in node.findall(".//w:t", NS)).strip()


def _has_positive_notes(xml: bytes, tag: str) -> bool:
    root = ET.fromstring(xml)
    return any(int(n.attrib.get(f"{{{W}}}id", "-1")) > 0 and _text(n)
               for n in root.findall(f"w:{tag}", NS))


def preflight(path: str | Path) -> None:
    path = Path(path)
    if path.suffix.lower() != ".docx":
        raise DocumentRejected("输入必须为DOCX文件")
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        for name in names:
            if name.startswith("word/") and name.endswith(".xml"):
                data = z.read(name)
                if re.search(br"<w:(?:ins|del|moveFrom|moveTo)(?:\s|>)", data):
                    raise DocumentRejected("检测到修订痕迹，请先接受或拒绝全部修订后再处理")
        if "word/endnotes.xml" in names and _has_positive_notes(z.read("word/endnotes.xml"), "endnote"):
            raise DocumentRejected("检测到尾注；首版仅处理页下脚注")
        if "word/footnotes.xml" in names:
            try:
                ET.fromstring(z.read("word/footnotes.xml"))
            except ET.ParseError as exc:
                raise DocumentRejected("脚注OOXML损坏") from exc


def extract_entries(path: str | Path) -> tuple[list[LocatedNode], dict[str, ET.ElementTree]]:
    located: list[LocatedNode] = []
    trees: dict[str, ET.ElementTree] = {}
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        if "word/footnotes.xml" in names:
            tree = ET.ElementTree(ET.fromstring(z.read("word/footnotes.xml")))
            trees["word/footnotes.xml"] = tree
            for note in tree.getroot().findall("w:footnote", NS):
                note_id = int(note.attrib.get(f"{{{W}}}id", "-1"))
                text = _text(note)
                if note_id > 0 and text:
                    entry = classify_and_parse(f"footnote:{note_id}", "脚注", str(note_id), text)
                    _protect_rich_text(note, entry)
                    located.append(LocatedNode(entry, "word/footnotes.xml", str(note_id)))
        tree = ET.ElementTree(ET.fromstring(z.read("word/document.xml")))
        trees["word/document.xml"] = tree
        paragraphs = tree.getroot().findall(".//w:body/w:p", NS)
        in_refs = False
        ref_no = 0
        for idx, paragraph in enumerate(paragraphs):
            text = _text(paragraph)
            style_node = paragraph.find("w:pPr/w:pStyle", NS)
            style = style_node.attrib.get(f"{{{W}}}val", "") if style_node is not None else ""
            if text in {"参考文献", "主要参考文献"}:
                in_refs = True
                continue
            if in_refs and (style.lower().startswith("heading") or re.match(r"^第?[一二三四五六七八九十]+[章节部分]", text)):
                break
            if in_refs and text:
                ref_no += 1
                entry = classify_and_parse(f"reference:{ref_no}", "参考文献", str(ref_no), text)
                _protect_rich_text(paragraph, entry)
                located.append(LocatedNode(entry, "word/document.xml", str(idx)))
    return located, trees


def _protect_rich_text(node: ET.Element, entry: CitationEntry) -> None:
    """Do not flatten runs that may carry italics, hyperlinks, or other formatting."""
    if len(node.findall(".//w:t", NS)) > 1 and entry.auto_changes:
        entry.normalized = entry.original
        entry.auto_changes = ""
        entry.format_status = "未格式化（复杂排版）"
        note = "包含多文本运行，为保护斜体、超链接或局部样式未自动改写"
        entry.review_note = (entry.review_note + "；" if entry.review_note else "") + note


def _replace_text(node: ET.Element, value: str) -> None:
    texts = node.findall(".//w:t", NS)
    if not texts:
        return
    if len(texts) != 1:
        return
    texts[0].text = value
    texts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def write_output(input_path: str | Path, output_path: str | Path,
                 located: list[LocatedNode], trees: dict[str, ET.ElementTree]) -> None:
    input_path, output_path = Path(input_path), Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    replacements = {x.entry.entry_id: x.entry.normalized for x in located
                    if x.entry.normalized and x.entry.auto_changes and x.entry.citation_type != "unknown"}
    if "word/footnotes.xml" in trees:
        for note in trees["word/footnotes.xml"].getroot().findall("w:footnote", NS):
            key = f"footnote:{note.attrib.get(f'{{{W}}}id', '')}"
            if key in replacements:
                _replace_text(note, " " + replacements[key].lstrip())
    paragraphs = trees["word/document.xml"].getroot().findall(".//w:body/w:p", NS)
    for item in located:
        if item.part == "word/document.xml" and item.entry.entry_id in replacements:
            _replace_text(paragraphs[int(item.node_id)], replacements[item.entry.entry_id])
    with zipfile.ZipFile(input_path) as zin, zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = (ET.tostring(trees[item.filename].getroot(), encoding="utf-8", xml_declaration=True)
                    if item.filename in trees else zin.read(item.filename))
            zout.writestr(item, data)
    with zipfile.ZipFile(output_path) as z:
        ET.fromstring(z.read("word/document.xml"))
        if "word/footnotes.xml" in z.namelist():
            ET.fromstring(z.read("word/footnotes.xml"))
