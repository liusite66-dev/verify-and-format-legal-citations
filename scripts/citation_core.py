from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field


@dataclass
class CitationEntry:
    entry_id: str
    location: str
    number: str
    original: str
    normalized: str = ""
    citation_type: str = "unknown"
    rule_numbers: list[int] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    title: str = ""
    container: str = ""
    publisher: str = ""
    year: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doi: str = ""
    identifier: str = ""
    format_status: str = "未处理"
    missing_fields: list[str] = field(default_factory=list)
    auto_changes: str = ""
    review_note: str = ""
    parse_method: str = "规则解析"
    parse_confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
YEAR_RE = re.compile(r"(?<!\d)(?:18|19|20)\d{2}(?!\d)")
PAGES_RE = re.compile(r"(?:第\s*)?(\d{1,5})\s*[-—–－至]\s*(\d{1,5})\s*页")
GBT_BOOK_RE = re.compile(
    r"^(?:\[\d+\]\s*)?([^.。]+?)[.] *\s*([^.。\[]+?)\[M\][.] *\s*"
    r"(?:[^:：.。]+[:：])?\s*([^,，.。]+?)[,，]\s*((?:19|20)\d{2})"
    r"(?::\s*(\d+(?:\s*[-—–]\s*\d+)?))?[.。]?$",
    re.I,
)
GBT_NORM_RE = re.compile(
    r"^(?:\[\d+\]\s*)?\s*\u300a?([^\u300b\[]+)\u300b?\[Z\][.。]?\s*"
    r"((?:19|20)\d{2})[-/.](\d{1,2})[-/.](\d{1,2})[.。]?$",
    re.I,
)
ZH_APA_RE = re.compile(
    r"^(?:\[\d+\]\s*)?([^.。]+?)[.] *\s*\(((?:19|20)\d{2})\)[.] *\s*"
    r"([^.。]+?)[.] *\s*([^,，.。]+?)[,，]\s*(\d+)\((\d+)\)[,，]\s*"
    r"(\d+(?:\s*[-—–]\s*\d+)?)[.。]?$"
)
EN_APA_RE = re.compile(
    r"^(?:\[\d+\]\s*)?(.+?)\s*\(((?:19|20)\d{2})\)[.] *\s*"
    r"([^.。]+?)[.] *\s*([^.。]+?)[.] *\s*(?:https?://doi\.org/|doi\s*[:：]\s*)?(10\.\S+?)[.。]?$",
    re.I,
)

# GB/T 7714 entries are common in imported theses.  Parse the type marker
# before applying the Manual's output template; punctuation around the marker
# is intentionally permissive because Word exports often use full-width forms.
GBT_JOURNAL_RE = re.compile(
    r"^(?:\[\d+\]\s*)?(?P<authors>.+?)\.\s*(?P<title>.+?)\[J\]\s*[.。]\s*"
    r"(?P<journal>[^,，.。]+?)\s*[,，]\s*(?P<year>(?:18|19|20)\d{2})\s*"
    r"(?:[,，]\s*(?:第\s*)?(?P<volume>\d+)\s*卷?\s*(?:第\s*)?(?P<issue>\d+)\s*期?|"
    r"[,，]\s*\((?P<issue_paren>\d+)\))?\s*"
    r"(?:[:：]\s*(?P<pages>\d+(?:\s*[-—–－至]\s*\d+)?))?\s*"
    r"(?:[,，]\s*(?:DOI\s*[:：]?\s*)?(?P<doi>10\.\d{4,9}/[-._;()/:A-Z0-9]+))?\s*[.。]? $",
    re.I | re.X,
)
GBT_THESIS_RE = re.compile(
    r"^(?:\[\d+\]\s*)?(?P<authors>.+?)\.\s*(?P<title>.+?)\[D\]\s*[.。]\s*"
    r"(?P<school>[^,，.。]+?)\s*[,，]\s*(?P<year>(?:18|19|20)\d{2})\s*[.。]?$",
    re.I | re.X,
)
GBT_BOOK_RE2 = re.compile(
    r"^(?:\[\d+\]\s*)?(?P<authors>.+?)\.\s*(?P<title>.+?)\[M\]\s*[.。]\s*"
    r"(?:(?P<city>[^:：,，.。]+)\s*[:：])?\s*(?P<publisher>[^,，.。]+?)\s*[,，]\s*"
    r"(?P<year>(?:18|19|20)\d{2})\s*(?:年\s*版)?(?:\s*[,，:]\s*(?P<pages>\d+(?:[-—–－至]\d+)?))?\s*[.。]? $",
    re.I | re.X,
)


