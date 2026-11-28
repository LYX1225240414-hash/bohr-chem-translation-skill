---
name: chem-literal-translation
description: 化学与材料科学文献的术语一致性英译中工作流，输出段落级双语对照与可回查锚点；内置可离线运行的术语核验脚本（term_lint.py），从原文自动抽候选术语生成术语表骨架，再把译文与术语表、原文逐条机械比对，检出原文残留未译、译名缺失、术语表内混用、数字/单位/引用/公式/段落数不一致，并区分「已等价转换为中文单位」与「真的丢失」；当用户需要翻译科研论文、锁定全篇译名、核对数字单位公式引用是否准确保留、或要求逐段可回查的双语对照结果时使用，支持 PDF/TXT/MD 输入与中英混排材料。
---

# 化学文献术语一致性翻译

把真实科研文献翻译成**术语稳定、段落对齐、逐条可核验**的中文，重点解决四个高频失败：同一术语前后译名不一致、长文漏段或错位、数字单位公式引用被译掉、译不准处被含混带过。

核心设计有两条，缺一条就会退化回"凭语感翻译"：

1. **术语表是执行依据，不是提示词装饰**——每次逐段翻译前重读，译后用脚本逐词比对，不靠印象。
2. **保真靠机械核验，不靠通顺**——数字、单位、引用编号、公式定界符、段落数全部可计数，由 `term_lint.py` 给出计数，脚本测不出的才人工判断。

## 何时使用

- 英译中科研论文（化学 / 材料 / 催化方向优先），要求术语全篇统一。
- 需要段落级双语对照、译法依据、可回查锚点。
- 需要明确标注译不准、材料残缺、公式为图片等无法判断之处。
- 需要一份可复核的自检报告（术语一致率、数字/单位/引用差异计数）。

不适用：非科研文本、创意翻译、无原文材料、要求凭空补造实验数据的场景。

## 运行环境与输出路径（重要）

- 平台把本 Skill 安装到 `/skills/weekly-skill`，用固定的 3 个案例运行。先读真实输入 `/input/case.json` 与 `/input/task.md`；`case.json` 可能含 `case_id`、`output_contract`、材料路径、目标读者与约束。**以实际字段为准，不从题目标签、文件名或示例推断材料内容**。
- 中间文件写在 `/app/work`，不污染输入目录；资源从 `/skills/weekly-skill/resources/` 读取，均为 UTF-8 文本。
- 若输入是 PDF：用平台的 `pdf-text-tool` 抽文字层，落到 `/app/work/source.txt` 再处理；文字层缺失时用 `ocr-tool`，仍失败则对应段落写 `uncertainties` 并降级 `status: partial`。
- 最终产物写到 `/app/output/result.json`（UTF-8 合法 JSON），并同时保存**纯文本中文译稿** `/app/output/translation_zh.md`（段落间空行分隔、顺序与原文一致，供脚本核验与人工校对）、**术语表** `/app/output/glossary.json`、**核验报告** `/app/output/term_report.md`。若 `output_contract` 指定其他产物路径，以合同为准。
- `result.json` 必须原样回填 `case_id`，完整包含 `output_contract` 的全部字段（不得改名、不得遗漏），再补充本 Skill 的扩展字段；合同字段与本表同名时以合同为准。
- 预算内**尽早写入诚实的部分结果**再增量完善；3 个案例、每条件 3 次运行由平台安排，参赛者不提供测试案例或白板。
- 禁止提交预制答案、正式案例答案、假造的运行日志或评测成绩；本 Skill 包内不应含任何 `result.json`。

## 输入输出

**输入**：论文文本或其路径（PDF / TXT / MD）；可选任务要求（翻译范围、目标读者、额外术语要求、图表题注是否翻译）。

**输出** `result.json` 字段如下（`output_contract` 优先）：

