---
name: verify-and-format-legal-citations
description: Format footnotes and existing reference-list entries in finalized Chinese legal-academic DOCX papers under the second edition of the Manual of Legal Citation. Use when a user asks to normalize legal-paper citations, convert GB/T 7714 or APA-like entries to Chinese legal citation style, or obtain a formatting report. Do not verify whether sources exist or whether bibliographic facts are correct. Preserve incomplete entries unchanged and report the fields the user must supply. Reject documents with tracked changes or endnotes; never overwrite the original.
---

# 法学引注自动格式化

仅格式化已经定稿的法学论文脚注和现有参考文献。不得联网检索，不得调用文献数据库，不得判断来源是否真实或是否支持正文观点。

## 工作流

1. 确认输入为 `.docx`。检测到修订痕迹、尾注或损坏的脚注结构时停止，并说明处理建议。
2. 运行：

```bash
python3 scripts/run.py INPUT.docx [--output-dir OUTPUT_DIR] [--preview-dir PREVIEW_DIR]
```

3. 交付 `<原文件名>_引注规范化.docx` 和 `<原文件名>_引注格式化报告.xlsx`。
4. 检查报告中的缺失字段；缺项条目必须保持原文。渲染输出 DOCX，确认正文、脚注编号、参考文献自动编号和版式未损坏。

## 格式化门禁

- 先识别文献类型并解析字段，再决定是否改写。
- 中文期刊至少需要作者、篇名、期刊名、年份和期号。
- 中文专著或析出文献至少需要作者、书名或篇名、出版社和出版年份。
- 外文文献至少需要作者、题名、期刊或出版物名称和年份。
- 法律文件至少需要规范名称；裁判文书至少需要案件名称和案号。
- 缺少任一必要字段时，整条保持原文；在 XLSX 的“缺失字段”和“待人工处理”列提示用户补充。
- 无法可靠识别类型、无法可靠分割一注多文献、含解释文字或复杂局部样式时保持原文。

## 安全边界

- 仅处理页下脚注以及标题为“参考文献”或“主要参考文献”的现有章节。
- 不新增、删除或重新排序引注，不检查脚注与参考文献的对应关系。
- 不核验作者、题名、年份、案号、法条或其他信息的真实性。
- 仅对规则已人工核验、类型明确、字段完整的条目自动改写。
- 保留脚注编号后的一个空格。
- 参考文献使用 Word 自动编号时，只改写段落文本，保留 `w:numPr`、编号层级、`numId` 和原顺序。
- 永不覆盖输入文件；输出前后校验输入哈希。

## 规则来源

读取 `references/rules.json`。只有 `verified` 为 `true` 的规则允许触发自动改写，其他规则只能报告建议。不得在公开 Skill 中放入用户持有的手册原文、完整 Markdown 或 OCR 文件。

## 失败处理

- 缺少必要字段时保持原文并列明缺项，不猜测或补写书目信息。
- 报告生成失败时保留中间结果，不得声称已经交付 XLSX。
- DOCX 结构异常时停止，不生成可能损坏的输出。

## 开发验证

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -v
```

XLSX 依赖 Codex 工作区 Node.js 与 `@oai/artifact-tool`；可用 `CITATION_NODE` 和 `CITATION_NODE_MODULES` 指定运行时。
