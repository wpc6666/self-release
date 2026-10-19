# Changelog

本文件记录 `self-release` skill 的所有版本变更。
格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.6.0] - 2026-10-19

### 新增

- **`skill` 短命令**：`~/.local/bin/skill` 薄包装，把
  `python3 ~/.dsh/skills/self-release/scripts/release.py --update X`
  变成 `skill update X`。缺 self-release 时会自动引导安装（第 0 级）。
- `install.sh` 装完后自动把 `skill` 放到 `~/.local/bin/` 并 chmod +x；
  PATH 里没有时给出加 PATH 的提示。
- 子命令：`update` / `update --all` / `install` / `list` / `check` /
  `bump` / `verify` / `init` / `up`。

### 说明

用户不再需要看长路径命令。对 agent 说「更新这个 skill」即可，
agent 按 AGENTS.md 直接跑 `skill update X`。

## [1.6.0] - 2026-10-19

### 变更

- （待补充：本次改动内容）

---

## [1.5.0] - 2026-10-19

### 新增：安装即记住仓库 + 只说名字就能更新

**1. 安装时自动记录仓库坐标**

`--install` 成功后会把仓库写进目标目录的 `.release.json`（新增 `_write_release_json()`）。
以前装完不留坐标，下次要更新还得再问一次仓库地址；现在装完即记住。

新增 `--from-repo URL`：本地没有任何坐标时，直接从指定仓库安装并写入坐标。

```bash
python3 scripts/release.py --install my-skill --from-repo https://github.com/me/repo.git
# ✅ 已记录仓库坐标：~/.dsh/skills/my-skill/.release.json
#    以后说「更新 my-skill」即可，不用再提供链接。
```

**2. 只说名字就能更新，不用先 cd**

`--update` / `--install` 改成可选参数，`--update NAME` 直接按名字定位到 `$DSH_HOME/skills/NAME`：

```bash
python3 scripts/release.py --update cfec-thesis-formatter   # 任意目录下都能跑
```

新增 `_use_skill_dir()` 与 `_skill_dir_by_name()`，切换目录后复用同一套解析逻辑，
不再需要「先 cd 进 skill 目录」这一步。

**3. 按仓库整体更新**

新增 `--update-repo NAME`：解析出该 skill 所属仓库，扫描所有已装 skill，
把坐标相同的全部更新一遍。适用于「一个仓库里放了多个 skill」的情况。

```bash
python3 scripts/release.py --update-repo self-release
# 同仓库的 skill：another, self-release
# ✅ 已更新 2 个 skill（整个仓库）
```

`run_update()` 更新完成后也会重新写一次 `.release.json`，保证坐标不会因覆盖而丢失。

### 修复

- `run_update()` 内部循环变量 `name` 与新增的参数 `name` 同名冲突，已改为 `_fn`
- 找不到 skill 时给出明确提示并返回退出码 1（原先是静默）

---

## [1.4.0] - 2026-10-19

### 新增：一键上架（`scripts/new_repo.py`）

说「把这个 skill 上架」就走完全流程，不用手工建仓库、开 Pages、写网页、改主页：

| 步骤 | 动作 |
|---|---|
| 1 | `gh repo create` 建公开仓库并推送 |
| 2 | 用 `templates/page.html` 套 `manifest.json` 生成 `index.html` |
| 3 | 提交并推送 |
| 4 | `gh api .../pages` 开 GitHub Pages |
| 5 | `gh repo edit` 写 About 描述与 topics |
| 6 | 克隆主页仓库，按分区插入卡片后推送 |

- 默认 **预览模式**，加 `--yes` 才真执行。
- `--no-homepage` / `--no-pages` / `--no-about` 可跳过任一步。
- `--section` 模糊匹配主页分区（学习知识库 / 工具项目 / 其他工具，默认工具项目）。
- 幂等：仓库已存在则跳过创建，Pages 已开则跳过，主页已有卡片则跳过。

