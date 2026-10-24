# SciNet

**用 AI 评审团和区块链，建立开放的论文评价体系。**

[![检查](https://github.com/flypigpet/scinet/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/flypigpet/scinet/actions/workflows/ci.yml)
[![版本](https://img.shields.io/badge/release-0.1.0a1-orange)](https://github.com/flypigpet/scinet/releases/tag/v0.1.0a1)
[![MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

[如何协作](#如何协作) · [快速开始](#快速开始) · [真实案例](#真实案例) · [路线图](#路线图) · [English](README.md)

SciNet 希望让论文凭研究证据和公开评审获得认可，减少对期刊名气的依赖。我们要做的是一套去中心化的学术评价机制：评价标准公开，评审意见可以核验，判断可以被质疑和修正。

**当前阶段：早期原型。** 已实现数值复算和可选的单模型评审。AI 评审团、区块链记录和社区治理仍在计划中，尚未实现。

## 如何协作

- **AI 评审团审查研究。** 计划让多位评审分别阅读材料、引用证据，并保留分歧。模型、提示词和评价标准应当公开。
- **复算检验具体结论。** 通过数据、代码和运行记录，让其他人检查评审意见是否站得住脚。当前原型验证的就是这一部分。
- **区块链记录评审历史。** 计划用内容哈希关联论文版本、签名评审和质疑记录，完整证据保存在链下。记录一项判断，不等于证明它正确。

我们希望把“标尺”本身也开放出来：任何人都能检查规则、提出不同标准，并对判断发起申诉。AI 意见一致不应直接决定科学结论，持币数量也不应决定学术价值。

## 先跑通第一步

当前 alpha 版本仅内置一个可运行示例：**Same Stats, Different Graphs（Datasaurus）**。它复算 13 组数据的 65 个统计量，运行选定的作者函数，把结果与来源放进本地 HTML 报告。可选的 AI 评审还会保存提示词、回答和请求的模型。

安装后，数值演示可以离线运行，无需 AI 账号。这是整个项目中的证据核验部分。

## 快速开始

需要 Git 和 Python **3.12+**。已在 Windows、Ubuntu 的 Python 3.12 环境验证。从源码安装：

```sh
git clone https://github.com/flypigpet/scinet.git
cd scinet
python -m venv .venv
```

激活环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS 使用 `source .venv/bin/activate`。然后运行：

```sh
python -m pip install .
scinet init --workspace demo
scinet --workspace demo run
scinet --workspace demo verify latest
```

用浏览器打开命令打印的 `REPORT=` 路径。报告中有 13 组散点图、全部计算值、作者代码运行结果，以及对应的证据文件链接。目前报告使用中文。

每次运行都会在 `demo/output/` 下创建独立目录。`verify latest` 检查最近一次运行的文件和证据引用。项目尚未发布到 PyPI。

## 真实案例

[查看一次实际运行，包括未经改写的 AI 回答 →](docs/cases/2026-10-24-datasaurus-live-review/README.zh-CN.md)

Datasaurus 案例展示了这套检查能发现什么：

- 同一批数据在某些两位小数规则下相同，按常规四舍五入却有差异。
- 保存的项目网页说明给出正相关系数，数据和论文给出的都是负值。
- 论文正文中的温度比较方向，与伪代码和作者代码相反。

案例页列出了每项观察的来源、模型请求、实际结果和待确认问题。这些是具体检查，尚未覆盖整篇论文的全部实验。

## 加入 AI 评审

另行安装并登录 Codex CLI。在克隆的仓库目录中下载论文材料，再启动一次新运行：

```sh
python scripts/acquire.py --workspace demo
scinet --workspace demo run --ai --model MODEL_ID
```

把 `MODEL_ID` 替换为你账号可用的模型。这一步需要联网并使用你的服务额度。论文文本、网页文本、作者代码、选定的问题和计算结果会发送给模型服务，详见[发送内容与保存记录](docs/AI_USAGE.md)。

## 当前支持到哪一步

CLI 目前围绕内置的 Datasaurus 案例编写，接入另一篇论文需要另做检查和运行适配。AI 会看到选定的问题和计算结果，属于带提示的评审；科学判断尚未经独立领域专家验证。

程序只运行选定的作者函数，有超时限制，**没有执行任意代码的安全沙箱**。文件哈希用于检查内容变化，不能证明论文结论，也不提供可信时间戳。原型尚未实现 AI 评审团、区块链或去中心化治理。

## 路线图

1. **别人也能重跑的证据。** 将检查扩展到更多论文。让 AI 先阅读材料，不提前给出复算结果或提示具体缺陷，再逐项核对它提出的判断。
2. **允许分歧的评审团。** 加入不同模型的分别评审，保留原始意见，并结合领域专家的核验，测量漏报、误报和重复评审的稳定性。多次调用本身不能证明独立性。
3. **共同维护的评审历史。** 定义带签名的记录格式，试验论文版本、评审和质疑记录的链上存证。原始材料按许可保存在链下，并提供独立校验记录的方法。
4. **公开的评价规则。** 公布标准及其修改过程，设计申诉、评审者信誉和防串通、防重复身份机制。在用于重要决策前验证这些机制。

这些是开发方向，并非已上线功能。尚未选择具体链或代币方案，也尚未证明这套系统能够替代期刊评价或降低出版成本。

## 文档

| 文档 | 内容 |
| --- | --- |
| [复现说明](docs/REPRODUCIBILITY.md) | 命令、输出文件和计算细节 |
| [AI 评审说明](docs/AI_USAGE.md) | 输入内容、模型记录和限制 |
| [验证记录](docs/VALIDATION.md) | 已执行的安装、测试和 CI 检查 |
| [来源与许可](docs/ASSETS.md) | 数据、代码和论文的出处 |

## 参与开发

可以从一篇有公开数据和代码的论文开始，也可以核验 AI 的判断、设计评审团对照实验，或参与签名记录和申诉机制的设计。参见[贡献指南](CONTRIBUTING.md)和[安全说明](SECURITY.md)。

## 许可

SciNet 使用 [MIT 许可](LICENSE)。附带数据和作者代码保留原 MIT 声明；论文和网页沿用各自的许可。另见[素材清单](docs/ASSETS.md)、[变更记录](CHANGELOG.md)和[引用信息](CITATION.cff)。
