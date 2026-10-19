#!/usr/bin/env bash
# ============================================================
# self-release 引导安装器（bootstrap installer）
#
# 解决「鸡生蛋」问题：新电脑上还没有这个 skill 时，
# 没有 release.py 可跑，所以需要一条命令把它装进来。
#
# 用法（一条命令，不需要克隆）：
#   curl -fsSL https://raw.githubusercontent.com/wpc6666/self-release/main/install.sh | bash
#
# 装完后，任何带 .release.json 的 skill 都可以一句话更新：
#   cd ~/.dsh/skills/X && python3 scripts/release.py --update
# ============================================================
set -euo pipefail

readonly REPO="wpc6666/self-release"
readonly BRANCH="${SELF_RELEASE_BRANCH:-main}"
readonly SKILL_NAME="self-release"

# 目标目录：优先 DSH_HOME，其次 ~/.dsh
DSH_HOME="${DSH_HOME:-${HOME}/.dsh}"
SKILLS_DIR="${DSH_HOME}/skills"
DEST="${SKILLS_DIR}/${SKILL_NAME}"

# 颜色（非终端时自动关闭）
if [[ -t 1 ]]; then
  C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_ERR=$'\033[31m'; C_RST=$'\033[0m'
else
  C_OK=""; C_WARN=""; C_ERR=""; C_RST=""
fi
ok()   { printf '%s✅ %s%s\n' "$C_OK"   "$*" "$C_RST"; }
warn() { printf '%s⚠️  %s%s\n' "$C_WARN" "$*" "$C_RST"; }
err()  { printf '%s❌ %s%s\n' "$C_ERR"  "$*" "$C_RST" >&2; }
die()  { err "$*"; exit 1; }

echo "════════════════════════════════════════════════════"
echo "  self-release 安装器"
echo "  仓库: github.com/${REPO} (${BRANCH})"
echo "  目标: ${DEST}"
echo "════════════════════════════════════════════════════"
echo

# ---------- 依赖检查 ----------
command -v git >/dev/null 2>&1 || die "需要 git，请先安装：xcode-select --install"
command -v python3 >/dev/null 2>&1 || die "需要 python3（3.8+）"

PY_VER=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
ok "git / python3 ${PY_VER} 就绪"

# ---------- 已存在则走更新 ----------
if [[ -f "${DEST}/scripts/release.py" ]]; then
  warn "检测到已安装：${DEST}"
  echo "  转为更新流程…"
  cd "${DEST}"
  if [[ -f .release.json ]] || [[ -f manifest.json ]]; then
    python3 scripts/release.py --update || die "更新失败"
  else
    die "目录存在但缺配置，请先手动删除：${DEST}"
  fi
  echo
  ok "已更新到最新版"
  echo
  echo "查看版本：cd ${DEST} && python3 scripts/release.py --check"
  exit 0
fi

# ---------- 备份已存在的非空目录 ----------
if [[ -d "${DEST}" ]] && [[ -n "$(ls -A "${DEST}" 2>/dev/null)" ]]; then
  BAK="${DEST}.bak.$(date '+%Y%m%d_%H%M%S')"
  warn "目标目录非空，先备份到 ${BAK}"
  mv "${DEST}" "${BAK}"
fi

mkdir -p "${SKILLS_DIR}"

# ---------- 下载 ----------
# 优先 tarball（一条请求拿全部文件），失败回退 git clone
TMPD=$(mktemp -d)
trap 'rm -rf "${TMPD}"' EXIT

TARBALL_URL="https://api.github.com/repos/${REPO}/tarball/${BRANCH}"
TGZ="${TMPD}/sr.tgz"

echo "正在下载…"
DOWNLOADED=0
if command -v curl >/dev/null 2>&1; then
  if curl -fsSL --retry 3 --connect-timeout 15 -o "${TGZ}" "${TARBALL_URL}" 2>/dev/null; then
    DOWNLOADED=1
  fi
fi
if [[ "${DOWNLOADED}" -eq 0 ]] && command -v gh >/dev/null 2>&1; then
  warn "curl 失败，改用 gh（私有仓库需要已登录）"
  if gh api "repos/${REPO}/tarball/${BRANCH}" > "${TGZ}" 2>/dev/null; then
    DOWNLOADED=1
  fi
fi

if [[ "${DOWNLOADED}" -eq 1 ]]; then
  mkdir -p "${TMPD}/x"
  tar xzf "${TGZ}" -C "${TMPD}/x" || die "解压失败"
  SRCROOT=$(find "${TMPD}/x" -mindepth 1 -maxdepth 1 -type d | head -1)
  [[ -n "${SRCROOT}" ]] || die "压缩包结构异常"
  mkdir -p "${DEST}"
  # 复制全部文件（含隐藏文件），排除 .git
  ( cd "${SRCROOT}" && tar cf - --exclude='.git' --exclude='.release.json' . ) \
    | ( cd "${DEST}" && tar xf - ) || die "复制失败"
  ok "tarball 下载安装完成"
elif command -v git >/dev/null 2>&1; then
  warn "下载失败，回退 git clone"
  git clone --depth 1 --branch "${BRANCH}" \
    "https://github.com/${REPO}.git" "${DEST}" || die "git clone 失败"
  rm -rf "${DEST}/.git"
  ok "git clone 安装完成"
else
  die "无法下载（curl / gh / git 均不可用）"
fi

# ---------- 钉死坐标（之后更新不再需要任何链接）----------
cat > "${DEST}/.release.json" <<EOF
{
  "repo": "https://github.com/${REPO}.git",
  "branch": "${BRANCH}"
}
EOF
ok "已写入 .release.json（以后更新不需要原始链接）"

# ---------- 自检 ----------
echo
echo "──────── 自检 ────────"
cd "${DEST}"
if python3 scripts/release.py --check >/dev/null 2>&1; then
  python3 scripts/release.py --check | sed 's/^/  /'
  echo
  ok "安装完成"
else
  warn "--check 未通过，但文件已就位，可手动排查："
  python3 scripts/release.py --check 2>&1 | sed 's/^/  /' || true
fi

echo
echo "════════════════════════════════════════════════════"
echo "  下一步"
echo "════════════════════════════════════════════════════"
echo "  发布 skill：cd <skill目录> && python3 scripts/release.py --check"
echo "  更新 skill：cd <skill目录> && python3 scripts/release.py --update"
echo "  查看全部  ：python3 ${DEST}/scripts/release.py --list"
echo
echo "  其他 skill 要接入一句话更新，跑一次："
echo "    cd <skill目录> && python3 ${DEST}/scripts/release.py --init <仓库地址>"
echo "════════════════════════════════════════════════════"