| 字段 | 要求 |
|---|---|
| case_id | 从 case.json 原样回填；确实没有才填 `N/A` |
| status | `success` / `partial` / `unable` / `refused`；部分完成须写明未完成范围与人工接管位置 |
| translation | 数组，每项含 `para_id` / `source` / `target` / `anchors` / `term_refs`；段数与原文自然段一一对应，标题、图注、表头、脚注单独成段并标 `block_type` |
| anchors | 每条译文可回查的位置：`p<页>:<段>` / `para:<编号>` / `fig<号>` / `tab<号>` / `eq<号>` / `ref:[n]`，必须指向输入材料的真实位置 |
| glossary | 对象，含 `terms` 数组，每项 `term` / `zh` / `variants` / `keep_original` / `positions` / `decision_basis`；`keep_original: true` 表示按约定保留原文（缩写、化学式、基因名、软件名） |
| verification | 对象，逐项给 `result`（pass/fail/na）与 `evidence`（**带具体计数或抽查片段**）：`term_consistency`、`numeric_fidelity`、`unit_fidelity`、`citation_formula_preserved`、`paragraph_completeness`、`anchor_spotcheck`、`no_new_facts`、`relation_preservation`、`uncertainty_disclosure` |
| translation_report | 对象，转述 `term_report.json` 的关键计数：`term_total` / `term_ok` / `untranslated_count` / `missing_term_count` / `inconsistent_count` / `number_mismatch_count` / `unit_mismatch_count` / `unit_converted_count` / `citation_mismatch_count` / `paragraph_gap_count` |
| gain_record | 对象，含 `conditions` / `mode` / `baseline` / `with_skill` / `delta_note` / `verifiable_artifacts`；按 `resources/gain_protocol.md` 填写，无对照产出时写 `na` 并说明 |
| uncertainties | 数组，每项含 `item` / `reason` / `anchor` / `handover`；译不准、材料残缺、公式为图片、引用无法解析分别说明 |
| sources | 使用的输入文件与页码/段号范围，界定输入边界（PDF 需注明页数与是否 OCR） |
| change_log | 自检回修记录：问题、修正、位置、时间顺序 |

## 工作流

### 第 0 步：落盘骨架（先保底）

读取 `/input/case.json` 与 `/input/task.md`，在 `/app/work` 建立工作副本，立即向 `/app/output/result.json` 写入含 `case_id`、`status: partial`、各扩展字段空数组的骨架；随后每完成一段就增量更新，避免超时只留下空结果。

### 第 1 步：确认输入边界

打开实际文件，不用文件名或标签推断内容。确认语言、篇幅、是否扫描件、是否含图表公式、参考文献是否完整；PDF 抽完文字层后核对页数与段落数是否对得上。记录 `sources`。文件缺失或整篇不可读 → `status: unable` 并写明具体路径与原因。

### 第 2 步：建术语表（先脚本，再定名）

```bash
L=/skills/weekly-skill/resources/scripts/term_lint.py
python3 "$L" build --source /app/work/source.txt --out /app/work
```

`build` 从原文抽候选术语（大写缩写、化学式、高频名词短语）写 `/app/work/glossary_draft.json`，按出现次数降序、最多 120 条，并对纯大写缩写默认预置 `keep_original: true`。

**Agent 必须逐条定名**，把结果写到 `/app/output/glossary.json`：

- `zh` 填领域通行译名；同一术语只允许一个译名，全篇锁定。
- `keep_original: true` 只给拉丁缩写、化学式、基因/软件名（XRD、SEM、DFT、LiFePO4 视材料约定而定）；缩写首次出现写"中文全称（缩写）"，后文用缩写，这属合规保留，不算未译。
- `decision_basis` 写定名依据（领域惯例 / 材料内定义 / 沿用作者用法），空着等于没依据。
- `variants` 只填**同一术语的可接受异体**（如"氧空位/氧空位缺陷"），不填近义不同概念。

定名后先跑一次计数摸底，确认术语规模与原文数字/单位/引用量，决定是否需要分段多轮：

