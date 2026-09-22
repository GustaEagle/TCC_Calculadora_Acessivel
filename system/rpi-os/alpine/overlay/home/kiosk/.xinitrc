#!/bin/sh
# Sessão gráfica do kiosk: nenhuma barra, menu ou gerenciador de janelas — apenas
# a janela da calculadora ocupando a tela. Espelha o padrão já validado para
# Pi OS em docs/build-img-linux.md, adaptado ao Alpine (OpenRC/BusyBox).

# Nunca apagar/desligar a tela (appliance sempre visível).
xset s off
xset -dpms
xset s noblank

# Esconder o cursor do mouse, se a ferramenta existir (não falhar o boot se não).
if command -v unclutter >/dev/null 2>&1; then
    unclutter --timeout 0 >/dev/null 2>&1 &
fi

# Nomes dos conectores DRM de cada porta HDMI (PRD §6: HDMI0 = LCD, HDMI1 =
# monitor externo). Os padroes do codigo sao HDMI-A-1/HDMI-A-2; descomente e
# corrija aqui se "python3 -m software.app --list-outputs" mostrar outros nomes
# neste kernel - assim nao e preciso alterar o codigo na imagem.
#export CALC_LCD_CONNECTOR=HDMI-A-1
#export CALC_MONITOR_CONNECTOR=HDMI-A-2

# Nomes das MESMAS portas como o xrandr as chama (o app usa isto para acender o
# painel certo ao trocar de tela). A conversao padrao e HDMI-A-1 -> HDMI-1;
# confira com "xrandr --listmonitors" e descomente se for diferente.
#export CALC_LCD_XRANDR_OUTPUT=HDMI-1
#export CALC_MONITOR_XRANDR_OUTPUT=HDMI-2

# Executar a calculadora a partir da raiz do projeto (/opt/calculadora), de onde
# "python3 -m software.app" resolve o pacote software/. O laço faz o papel de
# Restart=always: se o app fechar ou cair, ele reinicia sozinho.
# Trocar de tela (monitor externo ligado/removido em uso, RF-09) NAO passa por
# aqui: o proprio app troca de front no mesmo processo, preservando a conta em
# andamento e o historico. Este laco cobre so o caso de falha - se o app cair,
# ele volta.
cd /opt/calculadora || exit 1

# Com as duas portas HDMI ligadas, o driver modesetting autoconfigura os dois
# CRTCs lado a lado: o desktop ESTENDIDO ja existe antes de o Python arrancar, e
# apareceria nas duas telas por um instante, contra o PRD §7.2. Esta chamada
# aplica o layout exclusivo (uma unica saida ativa) antes de existir qualquer
# janela. Fica FORA do laco de propósito: o proprio app reaplica o layout a cada
# troca de front (RF-09), e repetir aqui so causaria um flash a cada reinicio.
python3 -m software.app --apply-video-layout

while true; do
    python3 -m software.app
    # Pequena pausa evita loop de reinício em CPU cheia caso o app falhe já no arranque.
    sleep 1
done
