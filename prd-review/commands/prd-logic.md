---
description: PRD 逻辑分析 - 仅审计价值、MVP纯度、可测试性
---

请对以下 PRD 文档进行**逻辑深度审计**（仅 Phase 1）。

**PRD 文件路径：** $ARGUMENTS

**审计要求：**
1. 首先运行 `python3 ~/.config/opencode/skills/prd-review/scripts/analyze_prd_meta.py $ARGUMENTS` 收集元数据
2. 仅执行 `~/.config/opencode/skills/prd-review/SKILL.md` 中 Phase 1 的内容：
   - A. 价值合理性 (40分) - 决策树检查
   - B. MVP 纯度 (35分) - P0优先级验证
   - C. 核心设计与可测试性 (25分)
3. 输出逻辑分小计和详细问题列表

**输出格式：**

### Phase 1: 逻辑深度审计

#### A. 价值合理性 (40分)
| 问题 | 证据提取 | 判定 | 扣分 |
| :--- | :--- | :--- | :--- |
| Q1-Q5 逐项检查... |

#### B. MVP 纯度 (35分)
| P0 功能 | 正向定义 | 风险词 | 阻断性验证 | 判定 |
| ... |

#### C. 核心设计与可测试性 (25分)
| 检查项 | 证据提取 | 判定 | 扣分 |
| ... |

**逻辑分总计：** {L_Score}/100

### 修正建议
1. [Critical] ...
2. [Major] ...
