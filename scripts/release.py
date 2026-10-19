#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill 自更新与发布辅助脚本（release.py）—— 通用版
==================================================

用途：当用户说「更新 / 发布这个 skill」时，自动定位 GitHub 仓库与当前版本，
辅助完成一次标准发布：

    改代码 → 版本递增（SKILL.md / manifest.json / CHANGELOG 三处同步）
         → 本地验证 → 同步本地 skill 与仓库 clone → 提交推送 → 打 tag

本脚本不绑定任何特定项目，全部按约定自动解析：

  仓库地址  ① skill 目录 .git/config 的 remote origin url
            ② manifest.json 的 repository / homepage 字段
            ③ SKILL.md 正文中第一个 github.com 链接
  当前版本  ① manifest.json 的 version（首选权威来源）
            ② SKILL.md frontmatter 的 version:
            ③ SKILL.md 一级标题里的 vX.Y.Z
  分支名    git branch --show-current（fork 仓库常为 master）

用法：
    python3 scripts/release.py --check                  # 定位：仓库、版本、tag、分支状态
    python3 scripts/release.py --bump patch             # 递增版本并同步三处文件
    python3 scripts/release.py --bump minor --dry-run   # 只预览，不写文件
    python3 scripts/release.py --verify                 # 一致性检查（本地 vs 远端 blob）
    python3 scripts/release.py --install                # 按配置坐标安装（新机器）
    python3 scripts/release.py --update                 # 按配置坐标拉最新
    python3 scripts/release.py --list                   # 列出所有 skill 的发布坐标
