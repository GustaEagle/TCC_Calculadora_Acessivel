<#
.SYNOPSIS
    Gera a imagem Alpine do Raspberry Pi a partir do WINDOWS, usando uma VM
    Debian no VirtualBox (equivalente ao `make rpi-img`, que so roda num Linux).

.DESCRIPTION
    O build precisa de um kernel Linux (loop device, mount, chroot, binfmt_misc,
    ext4/vfat) - nada disso existe no Windows. Este script NAO reimplementa o
    build: ele liga uma VM Debian 12 no VirtualBox, envia o repositorio, roda o
    MESMO build-alpine-img.sh la dentro e traz o .img de volta para esta pasta.
    A imagem sai identica a gerada num PC Linux.

    Nao precisa de WSL, Hyper-V, Docker nem reiniciar o Windows: so do VirtualBox
    e do cliente OpenSSH (que ja vem no Windows 10/11).

    Na 1a execucao ele cria a VM sozinho (fica em -VmDir):
      * baixa a imagem cloud oficial do Debian 12 (~430 MB) e confere o SHA512;
      * gera uma chave SSH so para essa VM e um ISO cloud-init com o usuario;
      * cria a VM (NAT, SSH em 127.0.0.1:-SshPort) e instala as dependencias.
    Nas proximas, so liga a VM, atualiza software/ e overlay/ e roda o build.
    A VM e desligada ao final (tambem em erro ou Ctrl+C).

    O rootfs fica no disco da VM entre execucoes, entao -Action continue funciona
    como o `make rpi-img-continue`. O checkout do Windows vem com CRLF
    (core.autocrlf=true); a copia na VM e convertida para LF antes do build,
    senao o .sh, a lista `packages` e o .xinitrc/.profile do kiosk quebram.

    Este arquivo e ASCII puro de proposito: o Windows PowerShell 5.1 le arquivos
    UTF-8 sem BOM como ANSI e estragaria os acentos.

.PARAMETER Action
    build      gera a imagem do ZERO (baixa, apk, pip, empacota)   = make rpi-img
    continue   reaproveita o rootfs da VM e refaz so o .img         = make rpi-img-continue
    clean      apaga o .work/ da VM (preserva o .img desta pasta)   = make rpi-img-clean
    distclean  apaga o .work/ da VM E o .img/build.log desta pasta  = make rpi-img-distclean
    vm-remove  apaga a VM inteira e seus arquivos (libera o disco)

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\system\rpi-os\alpine\build-alpine-img.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\system\rpi-os\alpine\build-alpine-img.ps1 -Action continue
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\system\rpi-os\alpine\build-alpine-img.ps1 -Action vm-remove
#>
[CmdletBinding()]
param(
    [ValidateSet('build', 'continue', 'clean', 'distclean', 'vm-remove')]
    [string]$Action = 'build',

    # Onde ficam a VM, a chave SSH e os downloads.
    [string]$VmDir = (Join-Path $env:LOCALAPPDATA 'calculadora-rpi-vm'),

    [ValidateRange(1, 64)]
    [int]$Cpus = 4,

    [ValidateRange(1024, 65536)]
    [int]$MemoryMB = 4096,

    [ValidateRange(1025, 65535)]
    [int]$SshPort = 2229
)

$ErrorActionPreference = 'Stop'

$ScriptDir = $PSScriptRoot
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir '..\..\..')).Path

$VmName = 'calculadora-rpi-builder'
$DebianUrl = 'https://cloud.debian.org/images/cloud/bookworm/latest'
$DebianImage = 'debian-12-generic-amd64.qcow2'
$DiskMB = 20480
$SshHost = 'calc-vm'

