---
name: self-release
version: 1.4.0
description: 当用户说「更新这个 skill / 发布这个 skill / 上架 / 上线 / 打个 tag 推上去」时使用。自动定位 GitHub 仓库、当前版本与分支，完成版本递增（三处元数据同步）→ 验证 → 提交推送 → 打 tag；也支持一键上架：建公开仓库 → 开 GitHub Pages → 生成手机适配的说明页 → 写入 About → 自动在主页加卡片。按 skill 自带坐标一键安装/更新，无需用户提供仓库地址或版本号。
license: MIT
---

# Skill 自更新与发布

用户说一句「更新这个 skill」或「更新 X」，就能走完从改代码到打 tag 推送的全流程。**不需要用户提供仓库地址、版本号、分支名。**

## 一句话流程

```
定位 → 递增版本 → 本地验证 → 同步 clone → 提交推送 → 打 tag → 汇报
```

## 核心机制：坐标写在 skill 自己身上

**这是本 skill 存在的原因。** 发布过的 skill 把仓库坐标钉在自己的 `.release.json` 里，任何机器装上后，agent 读配置就知道去哪拉更新——**用户永远不需要记住或粘贴原始链接。**

```
skill 目录/
├── .release.json      ← 仓库坐标（repo / branch / subdir），发布时写入
├── manifest.json      ← 版本号权威来源 + repository 兜底字段
├── SKILL.md           ← frontmatter version 兜底
└── scripts/release.py ← 读配置，执行安装/更新/发布
```

`.release.json` 长这样：

```json
{
  "repo": "https://github.com/wpc6666/self-release.git",
  "branch": "main",
  "subdir": ""
}
```

`subdir` 是 skill 在仓库里的相对路径；skill 在仓库根目录就留空。

---

## 四种使用场景

### 场景 0：新电脑，连这个 skill 都还没有（鸡生蛋）

**问题**：没有 `release.py`，就没有任何东西能读坐标。

**解法**：一条 curl 引导命令。这一步是唯一需要"链接"的地方，之后永久免链接。

```bash
curl -fsSL https://raw.githubusercontent.com/wpc6666/self-release/main/install.sh | bash
```

装到 `~/.dsh/skills/self-release/`（可用 `DSH_HOME` 改根目录），并自动写入 `.release.json`。

**agent 处理「我新电脑上啥都没有，装一下 X」时的正确做法**：

1. 先跑上面的 curl 装 self-release（一条命令，幂等，已装则自动转更新）
2. 再 `python3 ~/.dsh/skills/self-release/scripts/release.py --init <X的仓库地址>`
3. 最后 `--install --target ~/.dsh/skills/X`

第 2 步的仓库地址只需提供一次。

### 场景 A：用户说「更新这个 skill」（在本机改代码后发布）

在目标 skill 目录下：

```bash
python3 scripts/release.py --check     # 先定位
python3 scripts/release.py --bump minor
# …按下方「第二步」到「第七步」执行…
```

### 场景 B：用户说「更新 X」（别的机器上，本地已有该 skill）

**一句话搞定，不需要链接：**

```bash
cd ~/.dsh/skills/X
python3 scripts/release.py --update
```

脚本读 `.release.json` → `git fetch` + `git reset --hard origin/<branch>` → 保留本地 `.release.json`。

如果那个目录不是 git 仓库（比如当初是拷贝过去的），脚本自动改用 tarball 覆盖下载，效果一样。

### 场景 C：新机器，本地还没有这个 skill

```bash
# 先拿到 release.py（从本仓库或任一已有副本）
git clone https://github.com/wpc6666/self-release.git /tmp/sr
cd /tmp/sr && python3 scripts/release.py --install --target ~/.dsh/skills/X
```

但注意：`--install` 读的是**当前目录**的 `.release.json`。所以更常见的是——用户说「装一下 X」，agent 先确认 X 的仓库地址（一次），`--init` 钉死坐标后再 `--install`。**坐标只需提供一次，之后永久免链接。**

### 查看所有 skill 的发布坐标

```bash
python3 scripts/release.py --list
```

输出：

```
== 已装 skill 与发布坐标 ==
skill                 版本   仓库                                               分支/子目录
cfec-thesis-formatter 2.2.0  https://github.com/wpc6666/cfec-thesis-formatter.git main / 重财-论文格式规范
self-release          1.1.0  https://github.com/wpc6666/self-release.git         main
```

**agent 处理「更新 X」时的正确做法**：先跑 `--list` 查 X 有没有坐标。有 → 直接 `--update`；没有 → 问用户一次仓库地址，`--init` 钉死，以后就不用再问。

---

## 第一步：定位（发布前必须最先做）

在目标 skill 目录下执行：

```bash
python3 scripts/release.py --check
```