def normalize_typography(text: str) -> tuple[str, list[str]]:
    """Apply only low-risk typography changes; never invent metadata."""
    original = text
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("—", "-").replace("–", "-").replace("－", "-")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([，。；：、？！,.;:])", r"\1", text)
    text = re.sub(r"第\s*(\d+)\s*-\s*(\d+)\s*页", r"第\1-\2页", text)
    text = re.sub(r"\bdoi\s*[:：]\s*", "DOI: ", text, flags=re.I)
    return text, ([] if text == original else ["统一空格、连字符或标点"])


def _convert_external_style(e: CitationEntry, text: str) -> bool:
    """Convert a small set of deterministic GB/T 7714 and APA layouts."""
    value = unicodedata.normalize("NFKC", text).strip()
    match = GBT_JOURNAL_RE.match(value)
    if match:
        g = match.groupdict()
        authors = re.split(r"\s*(?:,|，|、|;|；)\s*", g["authors"].strip())
        authors = [a.strip() for a in authors if a.strip()]
        issue = g.get("issue") or g.get("issue_paren") or ""
        pages = (g.get("pages") or "").replace(" ", "").replace("—", "-").replace("–", "-").replace("－", "-").replace("至", "-")
        e.citation_type, e.rule_numbers = "zh_journal_article", [24, 43]
        e.authors, e.title, e.container, e.year = authors, g["title"].strip(), g["journal"].strip(), g["year"]
        e.volume, e.issue, e.pages, e.doi = g.get("volume") or "", issue, pages, (g.get("doi") or "").rstrip(".,;，。；")
        if e.volume:
            journal_part = f"{e.year}年第{e.volume}卷第{e.issue}期"
        else:
            journal_part = f"{e.year}年第{e.issue}期"
        e.normalized = f"{'、'.join(authors)}：《{e.title}》，载《{e.container}》{journal_part}"
        if pages:
            e.normalized += f"，第{pages}页"
        if e.doi:
            e.normalized += f"，DOI：{e.doi}"
        e.normalized += "。"
        e.auto_changes = "GB/T 7714期刊文章格式转换为法学引注格式"
        return True
    match = GBT_THESIS_RE.match(value)
    if match:
        g = match.groupdict(); authors = [x.strip() for x in re.split(r"\s*(?:,|，|、|;|；)\s*", g["authors"]) if x.strip()]
        e.citation_type, e.rule_numbers = "zh_thesis", [24, 40]
        e.authors, e.title, e.container, e.year = authors, g["title"].strip(), g["school"].strip(), g["year"]
        e.normalized = f"{'、'.join(authors)}：《{e.title}》，{e.container}{e.year}年学位论文。"
        e.auto_changes = "GB/T 7714学位论文格式转换为法学引注格式"
        return True
    match = GBT_BOOK_RE2.match(value)
    if match:
        g = match.groupdict(); authors = [x.strip() for x in re.split(r"\s*(?:,|，|、|;|；)\s*", g["authors"]) if x.strip()]
        e.citation_type, e.rule_numbers = "zh_book_or_chapter", [24, 25]
        e.authors, e.title, e.publisher, e.year, e.pages = authors, g["title"].strip(), g["publisher"].strip(), g["year"], (g.get("pages") or "").replace(" ", "")
        e.normalized = f"{'、'.join(authors)}：《{e.title}》，{e.publisher}{e.year}年版"
        if e.pages: e.normalized += f"，第{e.pages.replace('至', '-')}页"
        e.normalized += "。"
        e.auto_changes = "GB/T 7714专著格式转换为法学引注格式"
        return True
    match = GBT_BOOK_RE.match(value)
    if match:
        author, title, publisher, year, pages = (x.strip() if x else "" for x in match.groups())
        page_text = f"，第{pages.replace(' ', '').replace('—', '-').replace('–', '-')}页" if pages else ""
        e.citation_type, e.rule_numbers = "zh_book_or_chapter", [24, 25]
        e.authors, e.title, e.publisher, e.year, e.pages = [author], title, publisher, year, pages
        e.normalized = f"{author}：《{title}》，{publisher}{year}年版{page_text}。"
        e.auto_changes = "GB/T 7714专著格式转换为法学引注格式"
        return True
    match = GBT_NORM_RE.match(value)
    if match:
        title, year, month, day = match.groups()
        e.citation_type, e.rule_numbers, e.title, e.year = "legal_norm", [24, 71], title.strip(), year
        e.normalized = f"《{e.title}》，{year}年{int(month)}月{int(day)}日公布。"
        e.auto_changes = "GB/T 7714法律文献格式转换为法学引注格式"
        return True
    match = ZH_APA_RE.match(value)
    if match:
        author, year, title, journal, volume, issue, pages = (x.strip() for x in match.groups())
        pages = pages.replace(" ", "").replace("—", "-").replace("–", "-")
        e.citation_type, e.rule_numbers = "zh_journal_article", [24, 38]
        e.authors, e.title, e.container, e.year = [author], title, journal, year
        e.volume, e.issue, e.pages = volume, issue, pages
        e.normalized = f"{author}：《{title}》，载《{journal}》{year}年第{volume}卷第{issue}期，第{pages}页。"
        e.auto_changes = "APA期刊格式转换为法学引注格式"
        return True
    match = EN_APA_RE.match(value)
    if match:
        author, year, title, journal, doi = (x.strip() for x in match.groups())
        doi = doi.rstrip(".,;，。；")
        e.citation_type, e.rule_numbers = "foreign_source", [24, 99]
        e.authors, e.title, e.container, e.year, e.doi = [author], title, journal, year, doi
        e.normalized = f'{author}, "{title}," {journal}, {year}, DOI: {doi}.'
        e.auto_changes = "APA期刊格式转换为法学引注格式"
        return True
    return False


