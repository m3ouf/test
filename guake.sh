#!/bin/sh
notify-send "Guake will re-open when Backend is ready !"
guake

guake -n $(pwd)
guake -r "Backend Server" -e "source env/bin/activate"
guake -e "unset http_proxy; unset https_proxy; unset ftp_proxy; unset socks_proxy;"
guake -e "python manage.py runserver 8001"

guake -n $(pwd)
guake -r "Backend Terminal" -e "source env/bin/activate"
guake -e "unset http_proxy; unset https_proxy; unset ftp_proxy; unset socks_proxy;"

guake -n $(pwd)
guake -r "Backend Shell" -e "source env/bin/activate"
guake -e "unset http_proxy; unset https_proxy; unset ftp_proxy; unset socks_proxy;"
guake -e "python manage.py shell"
sleep 3
guake
