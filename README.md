# 最小调用示例（示意）

以下仅为字段结构演示，**不是正式案例答案，也不是任何真实文献的译文或评测结果**。

## 输入

```text
请翻译以下摘要，要求术语统一、段落级对照：
[此处粘贴原文段落]
```

## 调用方式

在 Agent 中加载本 Skill（目录 `bohr-translation-skill/`），把上述输入直接发给 Agent。
Agent 会按 SKILL.md 的 6 步流程执行，输出 `result.json`。

## 示意输出

见 `../resources/output_example.json`，其中每段译文带 `anchors`，术语进 `glossary`，
自检结果进 `verification`，不确定项进 `uncertainties`。

## 说明

- 示意输出里的文字仅展示结构，不代表任何真实论文的翻译质量。
- 真实评测由平台用固定的 3 个案例运行，参赛者不提供测试案例或白板。
