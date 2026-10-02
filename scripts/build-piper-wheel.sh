#!/usr/bin/env bash
#
# Compila UMA vez o wheel musl/aarch64 do `piper-tts` (design D7), para o build da
# imagem instalar com `PIPER_WHEEL=<arquivo>` (rápido e reprodutível). O sdist do
# PyPI é incompleto: compila-se da tag do git, que baixa/liga o espeak-ng estático.
#
# Dois motores, auto-detectados (força com ENGINE=docker|chroot):
#   - docker : `docker run --platform linux/arm64 alpine:3.24 ...` (precisa de
#              docker + binfmt arm64; a via mais limpa em máquina de dev).
#   - chroot : minirootfs Alpine aarch64 + qemu-aarch64-static num user namespace
#              (rootless: usa `unshare -r`; precisa de qemu-aarch64-static e binfmt).
#
# Uso:   ./build-piper-wheel.sh [OUT_DIR]        (padrão: system/rpi-os/alpine/wheels)
# Saída: OUT_DIR/piper_tts-*-linux_aarch64.whl  (caminho impresso no fim)
#        O build do Piper NÃO passa por auditwheel, então a tag fica
#        'linux_aarch64' e não 'musllinux_*_aarch64'. O binário é musl de
#        verdade (compilado no Alpine 3.24) — só não leva o rótulo. Como a
#        instalação é por caminho de arquivo na MESMA versão do Alpine, o pip
#        aceita a tag genérica.
#
# É LENTO no motor chroot (compila sob emulação qemu). O wheel é abi3: serve para
# qualquer Python 3.x da imagem.

set -euo pipefail

ALPINE_BRANCH="v3.24"
ALPINE_VERSION="${ALPINE_VERSION:-3.24.1}"
ARCH="aarch64"
MIRROR="https://dl-cdn.alpinelinux.org/alpine"
MINIROOTFS_FILE="alpine-minirootfs-${ALPINE_VERSION}-${ARCH}.tar.gz"
MINIROOTFS_URL="${MIRROR}/${ALPINE_BRANCH}/releases/${ARCH}/${MINIROOTFS_FILE}"
MINIROOTFS_SHA256="f55a90f69052c5bd6f92cb09a8f47065970830b194c917a006fb94028e721259"

