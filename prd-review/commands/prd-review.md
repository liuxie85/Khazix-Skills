---
description: PRD 全面审计 - 逻辑 + 结构完整评审
---

请对以下 PRD 文档进行全面质量审计。

**PRD 文件路径：** $ARGUMENTS

**审计要求：**
1. 首先运行 `python3 ~/.config/opencode/skills/prd-review/scripts/analyze_prd_meta.py $ARGUMENTS` 收集元数据
2. 按照 `~/.config/opencode/skills/prd-review/SKILL.md` 中定义的完整评审流程执行
3. 依次完成：
   - Phase 0: 熔断与红线检查
   - Phase 1: 逻辑深度审计 (70%)
   - Phase 2: 结构规范审计 (30%)
4. 输出完整的审计报告，包含最终评分和修正指令

请严格按照 SKILL.md 中定义的输出格式生成报告。
