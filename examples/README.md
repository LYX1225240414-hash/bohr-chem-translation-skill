# 最小调用示例（示意）

以下用一份**合成的教学样例**（两段，非任何真实文献）走完从原文到核验报告的全流程，用于说明接口与输出。**不是正式案例答案，也不是任何真实文献的译文或评测结果。**

## 一、输入

`/app/work/source.txt`（合成样例）：

```text
LiFePO4 electrodes delivered a capacity retention of 92% after 500 cycles at 1C [1].

The XRD patterns show no impurity phase. SEM images reveal uniform particles of 200 nm.

The diffusion coefficient increased by 3.5 times compared with the pristine sample [2,3].
```

`/app/output/glossary.json`（定名后）：

```json
{"terms": [
  {"term": "LiFePO4", "zh": "磷酸铁锂", "keep_original": false, "decision_basis": "领域通用译名"},
  {"term": "capacity retention", "zh": "容量保持率", "decision_basis": "标准译名"},
  {"term": "diffusion coefficient", "zh": "扩散系数", "decision_basis": "标准译名"},
  {"term": "XRD", "zh": "X 射线衍射", "keep_original": true, "decision_basis": "缩写保留原文"}
]}
```

`/app/output/translation_zh.md`（第一版译稿，**故意留了两处缺陷**用于演示检出）：

```text
LiFePO4 电极在 1C 倍率下循环 500 次后容量保持率为 92% [1]。

XRD 图谱显示无杂质相。SEM 图像显示粒径 200 nm 的均匀颗粒。

与原始样品相比，扩散系数提高了 3.5 倍。
```

## 二、调用方式

```bash
L=/skills/weekly-skill/resources/scripts/term_lint.py

# 1) 抽候选术语 → glossary_draft.json，供 Agent 逐条定名
python3 "$L" build --source /app/work/source.txt --out /app/work

# 2) 计数摸底（段落/数字/单位/引用/公式）
python3 "$L" stats --source /app/work/source.txt --target /app/output/translation_zh.md

# 3) 术语与保真核验
python3 "$L" check --source /app/work/source.txt \
                   --target /app/output/translation_zh.md \
                   --glossary /app/output/glossary.json --out /app/output
```

## 三、真实运行输出（本次实测，非虚构）

`check` 的 stdout：

```json
{"term_total": 5, "term_ok": 4, "untranslated_count": 1, "missing_term_count": 1,
 "inconsistent_count": 0, "suspected_variant_count": 0, "number_mismatch_count": 0,
 "unit_mismatch_count": 0, "unit_converted_count": 0,
 "citation_mismatch_count": 2, "formula_mismatch_count": 0}
```

`term_report.md` 的关键几行：

```text
## 术语未译（保留原文）（1）
- {"term": "LiFePO4", "zh": "磷酸铁锂", "occurrences": 1, ...}

## 引用标记差异（2）
- {"source_count": 2, "target_count": 1, "action": "引用标记数量不一致：核对是否漏引或重复"}
- {"missing_in_target": {"[2,3]": 1}, "action": "这些引用标记在译文中缺失或被改写"}
```

读法：脚本准确抓出两处真实缺陷——`LiFePO4` 约定应译却保留原文、末段漏掉引用标记 `[2,3]`；数字与单位判为 0 差异（原文 5 个数值与译文 5 个数值完全对齐，`200 nm` 保留）。这正是"译得通顺但漏了引用"这类人工通读容易滑过的失败。

## 四、另一个演示：单位等价与疑似另译

换一份合成样例（原文 `500 h` / `200 nm`，译文写 `500 小时` / `200 纳米`，且把 `容量保持率` 有一处写成 `容量保持比例`）：

```json
{"term_total": 2, "term_ok": 2, "untranslated_count": 0, "missing_term_count": 0,
 "inconsistent_count": 0, "suspected_variant_count": 1, "number_mismatch_count": 0,
 "unit_mismatch_count": 0, "unit_converted_count": 2, "citation_mismatch_count": 0,
 "formula_mismatch_count": 0}
```

读法：`h → 小时`、`nm → 纳米` 被识别为**等价转换**（`unit_converted_count: 2`），不误报成"单位丢失"；`容量保持比例` 只进 `suspected_variant_count` 提示人工确认，不计入 `inconsistent_count` 扣分——避免脚本把正常中文表达当成译法错误去乱改。

## 五、示意输出结构

见 `../resources/output_example.json`：每段译文带 `anchors` 与 `term_refs`，术语进 `glossary`，核验计数进 `verification` 与 `translation_report`，不确定项进 `uncertainties`。

## 六、说明

- 上述样例文本为合成的教学用例，不代表任何真实论文的翻译质量。
- 真实评测由平台用固定的 3 个案例运行，参赛者不提供测试案例或白板。
- PDF 输入需先用平台 `pdf-text-tool` 抽出文字层到 `/app/work/source.txt`，脚本只处理纯文本。