输出形如：

```
== 自动定位结果 ==
GitHub 仓库 : https://github.com/wpc6666/<repo>.git
本地 skill  : /Users/.../.dsh/skills/<name>
当前版本    : v2.2.0（manifest.json 单一权威来源）
最近 tag    : v2.2.0
HEAD        : 9ebe462 feat: ...
本地状态    : main 与 origin/main 同步
```

**如果 `--check` 报错或脚本不存在**，按下面的兜底顺序手工定位：

1. **仓库地址**，按优先级找：
   - `.release.json` 的 `repo`（最优先，钉死后永不再猜）
   - skill 目录下 `.git/config` 的 `[remote "origin"]` url
   - 向上最多 6 层找 `.git`（skill 在仓库子目录时）
   - `manifest.json` 的 `repository` / `homepage` 字段
   - `SKILL.md` 正文里第一个 `https://github.com/<user>/<repo>` 链接
   - 都找不到 → **停下来问用户**，不要猜
2. **当前版本**，按优先级找：
   - `manifest.json` 的 `version`
   - `SKILL.md` frontmatter 的 `version:`
   - `SKILL.md` 一级标题里的 `vX.Y.Z`
3. **最近 tag**：`git -C <skill_dir> tag --sort=-version:refname | head -1`
4. **分支名**：`git -C <skill_dir> branch --show-current`（注意 fork 仓库常是 `master` 不是 `main`）

> ⚠️ **分支名陷阱**：`wpc6666/AutoBuildImmortalWrt` 是 fork，默认分支是 `master`。直接 `git push origin main` 会报 `src refspec main does not match any`。推送前先 `git ls-remote --symref origin HEAD` 确认。

## 第二步：递增版本

语义化版本 `X.Y.Z`：

| 类型 | 何时用 | 命令 |
|---|---|---|
| `patch` | 只修 bug，行为不变 | `--bump patch` |
| `minor` | 新增向后兼容功能 | `--bump minor` |
| `major` | 破坏性变更 | `--bump major` |

```bash
python3 scripts/release.py --bump minor --dry-run   # 先预览
python3 scripts/release.py --bump minor             # 真写入
```

脚本会**同步三处**：`SKILL.md`（frontmatter + 一级标题）、`manifest.json`、`CHANGELOG.md`（插入新条目）。

> **必须手工补 CHANGELOG 的条目内容**。脚本只生成占位 `- （待补充）`。

## 第三步：本地验证（不允许跳过）

```bash
# Python 脚本语法
python3 -m py_compile scripts/*.py

# 实际跑一遍最小用例（按 skill 而定）
```

**红线**：没真跑过的验证，汇报时必须写「未运行」，不能暗示通过。

## 第四步：同步本地 ↔ 仓库 clone

这是最容易漏的一步。本地 skill 目录和仓库 clone 是**两份独立文件**，不改 clone 等于没发布。

```bash
REPO=/tmp/<repo>-sync
[ -d "$REPO" ] || git clone --depth 1 <repo_url> "$REPO"
# 把本地改动同步过去（注意仓库里 skill 可能在子目录）
rsync -a --delete --exclude '.git' --exclude '__pycache__' \
  <skill_dir>/ "$REPO/<skill_subdir>/"

# 必须一字不差
diff -r --exclude '__pycache__' <skill_dir> "$REPO/<skill_subdir>"
```

`diff -r` 无输出才算过。

## 第五步：提交推送

```bash
cd "$REPO"
git add -A
git -c user.name="白澤 程" \
    -c user.email="87405429+wpc6666@users.noreply.github.com" \
    commit -m "<type>: <一句话>"
git push origin <branch>
```

**署名硬要求**：必须用上面的 name/email。邮箱换成占位地址 GitHub 认不出账号，贡献图不会变绿。

提交前自查：

```bash
git config user.email | grep -q wpc6666 || echo "邮箱不对，需修正"
```

`<type>` 取 `feat` / `fix` / `docs` / `style` / `refactor` / `test` / `chore`。

## 第六步：打 tag

```bash
git tag -a "v<新版本>" -m "v<新版本>"
git push origin "v<新版本>"
```

**先确认推送真的成功**，不要依赖 `raw.githubusercontent.com`（有 CDN 缓存，推送后 60 秒仍可能返回旧内容）：

```bash
git ls-remote origin <branch>          # 远端 commit
git rev-parse --short HEAD             # 本地 commit，两者必须一致

git hash-object <file>                 # 本地 blob
gh api repos/<user>/<repo>/contents/<path> --jq '.sha'   # 远端 blob，必须一致
```

## 第七步：汇报（五项，缺一不可）