def classify_and_parse(entry_id: str, location: str, number: str, text: str) -> CitationEntry:
    normalized, changes = normalize_typography(text)
    e = CitationEntry(entry_id, location, number, text, normalized=normalized,
                      auto_changes="；".join(changes))
    if _convert_external_style(e, text):
        finalize_format_decision(e)
        return e
    doi = DOI_RE.search(text)
    if doi:
        e.doi = doi.group(0).rstrip(".,;，。；")
    year = YEAR_RE.search(text)
    if year:
        e.year = year.group(0)
    pages = PAGES_RE.search(text)
    if pages:
        e.pages = f"{pages.group(1)}-{pages.group(2)}"
    titles = re.findall(r"《([^》]{2,200})》", text)
    if re.search(r"(案号|民初|民终|刑初|刑终|行初|行终|指导性案例|公报案例)", text):
        e.citation_type, e.rule_numbers = "case", [24, 82]
    elif titles and (titles[0].startswith("中华人民共和国") or
                     re.search(r"(主席令|国务院令|法释|公告|文号|第\s*\d+\s*号)", text)):
        e.citation_type, e.rule_numbers = "legal_norm", [24, 71]
        e.title = titles[0]
    elif "载《" in text and titles:
        e.citation_type, e.rule_numbers, e.title = "zh_journal_article", [24, 38], titles[0]
        if len(titles) > 1:
            e.container = titles[1]
    elif titles:
        e.citation_type, e.rule_numbers, e.title = "zh_book_or_chapter", [24, 25], titles[0]
        if len(titles) > 1:
            e.container = titles[1]
    elif re.search(r"\b(see|supra|ibid|vol\.|no\.|pp?\.)\b", text, re.I) or re.search(r"[A-Za-z]{3,}", text):
        e.citation_type, e.rule_numbers = "foreign_source", [24, 99]
        quoted = re.search(r"[\"“]([^\"”]{4,250})[\"”]", text)
        if quoted:
            e.title = quoted.group(1)
    else:
        e.review_note = "无法可靠识别文献类型，保留原文"
    author_part = re.split(r"[:：]", text, maxsplit=1)[0].strip()
    author_part = re.sub(r"^(参见|另见|又见|See|see)\s*", "", author_part)
    if e.citation_type != "unknown" and 0 < len(author_part) <= 100:
        e.authors = [x.strip() for x in re.split(r"[、,，]|\s+and\s+", author_part) if x.strip()]
    if e.citation_type == "zh_journal_article":
        issue = re.search(r"(?:(?:第(\d+)卷)?第(\d+)期)", text)
        if issue:
            e.volume, e.issue = issue.group(1) or "", issue.group(2)
    elif e.citation_type == "zh_book_or_chapter":
        publication = re.search(r"[，,]\s*([^，。；;]*?出版社)\s*((?:19|20)\d{2})\s*年版", text)
        if publication:
            e.publisher, e.year = publication.group(1).strip(), publication.group(2)
    elif e.citation_type == "case":
        identifier = re.search(r"(?:\(|（)?\d{4}(?:\)|）)?[^，。；;]{0,40}?号", text)
        if identifier:
            e.identifier = identifier.group(0)
        if titles:
            e.title = titles[0]
        else:
            case_name = re.search(r"(?:参见)?\s*([^，。；;]{2,100}?(?:案|诉[^，。；;]+))(?=[，。；;])", text)
            if case_name:
                e.title = case_name.group(1).strip()
    finalize_format_decision(e)
    return e


