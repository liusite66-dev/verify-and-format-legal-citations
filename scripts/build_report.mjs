import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [inputJson, outputXlsx, previewDir] = process.argv.slice(2);
if (!inputJson || !outputXlsx) throw new Error("usage: build_report.mjs INPUT.json OUTPUT.xlsx [PREVIEW_DIR]");
const payload = JSON.parse(await fs.readFile(inputJson, "utf8"));
const entries = payload.entries || [];
const workbook = Workbook.create();
const summary = workbook.worksheets.add("汇总");
const detail = workbook.worksheets.add("格式化明细");
summary.showGridLines = false;
detail.showGridLines = false;

summary.getRange("A1:F1").merge();
summary.getRange("A1").values = [["法学引注格式化报告"]];
summary.getRange("A1:F1").format = { fill: "#17365D", font: { bold: true, color: "#FFFFFF", size: 16 }, rowHeight: 30 };
summary.getRange("A3:B12").values = [
  ["指标", "数量"], ["脚注数量", null], ["参考文献数量", null],
  ["脚注已格式化", null], ["参考文献已格式化", null], ["无需修改", null],
  ["缺少必要字段", null], ["无法识别类型", null], ["复杂排版未处理", null],
  ["规则未核验", null],
];
summary.getRange("B4").formulas = [["=COUNTIF('格式化明细'!$B$2:$B$10001,\"脚注\")"]];
summary.getRange("B5").formulas = [["=COUNTIF('格式化明细'!$B$2:$B$10001,\"参考文献\")"]];
summary.getRange("B6").formulas = [["=COUNTIFS('格式化明细'!$B$2:$B$10001,\"脚注\",'格式化明细'!$M$2:$M$10001,\"已格式化\")"]];
summary.getRange("B7").formulas = [["=COUNTIFS('格式化明细'!$B$2:$B$10001,\"参考文献\",'格式化明细'!$M$2:$M$10001,\"已格式化\")"]];
summary.getRange("B8").formulas = [["=COUNTIF('格式化明细'!$M$2:$M$10001,\"无需修改\")"]];
summary.getRange("B9").formulas = [["=COUNTIF('格式化明细'!$M$2:$M$10001,\"未格式化（信息不完整）\")"]];
summary.getRange("B10").formulas = [["=COUNTIF('格式化明细'!$M$2:$M$10001,\"未格式化（无法识别）\")"]];
summary.getRange("B11").formulas = [["=COUNTIF('格式化明细'!$M$2:$M$10001,\"未格式化（复杂排版）\")"]];
summary.getRange("B12").formulas = [["=COUNTIF('格式化明细'!$M$2:$M$10001,\"未格式化（规则未核验）\")"]];
summary.getRange("A3:B3").format = { fill: "#D9EAF7", font: { bold: true, color: "#17365D" }, borders: { preset: "outside", style: "thin", color: "#9FBAD0" } };
summary.getRange("A4:B12").format.borders = { preset: "inside", style: "thin", color: "#D9E2F3" };
summary.getRange("A14:F18").values = [
  ["处理说明", null, null, null, null, null],
  ["输入文件", payload.input_file || "", null, null, null, null],
  ["输入SHA-256", payload.input_sha256 || "", null, null, null, null],
  ["处理范围", payload.processing_scope || "", null, null, null, null],
  ["重要提示", "信息不完整的条目保持原文；请按明细中的缺失字段补充后重新运行。", null, null, null, null],
];
summary.getRange("A14:F14").merge();
summary.getRange("A14:F14").format = { fill: "#D9EAF7", font: { bold: true, color: "#17365D" } };
for (const row of [15, 16, 17, 18]) summary.getRange(`B${row}:F${row}`).merge();
summary.getRange("A14:F18").format.wrapText = true;
summary.getRange("A1:F18").format.font = { name: "Arial" };
summary.getRange("A1:F18").format.autofitRows();
summary.getRange("A:A").format.columnWidth = 18;
summary.getRange("B:F").format.columnWidth = 20;

const headers = ["条目ID", "位置", "编号", "原始文本", "规范化文本", "文献类型", "适用规则", "作者", "题名", "期刊/出版社", "年份", "卷期/页码", "处理状态", "缺失字段", "自动修改", "待人工处理", "解析方式", "解析置信度"];
detail.getRange("A1:R1").values = [headers];
const rows = entries.map(e => [
  e.entry_id || "", e.location || "", e.number || "", e.original || "", e.normalized || "",
  e.citation_type || "", (e.rule_numbers || []).join(", "), (e.authors || []).join("、"),
  e.title || "", e.container || e.publisher || "", e.year || "",
  [e.volume ? `卷${e.volume}` : "", e.issue ? `期${e.issue}` : "", e.pages ? `页${e.pages}` : ""].filter(Boolean).join("；"),
  e.format_status || "", (e.missing_fields || []).join("、"), e.auto_changes || "", e.review_note || "", e.parse_method || "规则解析", e.parse_confidence ?? 1,
]);
if (rows.length) detail.getRangeByIndexes(1, 0, rows.length, headers.length).values = rows;
detail.getRange("A1:R1").format = { fill: "#17365D", font: { bold: true, color: "#FFFFFF" }, wrapText: true };
detail.freezePanes.freezeRows(1);
detail.freezePanes.freezeColumns(3);
detail.getRange(`A1:R${Math.max(2, rows.length + 1)}`).format.font = { name: "Arial", size: 10 };
detail.getRange(`D2:R${Math.max(2, rows.length + 1)}`).format.wrapText = true;
detail.getRange("A:A").format.columnWidth = 16;
detail.getRange("B:C").format.columnWidth = 10;
detail.getRange("D:E").format.columnWidth = 42;
detail.getRange("F:H").format.columnWidth = 16;
detail.getRange("I:J").format.columnWidth = 25;
detail.getRange("K:P").format.columnWidth = 20;
detail.getRange(`M2:M${Math.max(2, rows.length + 1)}`).conditionalFormats.add("containsText", { text: "已格式化", format: { fill: "#E2F0D9", font: { color: "#375623" } } });
detail.getRange(`M2:M${Math.max(2, rows.length + 1)}`).conditionalFormats.add("containsText", { text: "未格式化", format: { fill: "#FFF2CC", font: { color: "#7F6000" } } });
detail.tables.add(`A1:P${Math.max(2, rows.length + 1)}`, true, "CitationFormattingTable");

await fs.mkdir(path.dirname(outputXlsx), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputXlsx);
if (previewDir) {
  await fs.mkdir(previewDir, { recursive: true });
  for (const [sheetName, fileName] of [["汇总", "summary.png"], ["格式化明细", "details.png"]]) {
    const blob = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
    await fs.writeFile(`${previewDir}/${fileName}`, new Uint8Array(await blob.arrayBuffer()));
  }
}
const inspect = await workbook.inspect({ kind: "table", range: "汇总!A1:F18", include: "values,formulas", tableMaxRows: 20, tableMaxCols: 8 });
console.log(inspect.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula error scan" });
console.log(errors.ndjson);