$Cpus = [Math]::Min($Cpus, [Environment]::ProcessorCount)
$totalMB = [int]((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1MB)
$MemoryMB = [Math]::Min($MemoryMB, [int]($totalMB / 2))

$SshKey = Join-Path $VmDir 'id_ed25519'
$SshConfig = Join-Path $VmDir 'ssh_config'
$SeedIso = Join-Path $VmDir 'seed.iso'
$VmScriptFile = Join-Path $VmDir 'calculadora-vm-build.sh'
$SrcTar = Join-Path $VmDir 'calculadora-src.tar.gz'

function Write-Step([string]$Message) { Write-Host "==> $Message" -ForegroundColor Cyan }
function Stop-WithError([string]$Message) {
    Write-Host "[erro] $Message" -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# Ferramentas do Windows
# ---------------------------------------------------------------------------
$VBoxManage = @(
    $(if ($env:VBOX_MSI_INSTALL_PATH) { Join-Path $env:VBOX_MSI_INSTALL_PATH 'VBoxManage.exe' }),
    (Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe')
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $VBoxManage) {
    Stop-WithError ("VirtualBox nao encontrado. Instale (nao precisa reiniciar): " +
        "winget install Oracle.VirtualBox  ou  https://www.virtualbox.org/wiki/Downloads")
}

$Ssh = (Get-Command ssh.exe -ErrorAction SilentlyContinue).Source
$Scp = (Get-Command scp.exe -ErrorAction SilentlyContinue).Source
$SshKeygen = (Get-Command ssh-keygen.exe -ErrorAction SilentlyContinue).Source
if (-not ($Ssh -and $Scp -and $SshKeygen)) {
    Stop-WithError ("cliente OpenSSH do Windows nao encontrado. Ative em Configuracoes > Aplicativos > " +
        "Recursos opcionais > Cliente OpenSSH (nao precisa reiniciar).")
}
# O tar do Git Bash nao entende C:\; o do Windows (bsdtar) sim.
$WinTar = Join-Path $env:SystemRoot 'System32\tar.exe'

# Chamadas nativas: stderr nao pode virar excecao (PowerShell 5.1) e o codigo
# de saida e conferido a mao.
function Invoke-VBox {
    $ErrorActionPreference = 'Continue'
    $output = & $VBoxManage @args 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0) {
        throw "VBoxManage $($args -join ' ') falhou (codigo $LASTEXITCODE):`n$($output -join "`n")"
    }
    $output
}

function Get-VmState {
    $ErrorActionPreference = 'Continue'
    $names = & $VBoxManage list vms 2>$null | ForEach-Object { if ("$_" -match '^"(.*)" \{') { $Matches[1] } }
    if ($names -notcontains $VmName) { return $null }
    $line = & $VBoxManage showvminfo $VmName --machinereadable 2>$null |
        Where-Object { "$_" -like 'VMState=*' } | Select-Object -First 1
    if ($line) { return ("$line" -replace '^VMState="(.*)"$', '$1') }
    'unknown'
}

function Test-VmSsh {
    $ErrorActionPreference = 'Continue'
    & $Ssh -F $SshConfig -o ConnectTimeout=5 $SshHost true 2>$null
    $LASTEXITCODE -eq 0
}

function Invoke-VmSsh([string]$Command, [switch]$AllowFail) {
    $ErrorActionPreference = 'Continue'
    & $Ssh -F $SshConfig $SshHost $Command | Out-Host
    if ($LASTEXITCODE -ne 0 -and -not $AllowFail) { throw "falhou na VM (codigo $LASTEXITCODE): $Command" }
}

function Invoke-Scp([string[]]$ScpArgs, [switch]$AllowFail) {
    $ErrorActionPreference = 'Continue'
    & $Scp -F $SshConfig @ScpArgs
    if ($LASTEXITCODE -ne 0 -and -not $AllowFail) { throw "scp falhou (codigo $LASTEXITCODE): $($ScpArgs -join ' ')" }
    $LASTEXITCODE -eq 0
}

function Write-LfFile([string]$Path, [string]$Text) {
    [IO.File]::WriteAllText($Path, ($Text -replace "`r`n", "`n"), (New-Object Text.UTF8Encoding $false))
}

# ISO9660+Joliet com rotulo "cidata": o cloud-init do Debian le user-data e
# meta-data dele no 1o boot (datasource NoCloud). Usa o IMAPI2 do Windows.
function New-SeedIso([string]$SourceDir, [string]$IsoPath) {
    if (-not ('CalcIsoWriter' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;

public static class CalcIsoWriter {
    public static void Save(object image, string path) {
        IStream src = (IStream)image;
        byte[] buf = new byte[65536];
        IntPtr read = Marshal.AllocHGlobal(sizeof(int));
        try {
            using (FileStream dst = File.Create(path)) {
                while (true) {
                    src.Read(buf, buf.Length, read);
                    int n = Marshal.ReadInt32(read);
                    if (n <= 0) break;
                    dst.Write(buf, 0, n);
                }
            }
        } finally {
            Marshal.FreeHGlobal(read);
        }
    }
}
'@
    }
    $fsi = New-Object -ComObject IMAPI2FS.MsftFileSystemImage
    $fsi.FileSystemsToCreate = 3   # ISO9660 + Joliet (Joliet guarda "user-data" em minusculas)
    $fsi.VolumeName = 'cidata'
    $fsi.Root.AddTree($SourceDir, $false)
    [CalcIsoWriter]::Save($fsi.CreateResultImage().ImageStream, $IsoPath)
}

# ---------------------------------------------------------------------------
# Criacao da VM (so na 1a vez)
# ---------------------------------------------------------------------------
function New-BuilderVm {
    Write-Step "Criando a VM '$VmName' em $VmDir (so na 1a vez)"
    New-Item -ItemType Directory -Force $VmDir | Out-Null

    # 1. Imagem cloud do Debian 12, conferida pelo SHA512SUMS oficial.
    $qcow = Join-Path $VmDir $DebianImage
    $sums = Join-Path $VmDir 'SHA512SUMS'
    & curl.exe -fsSL --retry 3 -o $sums "$DebianUrl/SHA512SUMS"
    if ($LASTEXITCODE -ne 0) { throw "nao consegui baixar $DebianUrl/SHA512SUMS (sem internet?)" }
    $expected = (Get-Content $sums | Where-Object { $_ -match "\s$([regex]::Escape($DebianImage))$" } |
            Select-Object -First 1) -replace '\s.*$', ''
    if (-not $expected) { throw "$DebianImage nao consta no SHA512SUMS do Debian" }
    if (-not (Test-Path $qcow) -or (Get-FileHash $qcow -Algorithm SHA512).Hash -ne $expected) {
        Write-Step "Baixando $DebianImage (~430 MB)"
        & curl.exe -fL --retry 3 -o $qcow "$DebianUrl/$DebianImage"
        if ($LASTEXITCODE -ne 0) { throw "download de $DebianImage falhou" }
        if ((Get-FileHash $qcow -Algorithm SHA512).Hash -ne $expected) {
            Remove-Item -Force $qcow
            throw "SHA512 de $DebianImage nao confere (download corrompido)"
        }
    }

    # 2. Chave SSH exclusiva desta VM, sem senha, legivel so pelo usuario
    #    (o OpenSSH do Windows recusa chave com permissao aberta).
    if (-not (Test-Path $SshKey)) {
        # PowerShell 5.1 descarta argumento vazio; '""' chega ao ssh-keygen como "".
        $emptyPass = if ($PSVersionTable.PSVersion -ge [version]'7.3') { '' } else { '""' }
        & $SshKeygen -q -t ed25519 -N $emptyPass -C $VmName -f $SshKey
        if ($LASTEXITCODE -ne 0) { throw 'ssh-keygen falhou' }
    }
    $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    & icacls.exe $SshKey /inheritance:r /grant:r "*${sid}:F" | Out-Null

    # 3. ISO do cloud-init: usuario "builder" com sudo e a chave publica.
    $seedDir = Join-Path $VmDir 'seed'
    Remove-Item -Recurse -Force $seedDir -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force $seedDir | Out-Null
    $pubKey = (Get-Content "$SshKey.pub" -Raw).Trim()
    Write-LfFile (Join-Path $seedDir 'meta-data') "instance-id: $VmName-1`nlocal-hostname: calc-builder`n"
    Write-LfFile (Join-Path $seedDir 'user-data') @"
#cloud-config
users:
  - name: builder
    groups: [sudo]
    sudo: "ALL=(ALL) NOPASSWD:ALL"
    shell: /bin/bash
    lock_passwd: true
    ssh_authorized_keys:
      - $pubKey
ssh_pwauth: false
"@
    Remove-Item -Force $SeedIso -ErrorAction SilentlyContinue
    New-SeedIso $seedDir $SeedIso

    # 4. VM. Sobra de uma tentativa anterior impede o createvm: limpa antes.
    $machineDir = Join-Path $VmDir $VmName
    $vdi = Join-Path $machineDir 'disk.vdi'
    $ErrorActionPreference = 'Continue'
    & $VBoxManage closemedium disk $vdi 2>$null | Out-Null
    $ErrorActionPreference = 'Stop'
    Remove-Item -Recurse -Force $machineDir -ErrorAction SilentlyContinue

    Invoke-VBox createvm --name $VmName --ostype Debian_64 --basefolder $VmDir --register | Out-Null
    Write-Step 'Convertendo o disco para VDI'
    Invoke-VBox clonemedium disk $qcow $vdi --format VDI | Out-Null
    Invoke-VBox modifymedium disk $vdi --resize $DiskMB | Out-Null
    Remove-Item -Force $qcow

    Invoke-VBox modifyvm $VmName --cpus $Cpus --memory $MemoryMB --ioapic on --rtcuseutc on `
        --graphicscontroller vmsvga --vram 16 --boot1 disk --boot2 none --boot3 none --boot4 none `
        --nic1 nat --nictype1 virtio `
        --uart1 '0x3F8' 4 --uartmode1 file (Join-Path $VmDir 'serial.log') | Out-Null
    # A imagem cloud usa console=ttyS0; sem porta serial o boot fica lento. O
    # serial.log tambem serve para diagnosticar um boot que nao sobe.
    Invoke-VBox storagectl $VmName --name SATA --add sata --controller IntelAhci --portcount 2 --hostiocache on | Out-Null
    Invoke-VBox storageattach $VmName --storagectl SATA --port 0 --device 0 --type hdd --medium $vdi | Out-Null
    Invoke-VBox storageattach $VmName --storagectl SATA --port 1 --device 0 --type dvddrive --medium $SeedIso | Out-Null
}

function Start-BuilderVm {
    if ((Get-VmState) -ne 'running') {
        $busy = Get-NetTCPConnection -LocalAddress 127.0.0.1, 0.0.0.0 -LocalPort $SshPort -State Listen -ErrorAction SilentlyContinue
        if ($busy) { throw "a porta $SshPort ja esta em uso no Windows; rode de novo com -SshPort <outra>" }
        # Regrava o redirecionamento a cada partida, assim -SshPort pode mudar.
        $ErrorActionPreference = 'Continue'
        & $VBoxManage modifyvm $VmName --natpf1 delete ssh 2>$null | Out-Null
        $ErrorActionPreference = 'Stop'
        Invoke-VBox modifyvm $VmName --natpf1 "ssh,tcp,127.0.0.1,$SshPort,,22" | Out-Null
        Write-Step 'Ligando a VM (headless)'
        Invoke-VBox startvm $VmName --type headless | Out-Null
    }

    $keyPath = $SshKey -replace '\\', '/'
    $knownHosts = (Join-Path $VmDir 'known_hosts') -replace '\\', '/'
    Write-LfFile $SshConfig @"
Host $SshHost
    HostName 127.0.0.1
    Port $SshPort
    User builder
    IdentityFile "$keyPath"
    IdentitiesOnly yes
    UserKnownHostsFile "$knownHosts"
    StrictHostKeyChecking no
    BatchMode yes
    LogLevel ERROR
    ServerAliveInterval 30
"@

    Write-Step 'Esperando o SSH da VM responder (1o boot demora mais)'
    $deadline = (Get-Date).AddMinutes(15)
    while (-not (Test-VmSsh)) {
        if ((Get-VmState) -ne 'running') { throw "a VM desligou durante o boot; veja $VmDir\serial.log" }
        if ((Get-Date) -gt $deadline) { throw "o SSH da VM nao respondeu em 15 min; veja $VmDir\serial.log" }
        Start-Sleep -Seconds 5
    }
    # Deixa o cloud-init terminar (usuario, crescer a particao) antes de usar.
    Invoke-VmSsh 'cloud-init status --wait >/dev/null 2>&1 || true' -AllowFail
}

function Stop-BuilderVm {
    if ((Get-VmState) -ne 'running') { return }
    Write-Step 'Desligando a VM'
    $ErrorActionPreference = 'Continue'
    & $VBoxManage controlvm $VmName acpipowerbutton 2>$null | Out-Null
    $deadline = (Get-Date).AddSeconds(90)
    while ((Get-VmState) -eq 'running' -and (Get-Date) -lt $deadline) { Start-Sleep -Seconds 2 }
    if ((Get-VmState) -eq 'running') { & $VBoxManage controlvm $VmName poweroff 2>$null | Out-Null }
}

# ---------------------------------------------------------------------------
# Script que roda DENTRO da VM (bash, via sudo).
# ---------------------------------------------------------------------------
$VmBuildScript = @'
set -euo pipefail

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[erro]\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "rode com sudo."
ACTION="${CALC_ACTION:?falta CALC_ACTION}"
HOME_DIR=/home/builder
SRC_TAR="$HOME_DIR/calculadora-src.tar.gz"
OUT="$HOME_DIR/out"
STAGE=/var/lib/calculadora-img-build
ALP="$STAGE/system/rpi-os/alpine"

# Montagens/loops largados por um build interrompido. Sem isso, o `rm -rf` do
# rootfs atravessaria o /dev montado e apagaria os dispositivos da VM.
release_stale() {
    local m img d
    awk -v p="$ALP/.work/" 'index($2, p) == 1 { print $2 }' /proc/mounts | sort -r |
        while read -r m; do umount -l "$m" 2>/dev/null || true; done
    if awk -v p="$ALP/.work/" 'index($2, p) == 1 { f = 1 } END { exit !f }' /proc/mounts; then
        die "ainda ha montagens em $ALP/.work; rode de novo (a VM reinicia do zero)."
    fi
    for img in "$ALP"/*.img; do
        [ -f "$img" ] || continue
        losetup -j "$img" | cut -d: -f1 | while read -r d; do losetup -d "$d" 2>/dev/null || true; done
    done
}

rm -rf "$OUT"
install -d -o builder -g builder "$OUT"

case "$ACTION" in
    clean|distclean)
        release_stale
        rm -rf "$ALP/.work" "$ALP"/*.img "$ALP/build.log"
        log "OK: .work/ da VM removido."
        exit 0 ;;
    build)    REUSE=0 ;;
    continue) REUSE=1 ;;
    *)        die "acao invalida: $ACTION" ;;
esac

# --- Dependencias (as mesmas do README, para Debian 12) ------------------------
need=0
for t in qemu-aarch64-static update-binfmts losetup parted sfdisk mkfs.vfat mkfs.ext4 sha256sum curl mountpoint; do
    command -v "$t" >/dev/null 2>&1 || need=1
done
if [ "$need" -eq 1 ]; then
    log "Instalando dependencias do build na VM (apt, so na 1a vez)"
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends ca-certificates curl parted fdisk dosfstools \
        e2fsprogs util-linux qemu-user-static binfmt-support
fi
BINFMT=/proc/sys/fs/binfmt_misc
[ -e "$BINFMT/register" ] || mount -t binfmt_misc binfmt_misc "$BINFMT"
update-binfmts --enable qemu-aarch64 >/dev/null 2>&1 || true
[ -e "$BINFMT/qemu-aarch64" ] || die "binfmt do qemu-aarch64 nao registrou (veja: update-binfmts --display qemu-aarch64)."

# --- Fontes: software/ e overlay/ sempre atualizados; .work/ preservado ----------
[ -f "$SRC_TAR" ] || die "nao achei $SRC_TAR (o .ps1 envia antes de rodar)."
release_stale
log "Atualizando software/ e system/rpi-os/alpine/ na VM"
mkdir -p "$STAGE"
rm -rf "$STAGE/software" "$ALP/overlay" "$ALP/build-alpine-img.sh" "$ALP/packages"
tar -xzf "$SRC_TAR" -C "$STAGE" --no-same-owner --warning=no-unknown-keyword
rm -f "$SRC_TAR"
find "$STAGE/software" -depth -type d \( -name __pycache__ -o -name .venv \) -exec rm -rf {} +
# Arquivos vindos do Windows chegam sem permissoes Unix; normaliza como num clone.
find "$STAGE/software" "$ALP/overlay" -type d -exec chmod 755 {} +
find "$STAGE/software" "$ALP/overlay" -type f -exec chmod 644 {} +
chmod 755 "$ALP/build-alpine-img.sh"
log "Convertendo CRLF -> LF (checkout do Windows)"
{ grep -rlI $'\r' "$STAGE/software" "$ALP/overlay" "$ALP/build-alpine-img.sh" "$ALP/packages" || true; } \
    | xargs -r -d '\n' sed -i 's/\r$//'

# --- Build -----------------------------------------------------------------------
cd "$ALP"
log "Rodando build-alpine-img.sh (REUSE_ROOTFS=$REUSE)"
set +e
REUSE_ROOTFS="$REUSE" ./build-alpine-img.sh 2>&1 | tee build.log
rc=${PIPESTATUS[0]}
set -e
install -o builder -g builder -m 644 build.log "$OUT/build.log"
[ "$rc" -eq 0 ] || die "o build falhou (codigo $rc)."

set -- "$ALP"/*.img
[ -f "$1" ] || die "o build terminou, mas nenhum .img apareceu em $ALP."
mv "$1" "$OUT/"
chown builder:builder "$OUT"/*
'@

# ---------------------------------------------------------------------------
# Fluxo principal
# ---------------------------------------------------------------------------
$state = Get-VmState
if ($state -eq 'inaccessible') {
    Stop-WithError "a VM '$VmName' esta inacessivel no VirtualBox. Rode com -Action vm-remove e depois de novo."
}

if ($Action -eq 'vm-remove') {
    if ($state) {
        Stop-BuilderVm
        Write-Step "Apagando a VM '$VmName'"
        Invoke-VBox unregistervm $VmName --delete | Out-Null
    }
    Remove-Item -Recurse -Force $VmDir -ErrorAction SilentlyContinue
    Write-Host "OK: VM e arquivos removidos ($VmDir)."
    exit 0
}

if ($Action -eq 'distclean') {
    Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $ScriptDir '*.img'), (Join-Path $ScriptDir 'build.log')
}
if (($Action -in 'clean', 'distclean') -and -not $state) {
    Write-Host 'OK: a VM de build nao existe, nao ha .work/ para apagar.'
    exit 0
}
if ($state -and (-not (Test-Path $SshKey))) {
    Stop-WithError "a VM existe mas a chave SSH sumiu de $VmDir. Rode com -Action vm-remove e depois de novo."
}

$rc = 1
$prevEncoding = [Console]::OutputEncoding
try {
    if (-not $state) { New-BuilderVm }
    Start-BuilderVm

    Write-Step 'Enviando fontes para a VM'
    Write-LfFile $VmScriptFile $VmBuildScript
    $uploads = @('calculadora-vm-build.sh')
    if ($Action -in 'build', 'continue') {
        Remove-Item -Force $SrcTar -ErrorAction SilentlyContinue
        & $WinTar -czf $SrcTar -C $RepoRoot --exclude __pycache__ --exclude .venv --exclude '*.pyc' `
            software system/rpi-os/alpine/overlay system/rpi-os/alpine/build-alpine-img.sh system/rpi-os/alpine/packages
        if ($LASTEXITCODE -ne 0) { throw 'tar dos fontes falhou' }
        $uploads += 'calculadora-src.tar.gz'
    }
    # Caminhos relativos: o scp confundiria "C:" de um caminho absoluto com um host.
    Push-Location $VmDir
    try { Invoke-Scp ($uploads + "${SshHost}:") | Out-Null } finally { Pop-Location }

    if ($Action -eq 'build') {
        Write-Step 'Build completo: download + apk + pip emulados em aarch64, pode levar bastante tempo.'
    }
    # Chamado direto (sem pipe) para a saida aparecer ao vivo; -t so em console
    # interativo, para o Ctrl+C chegar ao build dentro da VM.
    $ttyArgs = @()
    if (-not [Console]::IsInputRedirected -and -not [Console]::IsOutputRedirected) { $ttyArgs = @('-t') }
    [Console]::OutputEncoding = [Text.Encoding]::UTF8   # a saida do build tem acentos
    $ErrorActionPreference = 'Continue'
    & $Ssh -F $SshConfig @ttyArgs $SshHost "sudo env CALC_ACTION=$Action bash calculadora-vm-build.sh"
    $rc = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'

    if ($Action -in 'build', 'continue') {
        Push-Location $ScriptDir
        try {
            Invoke-Scp @("${SshHost}:out/build.log", '.') -AllowFail | Out-Null
            if ($rc -eq 0) {
                Write-Step 'Copiando a imagem para esta pasta'
                Invoke-Scp @("${SshHost}:out/*.img", '.') | Out-Null
                Invoke-VmSsh 'rm -rf out' -AllowFail
            }
        } finally { Pop-Location }
    }
} finally {
    [Console]::OutputEncoding = $prevEncoding
    Stop-BuilderVm
}

if ($rc -ne 0) {
    Stop-WithError "o build falhou (codigo $rc). Log: $(Join-Path $ScriptDir 'build.log')"
}

if ($Action -in 'build', 'continue') {
    $img = Get-ChildItem -Path $ScriptDir -Filter '*.img' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    Write-Host ''
    Write-Host '==========================================================================='
    Write-Host "Imagem gerada: $($img.FullName)"
    Write-Host ''
    Write-Host 'Grave no cartao SD pelo Windows com o Raspberry Pi Imager'
    Write-Host '("Escolher SO" -> "Usar personalizado") ou com o balenaEtcher.'
    Write-Host 'Confira a unidade do cartao: a gravacao apaga o destino.'
    Write-Host '==========================================================================='
}
exit 0
