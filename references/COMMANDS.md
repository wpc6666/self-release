# self-release 命令参考

> 唯一命令定义。用户入口见 `../README.md`，Agent 执行流程见 `../SKILL.md`。

## 安装引导

新电脑上还没有 self-release 时：

```bash
curl -fsSL https://raw.githubusercontent.com/wpc6666/self-release/main/install.sh | bash
```

默认安装到中央 skills 目录；安装器会把实际路径写入
`~/.config/self-release/skills-root`，之后 `skill` 命令与 `release.py` 自动读取。
也可用 `SKILLS_HOME=<skills目录>` 显式指定（`DSH_HOME` 仍兼容）。
安装是幂等的：已安装时转为更新流程，并刷新 `skill` 短命令。

## 日常命令

```bash
skill update X        # 更新某个 skill
skill update --all    # 全部更新
skill list            # 查看版本与发布坐标
skill up --yes        # 上架新 skill
```

## 完整 CLI

| 命令 | 作用 |
|---|---|
| `--check` | 定位仓库、版本、最近 tag 和分支状态 |
| `--bump <patch\|minor\|major>` | 递增版本并同步版本元数据 |
| `--bump <...> --dry-run` | 只预览，不写文件 |
| `--verify` | 比对本地文件与 GitHub 远端 blob |
| `--init URL [--branch B] [--subdir S]` | 写入 `.release.json` 坐标 |
| `--install` | 按当前目录坐标安装 |
| `--install NAME --from-repo URL` | 从指定仓库安装并记录坐标 |
| `--update` | 更新当前目录的 skill |
| `--update NAME` | 只按名称更新 |
| `--update-repo NAME` | 更新该仓库下的全部 skill |
| `--list` | 列出所有已安装 skill 的坐标 |

## 查看发布坐标

```bash
python3 scripts/release.py --list
```

输出包含：skill 名、当前版本、仓库地址、分支和子目录。
如果目标 skill 没有坐标，先 `--init` 一次，之后无需再提供仓库链接。

## `.release.json`

```json
{
  "repo": "https://github.com/wpc6666/self-release.git",
  "branch": "main",
  "subdir": ""
}
```

- `repo`：HTTPS 或 SSH 仓库地址。
- `branch`：默认 `main`，fork 仓库可能为 `master`。
- `subdir`：skill 在仓库中的相对路径；仓库根目录留空。

该文件由 `--install` / `--update` 自动维护，是仓库定位的第一优先级。

## 接入已有 skill

```bash
mkdir -p <skill_dir>/scripts
cp <skills目录>/self-release/scripts/release.py <skill_dir>/scripts/

cd <skill_dir>
python3 scripts/release.py --init https://github.com/<user>/<repo>.git --subdir "<路径>"
```

同时确认目标 skill 至少有 `manifest.json`，并优先提供 `repository` 作为兜底。

## 环境

- Python 3.8+，脚本仅使用标准库。
- `git`。
- `gh` CLI，仅远端 blob 校验需要。
