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

# Executar a calculadora a partir da raiz do projeto (/opt/calculadora), de onde
# "python3 -m software.app" resolve o pacote software/. O laço faz o papel de
# Restart=always: se o app fechar ou cair, ele reinicia sozinho.
cd /opt/calculadora || exit 1
while true; do
    python3 -m software.app
    status=$?

    # Codigo 75 = a saida de video mudou embaixo do app (monitor externo ligado
    # ou removido com a calculadora ja em uso, RF-09). Nao basta reiniciar o
    # app: o X fixa a geometria da tela no arranque, entao o painel novo so e
    # usado na resolucao dele com um servidor X novo. Sair daqui derruba o X; o
    # agetty refaz o autologin e o .profile sobe tudo de novo, ja no front certo.
    if [ "$status" -eq 75 ]; then
        exit 0
    fi

    # Pequena pausa evita loop de reinício em CPU cheia caso o app falhe já no arranque.
    sleep 1
done
