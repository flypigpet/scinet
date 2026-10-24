# SciNet

**用 AI 评审团和区块链，建立开放的论文评价体系。**

[![检查](https://github.com/flypigpet/scinet/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/flypigpet/scinet/actions/workflows/ci.yml)
[![版本](https://img.shields.io/badge/release-0.1.0a1-orange)](https://github.com/flypigpet/scinet/releases/tag/v0.1.0a1)
[![MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

[快速开始](#快速开始) · [如何工作](#如何工作) · [示例](#示例) · [路线图](#路线图) · [English](README.md)

SciNet 把同一篇论文交给多个 AI 模型，分别保留评审意见，再用数据和代码逐项核验。你可以看到每位评审的原话、它们的分歧，以及判断所依据的证据。

我们要替代的是由期刊主导的评价机制：标准公开，评审可核验，判断可以被质疑和修正。AI 评审团负责审查，复算检验具体结论，区块链将用于共同维护可验证的评审历史。

**实验性 AI 评审团已跑通：三个模型、20 条原始意见、逐项证据核验。** [查看真实案例](docs/cases/2026-10-24-powerlaw-panel/README.zh-CN.md)。签名、链上存证和社区治理仍在计划中。评审团请从下方开发分支安装；已有的 `v0.1.0a1` release 尚不包含该功能。

## 如何工作

1. **给每位评审相同材料。** 把论文文本、作者代码和数据固定为一份带哈希的材料包。通用提示词不预告具体缺陷，也不提供此前评审和复算结果。
2. **分别评审，保存原话。** 每个请求的模型使用新会话。全部原始回答冻结后，才允许启动复算。
3. **用数据核对判断。** 运行经过检查的复算脚本，保存输入、兼容性修改、环境和实际输出。
4. **把分歧摆出来。** 另一次模型调用结合证据整理意见，原始评审保持不变。一致、冲突、讨论范围不同和未核验的问题分别呈现。

每次运行都保存提示词、回答、原始客户端记录、来源和文件哈希。最终证据摘要可供后续签名或链上存证使用；目前仍是本地记录，没有链上交易或可信时间戳。

## 快速开始

powerlaw 示例使用 Git 和 **Python 3.12**。另行安装并登录 Codex CLI；模型调用需要联网，并使用你的服务额度。

```sh
git clone --branch codex/ai-review-panel https://github.com/flypigpet/scinet.git
cd scinet
python -m venv .venv
```

Windows 激活环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS 使用 `source .venv/bin/activate`。然后安装并下载原始材料：

```sh
python -m pip install ".[powerlaw]"
python examples/powerlaw/acquire.py --output work/powerlaw-inputs
```

将 `MODEL_A`、`MODEL_B` 和 `SYNTHESIS_MODEL` 替换为你账号可用的模型 ID，评审者至少使用两个不同的 ID：

```sh
scinet panel review --bundle work/powerlaw-inputs/bundle.json --output work/panel-01 --model MODEL_A --model MODEL_B
scinet panel recompute work/panel-01 --script examples/powerlaw/recompute.py
scinet panel synthesize work/panel-01 --model SYNTHESIS_MODEL --evidence-list examples/powerlaw/synthesis-evidence.json
scinet panel verify work/panel-01
```

用浏览器打开命令打印的 `REPORT=` 路径。每一步分别留存记录；评审失败会阻止后续复算，重试请使用新的输出目录。

附带的 [powerlaw 证据清单](examples/powerlaw/synthesis-evidence.json)包含全部计算 JSON 文件、兼容性差异和核验脚本。综合提示词不重复放入输入副本、源码副本和原始日志，所有原始文件仍在本地完整保存。换一篇论文，需要准备对应的证据清单。

[powerlaw 示例说明](examples/powerlaw/README.md)列出输入版本、核验范围和限制；[评审团指南](docs/PANELS.md)介绍一条命令运行全流程，以及如何接入自己的论文材料。项目尚未发布到 PyPI。

## 示例

| 示例 | 用途 |
| --- | --- |
| [三个模型的真实评审](docs/cases/2026-10-24-powerlaw-panel/README.zh-CN.md) | 20 条原始意见、三项有界数值支持，以及没有复现的数字和未测问题 |
| [powerlaw](examples/powerlaw/README.md) | 原始论文、发表时的代码和公开数据；先分别评审，再做限定范围的复算 |
| [Datasaurus 真实评审](docs/cases/2026-10-24-datasaurus-live-review/README.zh-CN.md) | 早期带提示的单模型评审，已公开具体观察和证据 |

无需 AI 账号的离线数值演示：

```sh
scinet init --workspace demo
scinet --workspace demo run
scinet --workspace demo verify latest
```

内置 Datasaurus 演示复算 13 组数据的 65 个统计量，并运行选定的作者函数。它的可选 `--ai` 路径会把选定的问题和计算结果提供给一个模型，保留为**旧版带提示演示**。先评审、后复算的实验使用 `scinet panel`。

## 当前支持到哪一步

- **会话分开，供应商相同。** 评审团目前通过 Codex CLI 调用所选模型。不同 ID 不能证明训练过程或错误彼此独立；服务没有报告的实际后端保持未知。
- **证据保留，判断仍可出错。** 综合阶段的标签和分组也是模型解释。引用校验不能证明原文支持某项判断，独立领域专家验证仍待完成。
- **核验范围明确。** 每篇论文需要相应的复算脚本。powerlaw 示例检查历史代码及部分结果，没有覆盖全部实验或现代版本。
- **本地完整性可检查。** 哈希可以与保存的参考值核对，但不能证明作者身份、科学结论或可信时间。进程超时也不是执行任意代码的安全沙箱。

提交自己的材料前，请阅读[模型会收到和保存什么](docs/AI_USAGE.md)。完整本地证据可能包含受许可约束的全文和私有路径；公开案例需要单独检查发布范围。

## 路线图

- **扩展评审团。** 接入不同供应商，增加重复评审，并结合领域专家测量漏报、误报和分歧的价值。
- **扩展复算。** 加入更多论文和核验脚本，写清已经覆盖及尚未检验的部分。
- **共同维护评审历史。** 加入签名身份，试验论文版本、评审、质疑和修正的链上存证，完整证据保留在链下。
- **开放评价标尺。** 公开评价规则及修改过程，建立申诉、评审者信誉和防串通、防重复身份机制。

AI 意见一致不应直接决定科学结论，持币数量也不应决定学术价值。尚未选择具体链或代币方案，替代期刊评价和降低出版成本仍是需要验证的目标。

## 文档

| 文档 | 内容 |
| --- | --- |
| [AI 评审团](docs/PANELS.md) | 命令、证据格式、分歧和完整性校验 |
| [powerlaw 示例](examples/powerlaw/README.md) | 原始材料下载和限定范围的复算 |
| [AI 使用说明](docs/AI_USAGE.md) | 输入内容、模型记录和限制 |
| [Datasaurus 复现说明](docs/REPRODUCIBILITY.md) | 早期演示的命令和计算细节 |
| [验证记录](docs/VALIDATION.md) | 已执行的安装、测试和 CI 检查 |
| [来源与许可](docs/ASSETS.md) | 内置数据、代码和论文的出处 |

## 参与开发

可以加入一篇有公开数据和代码的论文、核验评审引用、比较模型，也可以参与签名记录和申诉机制的设计。参见[贡献指南](CONTRIBUTING.md)和[安全说明](SECURITY.md)。

## 许可

SciNet 使用 [MIT 许可](LICENSE)。第三方数据、代码和论文保留各自的声明与权利。另见[素材清单](docs/ASSETS.md)、[变更记录](CHANGELOG.md)和[引用信息](CITATION.cff)。