### 新增：页面模板（`templates/page.html`）

- 移动端优先：`viewport-fit=cover`、表格横滑容器、`min-width:340px`、768px 与 380px 两档断点。
- 实测 320 / 360 / 375 / 390 / 430 / 768 六档零溢出。

### 说明

`sync.sh audit` **只核查不修复**——发现主页漏卡片只打印提示，不会自己改。要自动补卡片用本版的 `new_repo.py`。

## [1.3.2] - 2026-10-19

### 修复

- **`--update` 与 `--check` 用两套解析逻辑，导致「零配置 skill 装不上也更新不了」**（影响最大）。
  `_remote_coords()` 原来只读 `.release.json` + `manifest.json`，而 `detect_repo()` 有五级解析（含 SKILL.md 正文链接）。
  结果：`--check` 能定位到仓库，`--update` 却报「skill 配置里没有仓库坐标，无法自动更新」。
  实测复现：消费者机器上只有 `cfec-thesis-formatter`（无 `.release.json`，`manifest.json` 无 `repository`，但 SKILL.md 正文有仓库链接）→ `--update` 直接失败。
  现在 `_remote_coords()` 末尾接入 `detect_repo()` 兜底，两条路径共用同一套解析。

- **`run_list()` 同样只读 manifest**：`--list` 里这类 skill 的「仓库」列显示 `—`，agent 读表会以为没有坐标。
  现在同样接入 `detect_repo()` 兜底。

- **`_GH_RE` 前瞻字符集漏了反引号与中文标点**：SKILL.md 里链接常写成 `` `https://github.com/u/r`（main 分支…） ``，
  反引号不在原字符集 `[\s\)\]\"'#?]` 里，正则匹配失败 → 五级兜底的第 5 级形同虚设。
  实测复现：`https://github.com/wpc6666/cfec-thesis-formatter` + 反引号 → 修复前 `❌ None`，修复后正确匹配。
  现在字符集加入 `` ` `` 与 `，。、；：,;:<>|`。

### 影响

修复前，「一句话更新」对**没有 `.release.json` 的第三方 skill 完全不可用**——这正是本功能要解决的核心场景。
修复后实测：零配置的 cfec skill 直接 `--update` 成功拉到 v2.2.0。

---

## [1.3.1] - 2026-10-19

### 修复
- **`--verify` 在 `subdir: ""` 时静默跳过比对**：原判定用 `if cfg.get("subdir")`，空字符串为假 → 走进 `git rev-parse` 分支 → 非 git 目录直接打印"跳过"并 `return 0`（假通过）。现在改为 `if "subdir" in cfg`，`""` 被正确解释为"skill 在仓库根目录"，`rel_dir = "."`。
- 跳过分支补上修复提示，不再只给一句"跳过"。
- 这条 bug 会让「发布前必查」的 blob 比对失效——修好后立刻抓出了本 skill 自己 `release.py` 未推送的真实差异。

## [1.3.0] - 2026-10-19

### 修复
- **`--init` 会把坐标写到 self-release 自己身上**（严重）：`write_release_cfg()` 原来固定用 `SKILL_DIR`，导致 `cd ~/.dsh/skills/X && python3 ~/.dsh/skills/self-release/scripts/release.py --init <url>` 把 X 的坐标覆盖掉 self-release 自己的 `.release.json`。现在按三级优先级解析目标目录：`--target` → cwd（若含 SKILL.md/manifest.json/.release.json）→ `SKILL_DIR`。
- `--init` 新增 `--target` 参数支持。
- 目标目录不存在时报错退出，不再静默创建。
- 覆盖 self-release 自身坐标且新值不同时打印警告，避免手滑。
- 新增 `_warn()` 辅助函数（原来只有 `_err()`）。

### 变更
- SKILL.md 的 `--init` 用法改为三种写法并标出推荐顺序。

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
