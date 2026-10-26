#!/usr/bin/env bash
# notebook_env_proxy.sh — SCNet notebook 出网代理激活（在 notebook 上 source 使用，幂等）
#
# 用途：在 notebook（root@ssh.zzai.scnet.cn:11009，本机经 HPC wuzh02 两跳可达）
#       的 shell 里 `source` 本文件，自动解析平台自带的代理配置并导出
#       http_proxy / https_proxy / ftp_proxy / no_proxy（含对应大写变量）。
#       幂等：重复 source 不叠加、不改值、不报错；加 --force 可强制重探测。
#
# 来源文档：docs/NOTEBOOK_ENV_FACTS_2026-10-26.md（§2 出网与代理）
#
# 2026-10-26 实测结论（详见上述文档）：
#   1. 直连外网不通：baidu / dashscope 均连接超时（curl rc=28, http_code=000）；
#   2. 平台代理 10.16.1.51:3128 必须带认证：裸地址（无 user:pass）返回
#      HTTP 407（Proxy Authentication Required）；凭据只存在于 notebook 上的
#      平台文件里，本脚本不含、不打印、不外传任何凭据；
#   3. 带凭据代理：baidu 200（0.16s）/ dashscope 404（0.18s，根路径无页面，
#      属可达）；API 级可用性另见 docs/TASK_P2_NOTEBOOK_B_2026-10-26.md §1；
#   4. 非交互 ssh exec 的 env 里没有代理变量（平台的 source 写在
#      /etc/bashrc 与 /etc/bash.bashrc，仅交互 shell 生效）——这就是每个
#      非交互会话都要手动激活的原因。
#
# 探测顺序：
#   a) 已激活（NB_PROXY_ACTIVE 非空且无 --force）→ 直接返回；
#   b) /root/private_data/.ai_user_info/ai_proxy        （平台托管，含 no_proxy）
#   c) $SCNET_USER_HOME/.bashrc                          （root .bashrc 导出的挂载 home）
#   d) /public/home/aclhl3hbth/.bashrc                   （平台挂载用户 home，第 21–23 行）
#
# 故意不写死回落地址：裸 10.16.1.51:3128 实测 407 不可用，两处来源都解析失败
# 时直接报错退出，不猜测。
#
# 用法（在 notebook 上）：
#   source notebook_env_proxy.sh            # 激活（幂等）
#   source notebook_env_proxy.sh --force    # 丢弃现有值，重新探测
#   nb_proxy_status                         # 打印当前代理（凭据打码）+ 一次连通探测

# ---------- 工具函数（顶层定义，重复 source 也不重复定义副作用） ----------

# 打印代理 URL 但把 user:pass 打码（凭据不落日志）
nb_proxy_mask_url() {
    printf '%s\n' "$1" | sed -E 's#(https?://)[^/@]+:[^/@]+@#\1***:***@#'
}

# 从文件解析第一行 `export https_proxy=...`，成功则设全局 _NB_PROXY_URL（含凭据，勿打印）
_nb_proxy_parse_file() {
    local f="$1" line
    [ -r "$f" ] || return 1
    line=$(grep -h -m1 -E '^export https_proxy=' "$f" 2>/dev/null) || return 1
    _NB_PROXY_URL=${line#*https_proxy=}
    _NB_PROXY_URL=${_NB_PROXY_URL//\"/}
    _NB_PROXY_URL=${_NB_PROXY_URL//\'/}
    [ -n "$_NB_PROXY_URL" ] || return 1
    return 0
}

# 状态查看：当前代理（打码）+ no_proxy + 一次连通探测
nb_proxy_status() {
    if [ -n "${https_proxy:-}" ]; then
        echo "proxy    : $(nb_proxy_mask_url "$https_proxy")"
    else
        echo "proxy    : (unset)"
    fi
    echo "no_proxy : ${no_proxy:-(unset)}"
    if [ -z "${https_proxy:-}" ]; then
        echo "probe    : skipped (proxy not set)"
        return 0
    fi
    local out rc
    out=$(curl -sS -m 10 -o /dev/null -w '%{http_code} %{time_total}s' https://www.baidu.com 2>&1)
    rc=$?
    echo "probe    : baidu via proxy -> rc=$rc out=[$out]"
}

# ---------- 主流程（包在函数里，sourced/直接执行都安全） ----------
_nb_proxy_main() {
    # 幂等闸门：已激活且未 --force → 原样返回
    if [ -n "${NB_PROXY_ACTIVE:-}" ] && [ "${1:-}" != "--force" ]; then
        return 0
    fi

    _NB_PROXY_URL=''
    if _nb_proxy_parse_file /root/private_data/.ai_user_info/ai_proxy; then
        :
    elif [ -n "${SCNET_USER_HOME:-}" ] && _nb_proxy_parse_file "${SCNET_USER_HOME}/.bashrc"; then
        :
    elif _nb_proxy_parse_file /public/home/aclhl3hbth/.bashrc; then
        :
    else
        echo "notebook_env_proxy: ERROR 平台代理配置解析失败（ai_proxy 与 /public/home/*/.bashrc 均不可用）" >&2
        echo "notebook_env_proxy: 不要用裸地址 10.16.1.51:3128（实测 407，需要认证）；先人工确认平台文件位置" >&2
        return 1
    fi

    # 同时设置大小写两组；no_proxy 幂等合并（不叠加重复项）
    export http_proxy="$_NB_PROXY_URL"  HTTP_PROXY="$_NB_PROXY_URL"
    export https_proxy="$_NB_PROXY_URL" HTTPS_PROXY="$_NB_PROXY_URL"
    export ftp_proxy="$_NB_PROXY_URL"
    case ",${no_proxy:-}," in
        *,localhost,*) : ;;
        *) export no_proxy="localhost,127.0.0.1${no_proxy:+,${no_proxy}}" NO_PROXY="${no_proxy:-}" ;;
    esac
    export NB_PROXY_ACTIVE=1
    unset _NB_PROXY_URL

    echo "notebook_env_proxy: activated -> $(nb_proxy_mask_url "$https_proxy")"
    return 0
}

_nb_proxy_main "$@"
