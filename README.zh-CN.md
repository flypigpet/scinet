# SciNet

**针对单篇科学论文的证据审计原型。** SciNet 复算有限的数值主张，试运行选定的作者函数，并生成本地中文 HTML 证据报告；可选的 Codex 评审用于解释这些已记录的结果。

[English](README.md) · [复现说明](docs/REPRODUCIBILITY.md) · [AI 使用披露](docs/AI_USAGE.md) · [素材与许可](docs/ASSETS.md)

**0.1.0a1 是研究软件预览版。** 人工科学验证状态为 **待完成**（`human_validation_pending`）。本项目不能证明 AI 同行评审可靠，也不作论文录用或发表决定。

## 覆盖范围

目前只有一个案例：Matejka 与 Fitzmaurice 的 *Same Stats, Different Graphs*（CHI 2017）。参见[作者项目页](https://www.research.autodesk.com/publications/same-stats-different-graphs/)、[论文 DOI](https://doi.org/10.1145/3025453.3025912)及[固定版本作者仓库](https://github.com/jmatejka/same-stats-different-graphs/tree/b4d82f3a2ff8ef5849fecbdfab6dccafccbc1370)。

- 对 13 组、每组 142 个点的数据计算五项统计量，共 65 个值；分别使用 Python 标准库和 pandas/NumPy 路径交叉核对。
- 分别计算向下取整、向零截断与四舍五入；标准差使用样本标准差（`ddof=1`）。
- 只执行已检查、哈希固定的作者函数，记录种子、1,000 次提案和兼容性改动。
- 保存来源、计算结果、中文 HTML 报告及 SHA-256 清单；AI 评审可选。

这不包含论文全部实验、动画、原始随机轨迹、收敛或性能主张的复现。数值核对或软件测试通过，不能证明科学评审有效。作者代码运行有超时限制，但**独立进程不等于安全沙箱，不能用于执行任意投稿代码**。

## 安装与离线演示

需要 Python **3.12 或更高版本**和 Git。本地已验证 Windows/Python 3.12；Linux 仍待 CI 成功运行验证。安装时可能需要下载依赖；安装完成后，数值演示无需联网或 AI 账号。

```sh
git clone https://github.com/flypigpet/scinet.git
cd scinet
python -m venv .venv
```

在 Windows PowerShell 激活环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

POSIX shell 使用 `source .venv/bin/activate`。然后运行：

```sh
python -m pip install .
scinet init --workspace demo
scinet --workspace demo run
```

命令会显示新运行目录和报告位置，使用浏览器打开其中的 `report.html`。每次运行创建新目录，离线报告明确显示未运行 AI。PowerShell 中可检查最近一次运行：

```powershell
$run = Get-Content -LiteralPath demo/output/latest.txt
scinet verify $run
```

也可直接传入显示的运行目录：`scinet verify demo/output/run-<timestamp>-<id>`，需替换示例目录名。检查覆盖记录文件与证据引用结构，不能证明科学结论、作者身份或可信发表时间。

当前从源码安装，**尚未发布到 PyPI**。

## 可选 AI 评审

需要另行安装并登录 Codex CLI。`MODEL_ID` 代表你账号可用的模型标识，需自行替换；本文不指定或暗示某个模型可用。调用会使用你的服务额度。

在克隆的仓库目录中，把官方论文和项目页下载到本地工作区，再创建一次新运行：

```sh
python scripts/acquire.py --workspace demo
scinet --workspace demo run --ai --model MODEL_ID
```

下载需要网络。论文文本、网页文本、作者代码、待核验主张和计算结果会发送至模型服务。使用非公开材料前请阅读 [AI 使用披露](docs/AI_USAGE.md)。未登录、调用失败或超时会报错，不会用模板冒充模型输出。

对已包含下载材料、且尚未评审的运行，可使用 `scinet --workspace demo review RUN_DIR --model MODEL_ID`，并替换两个占位符。已有评审会保留；再次评审请创建新运行。

## 如何理解结果

运行目录保存数值结果、作者函数试运行记录、来源和实现快照，以及文件校验清单。AI 运行还保存实际提示词、输入哈希、结构化评审和调用记录；详见[复现说明](docs/REPRODUCIBILITY.md)。

提示词已经提醒模型关注精度规则以及网页与论文的区别，因此这是**单论文、单 AI 评审者的受引导演示**，不是盲测。论文是知名案例，不能排除模型训练记忆的影响。引用定位和科学判断仍待人工核验，未声称经过独立领域专家同行评审。旧本地运行中未记录的模型身份仍为未知。

哈希只检测相对于清单的变化，无法阻止文件与清单一同被替换。本项目没有数字签名、区块链存证或可信外部时间戳。

## 参与和许可

参见[贡献指南](CONTRIBUTING.md)、[安全说明](SECURITY.md)、[变更记录](CHANGELOG.md)和[引用元数据](CITATION.cff)。自动化检查用于验证实现，不代表科学验证；CI 成功运行前不宣称其通过。

SciNet 原创代码和文档使用 [MIT 许可](LICENSE)，附带的数值素材与作者代码保留原 MIT 声明。论文和网页拥有独立权利，通过脚本下载至本地，不能套用本项目 MIT 许可。公开源码和软件包排除论文全文、网页快照、本地运行结果及原始 AI 日志；详见[素材清单](docs/ASSETS.md)。