"""

import io
import os
import re
import sys
import json
import datetime
import subprocess
import argparse

AUTHOR_NAME = "白澤 程"
AUTHOR_EMAIL = "87405429+wpc6666@users.noreply.github.com"

# skill 根目录解析：
#   ① 显式环境变量 RELEASE_SKILL_DIR（最高优先）
#   ② 当前工作目录（若里面有 SKILL.md 或 manifest.json）——支持「cd 到目标 skill 再跑别的副本」
#   ③ 脚本所在位置的上一级（本文件位于 <skill_root>/scripts/release.py）
def _resolve_skill_dir():
    env = os.environ.get("RELEASE_SKILL_DIR")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    cwd = os.getcwd()
    for marker in ("SKILL.md", "manifest.json", ".release.json"):
        if os.path.isfile(os.path.join(cwd, marker)):
            return cwd
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


SKILL_DIR = _resolve_skill_dir()
MANIFEST_JSON = os.path.join(SKILL_DIR, "manifest.json")
SKILL_MD = os.path.join(SKILL_DIR, "SKILL.md")
CHANGELOG_MD = os.path.join(SKILL_DIR, "CHANGELOG.md")

_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
_GH_RE = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+?(?:\.git)?(?=[\s\)\]\"'#?]|$)")


def _err(msg):
    sys.stderr.write("错误: %s\n" % msg)
    sys.exit(1)


def _warn(msg):
    sys.stderr.write("警告: %s\n" % msg)


def _run(cmd, cwd=None, quiet=True):
    """跑命令，返回 (rc, stdout, stderr)。"""
    try:
        p = subprocess.run(
            cmd, cwd=cwd or SKILL_DIR,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=20,
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


# ----------------------------------------------------------
#  自动定位：仓库
# ----------------------------------------------------------
def _read_release_cfg():
    """读 .release.json（可选）：一次性钉死仓库/分支/子目录。"""
    path = os.path.join(SKILL_DIR, ".release.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def detect_repo():
    """按四级优先级解析 GitHub 仓库地址，找不到返回 None。"""
    # ⓿ .release.json 显式配置（最优先，钉死后永不再猜）
    cfg = _read_release_cfg()
    if cfg.get("repo"):
        return cfg["repo"], ".release.json 显式配置"

    # ① .git/config 的 remote origin
    git_cfg = os.path.join(SKILL_DIR, ".git", "config")
    if os.path.isfile(git_cfg):
        rc, out, _ = _run(["git", "config", "--get", "remote.origin.url"])
        if rc == 0 and out:
            return out, ".git/config"

    # 向上找最近一层 .git（skill 可能在仓库子目录）
    probe = SKILL_DIR
    for _ in range(6):
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        git_cfg2 = os.path.join(parent, ".git", "config")
        if os.path.isfile(git_cfg2):
            rc, out, _ = _run(["git", "config", "--get", "remote.origin.url"], cwd=parent)
            if rc == 0 and out:
                return out, ".git/config（上级目录 %s）" % parent
        probe = parent

    # ② manifest.json 的 repository / homepage
    if os.path.isfile(MANIFEST_JSON):
        try:
            with open(MANIFEST_JSON, encoding="utf-8") as f:
                data = json.load(f)
            for key in ("repository", "homepage", "repo", "url"):
                val = data.get(key)
                if isinstance(val, str) and "github.com" in val:
                    return val, "manifest.json 的 %s 字段" % key
                if isinstance(val, dict):
                    u = val.get("url", "")
                    if "github.com" in u:
                        return u, "manifest.json 的 %s.url 字段" % key
        except Exception:
            pass

    # ③ SKILL.md 正文第一个 github 链接
    if os.path.isfile(SKILL_MD):
        try:
            with open(SKILL_MD, encoding="utf-8") as f:
                text = f.read()
            m = _GH_RE.search(text)
            if m:
                return m.group(0).rstrip("."), "SKILL.md 正文链接"
        except Exception:
            pass

    return None, "未找到"


# ----------------------------------------------------------
#  自动定位：版本
# ----------------------------------------------------------
def detect_version():
    """按三级优先级解析版本号，返回 (version, 来源)。"""
    if os.path.isfile(MANIFEST_JSON):
        try:
            with open(MANIFEST_JSON, encoding="utf-8") as f:
                v = json.load(f).get("version", "")
            if _VERSION_RE.fullmatch(v):
                return v, "manifest.json"
        except Exception:
            pass

    if os.path.isfile(SKILL_MD):
        with open(SKILL_MD, encoding="utf-8") as f:
            text = f.read()
        m = re.search(r"(?m)^version:\s*(\d+\.\d+\.\d+)\s*$", text)
        if m:
            return m.group(1), "SKILL.md frontmatter"
        m = re.search(r"(?m)^#.*?v(\d+\.\d+\.\d+)\s*$", text)
        if m:
            return m.group(1), "SKILL.md 一级标题"

    _err("无法解析版本号：manifest.json 无 version，SKILL.md 也无 frontmatter version / 标题版本")


def _bump_version(current, part):
    major, minor, patch = (int(x) for x in current.split("."))
    if part == "major":
        return "%d.0.0" % (major + 1)
    if part == "minor":
        return "%d.%d.0" % (major, minor + 1)
    if part == "patch":
        return "%d.%d.%d" % (major, minor, patch + 1)
    _err("未知的递增类型: %r（可选 major/minor/patch）" % part)


# ----------------------------------------------------------
#  三处文件同步
# ----------------------------------------------------------
def _patch_skill_md(new_version):
    if not os.path.isfile(SKILL_MD):
        return None, None
    with open(SKILL_MD, encoding="utf-8") as f:
        before = f.read()
    text = before
    # frontmatter version
    text = re.sub(r"(?m)^version:\s*\d+\.\d+\.\d+\s*$",
                  "version: %s" % new_version, text, count=1)
    # 一级标题里的 vX.Y.Z（做了才改，避免误伤）
    text = re.sub(r"(?m)^(#[^\n]*?)v\d+\.\d+\.\d+", r"\g<1>v%s" % new_version,
                  text, count=1)
    return before, text


def _patch_manifest(new_version):
    if not os.path.isfile(MANIFEST_JSON):
        return None, None
    with open(MANIFEST_JSON, encoding="utf-8") as f:
        data = json.load(f)
    data["version"] = new_version
    return ("(旧 version=%s)" % data.get("version", "?")), \
           json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _patch_changelog(new_version):
    if not os.path.isfile(CHANGELOG_MD):
        return None, None
    with open(CHANGELOG_MD, encoding="utf-8") as f:
        text = f.read()
    today = datetime.date.today().strftime("%Y-%m-%d")
    entry = (
        "## [%s] - %s\n\n"
        "### 变更\n\n"
        "- （待补充：本次改动内容）\n\n"
        "---\n\n" % (new_version, today)
    )
    m = re.search(r"(?m)^##\s*\[", text)
    if m:
        return text, text[:m.start()] + entry + text[m.start():]
    return text, text.rstrip("\n") + "\n\n" + entry


def apply_bump(part, dry_run=False):
    current, src = detect_version()
    new = _bump_version(current, part)
    print("当前版本  : v%s  （来源：%s）" % (current, src))
    print("新版本    : v%s  （%s 递增）" % (new, part))
    print("本地 skill: %s" % SKILL_DIR)
    print()

    targets = []
    for name, path, fn in (
        ("SKILL.md", SKILL_MD, _patch_skill_md),
        ("manifest.json", MANIFEST_JSON, _patch_manifest),
        ("CHANGELOG.md", CHANGELOG_MD, _patch_changelog),
    ):
        before, after = fn(new)
        if before is None:
            print("  %-14s 不存在，跳过" % name)
            continue
        targets.append((name, path, before, after))

    for name, path, before, after in targets:
        changed = (before != after)
        print("  %-14s %s" % (name, "→ v%s" % new if changed else "无变化（可能已是该版本）"))
        if changed and not dry_run:
            with open(path, "w", encoding="utf-8") as f:
                f.write(after)

    if dry_run:
        print("\n[dry-run] 未写入任何文件。去掉 --dry-run 后真正写入。")
    else:
        print("\n完成。记得手工补 CHANGELOG 的条目内容（脚本只生成占位）。")
    return new


# ----------------------------------------------------------
#  --check
# ----------------------------------------------------------
def run_check():
    repo, repo_src = detect_repo()
    version, ver_src = detect_version()

    print("== 自动定位结果 ==")
    print("本地 skill  : %s" % SKILL_DIR)
    print("GitHub 仓库 : %s" % (repo or "❌ 未找到（需要手工确认）"))
    if repo:
        print("              （来源：%s）" % repo_src)
    print("当前版本    : v%s" % version)
    print("              （来源：%s）" % ver_src)

    # git 状态
    rc, branch, _ = _run(["git", "branch", "--show-current"])
    if rc == 0 and branch:
        print("当前分支    : %s" % branch)
    else:
        print("当前分支    : （非 git 仓库）")

    rc, tag, _ = _run(["git", "tag", "--sort=-version:refname"])
    if rc == 0:
        tags = [t for t in tag.splitlines() if t]
        print("最近 tag    : %s" % (tags[0] if tags else "（无 tag）"))

    rc, head, _ = _run(["git", "log", "-1", "--format=%h %s"])
    if rc == 0 and head:
        print("HEAD        : %s" % head)

    rc, status, _ = _run(["git", "status", "--porcelain"])
    if rc == 0:
        dirty = [l for l in status.splitlines() if l.strip()]
        print("工作区      : %s" % ("干净" if not dirty else "%d 个改动未提交" % len(dirty)))

    # 与远端同步状态
    if branch:
        rc, local, _ = _run(["git", "rev-parse", branch])
        rc2, remote, _ = _run(["git", "rev-parse", "origin/%s" % branch])
        if rc == 0 and rc2 == 0:
            print("同步状态    : %s" % ("与 origin 一致" if local == remote
                                        else "本地 %s / 远端 %s" % (local[:7], remote[:7])))

    print()
    if not repo:
        print("⚠️  未定位到仓库地址。按优先级检查：")
        print("   1. .git/config 的 [remote \"origin\"] url")
        print("   2. manifest.json 的 repository / homepage 字段")
        print("   3. SKILL.md 正文第一个 github.com 链接")
        print("   都找不到 → 停下来问用户，不要猜，不要新建仓库。")
    return 0 if repo else 2


def write_release_cfg(repo, branch=None, subdir=None, target=None):
    """写 .release.json，把仓库坐标钉死，之后自动定位不再靠猜。

    目标目录优先级：
      1. --target 显式指定
      2. cwd（若 cwd 有 SKILL.md / manifest.json / .release.json，且不是本脚本所在目录）
      3. SKILL_DIR（本脚本所在 skill）

    这样 `cd ~/.dsh/skills/X && python3 ~/.dsh/skills/self-release/scripts/release.py --init <url>`
    会正确写到 X，不会把 self-release 自己的坐标覆盖掉。
    """
    data = {"repo": repo}
    if branch:
        data["branch"] = branch
    if subdir:
        data["subdir"] = subdir

    dest = None
    if target:
        dest = os.path.abspath(os.path.expanduser(target))
    else:
        cwd = os.getcwd()
        if os.path.abspath(cwd) != os.path.abspath(SKILL_DIR):
            for marker in ("SKILL.md", "manifest.json", ".release.json"):
                if os.path.isfile(os.path.join(cwd, marker)):
                    dest = cwd
                    break
    if dest is None:
        dest = SKILL_DIR

    if not os.path.isdir(dest):
        _err("目标目录不存在：%s" % dest)
        return 1

    path = os.path.join(dest, ".release.json")
    # 防止手滑覆盖 self-release 自己的坐标
    if os.path.abspath(dest) == os.path.abspath(SKILL_DIR):
        cur = None
        if os.path.isfile(path):
            try:
                cur = json.load(io.open(path, encoding="utf-8")).get("repo")
            except Exception:
                cur = None
        if cur and cur != repo:
            _warn("注意：正在改写本 skill（self-release）自身的坐标：")
            _warn("  原 %s" % cur)
            _warn("  新 %s" % repo)
            _warn("  如果本意是给别的 skill 钉坐标，请先 cd 到那个目录，或用 --target。")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("已写入 %s" % path)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


# ----------------------------------------------------------
#  --install / --update：按 manifest 坐标安装或更新 skill
# ----------------------------------------------------------
SKILLS_ROOT = os.path.join(
    os.environ.get("DSH_HOME", os.path.join(os.path.expanduser("~"), ".dsh")),
    "skills")


def _remote_coords():
    """从 .release.json 或 manifest.json 解析 (repo, branch, subdir, skill_id)。

    这是「不需要原始链接就能更新」的核心：坐标写死在 skill 自己的配置里。
    """
    cfg = _read_release_cfg()
    repo = cfg.get("repo")
    branch = cfg.get("branch") or "main"
    subdir = cfg.get("subdir") or ""
    skill_id = None

    if os.path.isfile(MANIFEST_JSON):
        try:
            with io.open(MANIFEST_JSON, encoding="utf-8") as f:
                data = json.load(f)
            skill_id = data.get("id")
            if not repo:
                for k in ("repository", "homepage", "repo", "url"):
                    v = data.get(k)
                    if isinstance(v, str) and "github.com" in v:
                        repo = v
                        break
                    if isinstance(v, dict) and "github.com" in v.get("url", ""):
                        repo = v["url"]
                        break
            inst = data.get("install") or {}
            if isinstance(inst, dict):
                if inst.get("target") and not skill_id:
                    skill_id = os.path.basename(inst["target"].rstrip("/"))
        except Exception:
            pass

    if not skill_id:
        skill_id = os.path.basename(SKILL_DIR)
    return repo, branch, subdir, skill_id


def _normalize_repo(repo):
    """把各种写法的仓库地址规整成 https 形式。"""
    r = (repo or "").strip()
    if r.startswith("git@"):
        r = r.replace(":", "/", 1).replace("git@", "https://", 1)
    if not r.endswith(".git"):
        r = r.rstrip("/") + ".git"
    return r


def run_install(target=None):
    """从 skill 配置里的坐标安装（或修复）本 skill。"""
    repo, branch, subdir, skill_id = _remote_coords()
    if not repo:
        _err("skill 配置里没有仓库坐标（.release.json 的 repo 或 manifest.json 的 repository），"
             "无法自动安装。请先跑 --init <repo_url> 钉死坐标。")

    dest = os.path.expanduser(target) if target else os.path.join(SKILLS_ROOT, skill_id)
    url = _normalize_repo(repo)

    print("== 自动安装 ==")
    print("仓库   : %s" % url)
    print("分支   : %s" % branch)
    print("子目录 : %s" % (subdir or "(根目录)"))
    print("目标   : %s" % dest)
    print()

    if os.path.isdir(os.path.join(dest, ".git")):
        print("目标已是 git 仓库，改用更新流程。")
        return run_update(target=dest)

    parent = os.path.dirname(dest)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)

    if os.path.isdir(dest) and os.listdir(dest):
        _err("目标目录已存在且非空：%s\n请先备份或指定 --target" % dest)

    rc, out, err = _run(["git", "clone", "--depth", "1",
                         "--branch", branch, url, dest], cwd=parent or ".")
    if rc != 0:
        _err("git clone 失败：%s" % (err or out))

    if subdir:
        # skill 在仓库子目录：把子目录内容上移
        sub = os.path.join(dest, subdir)
        if not os.path.isdir(sub):
            _err("仓库里找不到子目录 %s" % subdir)
        for name in os.listdir(sub):
            src_p = os.path.join(sub, name)
            dst_p = os.path.join(dest, name)
            if os.path.exists(dst_p):
                continue
            os.rename(src_p, dst_p)

    print("✅ 已安装到 %s" % dest)
    return 0


def run_update(target=None, keep_local=None):
    """按 skill 配置里的坐标拉取最新版本。

    keep_local 里的文件名会被保留（默认保留 .release.json）。
    """
    repo, branch, subdir, skill_id = _remote_coords()
    if not repo:
        _err("skill 配置里没有仓库坐标，无法自动更新。")

    dest = os.path.expanduser(target) if target else SKILL_DIR
    url = _normalize_repo(repo)
    keep = set(keep_local or [".release.json"])

    print("== 自动更新 ==")
    print("仓库 : %s" % url)
    print("分支 : %s" % branch)
    print("目录 : %s" % dest)
    print()

    if not os.path.isdir(dest):
        _err("目标目录不存在：%s（先跑 --install）" % dest)

    # 备份要保留的本地文件
    saved = {}
    for name in keep:
        fp = os.path.join(dest, name)
        if os.path.isfile(fp):
            with io.open(fp, encoding="utf-8") as f:
                saved[name] = f.read()

    if os.path.isdir(os.path.join(dest, ".git")):
        rc, out, err = _run(["git", "fetch", "--depth", "1", "origin", branch], cwd=dest)
        if rc != 0:
            _err("git fetch 失败：%s" % (err or out))
        rc, out, err = _run(["git", "reset", "--hard", "origin/" + branch], cwd=dest)
        if rc != 0:
            _err("git reset 失败：%s" % (err or out))
    else:
        # 非 git 目录：下载 tarball 覆盖
        import tempfile, tarfile, shutil, urllib.request
        tmpd = tempfile.mkdtemp()
        tgz = os.path.join(tmpd, "s.tgz")
        dl = url.replace(".git", "").replace("https://github.com/",
                                             "https://api.github.com/repos/") + "/tarball/" + branch
        try:
            urllib.request.urlretrieve(dl, tgz)
        except Exception as e:
            _err("下载失败：%s（私有仓库请先 gh auth login）" % e)
        with tarfile.open(tgz, "r:gz") as tf:
            tf.extractall(tmpd)
        roots = [d for d in os.listdir(tmpd) if os.path.isdir(os.path.join(tmpd, d))]
        if not roots:
            _err("压缩包结构异常")
        srcroot = os.path.join(tmpd, roots[0])
        if subdir:
            srcroot = os.path.join(srcroot, subdir)
        for name in os.listdir(srcroot):
            s = os.path.join(srcroot, name)
            d = os.path.join(dest, name)
            if os.path.isdir(s):
                if os.path.isdir(d):
                    shutil.rmtree(d)
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
        shutil.rmtree(tmpd, ignore_errors=True)

    # 还原保留文件
    for name, content in saved.items():
        with io.open(os.path.join(dest, name), "w", encoding="utf-8") as f:
            f.write(content)

    # 版本号：优先 manifest.json，其次 git rev-parse
    ver = None
    mp = os.path.join(dest, "manifest.json")
    if os.path.isfile(mp):
        try:
            with io.open(mp, encoding="utf-8") as f:
                ver = (json.load(f) or {}).get("version")
        except Exception:
            pass
    if not ver:
        rc, out, _ = _run(["git", "rev-parse", "--short", "HEAD"], cwd=dest)
        ver = out.strip() or "(未知)"

    print("✅ 已更新到 v%s" % ver if ver and ver[0].isdigit() else "✅ 已更新到 %s" % ver)
    print("   保留的本地文件：%s" % (", ".join(sorted(keep)) if keep else "无"))
    return 0


def run_list():
    """列出所有已装 skill 及其配置的仓库坐标。"""
    if not os.path.isdir(SKILLS_ROOT):
        _err("skills 目录不存在：%s" % SKILLS_ROOT)
    rows = []
    for name in sorted(os.listdir(SKILLS_ROOT)):
        d = os.path.join(SKILLS_ROOT, name)
        if not os.path.isdir(d) or name.startswith("."):
            continue
        repo, branch, subdir, sid = None, "main", "", name
        cfgp = os.path.join(d, ".release.json")
        if os.path.isfile(cfgp):
            try:
                with io.open(cfgp, encoding="utf-8") as f:
                    c = json.load(f)
                repo = c.get("repo")
                branch = c.get("branch") or "main"
                subdir = c.get("subdir") or ""
            except Exception:
                pass
        mp = os.path.join(d, "manifest.json")
        ver = "?"
        if os.path.isfile(mp):
            try:
                with io.open(mp, encoding="utf-8") as f:
                    m = json.load(f)
                ver = m.get("version", "?")
                if not repo:
                    for k in ("repository", "homepage", "repo", "url"):
                        v = m.get(k)
                        if isinstance(v, str) and "github.com" in v:
                            repo = v
                            break
                        if isinstance(v, dict) and "github.com" in v.get("url", ""):
                            repo = v["url"]
                            break
            except Exception:
                pass
        rows.append((name, ver, repo or "—", branch, subdir or "—"))

    if not rows:
        print("没有找到可管理的 skill。")
        return 0

    print("== 已装 skill 与发布坐标 ==")
    w1 = max(len(r[0]) for r in rows) + 2
    w2 = max(len(r[1]) for r in rows) + 2
    w3 = max(len(r[2]) for r in rows) + 2
    print("%-*s%-*s%-*s%s" % (w1, "skill", w2, "版本", w3, "仓库", "分支/子目录"))
    for n, v, r, b, s in rows:
        tail = b if s == "—" else "%s / %s" % (b, s)
        print("%-*s%-*s%-*s%s" % (w1, n, w2, v, w3, r, tail))
    print()
    print("说「更新 X」时，agent 读这里的坐标即可，不需要你提供链接。")
    return 0


# ----------------------------------------------------------
#  --verify：本地与远端 blob 一致性
# ----------------------------------------------------------
def run_verify():
    repo, _ = detect_repo()
    if not repo:
        _err("未定位到仓库地址，无法比对")
    m = re.search(r"github\.com[/:]([\w.-]+)/([\w.-]+?)(?:\.git)?$", repo)
    if not m:
        _err("无法解析仓库坐标: %s" % repo)
    owner, name = m.group(1), m.group(2)

    version, _ = detect_version()
    cfg = _read_release_cfg()
    print("== 一致性检查 ==")
    print("仓库: %s/%s   版本: v%s\n" % (owner, name, version))

    # 相对仓库根的文件路径
    # 注意：subdir 为 "" 表示「skill 在仓库根目录」，是合法声明；
    # 只有「配置里根本没有 subdir 键」才需要回退去推断。
    if "subdir" in cfg:
        rel_dir = (cfg.get("subdir") or "").strip("/") or "."
    else:
        rc, git_root, _ = _run(["git", "rev-parse", "--show-toplevel"])
        if rc != 0:
            print("⚠️  非 git 仓库且 .release.json 未声明 subdir，跳过 blob 比对")
            print("    修复：在 .release.json 里加 \"subdir\": \"\"（仓库根）或具体子目录")
            return 0
        rel_dir = os.path.relpath(SKILL_DIR, git_root)

    ok = True
    for fname in ("SKILL.md", "manifest.json", "CHANGELOG.md", "README.md",
                  "scripts/release.py"):
        local = os.path.join(SKILL_DIR, fname)
        if not os.path.isfile(local):
            continue
        rel = fname if rel_dir == "." else "%s/%s" % (rel_dir, fname)

        rc, local_blob, _ = _run(["git", "hash-object", fname])
        if rc != 0:
            continue
        q = "repos/%s/%s/contents/%s" % (owner, name, rel)
        rc2, remote_sha, _ = _run(["gh", "api", q, "--jq", ".sha"])
        if rc2 != 0 or not remote_sha:
            print("  %-14s ⚠️  远端读取失败（未推送或路径不对）" % fname)
            ok = False
            continue
        same = (local_blob == remote_sha)
        print("  %-14s %s  local=%s remote=%s"
              % (fname, "✅" if same else "❌", local_blob[:12], remote_sha[:12]))
        if not same:
            ok = False

    print()
    print("结论: %s" % ("✅ 本地与远端完全一致" if ok else "❌ 存在差异，需要重新推送"))
    return 0 if ok else 1


# ----------------------------------------------------------
#  入口
# ----------------------------------------------------------
def main(argv=None):
    p = argparse.ArgumentParser(
        description="Skill 发布辅助：自动定位 GitHub 仓库与版本")
    p.add_argument("--check", action="store_true",
                   help="定位并显示仓库、当前版本、最近 tag、分支与同步状态")
    p.add_argument("--bump", choices=["major", "minor", "patch"],
                   help="递增版本并同步 SKILL.md / manifest.json / CHANGELOG.md")
    p.add_argument("--dry-run", action="store_true",
                   help="与 --bump 联用：只预览，不写文件")
    p.add_argument("--verify", action="store_true",
                   help="比对本地与远端 GitHub blob 是否一致")
    p.add_argument("--init", metavar="REPO_URL",
                   help="钉死仓库坐标，写入 .release.json（之后 --check 不再需要猜）")
    p.add_argument("--branch", help="配合 --init：显式指定分支名（fork 仓库常为 master）")
    p.add_argument("--subdir", help="配合 --init：skill 在仓库中的子目录（根目录留空）")
    p.add_argument("--install", action="store_true",
                   help="按 skill 配置里的坐标安装本 skill（新机器/首次）")
    p.add_argument("--update", action="store_true",
                   help="按 skill 配置里的坐标拉取最新版（保留 .release.json）")
    p.add_argument("--list", action="store_true",
                   help="列出所有已装 skill 及其配置的仓库坐标")
    p.add_argument("--target", help="配合 --install/--update：指定目标目录")
    a = p.parse_args(argv)

    if a.init:
        return write_release_cfg(a.init, branch=a.branch, subdir=a.subdir,
                                 target=a.target)
    if a.check:
        return run_check()
    if a.bump:
        apply_bump(a.bump, dry_run=a.dry_run)
        return 0
    if a.verify:
        return run_verify()
    if a.install:
        return run_install(target=a.target)
    if a.update:
        return run_update(target=a.target)
    if a.list:
        return run_list()
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