def apply_model_fields(entry: CitationEntry, fields: dict, confidence: float = 0.0) -> CitationEntry:
    """Apply an Agent/model-produced field map after deterministic parsing fails.

    The model must provide only values visible in the citation. This function
    never searches the Internet or invents missing metadata; it records the
    assisted path so the XLSX report can require human review.
    """
    allowed = {"citation_type", "authors", "title", "container", "publisher",
               "year", "volume", "issue", "pages", "doi", "identifier"}
    for key, value in fields.items():
        if key in allowed and value not in (None, ""):
            if key == "authors" and isinstance(value, str):
                value = [x.strip() for x in re.split(r"[,，、;；]", value) if x.strip()]
            setattr(entry, key, value)
    entry.parse_method = "模型辅助解析"
    entry.parse_confidence = float(confidence or 0)
    entry.review_note = (entry.review_note + "；" if entry.review_note else "") + "字段由模型辅助识别，未核验书目信息真实性"
    if entry.citation_type in ("zh_journal_article", "foreign_source"):
        authors = "、".join(entry.authors)
        if entry.citation_type == "zh_journal_article":
            period = f"{entry.year}年第{entry.issue}期" if entry.issue else f"{entry.year}年"
            entry.normalized = f"{authors}：《{entry.title}》，载《{entry.container}》{period}"
            if entry.pages: entry.normalized += f"，第{entry.pages}页"
            if entry.doi: entry.normalized += f"，DOI：{entry.doi}"
            entry.normalized += "。"
        else:
            entry.normalized = entry.original
    elif entry.citation_type == "zh_book_or_chapter":
        entry.normalized = f"{'、'.join(entry.authors)}：《{entry.title}》，{entry.publisher}{entry.year}年版。"
    finalize_format_decision(entry)
    entry.parse_method = "模型辅助解析"
    entry.parse_confidence = float(confidence or 0)
    return entry


REQUIRED_FIELDS = {
    "zh_journal_article": (("authors", "作者"), ("title", "篇名"), ("container", "期刊名"),
                           ("year", "年份"), ("issue", "期号")),
    "zh_book_or_chapter": (("authors", "作者"), ("title", "书名/篇名"),
                           ("publisher", "出版社"), ("year", "出版年份")),
    "zh_thesis": (("authors", "作者"), ("title", "篇名"), ("container", "学位授予单位"),
                  ("year", "年份")),
    "foreign_source": (("authors", "作者"), ("title", "题名"),
                       ("container", "期刊/出版物"), ("year", "年份")),
    "legal_norm": (("title", "法律文件名称"),),
    "case": (("title", "案件名称"), ("identifier", "案号")),
}


def finalize_format_decision(entry: CitationEntry) -> None:
    if entry.citation_type == "unknown":
        entry.normalized = entry.original
        entry.auto_changes = ""
        entry.format_status = "未格式化（无法识别）"
        entry.review_note = entry.review_note or "无法可靠识别文献类型，需人工确认"
        return
    required = REQUIRED_FIELDS.get(entry.citation_type, ())
    entry.missing_fields = [label for attr, label in required if not getattr(entry, attr)]
    if entry.missing_fields:
        entry.normalized = entry.original
        entry.auto_changes = ""
        entry.format_status = "未格式化（信息不完整）"
        entry.review_note = "请补充：" + "、".join(entry.missing_fields)
    elif entry.auto_changes and entry.normalized != entry.original:
        entry.format_status = "已格式化"
    else:
        entry.normalized = entry.original
        entry.auto_changes = ""
        entry.format_status = "无需修改"
