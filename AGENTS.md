# Project Guide

## 定位

`verify-and-format-legal-citations` 仅按《法学引注手册（第二版）》格式化法学论文 DOCX 的页下脚注和现有参考文献，不做真实性核验。

## 运行

```bash
python3 scripts/run.py INPUT.docx [--output-dir OUTPUT_DIR] [--preview-dir PREVIEW_DIR]
```

输出新的规范化 DOCX 和 XLSX 格式化报告，不覆盖输入文件。

## 目录

- `scripts/docx_io.py`：OOXML 预检、脚注和参考文献安全读写。
- `scripts/citation_core.py`：类型识别、字段解析、必填字段门禁和格式转换。
- `scripts/build_report.mjs`：中文 XLSX 汇总及明细。
- `references/rules.json`：150条规则索引及人工核验状态。
- `tests/`：格式转换、缺字段保护、OOXML拒绝逻辑和自动编号回归测试。

## 约定

- 缺少该文献类型必要字段时整条不改，只在报告提示补充字段。
- 不联网、不调用 MCP 或数据库，不输出真实性判断。
- 保留正文、页面设置、脚注编号、超链接、复杂局部样式、Word 自动编号和参考文献顺序。
- 修改规则状态前必须对照用户合法持有的原始手册；不得分发手册全文。
- 使用 `apply_patch` 手工修改源文件，不覆盖无关改动。