PIPER_GIT_URL="${PIPER_GIT_URL:-https://github.com/OHF-Voice/piper1-gpl}"
PIPER_GIT_REF="${PIPER_GIT_REF:-v1.8.0}"   # tags do repo têm prefixo 'v' (v1.8.0)
# linux-headers: o espeak-ng inclui <linux/limits.h> (speech.h), que no Alpine
# NAO vem com o build-base — em distros glibc esse header vem de carona no
# pacote de dev da libc. Sem ele a compilacao morre com
# "fatal error: linux/limits.h: No such file or directory".
BUILD_DEPS="build-base cmake git ninja linux-headers python3 python3-dev py3-pip"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUT_DIR="${1:-${REPO_ROOT}/system/rpi-os/alpine/wheels}"
WORK_DIR="${WORK_DIR:-${REPO_ROOT}/system/rpi-os/alpine/.work/wheel-build}"

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[aviso]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[erro]\033[0m %s\n' "$*" >&2; exit 1; }

# Comando que compila o wheel dentro de um /bin/sh Alpine aarch64.
build_cmd() {
    cat <<SH
set -eu
apk update
apk add --no-progress ${BUILD_DEPS} || { apk add --no-progress ${BUILD_DEPS/ninja/samurai}; ln -sf /usr/bin/samu /usr/bin/ninja; }
rm -rf /wheelhouse && mkdir -p /wheelhouse
# 'pip wheel' não instala no sistema (não aceita --break-system-packages); a
# build isolation resolve o backend (scikit-build-core) num venv próprio.
pip3 wheel --no-cache-dir --no-deps -w /wheelhouse \
    "piper-tts @ git+${PIPER_GIT_URL}@${PIPER_GIT_REF}"
ls -l /wheelhouse
SH
}

pick_engine() {
    if [ -n "${ENGINE:-}" ]; then echo "${ENGINE}"; return; fi
    if command -v docker >/dev/null 2>&1; then echo docker; return; fi
    if command -v qemu-aarch64-static >/dev/null 2>&1; then echo chroot; return; fi
    die "sem docker e sem qemu-aarch64-static: não há como emular aarch64. Force ENGINE=."
}

# --- Motor docker ----------------------------------------------------------
build_docker() {
    log "Motor docker: alpine:3.24 arm64"
    mkdir -p "${OUT_DIR}"
    docker run --rm --platform linux/arm64 \
        -v "${OUT_DIR}:/out" "alpine:${ALPINE_VERSION%.*}" \
        /bin/sh -c "$(build_cmd); cp /wheelhouse/piper_tts-*.whl /out/"
}

# --- Motor chroot (rootless via user namespace) ----------------------------
qemu_static_path() { command -v qemu-aarch64-static || echo /usr/bin/qemu-aarch64-static; }

build_chroot() {
    # Reexec dentro de um user+mount namespace (root mapeado), uma vez. SEM -pf:
    # um pid namespace forçaria o unshare a forkar e o processo pai retornaria
    # cedo (o supervisor daria a tarefa por concluída e mataria a compilação).
    if [ "${_PIPER_NS:-0}" != "1" ]; then
        log "Motor chroot: entrando em user namespace (rootless)"
        exec env _PIPER_NS=1 unshare -rm "${BASH_SOURCE[0]}" "${OUT_DIR}"
    fi

    local rootfs="${WORK_DIR}/rootfs" dl="${WORK_DIR}/${MINIROOTFS_FILE}"
    mkdir -p "${WORK_DIR}"

    if [ ! -e "${rootfs}/etc/alpine-release" ]; then
        [ -f "${dl}" ] || { log "Baixando minirootfs"; curl -fSL "${MINIROOTFS_URL}" -o "${dl}.part"; mv "${dl}.part" "${dl}"; }
        echo "${MINIROOTFS_SHA256}  ${dl}" | sha256sum -c - || die "sha256 do minirootfs não confere."
        log "Extraindo minirootfs"
        rm -rf "${rootfs}"; mkdir -p "${rootfs}"
        # --no-same-owner: no user namespace rootless só o uid 0 é mapeado, então
        # restaurar donos/gids (ex.: shadow gid 42) falha. Os arquivos ficam do
        # root do namespace, o que basta para compilar.
        tar --no-same-owner -xzf "${dl}" -C "${rootfs}"
    fi

    install -Dm755 "$(qemu_static_path)" "${rootfs}/usr/bin/qemu-aarch64-static"
    cp -f /etc/resolv.conf "${rootfs}/etc/resolv.conf"
    printf '%s/%s/main\n%s/%s/community\n' "${MIRROR}" "${ALPINE_BRANCH}" "${MIRROR}" "${ALPINE_BRANCH}" \
        > "${rootfs}/etc/apk/repositories"

    mkdir -p "${rootfs}/proc" "${rootfs}/dev"
    # rbind (não `-t proc`): montar um proc novo exigiria CAP sobre um pid ns
    # próprio, que não temos sem -p. O rbind do /proc do host basta para o build.
    mount --rbind /proc "${rootfs}/proc"
    mount --rbind /dev "${rootfs}/dev"
    cleanup() { umount -lR "${rootfs}/dev" 2>/dev/null || true; umount -lR "${rootfs}/proc" 2>/dev/null || true; }
    trap cleanup EXIT

    log "Compilando o wheel no chroot aarch64 (LENTO sob qemu) — tag ${PIPER_GIT_REF}"
    build_cmd | chroot "${rootfs}" /usr/bin/qemu-aarch64-static /bin/sh \
        || die "falha ao compilar o wheel (ver saída acima)."

    mkdir -p "${OUT_DIR}"
    cp -f "${rootfs}"/wheelhouse/piper_tts-*.whl "${OUT_DIR}/"
}

main() {
    local engine; engine="$(pick_engine)"
    case "${engine}" in
        docker) build_docker ;;
        chroot) build_chroot ;;
        *) die "ENGINE inválido: ${engine}" ;;
    esac
    local whl; whl="$(ls -1 "${OUT_DIR}"/piper_tts-*.whl 2>/dev/null | head -n1 || true)"
    [ -n "${whl}" ] || die "nenhum wheel gerado em ${OUT_DIR}."
    printf '\n\033[1;32mWheel pronto:\033[0m %s\n' "${whl}"
    printf 'Use no build da imagem:  make rpi-img PIPER_WHEEL=%s\n' "${whl}"
}

main "$@"
