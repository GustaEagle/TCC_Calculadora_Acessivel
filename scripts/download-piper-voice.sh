#!/usr/bin/env bash
#
# Baixa e verifica (sha256) a voz neural pt-BR "cadu" do Piper — os dois arquivos
# que o motor precisa: o modelo `.onnx` e a sua config `.onnx.json`.
#
# Reutilizável pelo Docker (make up) e pelo build da imagem Alpine
# (build-alpine-img.sh). É IDEMPOTENTE: se os arquivos já existem e o hash bate,
# não baixa de novo. Ver openspec/changes/replace-tts-with-piper (D7).
#
# Uso:   ./download-piper-voice.sh [DIR_DESTINO]
#        (padrão: /opt/piper/voices)
#
# O aparelho é OFFLINE: este script roda só no BUILD (Docker/imagem), nunca no Pi
# em uso. Nada de voz é baixado em execução (spec speech-engine).
#
# sha256 fixo (reprodutibilidade): preencha CADU_*_SHA256 assim que a equipe
# tiver o hash da voz que possui (tarefa 2.2). Sem o hash:
#   - por padrão (dev): baixa, IMPRIME o sha256 obtido para você fixar, e segue;
#   - com STRICT=1 (imagem): FALHA, para nunca embutir uma voz não verificada.

set -euo pipefail

VOICE_NAME="pt_BR-cadu-medium"
# rhasspy/piper-voices (HuggingFace): pt / pt_BR / cadu / medium.
BASE_URL="${PIPER_VOICE_BASE_URL:-https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/cadu/medium}"

# sha256 fixo da voz. Obtidos do rhasspy/piper-voices (HuggingFace) em
# 2026-09-30, baixando os dois arquivos e conferindo o hash; é o que torna o
# build reprodutível e o que STRICT=1 (imagem) exige. Env tem prioridade, para
# quem precise apontar para outra cópia da voz.
#   pt_BR-cadu-medium.onnx       61 MB
#   pt_BR-cadu-medium.onnx.json   5 KB
CADU_ONNX_SHA256="${CADU_ONNX_SHA256:-765f0809a6ea9035d4a6d0d008dbf8876e68b2dd32029312672fa8f405bdb535}"
CADU_JSON_SHA256="${CADU_JSON_SHA256:-5fe03aa3d4901880554905b12075713cd552598c8a350455a1ec73f8b4e6be19}"

DEST_DIR="${1:-/opt/piper/voices}"
STRICT="${STRICT:-0}"

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[aviso]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[erro]\033[0m %s\n' "$*" >&2; exit 1; }

command -v curl    >/dev/null 2>&1 || die "curl não encontrado."
command -v sha256sum >/dev/null 2>&1 || die "sha256sum não encontrado."

mkdir -p "${DEST_DIR}"

# Baixa (se faltar) e verifica um arquivo. Idempotente: pula se já bate o hash.
fetch_and_verify() {
    local file="$1" expected="$2"
    local dest="${DEST_DIR}/${file}"
    local url="${BASE_URL}/${file}"

    if [ -f "${dest}" ] && [ -n "${expected}" ] \
       && echo "${expected}  ${dest}" | sha256sum -c - >/dev/null 2>&1; then
        log "${file}: já presente e verificado — pulando."
        return 0
    fi
    if [ ! -f "${dest}" ]; then
        log "Baixando ${file}"
        curl -fSL "${url}" -o "${dest}.part"
        mv "${dest}.part" "${dest}"
    fi

    local actual
    actual="$(sha256sum "${dest}" | awk '{print $1}')"
    if [ -n "${expected}" ]; then
        [ "${actual}" = "${expected}" ] \
            || die "sha256 de ${file} não confere:
  esperado: ${expected}
  obtido:   ${actual}
(voz corrompida, ou o hash fixado está desatualizado)."
        log "${file}: sha256 OK."
    else
        warn "sha256 de ${file} não fixado. Obtido: ${actual}"
        warn "Fixe em scripts/download-piper-voice.sh (CADU_*_SHA256) para builds reprodutíveis."
        [ "${STRICT}" = "1" ] && die "STRICT=1: recuso embutir '${file}' sem sha256 fixo."
    fi
}

log "Voz ${VOICE_NAME} -> ${DEST_DIR}"
fetch_and_verify "${VOICE_NAME}.onnx"      "${CADU_ONNX_SHA256}"
fetch_and_verify "${VOICE_NAME}.onnx.json" "${CADU_JSON_SHA256}"
log "Pronto: voz cadu em ${DEST_DIR}"
