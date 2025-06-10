@echo off
echo Iniciando aplicação...
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
pause
