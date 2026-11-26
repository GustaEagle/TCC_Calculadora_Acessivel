"""Tests for the calculator software prototype."""

import os

# Testes herméticos: nunca carregar a voz neural instalada NA MÁQUINA de quem
# roda a suíte (~/.local/share/piper/voices, /opt/piper/voices). Com ela, cada
# SpeechService real carregava o modelo e aquecia o cache, a suíte ficava ~80x
# mais lenta e os testes cronometrados da reprodução falhavam. Um teste que
# precise da voz define CALC_PIPER_VOICE com o caminho explicitamente.
os.environ.setdefault("CALC_PIPER_VOICE", "off")
