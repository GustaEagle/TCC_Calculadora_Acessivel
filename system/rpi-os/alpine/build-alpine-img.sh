#!/usr/bin/env bash
#
# Gera uma imagem Alpine Linux (aarch64) bootável para o Raspberry Pi 4B que
# arranca DIRETO na calculadora acessível (modo kiosk). Ver o plano em
# openspec/changes/add-alpine-rpi-image/ (proposal/design/specs/tasks).
#
# O que este script faz (tudo "baked", offline no aparelho):
#   1. Baixa e verifica (sha256) o minirootfs oficial do Alpine 3.24.1 aarch64.
#   2. Monta um rootfs ext4 "sys" (gravável) e instala, num chroot emulado com
#      qemu-aarch64-static, os pacotes (apk) + kernel/firmware do Pi + as libs
#      Python (pip) de software/requirements.txt.
#   3. Configura autologin do usuário "kiosk" -> startx -> a calculadora.
#   4. Empacota tudo num arquivo .img (partição FAT de boot + root ext4).
#
# O .img resultante NÃO é versionado (ver .gitignore). Gravar no cartão é um
# passo manual documentado no README.md (dd), separado deste build.
#
# IMPORTANTE: este script cria/gerencia apenas um ARQUIVO de imagem via loopback;
# ele nunca escreve em /dev/sdX nem no cartão. A gravação no SD é feita por você.
#
# Uso:   sudo ./build-alpine-img.sh
# Saída: ./calculadora-alpine-3.24.1-aarch64.img
#
# NOTA DE HONESTIDADE: o boot real (firmware/kernel/dtb do Pi, modo do LCD
# Waveshare, áudio e TTS) só pode ser confirmado NO HARDWARE. Pontos que exigem
# validação estão marcados com "# VALIDAR NO HARDWARE".

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuração (pinos de versão — reprodutibilidade)
# ---------------------------------------------------------------------------
ALPINE_BRANCH="v3.24"
ALPINE_VERSION="3.24.1"
ARCH="aarch64"
MIRROR="https://dl-cdn.alpinelinux.org/alpine"

MINIROOTFS_FILE="alpine-minirootfs-${ALPINE_VERSION}-${ARCH}.tar.gz"
MINIROOTFS_URL="${MIRROR}/${ALPINE_BRANCH}/releases/${ARCH}/${MINIROOTFS_FILE}"
# sha256 oficial (latest-releases.yaml do Alpine 3.24.1 aarch64).
MINIROOTFS_SHA256="f55a90f69052c5bd6f92cb09a8f47065970830b194c917a006fb94028e721259"

IMG_SIZE="2G"          # tamanho total da imagem (SD >= 2 GB; encolha depois com pishrink)
BOOT_SIZE_MIB=256      # partição de boot FAT32
HOSTNAME="calculadora"
KIOSK_USER="kiosk"

# --- Voz neural (Piper + cadu) ---------------------------------------------
# O piper-tts NÃO tem wheel musl no PyPI (design D7): um wheel musl/aarch64 é
# compilado UMA vez (tarefa 2.1) e reaproveitado aqui. Aponte para um arquivo
# local (PIPER_WHEEL) OU uma URL (PIPER_WHEEL_URL + PIPER_WHEEL_SHA256).
PIPER_WHEEL="${PIPER_WHEEL:-}"
PIPER_WHEEL_URL="${PIPER_WHEEL_URL:-}"
PIPER_WHEEL_SHA256="${PIPER_WHEEL_SHA256:-}"
# Escape hatch (opt-in): sem wheel pré-compilado, PIPER_BUILD_IN_CHROOT=1 compila
# o wheel DENTRO do chroot qemu (build-base/cmake/git/ninja + pip wheel da tag do
# git; o toolchain é removido depois). Autossuficiente, porém LENTO sob qemu
# (dezenas de min). O design (D7) prefere o wheel pré-compilado fora do build.
PIPER_BUILD_IN_CHROOT="${PIPER_BUILD_IN_CHROOT:-0}"
PIPER_GIT_URL="${PIPER_GIT_URL:-https://github.com/OHF-Voice/piper1-gpl}"
PIPER_GIT_REF="${PIPER_GIT_REF:-v1.8.0}"   # tags do repo piper1-gpl têm prefixo 'v'
# Onde a voz fica embutida no aparelho (o mesmo caminho que o speech.py procura).
VOICE_DIR="/opt/piper/voices"
# sha256 fixo da voz cadu (repassado ao download-piper-voice.sh). Preencha assim
# que a equipe tiver o hash (tarefa 2.2); com STRICT=1 o download recusa voz sem hash.
export CADU_ONNX_SHA256="${CADU_ONNX_SHA256:-}"
export CADU_JSON_SHA256="${CADU_JSON_SHA256:-}"

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"   # .../TCC_Calculadora_Acessivel
OVERLAY_DIR="${SCRIPT_DIR}/overlay"
PACKAGES_FILE="${SCRIPT_DIR}/packages"
REQUIREMENTS="${REPO_ROOT}/software/requirements.txt"
SOFTWARE_DIR="${REPO_ROOT}/software"
VOICE_SCRIPT="${REPO_ROOT}/scripts/download-piper-voice.sh"