1. **做了什么**
2. **改了哪些文件**（完整路径）
3. **跑了哪些验证**（具体命令 + 真实结果）
4. **哪些没验**（没跑就写「未运行」）
5. **剩余风险 / 待办**

---

## 一键上架（新 skill 从零到能访问）

用户说「把这个 skill 上架 / 发布到 GitHub / 上线」，跑：

```bash
cd <skill目录>
python3 <self-release>/scripts/new_repo.py --dry-run    # 先看要做什么
python3 <self-release>/scripts/new_repo.py --yes        # 真执行
```

**六步全自动**：

| 步 | 动作 | 幂等行为 |
|---|---|---|
| 1 | `gh repo create` 建公开仓库并推送 | 仓库已存在则跳过 |
| 2 | 套 `templates/page.html` 生成 `index.html` | 每次重新生成 |
| 3 | 提交并推送 | 无改动则跳过提交 |
| 4 | `gh api .../pages` 开 Pages | 已开则跳过 |
| 5 | `gh repo edit` 写 About + topics | 覆盖式更新 |
| 6 | 克隆主页仓库插入卡片并推送 | 已有卡片则跳过 |

**可选参数**：

| 参数 | 作用 |
|---|---|
| `--dry-run`（默认） | 只打印将要执行的命令，不改任何东西 |
| `--yes` | 真正执行 |
| `--no-homepage` | 跳过主页卡片（不想动公开主页时用） |
| `--no-pages` / `--no-about` | 跳过开 Pages / 写 About |
| `--section 学习知识库` | 指定主页分区，默认「工具项目」 |

**前置条件**：`gh auth status` 通过；skill 目录里有 `manifest.json`（提供 id / name / description / version / tags）。

> ⚠️ **`sync.sh audit` 只核查不修复**。它发现主页漏卡片只会打印「补主页卡片：编辑 ... 后 push」，不会自己改。要自动补用 `new_repo.py`。

## 「一句话更新」到底怎么成立的

用户说「更新 X」，agent 不需要问任何东西，靠的是**三级兜底**：

| 级别 | 前提 | agent 动作 |
|---|---|---|
| 1 | `~/.dsh/skills/X/.release.json` 存在 | `cd X && python3 scripts/release.py --update` |
| 2 | 只有 `manifest.json` 的 `repository` | 同上（`_remote_coords()` 自动回退读 manifest） |
| 3 | 什么坐标都没有 | **问用户一次**仓库地址 → `--init` 钉死 → 之后永久免问 |

所以「不需要原始链接」的准确含义是：**链接只需提供一次，之后写进 skill 自己的配置，永远不用再提供。**

而新电脑上连 self-release 都没有时，用 `install.sh` 这条 curl 引导命令破局——那是唯一一次需要记住 URL 的地方。

### 让别的 skill 也能一句话更新

每个要接入的 skill 跑一次：

```bash
cd ~/.dsh/skills/X
python3 ~/.dsh/skills/self-release/scripts/release.py --init https://github.com/<user>/<repo>.git --subdir "<路径>"
```

`--init` 写 `.release.json`，之后 `--update` / `--list` 全部自动。

---

## 新 skill 接入自动化

```bash
mkdir -p <skill_dir>/scripts
cp ~/.dsh/skills/self-release/scripts/release.py <skill_dir>/scripts/

# 钉死坐标（只需一次）
cd <skill_dir>
python3 scripts/release.py --init https://github.com/<user>/<repo>.git \
                           --subdir "<skill 在仓库里的路径，根目录留空>"
```

`--init` 写入 `.release.json`，之后 `--check` / `--update` / `--list` 全部自动，不再需要用户提供链接。

同时确认 `manifest.json` 里至少有 `id`、`version`，最好补上 `repository` 作为兜底。

---

## 边界与红线

| 情况 | 处理 |
|---|---|
| 找不到仓库地址 | **停下来问用户**，不要猜，不要新建仓库 |
| 本地和 clone 不一致 | 停下来查原因（可能是上次漏同步），不要强行 `--force` |
| `git push` 报 TLS / `SSL_ERROR_SYSCALL` | GitHub 偶发抖动，直接重试，不要改 git 配置 |
| 推送后 raw CDN 还是旧内容 | 正常现象，用 `git ls-remote` + `gh api contents` 验证 |
| 目标目录非空 | 拒绝写入（防误覆盖），先问用户 |
| 用户没说要发布 | 只改本地，**不提交、不推送、不打 tag** |
| `--update` 会丢本地改动 | 脚本只保留 `.release.json`，其余按远端覆盖。有未提交改动先提醒用户 |

## 与仓库发布流程的关系

**任何 skill 的发布都走这套流程。** 若发布的是仓库本身的 README / index.html / Pages，另见 `AGENTS.md` 的「仓库维护」章节。