```bash
python3 "$L" stats --source /app/work/source.txt --target /app/output/translation_zh.md
```

### 第 3 步：按语义边界分段

按原文自然段切分，段号 `para_id` 用 `p001`、`p002` 递增，与原文段落顺序严格一致。跨页、跨栏、跨章节处**不合并、不拆分、不漏**；标题、图注、表头、脚注各自成段并标 `block_type`（`title` / `body` / `caption` / `table_head` / `footnote`）。每段记录起始锚点，供 `anchors` 使用。

### 第 4 步：逐段翻译

对每段执行：

1. **重读术语表**（不是回忆），遇表中术语必须用锁定译名；遇新术语先补表再译，补表项同步写进 `glossary`。
2. 保留原文段落结构、句序、图表编号、公式、文献引用标记（`[n]`、`\cite{}` 原样保留）。
3. 指代、否定（不/未/无/非/never/not）、限定（仅/部分/显著/may/can）、因果与让步关系逐项对齐，不强化也不弱化。
4. 数字与单位原样保留（含有效数字、上下标、量纲）；`6 h` 写成 `6 小时` 属等价，但要全篇统一一种写法。
5. 同时产出两份：`result.json` 的 `translation` 数组（带 `anchors`、`term_refs`），与 `/app/output/translation_zh.md` 纯文本译稿（段落间空行分隔、顺序与原文一致）。

### 第 5 步：机械核验与回修（可核验）

**先跑脚本，再人工判读**——这是"术语稳、关系准"的机械证据：

```bash
python3 "$L" check --source /app/work/source.txt \
                   --target /app/output/translation_zh.md \
                   --glossary /app/output/glossary.json --out /app/output
```

产物：`/app/output/term_report.json`（机读）、`/app/output/term_report.md`（人读，按类别分组）。各类处置如下：

| 类别 | 含义 | 必须动作 |
|---|---|---|
| `untranslated` | 约定应译的术语在译文中仍保留原文写法 | **改译文**用锁定译名；确属应保留的（缩写/化学式）改术语表 `keep_original: true` 并写 `decision_basis` |
| `missing_terms` | 译名在译文中一次都没出现 | 确认是漏译还是术语表译名与实际用法不符，二者都要消除 |
| `inconsistent` | 术语表内 `zh` 与 `variants` 混用 | **统一为 `zh`**，其余写法要么替换、要么补进 `variants` 并说明 |
| `suspected_variants` | 疑似另有译法（脚本只提示，不扣分） | **人工判断**：确实是同一概念的另一种译法才改；属不同概念则忽略，避免误改专业表述 |
| `number_mismatch` | 数字多重集不一致（引用编号已剔除，不重复报） | 逐条回原文核对，漏译补上、译错改正 |
| `unit_mismatch` | 单位出现次数不一致（已识别中文单位等价写法） | 按原文补回或统一写法；`unit_converted` 列出的属等价转换，无需改 |
| `citation_mismatch` | 引用标记数量或内容不一致 | 补齐缺失的 `[n]`，不得改写或合并编号 |
| `formula_mismatch` | 公式定界符数量不一致 | 公式原样复制，不翻译不改写 |
| `paragraph_gap` | 段落数差异过大 | 回第 3 步重分段，找漏段或合并段 |
| `negation_drift` | 否定表达数量差异（只提示） | 逐处核对，确认是否真有否定被译丢或误加 |

脚本跑完后仍需人工判断的部分（脚本测不出，写进 `verification` 的 `relation_preservation` 与 `uncertainties`）：指代对象是否指向正确、限定词强度是否被改写、因果让步关系是否被翻转、术语在同一概念下是否真的等价。**脚本给 0 差异不等于译对了意思，只等于没漏数字和标记。**

修完重跑 `check`，直到 `untranslated` / `missing_terms` / `inconsistent` / `number_mismatch` / `citation_mismatch` 均为 0，或每条残留都在 `uncertainties` 里有明确理由。每轮回修写入 `change_log`。

