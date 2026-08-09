# Disparo do X no login automático do usuário kiosk (apenas no console físico tty1).
# O autologin é feito pelo agetty via /etc/inittab (ver build-alpine-img.sh);
# ao logar no tty1, este .profile sobe o X, que por sua vez roda o .xinitrc.
#
# A guarda por tty1 evita tentar iniciar o X em sessões que não sejam o console
# local (ex.: um SSH futuro), que falhariam sem tela.

if [ -z "${DISPLAY:-}" ] && [ "$(tty)" = "/dev/tty1" ]; then
    exec startx
fi
