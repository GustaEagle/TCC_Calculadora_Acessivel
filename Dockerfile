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
#  - espeak / libespeak1   : motor TTS offline usado pelo pyttsx3
#  - libasound2-plugins    : ponte ALSA -> PulseAudio (áudio para o host)
#  - fonts-dejavu-core     : fontes para a UI não ficar sem glifos
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-tk \
        espeak \
        libespeak1 \
        libasound2-plugins \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala as dependências Python primeiro para aproveitar o cache de camadas.
COPY software/requirements.txt software/requirements.txt
RUN pip3 install -r software/requirements.txt

# Copia apenas o código da aplicação (o resto é ignorado pelo .dockerignore).
COPY software/ software/

# Entry point: mesmo módulo usado localmente (software/app.py).
CMD ["python3", "-m", "software.app"]
