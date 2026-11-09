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
#   cd <skills目录>/X && python3 scripts/release.py --update
# ============================================================
set -euo pipefail

readonly REPO="wpc6666/self-release"
readonly BRANCH="${SELF_RELEASE_BRANCH:-main}"
readonly SKILL_NAME="self-release"

# 目标目录优先级：
#   1. SKILLS_HOME —— 直接指向中央 skills 目录
#   2. DSH_HOME/skills —— 兼容旧用法
#   3. 上次安装记下的根目录 ~/.config/self-release/skills-root
#   4. XDG 数据目录（默认 ~/.local/share/skills）
# 安装时会记住实际路径，后续 skill / release.py 不再依赖环境变量。
CONFIG_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}/self-release"
CONFIG_FILE="${CONFIG_DIR}/skills-root"
if [[ -n "${SKILLS_HOME:-}" ]]; then
  SKILLS_DIR="${SKILLS_HOME}"
elif [[ -n "${DSH_HOME:-}" ]]; then
  SKILLS_DIR="${DSH_HOME}/skills"
elif [[ -r "${CONFIG_FILE}" ]]; then
  IFS= read -r SKILLS_DIR < "${CONFIG_FILE}" || SKILLS_DIR=""
  [[ -n "${SKILLS_DIR}" ]] || SKILLS_DIR="${XDG_DATA_HOME:-${HOME}/.local/share}/skills"
else
  SKILLS_DIR="${XDG_DATA_HOME:-${HOME}/.local/share}/skills"
fi
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

# 记住本次安装根目录：之后 skill 命令与 release.py 都读这里，
# 不再依赖用户每次手动设置 DSH_HOME。
remember_root() {
  mkdir -p "${CONFIG_DIR}"
  printf '%s\n' "${SKILLS_DIR}" > "${CONFIG_FILE}"
}

# 安装/刷新 skill 短命令。更新流程也会走到这里，避免旧版命令继续指向旧目录。
install_cli() {
  local src="${DEST}/skill"
  local bin="${HOME}/.local/bin/skill"
  [[ -f "${src}" ]] || return 0
  mkdir -p "$(dirname "${bin}")"
  if [[ -f "${bin}" ]] && ! cmp -s "${src}" "${bin}"; then
    cp "${bin}" "${bin}.bak.$(date '+%Y%m%d_%H%M%S')"
  fi
  cp "${src}" "${bin}"
  chmod +x "${bin}"
  ok "已安装 skill 命令：${bin}"
}

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
  remember_root
  cd "${DEST}"
  if [[ -f .release.json ]] || [[ -f manifest.json ]]; then
    python3 scripts/release.py --update || die "更新失败"
  else
    die "目录存在但缺配置，请先手动删除：${DEST}"
  fi
  install_cli
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
  SRCROOT=$(find "${TMPD}/x" -mindepth 1 -maxdepth 1 -type d -print -quit)
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

# ---------- 记住根目录 + 安装 skill 短命令 ----------
# 这是「只说一句话」的关键：用户敲 skill update X，而不是一长串 python3 路径
remember_root
install_cli
if [[ ! -f "${DEST}/skill" ]]; then
  warn "仓库里没有 skill 命令（旧版本），跳过；可用长命令："
  echo "    python3 ${DEST}/scripts/release.py --list"
fi
case ":${PATH}:" in
  *":${HOME}/.local/bin:"*) ;;
  *)
    warn "${HOME}/.local/bin 不在 PATH 里，把下面这行加到 ~/.zshrc："
    echo "    export PATH=\"\${HOME}/.local/bin:\${PATH}\""
    ;;
esac

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
echo "  更新 skill：skill update <名字>        （只说名字，不用 cd）"
echo "  更新全部  ：skill update --all"
echo "  装新 skill：skill install <名字> --from-repo <仓库地址>"
echo "  查看全部  ：skill list"
echo "  上架新 skill：cd <skill目录> && skill up --yes"
echo
echo "  提示：以后直接对 agent 说「更新这个 skill」就行，它会自己跑 skill update"
echo "════════════════════════════════════════════════════"
