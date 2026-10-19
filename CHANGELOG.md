# Changelog

本文件记录 `self-release` skill 的所有版本变更。
格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.2.0] - 2026-10-19

### 新增
- `install.sh` 引导安装器：新电脑上还没有本 skill 时，一条 `curl ... | bash` 即可装好并自动写入 `.release.json`。解决"鸡生蛋"问题——没有 `release.py` 就没东西能读坐标。
- `install.sh` 幂等：检测到已安装时自动转为更新流程；目标目录非空时先备份为 `.bak.<时间戳>`。
- `install.sh` 三级下载兜底：curl tarball → `gh api` tarball（私有仓库）→ `git clone`。
- SKILL.md 新增「场景 0：新电脑，连这个 skill 都还没有」与「『一句话更新』到底怎么成立的」两节，明确三级兜底机制与「链接只需提供一次」的准确含义。
- `manifest.json` 的 `install` 字段补充 `command` 与 `alt_command`。

### 变更
- SKILL.md 场景数从三种改为四种（新增场景 0）。
- `manifest.json` 版本与 SKILL.md frontmatter 同步至 `1.2.0`。

## [1.1.0] - 2026-10-19

### 新增
- `--install`：按 skill 自带的 `.release.json` 坐标安装，支持仓库根目录与子目录两种布局。
- `--update`：按坐标拉取最新版本，自动区分 git 仓库（`fetch` + `reset --hard`）与非 git 目录（tarball 覆盖）两条路径；更新时保留本地 `.release.json`，不覆盖用户钉死的坐标。
- `--list`：列出 `~/.dsh/skills/` 下所有 skill 的版本与发布坐标，agent 处理「更新 X」时先查这张表。
- `manifest.json`：补齐 `id` / `repository` / `homepage` / `install` / `tags` 等字段，作为 `.release.json` 缺失时的兜底来源。
- SKILL.md 新增「核心机制：坐标写在 skill 自己身上」与「三种使用场景」两节，明确 A（发布）/B（更新）/C（新装）三条路径。

### 修复
- 脚本缺 `import io`，导致 `--list` 读 `manifest.json` 时静默抛异常、版本号全部显示为 `?`。
- `manifest.json` 缺失时 `_remote_coords()` 未回退到目录名推导 skill id。

### 变更
- SKILL.md frontmatter 版本与一级标题同步至 `1.1.0`。
- 定位优先级文档补齐 `.release.json` 为第一顺位（原文档遗漏）。

## [1.0.0] - 2026-10-19

### 新增
- 初版。四级自动定位（`.release.json` → `.git/config` → 向上 6 层 `.git` → `manifest.json` → SKILL.md 链接）。
- 三级版本解析（`manifest.json` → SKILL.md frontmatter → 一级标题）。
- `--check` / `--bump` / `--verify` / `--init` 四个子命令。
- 发布七步流程：定位 → 递增版本 → 本地验证 → 同步 clone → 提交推送 → 打 tag → 汇报。
