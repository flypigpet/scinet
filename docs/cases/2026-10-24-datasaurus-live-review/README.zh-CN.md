# 公开案例：对《Same Stats, Different Graphs》的一次真实 AI 审计

[English](README.md) · [项目说明](../../../README.zh-CN.md) · [公开文件清单](publication.json)

**2026 年 10 月 24 日（北京时间）**，SciNet 在复算论文部分结果后，完成了一次新的真实模型调用。模型对四项预先设定的主张给出 **2 项有条件支持、1 项支持、1 项未验证**，并指出一处温度比较方向的表述不一致；随后通过原 PDF 和作者代码进行了自动化核对。

这是**单篇已知论文、单模型、带检查提示的纯文本审计案例**。它展示可追溯的审计流程，不是 AI 同行评审准确率测试。**人类领域专家验证仍待完成。** [中文模型原始回答](evidence/review.json)按原字节公开；本页的组织与解释属于事后编辑。

## 模型与运行记录

| 项目 | 实际记录 |
| --- | --- |
| 明确请求的模型 | `gpt-6-astra`（GPT-6-Astra） |
| 服务端实际模型快照 | **未知**；客户端事件未返回不可变的内部版本 |
| 评审次数 | 一次新的 Codex CLI 模型调用；没有独立模型评审团 |
| 客户端版本 | `codex-cli 0.163.0-alpha.11.2` |
| UTC 起止时间 | `2026-10-23T23:55:37.497224+00:00` 至 `2026-10-23T23:56:47.931622+00:00` |
| 北京时间 | 2026-10-24 07:55:37–07:56:47（UTC+08:00） |
| 调用耗时与退出状态 | 70.434398 秒；退出码 0 |
| 客户端报告用量 | 输入 36,678 tokens；输出 2,039 tokens；推理输出 93 tokens；缓存输入 0 |
| 推理强度 | 没有显式指定；实际生效值未知 |
| SciNet 实现 | `v0.1.0a1`，提交 [`e6db99d`](https://github.com/flypigpet/scinet/tree/e6db99da565473785632096471ea3e8d2f53648b) |
| 计算环境 | Windows 11、Python 3.12.14、NumPy 2.3.5、pandas 3.0.1；完整依赖版本见调用记录 |

[公开调用记录](evidence/call-record.json)包含归一化命令、时间、依赖版本和哈希；[原始调用来源记录](evidence/review_provenance.json)按原字节保留。调用使用 `--ignore-user-config`，不能把本机配置中的推理偏好视作实际设置；模型目录里的默认值也不能证明运行时生效值。启动期间出现模型／插件目录刷新网络警告，随后本次调用正常完成，完整警告日志留在本地。

这些是**客户端捕获的记录**，不是模型服务商签发的后台身份凭证。没有返回货币成本，因此不根据 token 数推算价格。

## 模型看到了什么

SciNet 先进行数值计算和作者函数试运行，再向模型提供六份文本：论文提取文本、作者网页提取文本、原始作者代码、四项待核验主张、`metrics.json`、`author_smoke.json`。

[提示词指令部分](prompt-instructions.txt)是原始前缀的精确副本。它已明确提醒模型检查样本／总体标准差、向下取整／向零截断／四舍五入、网页与论文差异，以及复现范围。完整提示词还包含论文与网页全文，因此不直接公开；其 SHA-256 和六份实际输入的哈希分别见[调用记录](evidence/call-record.json)和[输入哈希表](evidence/review_input_hashes.json)。[输出 JSON 结构要求](evidence/review_schema.json)一并公开。

本次模型**没有调用工具、独立复算、读取逐点坐标文件，也没有看到图形、动画或事后渲染的 PDF 页面**。客户端事件中只有一个回答条目，其内容与保存的模型回答一致。[固定版本的提示词组装代码](https://github.com/flypigpet/scinet/blob/e6db99da565473785632096471ea3e8d2f53648b/scinet/pipeline.py#L87-L128)可供检查。

## 四项结果及其边界

| 核验主张 | 模型判断 | 实际结果 |
| --- | --- | --- |
| C1：五项统计量保留两位小数后相同 | 有条件支持 | 13 组 × 142 点，共 1,846 行。向下取整和向零截断各自得到组间一致结果；采用普通四舍五入 `ROUND_HALF_UP` 时，五项指标都出现组间差异。 |
| C2：作者网页给出了正相关系数 | 支持 | 下载时的 Fig 5 图注写作 `R=0.06`，没有显式加号。复算的相关系数全部为负，论文 Figure 6 则写为负值 −0.06。问题属于网页图注。 |
| C3：作者函数能移动点并维持统计约束 | 有条件支持 | 完成 1,000 次提案，接受 687 次、拒绝 313 次；142 个点均有位移，坐标有限且满足原来的 floor 统计约束。只运行了选定函数与适配后的驱动循环。 |
| C4：全部实验、动画、原始轨迹和性能都已复现 | 未验证 | 这是一项防止夸大范围的检查项，不是 SciNet 已完成的成功声明。当前材料不足以支持完整论文复现。 |

对应原始材料：[模型回答](evidence/review.json)、[预设主张](evidence/claims.json)、[数值结果](evidence/metrics.json)、[仅处理路径后的执行记录](evidence/author_smoke.json)。

C1 中，按 x 均值、y 均值、x 样本标准差、y 样本标准差、Pearson r 的顺序：

- 向下取整到两位：`[54.26, 47.83, 16.76, 26.93, -0.07]`。
- 向零截断到两位：`[54.26, 47.83, 16.76, 26.93, -0.06]`。
- Figure 6 的显示值与向零截断一致，但不能只凭图注推定作者的具体生成方式。
- 标准差分母为 `n−1`。标准库与 pandas/NumPy 两条计算路径的最大误差为 `7.105427357601002e-15`，低于 `1e-10`。这是同一数据上的计算交叉核对，不是两个独立科学研究。

C2 的预设主张用 `+0.06` 表示正值；模型进一步明确，网页并没有印出 `+` 字符。网页快照采集于 **2026-10-23 10:08:51 UTC**，在线页面以后可能变化。

C3 中，两处 pandas 赋值改为 `.loc`，跳过了完整包加载、绘图和原始命令行入口。距离圆形目标的平均偏差由 `9.626466015989623` 降至 `9.455052975996075`，不足以证明收敛为圆。1.462 秒的有限测试也不能与论文完整实验耗时直接比较。公开材料包括实际[适配器](evidence/author_smoke/adapter.py)、[种子坐标](evidence/author_smoke/seed-original.csv)、[最终坐标](evidence/author_smoke/generated.csv)和[原始数值结果 JSON](evidence/author_smoke/smoke-result.json)，并保留作者 MIT 声明。运行有超时限制，但不是可执行任意投稿代码的安全沙箱。

## 额外发现：温度比较方向

模型在 F3 中指出了指令前缀未具体提示的一处差异：

| 位置 | 比较关系 |
| --- | --- |
| 原 PDF 第 3 页第一段 | 温度小于随机值 |
| 原 PDF 第 2 页伪代码第 10 行 | 温度大于随机值 |
| 作者 `perturb` 函数[第 398 行](https://github.com/jmatejka/same-stats-different-graphs/blob/b4d82f3a2ff8ef5849fecbdfab6dccafccbc1370/samestats/samestats.py#L398) | 随机值小于温度 |

协调助手与另一自动化子代理核对了来源。评审结束后，再渲染原 PDF 第 2、3 页检查，确认不是文本提取错误。[事后证据核对记录](evidence/evidence_assessment.json)与模型原始回答分开保存。

这支持“**正文、伪代码与实现存在表述不一致**”，但不等于算法失效或论文主要结论被推翻。实际代码还包含其他边界条件和外层统计接受约束。没有核验该观察是否首次被发现；事后检查也不等于人类专家验证或独立模型投票。

## 证据来源与公开范围

| 来源 | 版本及定位 |
| --- | --- |
| 论文 | Justin Matejka、George Fitzmaurice，*Same Stats, Different Graphs*，CHI 2017；[DOI](https://doi.org/10.1145/3025453.3025912)、[官方 PDF](https://research.autodesk.com/app/uploads/2023/03/same-stats-different-graphs.pdf_rec2hRjLLGgM7Cn2T.pdf) |
| 作者项目网页 | [Autodesk 官方页面](https://www.research.autodesk.com/publications/same-stats-different-graphs/)，对应日期快照的 Fig 5 图注 |
| 作者代码与数据 | [固定到 `b4d82f3` 的仓库](https://github.com/jmatejka/same-stats-different-graphs/tree/b4d82f3a2ff8ef5849fecbdfab6dccafccbc1370)，保留原 MIT 许可 |
| 获取记录 | [原始链接、时间与 SHA-256](evidence/provenance.json) |
| 引用名称对应关系 | [证据来源映射](evidence/source-map.json)，标明哪些材料需要另行下载 |

公开案例是明确筛选过的材料，**不是完整本地证据包**。[publication.json](publication.json)逐项记录复制与处理方式。模型回答及标注为未修改的记录按原字节保留。`author_smoke.json` 仅替换本机路径并重新序列化 JSON，数值和局限均保留；`call-record.json` 是删除绝对路径及会话标识后新编的摘要。

论文和网页全文、完整提示词、原始调用日志、原始 HTML 报告、PDF 截图与完整证据 ZIP 继续留在本地。因此，公众不能仅靠这个子集精确重放当时的全部输入；可另行获取来源，依据链接、定位和哈希进行比对。哈希本身不能展示或认证未公开的内容，论文和网页也未被重新授权为 MIT。

## 检查与重跑

在包含本案例的仓库根目录、安装 SciNet 后，可以检查**公开文件子集**的完整性：

```sh
python -c "from scinet.evidence import verify; errors = verify('docs/cases/2026-10-24-datasaurus-live-review'); print(errors or 'Public case hashes OK'); raise SystemExit(bool(errors))"
```

`manifest.json` 对应公开文件字节，`review_input_hashes.json` 对应原始模型输入；处理过路径的执行记录与原始输入哈希不同是预期结果。不要对本子集直接运行完整流程的 `scinet verify`，因为全文输入和日志被有意排除。哈希不等于可信签名、区块链证明或外部时间戳。

另一个原记录细节也明确保留：`author_smoke.json.adapter_sha256` 对应适配器**经过 Windows 换行转换前的内存文本**，不是磁盘文件字节。对文件执行一次 CRLF→LF 替换可得到该记录值。[调用记录中的 `adapter_hash_note`](evidence/call-record.json)同时列出两个哈希，公开清单使用实际文件字节的哈希，没有悄悄改写原值。

若重跑计算，请在另一个检出目录使用实现提交 `e6db99da565473785632096471ea3e8d2f53648b`，按[项目安装说明](../../../README.zh-CN.md)安装后运行：

```sh
scinet init --workspace case-replay
scinet --workspace case-replay run
scinet --workspace case-replay verify latest
```

若要开展**新的一次 AI 评审**，另行获取论文和网页，并填写账号可用的模型标识：

```sh
python scripts/acquire.py --workspace case-replay
scinet --workspace case-replay run --ai --model MODEL_ID
```

这会创建新运行并可能使用服务额度。不能保证模型持续可用、后台版本固定、回答相同或未来网页字节不变。宣称精确重放前，需要核对环境与原始输入哈希。公开的适配器供检查使用；受超时等约束的执行入口仍是 SciNet 命令。

## 可以说明什么，不能说明什么

本次回答能区分数值显示规则、网页符号问题和未覆盖的复现范围，并提出一个可回到原文检查的额外疑点。有限的自动化事后核对未发现这四条判断中的无依据数值断言或伪造定位，但这**不是准确率指标**。

提示词已引导多个检查方向，也无法排除模型在训练中见过这个知名案例。当前只有一篇论文、一次模型调用，没有盲测标准答案、人类领域专家评估，也未测量误报、漏报和多次评审稳定性。复算结果由程序提供，并非模型独立执行。服务端隐藏上下文和内部推理不可获取。这些结果不能证明可以替代同行评审、决定论文发表、实现去中心化治理或抵御对抗性投稿。
