# 三个模型、20 条完整原始意见，以及有界数值核验

**案例日期：2026-10-24。审阅对象是 2014 年 `powerlaw` 论文的原始附录，不是当前 `powerlaw` 软件包。**

[English](README.md) · [论文及原始附录](https://doi.org/10.1371/journal.pone.0085777)

三个指定模型在各自新会话中阅读相同原始材料，没有收到问题清单、旧评审或计算结果。**20 条原始意见全部保留，不作改写。** 各份响应冻结后，选定复算在有限范围内支持了三项实现疑虑；部分论文印刷数值没有完全恢复，另有一些意见尚未数值核验。

**全流程完成。** 最终[综合响应](evidence/synthesis/response.json)逐项覆盖 20 条原始意见，未改写任何评审。综合请求模型为 `gpt-6.1-sol`，耗时 355.13 秒；[调用摘要](evidence/synthesis/call_summary.json)记录请求配置、用量、哈希及后端版本未知的限制。以下摘要由维护者整理，原始模型输出另行保留。

## 实际完成了什么

| 评审者 | 请求模型 | 原始意见数 | 调用耗时 | 原始响应 |
|---|---|---:|---:|---|
| r1 | `gpt-6.1-sol` | 8 | 83.83 秒 | [原样 JSON](evidence/reviews/r1/response.json) |
| r2 | `gpt-6-astra` | 7 | 146.58 秒 | [原样 JSON](evidence/reviews/r2/response.json) |
| r3 | `gpt-6-sol` | 5 | 62.74 秒 | [原样 JSON](evidence/reviews/r3/response.json) |

三次调用均记录 `completed`、退出码 0、未观察到工具调用。完整提示词的 SHA-256 相同：`86dc6133079ca501f13ba6a9464a46961bcc1bcc4464d09cd11132efc07834fa`。[统一指令前缀](evidence/review_instructions_prefix.txt)公开；包含论文、代码和数据的完整提示词不公开。

表中是**请求标识**，不是已经确认的不可变后端版本；三份记录的 `model_resolved` 均为 `null`。[r1](evidence/reviews/r1/call_summary.json)、[r2](evidence/reviews/r2/call_summary.json)、[r3](evidence/reviews/r3/call_summary.json)调用摘要保留 CLI 版本、时间、用量、输入哈希和工具观察状态。不同会话不证明训练数据、服务商或错误模式相互独立，也不能排除模型此前熟悉这篇论文。

[原始评审](evidence/freezes/reviews_freeze.json)于 **03:45:54 UTC** 冻结；[计算](evidence/computations/execution.json)于 **03:47:45 UTC** 开始，**03:48:14 UTC** 结束，退出码 0。[执行记录](evidence/computations/runner_execution.json)包含九组选定作者拟合、独立连续计算、四项定向检查和四项扩展检查。执行完成不等于科学结论全部通过。

## 三项疑虑获得了有界数值支持

| 对应原始意见 | 本次实测 | 不能外推到什么 |
|---|---|---|
| 有限上界归一化：r1/F2、r2/F2、r3/F3 | 固定连续 `Power_Law` 的 `xmin=1`、`xmax=10`、`alpha=2`，PDF 积分为 **0.9**，CDF 却达到 **1**。离散 PMF 总和为 1，但 10 处左累计概率为 **0.993547**，代码返回 1。 | 尚未数值检验其他子类、有限上界词频图、`round` 分支，以及对论文具体拟合值的影响。 |
| KS 选项未生效：r1/F3、r2/F3 | 连续停电尾部固定下界时，两种请求方法都给出 `alpha=2.272637`、`D=0.060674`；独立最小化相同已说明距离可得 `alpha=2.203524`、`D=0.040363`。 | 不否定默认最大似然估计；此检查未运行离散 KS 分支或外层阈值选择。 |
| `nested=False` 被覆盖：r1/F4、r2/F4 | 一个参数顺序下，对象接口给出 **p=0.382195**，与嵌套公式相同；直接传递 False 得到 **p=0.532438**。交换顺序后 False 得以保留。 | 本例两者均大于 0.05。这是选项处理检查，不是嵌套统计检验校准，也不能据此推翻所有科学结论。 |

证据见 [C1—C4 数值记录](evidence/computations/concern_checks.json)的 `result.checks`。C1 保留的英文范围说明有歧义，准确含义是：这些有限上界检查**不否定未设置 `xmax` 的默认拟合**，不是“全部默认拟合受影响”。

检查 C3 还量化了离散模型接收非整数输入时的敏感性。它来自复用的旧检查；本轮 20 条原始意见没有明确提出这一问题，不能计为本轮模型的新发现。

## 哪些数字对应，哪些没有完全恢复

[独立连续实现](evidence/computations/independent_continuous.json)与本次适配的历史作者实现，在五组选定拟合和候选扫描上满足绝对误差 **1e-12**。这说明已披露公式和输入上的计算一致，不是对所有统计定义或全文的认证。[比较记录](evidence/computations/independent_comparison.json)

| 数量 | 论文印刷值 | 本次有界复算 |
|---|---:|---:|
| 停电默认指数 | 2.273 | 2.272637 |
| 停电默认 `xmin` 与距离 | 230；0.061 | 230；0.060674 |
| 停电默认标准误 | **0.167** | **0.165683**，三位小数为 0.166 |
| 停电：幂律对指数 `(R, p)` | (12.755, 0.152) | (12.754563, 0.152293) |
| 词频：幂律对对数正态 `(R, p)` | (0.928, 0.426) | (0.928018, 0.425846) |
| 线虫：幂律对指数 `(R, p)` | (16.384, 0.024) | (16.384325, 0.024184) |
| 线虫：幂律对截断幂律 `(R, p)` | **(-0.081, 0.687)** | **(-0.070652, 0.706989)** |

来源：[作者拟合](evidence/computations/author_results.json)、[词频比较](evidence/computations/words_lognormal.json)、[线虫比较](evidence/computations/worm_comparisons.json)。两处加粗差异明确保留，目前未隔离出其原因。后一比较在两版本中都未达到 0.05 显著性阈值，但这不证明模型等价。历史优化实现没有保留优化器收敛标志。

## 未测意见，以及并非真正冲突的标签

- r1/F5 与 r2/F5 指出合法的零对数密度被替换。本次没有执行所建议的 `Lambda=1` 边界测试；[指数精度检查](evidence/computations/exponential_precision.json)采用不同拟合速率，不能冒充该项核验。
- r1/F6 与 r3/F5 指出绘图坐标轴参数未转发；没有实际运行双坐标轴测试。
- r3/F2 指出下界为 `None` 时的比较。本次未执行此例；Python 3 改变了跨类型排序规则，因此现代环境中的报错不能直接证明原 Python 2 环境当年失败。[Python 官方迁移说明](https://docs.python.org/3/whatsnew/3.0.html#ordering-comparisons)
- r3/F4 指出面向对象支持字典中的 `gamma: None`。这是源码核对意见；该入口及另一个函数式 gamma 实现均未在这些检查中运行。
- 完整图 S1 模拟、保留依赖结构的推断、绝对拟合优度和统计校准仍未验证。

r1/F8 标为 `supported`，r2/F7 标为 `concern`，但论证内容相同：论文讨论了独立性限制，而未能区分两个分布，不等于证明等价或绝对拟合充分。标签和侧重点不同，不能制造科学观点冲突。第三位评审者未提到某主题，也不代表赞同或反对。

## 筛选、适配和公开证据边界

这是协调者已经了解的一个定向选择的软件论文案例。**论文筛选和检查设计受旧案例启发，不是双盲实验。** 评审者材料包没有包含旧意见或计算结果；定向与扩展检查在本轮意见冻结后复用，不是这些模型新设计的检查。[协议](evidence/protocol.json)与[执行记录](evidence/computations/runner_execution.json)已披露这些限制。单一案例不能用于估计模型准确率。

对象为 PLOS 原始 2014 年 Code S1/S2，数据固定到仓库提交 `d2b563a7a08bad96b4085fa69f351e9d9a20b1e7`。[兼容适配记录](evidence/computations/compatibility.json)说明 Python 2 转换、现代数组比较、掩码取反和 API 迁移。没有重建原历史环境；尤其没有确认原 NumPy 掩码表达式当年的行为。本结果不评价当前软件版本。

公开子集包含：

- 三份原始评审响应，逐字节保留；[材料清单](evidence/packet.json)、[协议](evidence/protocol.json)和[评审结构](evidence/schema.json)。
- 统一指令前缀及来源哈希；调用摘要已去除本机路径、调用命令、上下文环境变量名和会话标识。
- 使用相对路径的原始[输入冻结](evidence/freezes/input_freeze.json)、[评审冻结](evidence/freezes/reviews_freeze.json)、[计算冻结](evidence/freezes/checks_freeze.json)和[计算文件清单](evidence/freezes/computation_inventory.json)。
- 选定计算 JSON：`publication` 说明来源哈希和删减字段，`result` 保存保留内容。本机路径和逐点观测数组已移除，保留字段的数值未改。

论文全文/PDF、原始数据、作者源码、完整提示词和原始日志不公开。冻结清单描述完整本地证据包，包含本公开子集未提供的文件；公开子集本身不是完整可重放证据包。哈希只能标识字节和本地变化，不证明作者身份、可信执行时间、科学正确性或链上认证。本次没有人类领域专家验证。

## 综合结果与完整性记录

最终综合分成 10 个主题：8 组意见相容，2 组只有一位评审提出；没有标记明确冲突。20 条意见中，11 条被标为 `supported`、8 条 `partly_supported`、1 条 `unresolved`。这些标签评价的是**评审意见获得什么证据支持**，不是论文的通过票，也不是模型准确率。12 条引用计算作为依据，8 条仅作源码核对；后者不能写成已经运行验证。

综合使用[明确列出的 17 份计算证据](evidence/synthesis/selection.json)，同时接收原始可读材料和三份原始评审。未送入这次综合的文件仍保留路径、长度和哈希。全文和重复源码使首次综合超过客户端长度限制；之后一次综合因恢复连接诊断被校验器拒绝。两次均保留为失败记录，最终续跑只重新调用综合模型，没有重做评审或复算。另两次早期启动失败也有记录。[尝试历史](evidence/attempt_history.json) · [完整流程事件链](evidence/timeline.jsonl)

[本地证据根承诺](evidence/local_commitment.json)为 `75da6b7b5a05564ac37489328ef0a4eb0685373efd6bae998e864a570913c1f8`。它覆盖完整本地文件及两个被归档的前序运行；其中很多文件未公开。公开子集有独立的[文件清单](publication.json)，两者不能混用。文件来源和删减方式见[转换说明](evidence/SOURCES.md)。这些记录可以供未来签名和链上存证引用，当前没有签名、可信时间戳或链上交易。

从仓库根目录校验公开文件：

```sh
python docs/cases/2026-10-24-powerlaw-panel/verify.py
```
