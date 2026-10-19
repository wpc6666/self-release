# self-release · Skill 自更新与发布

> 用户说一句「更新这个 skill」或「更新 X」，agent 自动定位 GitHub 仓库和版本，走完改版 → 验证 → 推送 → 打 tag 全流程。**不需要你记住或粘贴任何仓库链接。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)](CHANGELOG.md)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey.svg)](#环境要求)

## 解决什么问题

发布 skill 时每次都要手打仓库地址、翻版本号、想分支名——重复且容易错。更麻烦的是**换一台机器后，本地 skill 不知道自己的仓库在哪**，用户还得重新找链接。

这个 skill 把坐标钉在 skill 自己身上：发布一次，写进 `.release.json`，之后任何机器、任何会话，说一句「更新 X」就能拉最新版。

```bash
# 以前：得先问用户「这个 skill 的仓库是哪个？」
# 现在：
python3 scripts/release.py --update
```

### 「一句话更新」靠什么成立

用户说「更新 X」，agent 不问任何东西，靠三级兜底：

| 级别 | 前提 | agent 动作 |
|---|---|---|
| 1 | `X/.release.json` 存在 | `cd X && python3 scripts/release.py --update` |
| 2 | 只有 `manifest.json` 的 `repository` | 同上（自动回退读 manifest） |
| 3 | 什么坐标都没有 | **问用户一次**仓库地址 → `--init` 钉死 → 之后永久免问 |

所以「不需要原始链接」的准确含义是：**链接只需提供一次，之后写进 skill 自己的配置，永远不用再提供。**

新电脑上连本 skill 都没有时，用上面的 `install.sh` 破局——那是唯一一次需要记住 URL 的地方。

## 一条命令安装

新电脑上还没有这个 skill 时：

```bash
curl -fsSL https://raw.githubusercontent.com/wpc6666/self-release/main/install.sh | bash
```

装到 `~/.dsh/skills/self-release/`，自动写入 `.release.json`。**幂等**——已装过会转为更新流程。

## 快速开始

### 发布：改完代码后升版本推送

```bash
cd ~/.dsh/skills/<你的 skill>

python3 scripts/release.py --check                  # 定位：仓库 / 版本 / tag / 分支状态
python3 scripts/release.py --bump patch --dry-run   # 先预览版本变化
python3 scripts/release.py --bump patch             # 真写入（同步三处文件）
python3 scripts/release.py --verify                 # 本地 vs 远端 blob 一致性
```

然后按 `SKILL.md` 的七步流程走：验证 → 同步 clone → 提交推送 → 打 tag → 汇报。

### 更新：别的机器上拉最新版

```bash
cd ~/.dsh/skills/X
python3 scripts/release.py --update
```

自动区分两条路径：

- 目录是 git 仓库 → `git fetch` + `git reset --hard origin/<branch>`
- 目录不是 git 仓库（当初是拷贝的）→ 下载 tarball 覆盖

两种情况都**保留本地 `.release.json`**，不会覆盖你钉死的坐标。

### 新装：新机器上从零装

```bash
git clone https://github.com/wpc6666/self-release.git /tmp/sr
cd /tmp/sr
python3 scripts/release.py --init https://github.com/<user>/<repo>.git --subdir "<路径>"
python3 scripts/release.py --install --target ~/.dsh/skills/X
```

坐标只需提供一次，之后永久免链接。

### 查看所有 skill 的坐标

```bash
python3 scripts/release.py --list
```

```
== 已装 skill 与发布坐标 ==
skill                 版本   仓库                                               分支/子目录
cfec-thesis-formatter 2.2.0  https://github.com/wpc6666/cfec-thesis-formatter.git main / 重财-论文格式规范
self-release          1.1.0  https://github.com/wpc6666/self-release.git         main
```

## 全部命令

| 命令 | 作用 |
|---|---|
| `--check` | 定位：仓库地址、当前版本、最近 tag、分支同步状态 |
| `--bump <patch\|minor\|major>` | 递增版本，同步 `SKILL.md` + `manifest.json` + `CHANGELOG.md` |
| `--bump <...> --dry-run` | 只预览，不写文件 |
| `--verify` | 比对本地文件 blob 与远端 GitHub blob |
| `--init <repo_url>` | 钉死仓库坐标，写入 `.release.json` |
| `--install` | 按坐标安装（新机器首次） |
| `--update` | 按坐标拉最新版（保留 `.release.json`） |
| `--list` | 列出所有已装 skill 的版本与发布坐标 |

## 自动定位规则

按优先级依次尝试，命中即停：

| 目标 | 优先级 |
|---|---|
| **仓库地址** | `.release.json` 的 `repo` → `.git/config` 的 `origin` → 向上 6 层找 `.git` → `manifest.json` 的 `repository`/`homepage` → `SKILL.md` 正文首个 GitHub 链接 |
| **当前版本** | `manifest.json` 的 `version` → `SKILL.md` frontmatter 的 `version:` → 一级标题里的 `vX.Y.Z` |
| **分支名** | `git branch --show-current` |

全部落空时 `--check` 返回 **exit=2** 并打印排查清单，此时应停下来问用户——**不猜、不新建仓库**。

## `.release.json` 格式

```json
{
  "repo": "https://github.com/wpc6666/self-release.git",
  "branch": "main",
  "subdir": ""
}
```

- `repo`：仓库地址，支持 `https://` 与 `git@` 两种写法
- `branch`：默认 `main`；fork 仓库常为 `master`
- `subdir`：skill 在仓库里的相对路径，skill 在仓库根目录就留空或省略

## 接入新 skill

```bash
mkdir -p <skill_dir>/scripts
cp ~/.dsh/skills/self-release/scripts/release.py <skill_dir>/scripts/

cd <skill_dir>
python3 scripts/release.py --init https://github.com/<user>/<repo>.git --subdir "<路径>"
```

同时确认 `manifest.json` 至少有 `id` 和 `version`，最好补 `repository` 作为兜底。

## 环境要求

- Python 3.8+（只用标准库，无第三方依赖）
- `git`
- `gh` CLI（仅 `--verify` 需要，用于查远端 blob）

## 边界与红线

| 情况 | 处理 |
|---|---|
| 找不到仓库地址 | 停下来问用户，不猜、不新建仓库 |
| 本地和 clone 不一致 | 查原因（可能上次漏同步），不强行 `--force` |
| `git push` 报 TLS / `SSL_ERROR_SYSCALL` | GitHub 偶发抖动，直接重试，不改 git 配置 |
| 推送后 raw CDN 还是旧内容 | 正常现象，用 `git ls-remote` + `gh api contents` 验证 |
| 目标目录非空 | 拒绝写入，先问用户 |
| 用户没说要发布 | 只改本地，不提交、不推送、不打 tag |

## 相关项目

- [plot-cjk-config](https://github.com/wpc6666/plot-cjk-config) — macOS 中文绘图配置，R / Python / Stata 三套工具链不出豆腐块
- [dsh-agents](https://github.com/wpc6666/dsh-agents) — 跨工具 AI Agent 全局行为准则

## 许可

[MIT](LICENSE) © 白澤 程
