# SciNet

**复算论文结果，查看 AI 评审和原始证据。**

[![检查](https://github.com/flypigpet/scinet/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/flypigpet/scinet/actions/workflows/ci.yml)
[![版本](https://img.shields.io/badge/release-0.1.0a1-orange)](https://github.com/flypigpet/scinet/releases/tag/v0.1.0a1)
[![MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

[快速开始](#快速开始) · [真实案例](#真实案例) · [文档](#文档) · [English](README.md)

SciNet 计算论文中的数值，运行选定的作者代码，再把结果、来源和可选的 AI 评审放进一份本地 HTML 报告。你可以查看计算过程，也可以沿着评审意见找到对应的证据。

当前 alpha 版本仅内置一个可运行示例：**Same Stats, Different Graphs（Datasaurus）**。安装后即可离线运行，无需 AI 账号。

- **核对数字。** 用两种实现复算 13 组数据的 65 个统计量。
- **运行代码。** 固定随机种子，执行选定的作者函数，记录兼容性修改。
- **留下记录。** 保存输入、输出和文件哈希；AI 运行还保存提示词、回答和请求的模型。

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

程序只运行选定的作者函数，有超时限制，**没有执行任意代码的安全沙箱**。文件哈希用于检查内容变化，不能证明论文结论，也不提供可信时间戳。目前没有实现区块链功能。

## 文档

| 文档 | 内容 |
| --- | --- |
| [复现说明](docs/REPRODUCIBILITY.md) | 命令、输出文件和计算细节 |
| [AI 评审说明](docs/AI_USAGE.md) | 输入内容、模型记录和限制 |
| [验证记录](docs/VALIDATION.md) | 已执行的安装、测试和 CI 检查 |
| [来源与许可](docs/ASSETS.md) | 数据、代码和论文的出处 |

## 参与开发

可以从一篇有公开数据和代码的论文开始，也可以补充复算检查，或对照原文核验已有发现。参见[贡献指南](CONTRIBUTING.md)和[安全说明](SECURITY.md)。

## 许可

SciNet 使用 [MIT 许可](LICENSE)。附带数据和作者代码保留原 MIT 声明；论文和网页沿用各自的许可。另见[素材清单](docs/ASSETS.md)、[变更记录](CHANGELOG.md)和[引用信息](CITATION.cff)。
