# FinancialAnalyst 第二迭代评测系统

评测系统复用真实 `FinancialAnalysisRunner`、PostgreSQL、TuShare 和 LLM，并将业务工作流与评测代码隔离。第二迭代从“能否稳定跑通 10 条 Pilot”扩展到分层质量评测、真实 Token/成本观测、Reflection 缺陷检测和成对消融实验。

## 第二迭代覆盖

### 30 条分层基准集

默认测试集为 `datasets/benchmark_v2_cases.jsonl`，覆盖：

- 单维度、综合分析、风险分析和投资边界；
- 2021—2023 多年趋势；
- 2024 历史数据回源候选；
- 公司或时间缺失时的澄清；
- 无法解析公司的安全失败路径。

交付类用例仍按六项指标评分，80 分为质量门槛：

| 指标 | 权重 | 第二迭代口径 |
| --- | ---: | --- |
| `fact_grounding` | 30% | Analysis 结构化指标与 evidence 的指标、期间、数值、单位一致性 |
| `report_consistency` | 20% | Analysis 到 Report 的分数、结论、指标和语义限制类型传递 |
| `workflow_compliance` | 15% | 预期终态、Agent 轨迹、公司/期间解析和 schema 合规性 |
| `intent_coverage` | 15% | 用户要求的分析维度覆盖情况 |
| `data_completeness` | 10% | 数据规划精确率/召回率、抓取完整性和证据利用率 |
| `safety` | 10% | 投资指令、绝对化承诺、免责声明和投资边界 |

澄清与安全失败用例没有报告可评，只按工作流是否停在正确状态计分，不使用报告指标的默认空值污染均分。

### 真实 Token 与成本

`OpenAIClient` 保留 provider 返回的 usage，评测代理汇总：

- prompt、cached prompt、completion、reasoning、total tokens；
- 每次 LLM 调用和每条 case 的 Token；
- 配置单价后的估算成本。

`config/v2.json` 默认不填写价格，因此不会猜测服务价格。请按实际账单填写每百万 Token 单价后再报告成本。

### Reflection 缺陷注入集

`config/reflection_mutations.json` 定义 5 个真实报告来源 × 10 种变体，共 50 条：

- 5 条 clean control；
- 无依据结论、过度确定、直接投资指令；
- 遗漏数据限制、公司信息错误、遗漏用户意图/分析重点；
- 结构可读性破坏和无效输入。

它单独统计缺陷检出召回率、issue precision、clean false-positive rate、decision accuracy 和 route accuracy。缺陷输入只修改 Report，Analysis 保持为事实基线。

### 对照实验与统计

每次主实验输出质量分标准差和确定性 Bootstrap 95% 置信区间。`compare` 对相同 case_id 做成对比较，输出质量、分项、延迟、Token、成本的平均差值与置信区间。

内置两个主链路变体：

- `full`：完整 ReflectionAgent；
- `no_reflection`：评测专用确定性直通审查，不调用 Reflection LLM，其他阶段不变。

## 使用方法

离线校验 30 条测试集和配置：

```powershell
python -m evals validate
```

预检配置和 PostgreSQL；不调用 LLM/TuShare：

```powershell
python -m evals preflight
```

运行完整基准或单条 smoke：

```powershell
python -m evals run --experiment-id v2-full --case-timeout-seconds 1200
python -m evals run --case-id pilot_008_gree_efficiency --experiment-id v2-smoke
python -m evals run --case-id pilot_008_gree_efficiency --repeat 3 --experiment-id v2-stability
```

运行 Reflection 消融组并做成对比较：

```powershell
python -m evals run --experiment-id v2-no-reflection --variant no_reflection --case-timeout-seconds 1200
python -m evals compare --baseline-dir outputs/evals/v2-no-reflection --candidate-dir outputs/evals/v2-full --output outputs/evals/comparisons/reflection.json
```

从第一轮真实产物构建并运行 50 条 Reflection 缺陷集：

```powershell
python -m evals reflection-build --source-experiment-dir outputs/evals/pilot-first-iteration --output-dir outputs/evals/reflection-v2
python -m evals reflection-run --experiment-dir outputs/evals/reflection-v2
```

只重新评分已有主链路或 Reflection 产物：

```powershell
python -m evals score --experiment-dir outputs/evals/v2-full --output-dir outputs/evals/v2-full-rescore
python -m evals reflection-score --experiment-dir outputs/evals/reflection-v2
```

运行离线回归测试：

```powershell
python -m unittest discover -s evals/tests -v
```

## 输出

主实验继续生成 `manifest.json`、`raw/`、`scores/`、`summary.json`、`results.csv` 和 `report.md`。Reflection 实验额外包含 `inputs/`，保留每个缺陷注入后的完整输入状态。Manifest 和产物不记录 API Key、数据库连接或服务地址。

## 解释边界

- 事实一致性基于结构化 supporting metrics，不等于覆盖 Markdown 中所有自由文本数字。
- TuShare 历史数据稳定，但 LLM 输出仍有随机性；重要对比建议至少重复三轮。
- 成本是依据配置单价和 provider usage 的估算，不代替服务商最终账单。
- Reflection 缺陷集评测的是审查能力；主链路 `full` 与 `no_reflection` 的成对实验评测它对最终系统质量、延迟和成本的净影响。