WORK_DIR="${SCRIPT_DIR}/.work"          # ignorado pelo git
DL_DIR="${WORK_DIR}/downloads"
ROOTFS="${WORK_DIR}/rootfs"
MNT="${WORK_DIR}/mnt"
OUT_IMG="${SCRIPT_DIR}/calculadora-alpine-${ALPINE_VERSION}-${ARCH}.img"

LOOP_DEV=""

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[aviso]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[erro]\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Limpeza (sempre desmonta e solta o loop, mesmo em erro)
# ---------------------------------------------------------------------------
cleanup() {
    set +e
    mountpoint -q "${MNT}/boot" && umount "${MNT}/boot"
    mountpoint -q "${MNT}"      && umount "${MNT}"
    # /dev e /sys entram como rbind: desmontar recursivo+lazy p/ não deixar submounts.
    for m in proc sys dev; do
        mountpoint -q "${ROOTFS}/${m}" && umount -R -l "${ROOTFS}/${m}"
    done
    [ -n "${LOOP_DEV}" ] && losetup -d "${LOOP_DEV}" 2>/dev/null
    set -e
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Pré-condições
# ---------------------------------------------------------------------------
check_prereqs() {
    [ "$(id -u)" -eq 0 ] || die "Rode como root (sudo): o build usa loopback, mount e chroot."

    local missing=0
    for t in qemu-aarch64-static losetup parted sfdisk mkfs.vfat mkfs.ext4 sha256sum tar blkid curl; do
        command -v "$t" >/dev/null 2>&1 || { warn "faltando: $t"; missing=1; }
    done
    if [ "$missing" -ne 0 ]; then
        die "Instale as dependências (Debian/derivados):
  sudo apt install -y qemu-user-static binfmt-support parted util-linux dosfstools e2fsprogs curl
Se o chroot aarch64 não executar, registre o binfmt:
  sudo update-binfmts --enable qemu-aarch64   (ou: docker run --privileged --rm tonistiigi/binfmt --install arm64)"
    fi

    # binfmt: precisa executar binários aarch64 dentro do chroot.
    if [ ! -e /proc/sys/fs/binfmt_misc/qemu-aarch64 ] && [ ! -e /proc/sys/fs/binfmt_misc/qemu-aarch64-static ]; then
        warn "binfmt qemu-aarch64 não parece registrado; o chroot pode falhar."
        warn "Registre com: sudo update-binfmts --enable qemu-aarch64"
    fi

    [ -f "${PACKAGES_FILE}" ]  || die "não achei ${PACKAGES_FILE}"
    [ -f "${REQUIREMENTS}" ]   || die "não achei ${REQUIREMENTS}"
    [ -d "${SOFTWARE_DIR}" ]   || die "não achei ${SOFTWARE_DIR}"
    [ -d "${OVERLAY_DIR}" ]    || die "não achei ${OVERLAY_DIR}"
}

# Caminho do qemu estático (nome varia entre distros).
qemu_static_path() {
    command -v qemu-aarch64-static || echo /usr/bin/qemu-aarch64-static
}

# ---------------------------------------------------------------------------
# 1. Baixar + verificar minirootfs
# ---------------------------------------------------------------------------
download_and_verify() {
    log "Baixando minirootfs ${ALPINE_VERSION} (${ARCH})"
    mkdir -p "${DL_DIR}"
    local tarball="${DL_DIR}/${MINIROOTFS_FILE}"
    if [ ! -f "${tarball}" ]; then
        curl -fSL "${MINIROOTFS_URL}" -o "${tarball}"
    fi
    log "Verificando sha256"
    echo "${MINIROOTFS_SHA256}  ${tarball}" | sha256sum -c - \
        || die "checksum do minirootfs não confere (download corrompido ou versão mudou)."
}

# ---------------------------------------------------------------------------
# 2. Extrair rootfs e preparar chroot
# ---------------------------------------------------------------------------
prepare_rootfs() {
    log "Extraindo rootfs"
    rm -rf "${ROOTFS}"
    mkdir -p "${ROOTFS}"
    tar -xzf "${DL_DIR}/${MINIROOTFS_FILE}" -C "${ROOTFS}"

    # qemu para rodar binários aarch64 no chroot.
    install -Dm755 "$(qemu_static_path)" "${ROOTFS}/usr/bin/qemu-aarch64-static"

    # DNS + repositórios (main + community) para o apk baixar os pacotes.
    cp /etc/resolv.conf "${ROOTFS}/etc/resolv.conf"
    cat > "${ROOTFS}/etc/apk/repositories" <<EOF
${MIRROR}/${ALPINE_BRANCH}/main
${MIRROR}/${ALPINE_BRANCH}/community
EOF

    mount_chroot
}

# Prepara o chroot para uso: qemu + montagens. Idempotente, serve tanto para o
# build do zero quanto para REUSE_ROOTFS=1 (onde o rootfs já existe, mas o qemu
# foi removido no fim do build anterior e as montagens não existem mais).
mount_chroot() {
    install -Dm755 "$(qemu_static_path)" "${ROOTFS}/usr/bin/qemu-aarch64-static"
    mountpoint -q "${ROOTFS}/proc" || mount -t proc none "${ROOTFS}/proc"
    # IMPORTANTE: /dev e /sys do host têm propagação "shared". Um rbind puro põe
    # as cópias no MESMO peer group do original, então o umount da limpeza
    # PROPAGA DE VOLTA e desmonta o /dev/shm e o /dev/pts do host — o que quebra
    # todo app Electron/Chromium (VS Code, Chrome) da máquina de build até o
    # próximo boot. O --make-rslave corta a propagação de volta (host -> chroot
    # continua funcionando, chroot -> host não).
    if ! mountpoint -q "${ROOTFS}/sys"; then
        mount --rbind /sys "${ROOTFS}/sys"
        mount --make-rslave "${ROOTFS}/sys"
    fi
    if ! mountpoint -q "${ROOTFS}/dev"; then
        mount --rbind /dev "${ROOTFS}/dev"
        mount --make-rslave "${ROOTFS}/dev"
    fi
}

# Executa um comando dentro do rootfs (aarch64 via qemu/binfmt).
in_chroot() { chroot "${ROOTFS}" /usr/bin/qemu-aarch64-static /bin/sh -c "$*"; }

# ---------------------------------------------------------------------------
# 3. Instalar pacotes (apk) + kernel/firmware + libs Python (pip)
# ---------------------------------------------------------------------------
install_packages() {
    log "apk update + instalação dos pacotes"
    # Lista de pacotes: uma linha por pacote, ignora comentários/linhas vazias.
    local pkgs
    pkgs="$(grep -vE '^\s*(#|$)' "${PACKAGES_FILE}" | awk '{print $1}' | tr '\n' ' ')"

    in_chroot "apk update"
    in_chroot "apk add --no-progress ${pkgs}"

    log "Gerando initramfs do Pi (mkinitfs)"
    # Features mínimas para montar o root ext4 no cartão (mmc) e vídeo KMS.
    cat > "${ROOTFS}/etc/mkinitfs/mkinitfs.conf" <<'EOF'
features="base ext4 mmc kms keymap"
EOF
    local kver
    kver="$(ls "${ROOTFS}/lib/modules" | head -n1)"
    [ -n "${kver}" ] || die "não achei módulos do kernel em /lib/modules (linux-rpi instalou?)."
    in_chroot "mkinitfs -o /boot/initramfs-rpi ${kver}"

    log "Instalando libs Python (pip) de requirements.txt"
    install -Dm644 "${REQUIREMENTS}" "${ROOTFS}/tmp/requirements.txt"
    # O marcador do requirements.txt pula o piper-tts em aarch64: aqui o pip só
    # instala ttkbootstrap. O Piper vem do wheel musl pré-compilado (install_piper).
    # --retries/--timeout: a rede do chroot emulado (qemu) reseta conexoes com
    # frequencia; o pillow (compilado, grande) saiu para o apk por isso mesmo,
    # e o que sobra aqui e' um wheel pequeno e puro Python.
    in_chroot "pip3 install --break-system-packages --no-cache-dir \
        --retries 10 --timeout 60 -r /tmp/requirements.txt"

    install_piper
}

# ---------------------------------------------------------------------------
# 3b. Voz neural: wheel musl do piper-tts (--no-deps sobre py3-onnxruntime) + cadu
# ---------------------------------------------------------------------------
# Garante o Piper num rootfs REAPROVEITADO (REUSE_ROOTFS=1).
#
# install_piper vive dentro de install_packages, que o caminho de reuso pula -
# sem isto, `make rpi-img CONTINUE=1` produziria uma imagem SEM voz neural e em
# silêncio: no aparelho o app cairia no fallback espeak-ng (WRN-011) e ninguém
# perceberia até ouvir a voz errada. Verifica antes de instalar para não repetir
# o download/verificação da voz a cada rebuild.
ensure_piper() {
    if in_chroot "python3 -c 'import piper'" >/dev/null 2>&1; then
        log "Piper já presente no rootfs reaproveitado"
        return 0
    fi
    warn "Piper ausente no rootfs reaproveitado — instalando agora."
    install_piper
}

install_piper() {
    log "Instalando o Piper (voz cadu)"

    # 1) Instalar o piper: wheel pré-compilado (local/URL) OU build no chroot.
    #    Em todos os casos, --no-deps: o onnxruntime vem do apk (py3-onnxruntime).
    if [ -n "${PIPER_WHEEL}" ] || [ -n "${PIPER_WHEEL_URL}" ]; then
        install_piper_prebuilt
    elif [ "${PIPER_BUILD_IN_CHROOT}" = "1" ]; then
        build_and_install_piper_in_chroot
    else
        die "Sem wheel do Piper. Escolha um caminho:
  - wheel pré-compilado (design D7):  PIPER_WHEEL=<arquivo.whl>  ou  PIPER_WHEEL_URL=<url>
  - compilar no chroot (lento):       PIPER_BUILD_IN_CHROOT=1
O sdist do PyPI é incompleto, por isso não dá para 'pip install piper-tts' direto em musl."
    fi

    # pathvalidate (Python puro) é dependência do piper e não veio pelo --no-deps.
    in_chroot "pip3 install --break-system-packages --no-cache-dir pathvalidate"

    # 2) Gate: o piper tem de importar no Python do rootfs (3.14/musl).
    in_chroot "python3 -c 'import piper; print(\"piper OK\")'" \
        || die "piper não importa no rootfs — ver design (risco Python 3.14/musl)."

    # 3) Enxugar os MODELOS de outras línguas embutidos no piper (~26 MB): a
    #    imagem só usa pt-BR.
    #
    #    Apagar os DIRETÓRIOS (como se fazia antes) quebrava o pacote: o
    #    piper/voice.py faz `from .tashkeel import TashkeelDiacritizer` no topo
    #    do módulo, sem condição — sem o pacote, `import piper` morre com
    #    ModuleNotFoundError e a imagem sai sem voz nenhuma.
    #
    #    Então só os .onnx saem (21 MB do hebraico + 4,8 MB do árabe) e todo o
    #    código Python fica. Esses modelos só são carregados para voz árabe (ar)
    #    ou hebraica (he), e a instanciação é preguiçosa (voice.py), então o
    #    caminho pt-BR nunca os toca.
    in_chroot 'rm -f /usr/lib/python3*/site-packages/piper/hebrew/nakdimon.onnx \
                     /usr/lib/python3*/site-packages/piper/tashkeel/model.onnx || true'

    # 4) Baixar e verificar a voz cadu direto no rootfs (STRICT: nunca embutir voz sem sha256).
    [ -f "${VOICE_SCRIPT}" ] || die "não achei ${VOICE_SCRIPT}"
    log "Baixando/verificando a voz cadu em ${ROOTFS}${VOICE_DIR}"
    STRICT=1 "${VOICE_SCRIPT}" "${ROOTFS}${VOICE_DIR}"
}

# Resolve o wheel pré-compilado (arquivo local ou download verificado) e instala.
# Resolve o valor de PIPER_WHEEL num arquivo que existe de facto.
#
# Absorve dois tropecos reais do jeito como o Makefile chama este script:
#   - ele faz `cd` para a pasta do script antes de executar, entao um caminho
#     RELATIVO a raiz do repositorio (o natural de digitar) resolveria errado;
#   - ele passa o valor entre aspas, entao um glob como "piper_tts-*.whl" chega
#     aqui LITERAL, com o asterisco, e nunca casa com [ -f ].
# compgen -G expande o padrao sem sofrer word splitting - necessario porque o
# caminho deste repositorio contem espacos ("Area de trabalho").
resolve_wheel_path() {
    local spec="$1" candidate match
    for candidate in "${spec}" "${REPO_ROOT}/${spec}"; do
        if [ -f "${candidate}" ]; then
            printf '%s\n' "${candidate}"
            return 0
        fi
        match="$(compgen -G "${candidate}" 2>/dev/null | head -n1)" || true
        if [ -n "${match}" ] && [ -f "${match}" ]; then
            printf '%s\n' "${match}"
            return 0
        fi
    done
    return 1
}

install_piper_prebuilt() {
    log "Piper: usando wheel pré-compilado"
    # O NOME do arquivo é significativo: o pip lê nome, versão e tags do próprio
    # nome do wheel e recusa qualquer coisa fora do padrão
    # {nome}-{versao}-{python}-{abi}-{plataforma}.whl, com
    # "Invalid wheel filename (wrong number of parts)". Por isso o nome ORIGINAL
    # é preservado aqui, em vez de normalizado para algo genérico.
    local wheel_host wheel_name
    if [ -n "${PIPER_WHEEL}" ]; then
        local wheel_src
        wheel_src="$(resolve_wheel_path "${PIPER_WHEEL}")" || die \
"PIPER_WHEEL não resolve para nenhum arquivo: ${PIPER_WHEEL}
Tentei o caminho como dado e relativo a ${REPO_ROOT}, expandindo globs.
Gere o wheel com 'make piper-wheel' (sai em system/rpi-os/alpine/wheels/)."
        log "Wheel do Piper: ${wheel_src}"
        wheel_name="$(basename "${wheel_src}")"
        wheel_host="${WORK_DIR}/${wheel_name}"
        cp -f "${wheel_src}" "${wheel_host}"
    else
        log "Baixando o wheel do Piper"
        # Nome vindo da URL, sem query string nem fragmento.
        wheel_name="$(basename "${PIPER_WHEEL_URL%%[?#]*}")"
        wheel_host="${WORK_DIR}/${wheel_name}"
        curl -fSL "${PIPER_WHEEL_URL}" -o "${wheel_host}"
        if [ -n "${PIPER_WHEEL_SHA256}" ]; then
            echo "${PIPER_WHEEL_SHA256}  ${wheel_host}" | sha256sum -c - \
                || die "sha256 do wheel do Piper não confere."
        else
            warn "PIPER_WHEEL_SHA256 não fixado — build não reprodutível."
        fi
    fi

    # Recusar aqui, com o nome à vista, é mais claro que o erro do pip lá dentro.
    case "${wheel_name}" in
        *-*-*-*-*.whl) ;;
        *) die "nome de wheel inválido para o pip: '${wheel_name}'
Esperado {nome}-{versao}-{python}-{abi}-{plataforma}.whl (ex.:
piper_tts-1.8.0-cp39-abi3-linux_aarch64.whl). Não renomeie o arquivo." ;;
    esac

    cp -f "${wheel_host}" "${ROOTFS}/tmp/${wheel_name}"
    in_chroot "pip3 install --break-system-packages --no-cache-dir --no-deps '/tmp/${wheel_name}'"
    rm -f "${ROOTFS}/tmp/${wheel_name}"
}

# Escape hatch: compila o wheel musl/aarch64 do piper-tts DENTRO do chroot qemu.
# Instala o toolchain como grupo virtual (.piper-build) e o remove no fim, para o
# ~200 MB de build-base/cmake NÃO ir para a imagem. Lento sob qemu.
build_and_install_piper_in_chroot() {
    warn "Piper: compilando o wheel no chroot (PIPER_BUILD_IN_CHROOT=1) — LENTO sob qemu."
    # O CMakeLists do piper baixa e compila o espeak-ng estático (precisa de git,
    # cmake, ninja e compilador C); a extensão liga contra Python.h (python3-dev).
    # linux-headers e obrigatorio: o espeak-ng inclui <linux/limits.h>, que no
    # Alpine nao acompanha o build-base (ver scripts/build-piper-wheel.sh).
    in_chroot "apk add --no-progress --virtual .piper-build \
        build-base cmake git ninja linux-headers python3-dev"
    in_chroot "rm -rf /tmp/piper-wheelhouse && mkdir -p /tmp/piper-wheelhouse"
    # Build isolation (padrão) puxa o backend scikit-build-core do PyPI; --no-deps
    # não baixa o onnxruntime (vem do apk). CMake/ninja/git são os do apk (PATH).
    in_chroot "pip3 wheel --no-cache-dir --no-deps -w /tmp/piper-wheelhouse \
        'piper-tts @ git+${PIPER_GIT_URL}@${PIPER_GIT_REF}'" \
        || die "falha ao compilar o wheel do Piper no chroot (ver log; tag=${PIPER_GIT_REF})."
    in_chroot "pip3 install --break-system-packages --no-cache-dir --no-deps /tmp/piper-wheelhouse/piper_tts-*.whl"
    # Guardar o wheel fora do rootfs para reuso (evita recompilar no próximo build).
    cp -f "${ROOTFS}"/tmp/piper-wheelhouse/piper_tts-*.whl "${WORK_DIR}/" 2>/dev/null \
        && log "Wheel salvo em ${WORK_DIR}/ (reuse com PIPER_WHEEL=... no próximo build)." || true
    in_chroot "apk del .piper-build" || warn "não consegui remover o toolchain .piper-build."
    in_chroot "rm -rf /tmp/piper-wheelhouse"
}

# ---------------------------------------------------------------------------
# 4. Configurar sistema: hostname, fstab, autologin, serviços, usuário kiosk
# ---------------------------------------------------------------------------
configure_system() {
    log "Configurando sistema (hostname, fstab, autologin, serviços)"

    echo "${HOSTNAME}" > "${ROOTFS}/etc/hostname"

    # fstab: SD do Pi = mmcblk0 (p1 boot FAT, p2 root ext4).
    cat > "${ROOTFS}/etc/fstab" <<'EOF'
/dev/mmcblk0p1  /boot  vfat  defaults           0 2
/dev/mmcblk0p2  /      ext4  defaults,noatime   0 1
tmpfs           /tmp   tmpfs defaults           0 0
EOF

    # Usuário kiosk (sem senha; o autologin não pede senha) e grupos de hardware.
    in_chroot "adduser -D -s /bin/sh ${KIOSK_USER} || true"
    # video/audio/input/tty já existem no Alpine base. gpio e i2c NÃO existem —
    # são convenção do Raspberry Pi OS, não do Alpine — então é preciso criá-los
    # aqui: a regra overlay/etc/udev/rules.d/99-gpio.rules refere-se a eles e o
    # udev ignora em silêncio uma regra cujo grupo não existe, deixando o
    # /dev/gpiochip0 em root:root 0600 e o teclado morto por falta de permissão.
    in_chroot "addgroup -S gpio 2>/dev/null || true"
    in_chroot "addgroup -S i2c 2>/dev/null || true"
    for g in video audio input tty gpio i2c; do
        in_chroot "addgroup ${KIOSK_USER} ${g} 2>/dev/null || true"
    done

    # Autologin do kiosk no tty1 via agetty (BusyBox init lê /etc/inittab).
    # Substitui a linha de getty do tty1; se não existir, acrescenta.
    if grep -qE '^tty1::' "${ROOTFS}/etc/inittab"; then
        sed -i -E "s|^tty1::.*|tty1::respawn:/sbin/agetty --autologin ${KIOSK_USER} --noclear tty1 linux|" \
            "${ROOTFS}/etc/inittab"
    else
        echo "tty1::respawn:/sbin/agetty --autologin ${KIOSK_USER} --noclear tty1 linux" \
            >> "${ROOTFS}/etc/inittab"
    fi

    # Serviços OpenRC essenciais (tolerante: avisa se algum nome não existir).
    add_svc() { in_chroot "rc-update add $1 $2" 2>/dev/null || warn "serviço '$1' não encontrado (runlevel $2)"; }
    for s in devfs sysfs udev udev-trigger udev-settle; do add_svc "$s" sysinit; done
    for s in hwclock modules sysctl hostname bootmisc syslog localmount; do add_svc "$s" boot; done
    add_svc local default

    # Garante que /opt/calculadora existe (o app entra no passo install_app).
    mkdir -p "${ROOTFS}/opt/calculadora"
}

# ---------------------------------------------------------------------------
# 5. Overlay (kiosk: .profile, .xinitrc, asound.conf, usercfg.txt) + app
# ---------------------------------------------------------------------------
apply_overlay_and_app() {
    log "Aplicando overlay"
    # Copia tudo de overlay/ preservando a árvore (home/, etc/, boot/).
    cp -a "${OVERLAY_DIR}/." "${ROOTFS}/"

    # Dono do home do kiosk e permissão de execução do .xinitrc.
    in_chroot "chown -R ${KIOSK_USER}:${KIOSK_USER} /home/${KIOSK_USER}"
    chmod 0755 "${ROOTFS}/home/${KIOSK_USER}/.xinitrc"

    log "Copiando a aplicação para /opt/calculadora/software"
    rm -rf "${ROOTFS}/opt/calculadora/software"
    cp -a "${SOFTWARE_DIR}" "${ROOTFS}/opt/calculadora/software"
    # Limpa caches/venv que não devem ir para a imagem.
    find "${ROOTFS}/opt/calculadora/software" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
    find "${ROOTFS}/opt/calculadora/software" -type d -name '.venv' -exec rm -rf {} + 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# 6. Smoke tests no chroot (falha cedo se o ambiente base quebrar)
# ---------------------------------------------------------------------------
smoke_tests() {
    log "Smoke: import de tkinter + ttkbootstrap (gate obrigatório)"
    # 'import tkinter' não abre janela; valida o _tkinter em musl e o ttkbootstrap.
    in_chroot "python3 -c 'import tkinter, ttkbootstrap; print(\"tkinter/ttkbootstrap OK\")'" \
        || die "Tkinter/ttkbootstrap não importam no rootfs — base gráfica quebrada (ver design, risco musl×Tkinter)."

    log "Smoke: síntese real do Piper (voz cadu -> PCM), sem placa de som — gate obrigatório"
    # Síntese não precisa de áudio: o Piper gera PCM em memória. Isso valida o
    # import do piper/onnxruntime no Python 3.14/musl (não testado upstream) e a
    # voz cadu embutida, e falha CEDO se algo disso quebrar — mais forte que o
    # antigo pyttsx3.init(). A REPRODUÇÃO pelo aplay é validada NO HARDWARE
    # (README, checklist). O qemu-user é lento: a síntese pode levar dezenas de s.
    install -Dm644 /dev/stdin "${ROOTFS}/tmp/piper_smoke.py" <<PYEOF
import sys
from pathlib import Path
from piper import PiperVoice
model = Path("${VOICE_DIR}/pt_BR-cadu-medium.onnx")
cfg = Path(str(model) + ".json")
voice = PiperVoice.load(str(model), config_path=str(cfg) if cfg.is_file() else None)
pcm = b"".join(
    getattr(c, "audio_int16_bytes", b"") for c in voice.synthesize("Calculadora pronta")
)
assert pcm, "Piper devolveu PCM vazio"
print("Piper OK: %d bytes de PCM da voz cadu" % len(pcm))
PYEOF
    in_chroot "python3 /tmp/piper_smoke.py" \
        || die "Síntese do Piper falhou no chroot (import 3.14/musl, onnxruntime ou voz cadu) — ver design, risco Python 3.14."
    rm -f "${ROOTFS}/tmp/piper_smoke.py"
}

# ---------------------------------------------------------------------------
# 7. Montar a imagem .img (boot FAT + root ext4)
# ---------------------------------------------------------------------------
build_image() {
    log "Criando imagem ${OUT_IMG} (${IMG_SIZE})"

    # Desmonta o chroot antes de empacotar (não copiar proc/sys/dev).
    for m in dev/pts dev proc sys; do
        mountpoint -q "${ROOTFS}/${m}" && umount -l "${ROOTFS}/${m}" || true
    done
    rm -f "${ROOTFS}/usr/bin/qemu-aarch64-static"   # não precisa no aparelho

    rm -f "${OUT_IMG}"
    truncate -s "${IMG_SIZE}" "${OUT_IMG}"

    # Tabela MBR: p1 FAT32 (boot, com flag lba), p2 ext4 (root).
    parted -s "${OUT_IMG}" mklabel msdos
    parted -s "${OUT_IMG}" mkpart primary fat32 1MiB "$((BOOT_SIZE_MIB + 1))MiB"
    parted -s "${OUT_IMG}" set 1 lba on
    parted -s "${OUT_IMG}" set 1 boot on
    parted -s "${OUT_IMG}" mkpart primary ext4 "$((BOOT_SIZE_MIB + 1))MiB" 100%

    # O parted grava o ID de tipo do MBR a partir do sistema de arquivos que
    # encontra na partição — e como ela ainda está vazia aqui, a p1 acaba com
    # 0x83 (Linux) em vez de 0x0c (W95 FAT32 LBA). O bootloader da Pi 4 procura
    # a partição de boot pelo tipo FAT no MBR, então forçamos 0x0c.
    sfdisk --part-type "${OUT_IMG}" 1 0c

    LOOP_DEV="$(losetup -f --show -P "${OUT_IMG}")"
    log "Loop: ${LOOP_DEV}"
    local bootp="${LOOP_DEV}p1" rootp="${LOOP_DEV}p2"

    mkfs.vfat -F32 -n BOOT "${bootp}" >/dev/null
    mkfs.ext4 -q -L root "${rootp}"

    mkdir -p "${MNT}"
    mount "${rootp}" "${MNT}"
    mkdir -p "${MNT}/boot"
    mount "${bootp}" "${MNT}/boot"

    log "Copiando rootfs para a partição root"
    # Copia tudo do rootfs EXCETO o diretório /boot: o conteúdo dele vai para a
    # partição FAT (populate_boot). Excluímos o PRÓPRIO './boot' (não só './boot/*')
    # porque ${MNT}/boot é a FAT montada — recriar/chown esse diretório numa FAT dá
    # "Operação não permitida". O mountpoint /boot já existe no ext4 (mkdir acima).
    tar -C "${ROOTFS}" --exclude='./boot' -cf - . | tar -C "${MNT}" -xf -

    log "Montando partição de boot (firmware + kernel + dtbs)"
    populate_boot "${ROOTFS}/boot" "${MNT}/boot"

    sync
    umount "${MNT}/boot"
    umount "${MNT}"
    losetup -d "${LOOP_DEV}"; LOOP_DEV=""

    log "Pronto: ${OUT_IMG}"
}

# Copia firmware/kernel/dtbs do rootfs para a FAT e escreve config.txt/cmdline.txt.
populate_boot() {
    local src="$1" dst="$2"

    # Firmware do Pi 4 + kernel + initramfs (nomes do pacote raspberrypi-bootloader/linux-rpi).
    # VALIDAR NO HARDWARE: o layout exato pode variar por versão do Alpine.
    cp -a "${src}/." "${dst}/" 2>/dev/null || true

    # dtbs/overlays podem estar em /boot/dtbs-rpi/. O firmware do Pi procura o .dtb
    # e a pasta overlays/ na RAIZ da partição de boot — então achatamos aqui.
    local dtb
    dtb="$(find "${src}" -name 'bcm2711-rpi-4-b.dtb' 2>/dev/null | head -n1)"
    if [ -n "${dtb}" ]; then
        cp -a "${dtb}" "${dst}/bcm2711-rpi-4-b.dtb"
    else
        warn "bcm2711-rpi-4-b.dtb não encontrado no rootfs — VALIDAR NO HARDWARE."
    fi
    local ovl
    ovl="$(find "${src}" -type d -name overlays 2>/dev/null | head -n1)"
    [ -n "${ovl}" ] && { mkdir -p "${dst}/overlays"; cp -a "${ovl}/." "${dst}/overlays/"; }

    # config.txt base: carrega kernel/initramfs e inclui o usercfg.txt (overlay).
    cat > "${dst}/config.txt" <<'EOF'
# Gerado por build-alpine-img.sh. Overrides do produto ficam em usercfg.txt.
[all]
arm_64bit=1
kernel=vmlinuz-rpi
initramfs initramfs-rpi followkernel
disable_splash=1
include usercfg.txt
EOF

    # cmdline.txt: root no cartão (mmcblk0p2), console no tty1, boot silencioso.
    printf 'root=/dev/mmcblk0p2 rootfstype=ext4 rootwait console=tty1 quiet\n' > "${dst}/cmdline.txt"
}

# ---------------------------------------------------------------------------
main() {
    check_prereqs
    mkdir -p "${WORK_DIR}"
    # REUSE_ROOTFS=1 reaproveita os PACOTES já instalados em ${ROOTFS} (pula
    # download/apk/pip, a fase lenta e pesada) mas RECOPIA o app e o overlay —
    # senão a imagem sairia com uma versão antiga de software/. Use ao iterar no
    # código do app sem mudar dependências.
    if [ "${REUSE_ROOTFS:-0}" = "1" ] && [ -d "${ROOTFS}/etc" ]; then
        warn "REUSE_ROOTFS=1: reaproveitando pacotes de ${ROOTFS} (pulando download/apk/pip)."
        mount_chroot
        ensure_piper            # a voz neural não pode faltar por causa do reuso
        apply_overlay_and_app   # app/overlay sempre atualizados a partir do repo
        smoke_tests
    else
        download_and_verify
        prepare_rootfs
        install_packages
        configure_system
        apply_overlay_and_app
        smoke_tests
    fi
    build_image
    cat <<EOF

===========================================================================
Imagem gerada: ${OUT_IMG}

Grave no cartão (substitua sdX pelo SEU cartão — cuidado, apaga o alvo!):
  sudo dd if=${OUT_IMG} of=/dev/sdX bs=4M conv=fsync status=progress

Depois insira no Raspberry Pi 4B e ligue. Ele deve arrancar direto na
calculadora. Rode a checklist de validação do README.md (seção 9 do tasks).
===========================================================================
EOF
}

main "$@"
