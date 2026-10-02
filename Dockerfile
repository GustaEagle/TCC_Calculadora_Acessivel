# Imagem para rodar a calculadora acessível localmente (GUI + TTS) via Docker.
# Base Debian bookworm: seu python3 do sistema é 3.11 (igual ao CI) e traz o
# Tkinter funcionando de fábrica (python3-tk), o que a imagem oficial python:slim
# não oferece sem recompilar.
FROM debian:bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PIP_NO_CACHE_DIR=1

# Dependências de sistema:
#  - python3 / python3-tk : interpretador 3.11 + Tkinter (ttkbootstrap)
#  - espeak-ng             : fonemizador do Piper e motor TTS de FALLBACK
#    (WRN-011). A voz principal é neural (Piper + cadu), instalada por pip
#    (piper-tts, wheel glibc) mais o modelo baixado abaixo.
#  - curl                  : baixa a voz cadu no build (download-piper-voice.sh)
#  - libasound2-plugins    : ponte ALSA -> PulseAudio (áudio para o host)
#  - alsa-utils            : fornece o binário "aplay" que reproduz o PCM
#    (o speech.py toca raw pela stdin do aplay)
#  - fonts-dejavu-core     : fontes para a UI não ficar sem glifos
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-tk \
        espeak-ng \
        libespeak-ng1 \
        curl \
        libasound2-plugins \
        alsa-utils \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Sem isso, aplay/ALSA tenta abrir uma placa de som física ("hw:0") que não
# existe no container e falha; direciona o PCM padrão para o plugin "pulse"
# (fornecido por libasound2-plugins), que fala com o PulseAudio do host via
# o socket montado em /tmp/pulse-native (ver docker-compose.yml).
RUN printf 'pcm.!default {\n  type pulse\n}\nctl.!default {\n  type pulse\n}\n' > /etc/asound.conf

WORKDIR /app

# Instala as dependências Python primeiro para aproveitar o cache de camadas.
# Em glibc o piper-tts vem do PyPI com wheel (puxa o onnxruntime); o marcador do
# requirements.txt só pula o piper em aarch64 (imagem Alpine, wheel próprio).
COPY software/requirements.txt software/requirements.txt
RUN pip3 install -r software/requirements.txt

# Baixa a voz neural cadu para o caminho padrão que o speech.py procura
# (/opt/piper/voices). Idempotente; o app é offline em execução.
COPY scripts/download-piper-voice.sh /usr/local/bin/download-piper-voice.sh
RUN /usr/local/bin/download-piper-voice.sh /opt/piper/voices

# Copia apenas o código da aplicação (o resto é ignorado pelo .dockerignore).
COPY software/ software/

# Entry point: mesmo módulo usado localmente (software/app.py).
CMD ["python3", "-m", "software.app"]
