# self-release 使用场景

> 上层：`../SKILL.md`；命令：`COMMANDS.md`。

## 四种使用场景

### 场景 0：新电脑，连这个 skill 都还没有（鸡生蛋）

**问题**：没有 `release.py`，就没有任何东西能读坐标。

**解法**：执行 [COMMANDS.md](COMMANDS.md#安装引导) 的 curl
引导。这一步是唯一需要仓库链接的地方，之后永久免链接。

装到 `~/.dsh/skills/self-release/`（可用 `DSH_HOME` 改根目录），并自动写入 `.release.json`。

**agent 处理「我新电脑上啥都没有，装一下 X」时的正确做法**：

1. 先跑上面的 curl 装 self-release（一条命令，幂等，已装则自动转更新）
2. 再 `cd <skills目录>/X && skill init <X的仓库地址>`（或用 `--target <skills目录>/X`）
3. 最后 `skill install X --from-repo <X的仓库地址>`

第 2 步的仓库地址只需提供一次。

### 场景 A：用户说「更新这个 skill」（在本机改代码后发布）

在目标 skill 目录下：

```bash
python3 scripts/release.py --check     # 先定位
python3 scripts/release.py --bump minor
# …按下方「第二步」到「第七步」执行…
```

### 场景 B：用户说「更新 X」——只说名字就够，不用 cd

```bash
skill update X
```

脚本按名字定位到 `$DSH_HOME/skills/X`，读它的 `.release.json` → `git fetch` +
`git reset --hard origin/<branch>` → 保留本地 `.release.json`。

如果那个目录不是 git 仓库（比如当初是拷贝过去的），脚本自动改用 tarball 覆盖下载，效果一样。

**整个仓库一起更新**（一个仓库里放了多个 skill 时）：

```bash
skill update X
```

解析出 X 所属仓库 → 扫描所有已装 skill → 坐标相同的全部更新一遍。

### 场景 C：新机器，本地还没有这个 skill

```bash
skill install X --from-repo https://github.com/<user>/<repo>.git
```

`--from-repo` 装完后**自动把坐标写进目标目录的 `.release.json`**，
之后 `--update X` 一句话即可，不需要再提供链接。

如果连 self-release 本身都还没有，先用场景 0 的 curl 引导命令。

### 命令速查

完整命令、参数与副作用见 [COMMANDS.md](COMMANDS.md#完整-cli)。

### 查看所有 skill 的发布坐标

运行 `python3 scripts/release.py --list`，字段说明见
[COMMANDS.md](COMMANDS.md#查看发布坐标)。

**agent 处理「更新 X」时的正确做法**：先跑 `--list` 查 X 有没有坐标。有 → 直接
`--update X`；没有 → 问用户一次仓库地址，`--init` 或 `--install --from-repo` 钉死，以后就不用再问。