### 第 5.5 步：增益记录（使用增益 25 分）

按 `resources/gain_protocol.md` 记录对照条件、指标与可复算产物，写入 `result.json` 的 `gain_record`。无外部白板时用"同一运行内两版译稿"方式：先不查术语表盲译一版 `draft_blind.md`，再按本工作流产出定稿，两版分别跑 `check`，比较 `untranslated_count` / `missing_term_count` / `inconsistent_count` / `number_mismatch_count` / `unit_mismatch_count` 的变化。**不得编造对照数据**，测不出就写 `na` 并说明原因。

### 第 6 步：输出与复核

写 `/app/output/result.json`，确认：`case_id` 已回填、`output_contract` 字段齐全、`translation` 段数与原文一致且每段有 `anchors`、`glossary` 的 `decision_basis` 非空、`verification` 每项带计数、`translation_report` 与 `term_report.json` 数值一致、`uncertainties` 与 `change_log` 如实填写。译稿中不得出现未标注的推断内容。

## 异常处理

| 情况 | 处理 |
|---|---|
| PDF 文字层缺失 / 扫描件模糊 | 先 `ocr-tool`，仍失败则对应段标 `[原文不可读]`，写入 `uncertainties` 与 `handover`，整体 `status: partial` |
| 公式或表格为图片 | 保留占位与 `eq<号>` / `tab<号>` 锚点，说明无法读取，不猜内容 |
| 原文残缺 / 语言混杂 | 逐处标注，可译部分照常输出，整体 `partial` |
| 文献引用无法解析 | 原样保留标记，说明无法核验，不重新编号 |
| 术语冲突（同一缩写指不同对象） | 术语表分列两条，`positions` 写清，译文按位置区分 |
| 篇幅超出单轮预算 | 分段增量落盘，先保 `status: partial` 的完整前半部分，再续译后半部分并合并，不重复段 |
| 脚本报 source/target 为空 | 检查路径与编码（必须 UTF-8），PDF 未抽文字层是最常见原因 |

## 资源

- `resources/scripts/term_lint.py`：**执行内核**。`build` 抽候选术语生成术语表骨架、`check` 把译稿与术语表/原文逐条比对并输出十类问题、`stats` 做段落/数字/单位/引用/公式计数摸底。纯标准库（`argparse`/`re`/`json`/`collections`/`pathlib`），无第三方依赖，可完全离线运行。
- `resources/checklist.md`：带计数口径的译后自检清单。
- `resources/gain_protocol.md`：使用增益对照协议与 `gain_record` 记录格式。
- `resources/field_dict.md`：字段字典、锚点格式与术语表规范。
- `resources/glossary_template.json`：术语表模板。
- `resources/output_example.json`：输出结构示意（非答案）。
- `environment/resources.yaml`：资源清单、依赖、运行时与产物说明。
- `examples/README.md`：最小调用示例（示意）。

## 最小示例（示意，非真实案例译文）

```bash
L=/skills/weekly-skill/resources/scripts/term_lint.py
python3 "$L" build  --source /app/work/source.txt --out /app/work
# 人工/Agent 定名 → /app/output/glossary.json
python3 "$L" check  --source /app/work/source.txt \
                    --target /app/output/translation_zh.md \
                    --glossary /app/output/glossary.json --out /app/output
```

示意输出（仅结构与计数口径，数值为占位）：

```json
{"term_total": 12, "term_ok": 10, "untranslated_count": 1, "missing_term_count": 1,
 "inconsistent_count": 0, "suspected_variant_count": 2,
 "number_mismatch_count": 0, "unit_mismatch_count": 0, "unit_converted_count": 3,
 "citation_mismatch_count": 0, "formula_mismatch_count": 0}
```

真正的结果必须来自本次实际运行，示意输出不得冒充正式案例答案。
