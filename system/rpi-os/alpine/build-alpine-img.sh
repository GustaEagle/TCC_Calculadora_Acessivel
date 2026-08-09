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

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"   # .../TCC_Calculadora_Acessivel
OVERLAY_DIR="${SCRIPT_DIR}/overlay"
PACKAGES_FILE="${SCRIPT_DIR}/packages"
REQUIREMENTS="${REPO_ROOT}/software/requirements.txt"
SOFTWARE_DIR="${REPO_ROOT}/software"

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
    for t in qemu-aarch64-static losetup parted mkfs.vfat mkfs.ext4 sha256sum tar blkid curl; do
        command -v "$t" >/dev/null 2>&1 || { warn "faltando: $t"; missing=1; }
    done
    if [ "$missing" -ne 0 ]; then
        die "Instale as dependências (Debian/derivados):
  sudo apt install -y qemu-user-static binfmt-support parted dosfstools e2fsprogs curl
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

    mount -t proc none "${ROOTFS}/proc"
    mount --rbind /sys "${ROOTFS}/sys"
    mount --rbind /dev "${ROOTFS}/dev"
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
    in_chroot "pip3 install --break-system-packages --no-cache-dir -r /tmp/requirements.txt"

    # pyttsx3 carrega libespeak-ng.so.1; se algum caminho procurar libespeak.so.1,
    # criar symlink de compatibilidade (defensivo). Ver design D6.
    in_chroot 'nglib=$(ls /usr/lib/libespeak-ng.so.1* 2>/dev/null | head -n1); \
               [ -n "$nglib" ] && [ ! -e /usr/lib/libespeak.so.1 ] && ln -sf "$nglib" /usr/lib/libespeak.so.1 || true'
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
    for g in video audio input tty; do
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

    log "Smoke: inicialização do TTS (pyttsx3 -> espeak-ng)"
    # Só init + enumeração de vozes: reproduzir áudio (runAndWait) exige placa de
    # som e é validado NO HARDWARE (README, checklist 9.3). Aqui é aviso, não gate,
    # porque o chroot emulado (qemu-user) não tem áudio e pode dar falso negativo.
    if in_chroot "python3 -c 'import pyttsx3; e=pyttsx3.init(); print(\"vozes:\", len(e.getProperty(\"voices\")))'"; then
        log "TTS inicializou no chroot."
    else
        warn "pyttsx3.init() falhou no chroot (pode ser limitação do qemu-user). VALIDAR NO HARDWARE (checklist 9.3)."
    fi
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
    parted -s "${OUT_IMG}" mkpart primary ext4 "$((BOOT_SIZE_MIB + 1))MiB" 100%

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
    # REUSE_ROOTFS=1 reaproveita ${ROOTFS} já montado e pula download/apk/pip/smoke
    # — útil para reiterar só a fase de imagem sem refazer o rootfs (~15 min).
    if [ "${REUSE_ROOTFS:-0}" = "1" ] && [ -d "${ROOTFS}/etc" ]; then
        warn "REUSE_ROOTFS=1: reaproveitando ${ROOTFS} (pulando download/apk/pip/smoke)."
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
