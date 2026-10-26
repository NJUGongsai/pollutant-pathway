#!/usr/bin/env bash
# nb_ssh.sh — 本机到 SCNet notebook 的 SSH 封装（默认两跳：本机 → HPC wuzh02 → notebook）
#
# 用法：
#   bash scripts/hpc/nb_ssh.sh "<command>"                # 在 notebook 上执行命令
#   bash scripts/hpc/nb_ssh.sh --put <local> <remote>     # 上传单个文件（两跳 scp，经 HPC /tmp 暂存后即删）
#
# 事实依据（2026-10-26 实测，docs/NOTEBOOK_ENV_FACTS_2026-10-26.md §5）：
#   - notebook 密钥 id_ed25519_nb 不在本机 ~/.ssh/，在 HPC 的
#     ~/.ssh/id_ed25519_nb（迁移/重建后于 2026-10-26 10:04 更新）；
#     因此默认走两跳：本机 --ssh--> aclhl3hbth@wuzh02.hpccube.com:65091
#     --ssh(~/.ssh/id_ed25519_nb)--> root@ssh.zzai.scnet.cn:11009。
#   - 若本机将来放了直连密钥，设 NB_KEY=<path> 即切换为直连模式。
#
# 环境变量（均可覆盖默认值）：
#   NB_KEY        本机直连 notebook 的私钥（存在则启用直连模式；默认 ~/.ssh/id_ed25519_nb，通常不存在）
#   NB_HOST/NB_PORT/NB_USER    notebook 端（默认 ssh.zzai.scnet.cn / 11009 / root）
#   NB_HPC_KEY                 HPC 跳板私钥（默认 ~/.ssh/hpc_wuzh02_key，2026-10-26 实测可用；
#                              不存在则回落 /Volumes/CC/Enzyme_Agent/aclhl3hbth_wuzh02...txt）
#   NB_HPC_HOST/NB_HPC_PORT/NB_HPC_USER     HPC 跳板（默认 wuzh02.hpccube.com / 65091 / aclhl3hbth）
#
# 已知噪音：HPC 登录会打印 perl locale warning（无害）；两跳命令经 `bash -s`
# 传命令原文，本封装不支持给远端命令喂 stdin。
#
# 失败语义：任何一步连不上/密钥缺失都立即报明确错误并退出非 0，不静默失败。

set -euo pipefail

NB_HOST=${NB_HOST:-ssh.zzai.scnet.cn}
NB_PORT=${NB_PORT:-11009}
NB_USER=${NB_USER:-root}
NB_KEY=${NB_KEY:-${HOME}/.ssh/id_ed25519_nb}

NB_HPC_HOST=${NB_HPC_HOST:-wuzh02.hpccube.com}
NB_HPC_PORT=${NB_HPC_PORT:-65091}
NB_HPC_USER=${NB_HPC_USER:-aclhl3hbth}
NB_HPC_KEY=${NB_HPC_KEY:-${HOME}/.ssh/hpc_wuzh02_key}
NB_HPC_KEY_FALLBACK=${NB_HPC_KEY_FALLBACK:-/Volumes/CC/Enzyme_Agent/aclhl3hbth_wuzh02.hpccube.com_RsaKeyExpireTime_2026-11-30_10-12-36.txt}

die() { echo "nb_ssh: ERROR: $*" >&2; exit 1; }

usage() {
    sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
}

# 单引号转义（用于把 remote 路径安全嵌进 HPC 上的内层 ssh 命令）
_shq() { printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"; }

_pick_hpc_key() {
    if [ -f "$NB_HPC_KEY" ]; then return 0; fi
    if [ -f "$NB_HPC_KEY_FALLBACK" ]; then
        NB_HPC_KEY="$NB_HPC_KEY_FALLBACK"
        return 0
    fi
    return 1
}

# 两跳公共前缀：本机→HPC 的 ssh，把内层" notebook 命令"经 stdin 送达
_twohop() {
    # $1 = 内层要在 notebook 上执行的 shell 片段（如 `bash -s` 或 `cat > path`）
    local inner
    inner="ssh -i $(_shq '~/.ssh/id_ed25519_nb') -p ${NB_PORT} -o StrictHostKeyChecking=no -o ConnectTimeout=20 ${NB_USER}@${NB_HOST} $1"
    ssh -i "$NB_HPC_KEY" -p "$NB_HPC_PORT" \
        -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=20 \
        "${NB_HPC_USER}@${NB_HPC_HOST}" "$inner"
}

main() {
    local mode=${1:-}
    case "$mode" in
        -h|--help) usage ;;
        '') die "缺少命令。用法: bash scripts/hpc/nb_ssh.sh \"<command>\" | --put <local> <remote> | --help" ;;
    esac
    shift

    # 直连模式：本机存在 notebook 私钥
    if [ -f "$NB_KEY" ]; then
        case "$mode" in
            --put)
                local lf=${1:-} rf=${2:-}
                [ -n "$lf" ] && [ -n "$rf" ] || die "--put 需要 <local> <remote> 两个参数"
                [ -f "$lf" ] || die "本地文件不存在: $lf"
                scp -i "$NB_KEY" -P "$NB_PORT" \
                    -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=20 \
                    "$lf" "${NB_USER}@${NB_HOST}:${rf}"
                ;;
            *)
                ssh -i "$NB_KEY" -p "$NB_PORT" \
                    -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=20 \
                    "${NB_USER}@${NB_HOST}" "$mode"
                ;;
        esac
        return 0
    fi

    # 两跳模式（默认）
    _pick_hpc_key || die "HPC 跳板密钥不存在: $NB_HPC_KEY（及回落 $NB_HPC_KEY_FALLBACK）。可用 NB_HPC_KEY=<path> 指定；或放本机直连密钥后 NB_KEY=<path> 走直连"
    case "$mode" in
        --put)
            local lf=${1:-} rf=${2:-}
            [ -n "$lf" ] && [ -n "$rf" ] || die "--put 需要 <local> <remote> 两个参数"
            [ -f "$lf" ] || die "本地文件不存在: $lf"
            # 两跳 scp：本机 → HPC /tmp 暂存 → notebook → 删暂存。
            # 不要用 `cat "$lf" | _twohop "cat > ..."`：内层 `>` 会被 HPC 侧 shell
            # 抢先解释，文件写到跳板机（2026-10-26 实测 Permission denied）。
            local staging
            staging="/tmp/nb_put_$$_$(basename "$lf")"
            scp -i "$NB_HPC_KEY" -P "$NB_HPC_PORT" \
                -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=20 \
                "$lf" "${NB_HPC_USER}@${NB_HPC_HOST}:${staging}"
            ssh -i "$NB_HPC_KEY" -p "$NB_HPC_PORT" \
                -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=20 \
                "${NB_HPC_USER}@${NB_HPC_HOST}" \
                "scp -i ~/.ssh/id_ed25519_nb -P ${NB_PORT} -o StrictHostKeyChecking=no -o BatchMode=yes $(_shq "$staging") ${NB_USER}@${NB_HOST}:$(_shq "$rf") && rm -f $(_shq "$staging")"
            ;;
        *)
            printf '%s' "$mode" | _twohop "bash -s"
            ;;
    esac
}

main "$@"
