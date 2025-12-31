#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

# --- LIMPIEZA DESACTIVADA ---
# echo "from django.contrib.admin.models import LogEntry; \
# from Perfil.models import DatosPersonales; \
# LogEntry.objects.all().delete(); \
# DatosPersonales.objects.all().delete();" \
# | python manage.py shell

# 1. Crear usuario principal (Jandry)
echo "from django.contrib.auth import get_user_model; \
User = get_user_model(); \
User.objects.filter(username='Jandry').exists() or \
User.objects.create_superuser('Jandry', 'Jandry@gmail.com', 'NCQM200406')" \
| python manage.py shell

# 2. Crear SEGUNDO usuario
# IMPORTANTE: Cambia 'Invitado', el correo y el password antes de ejecutar
echo "from django.contrib.auth import get_user_model; \
User = get_user_model(); \
User.objects.filter(username='Invitado').exists() or \
User.objects.create_superuser('Invitado', 'invitado@gmail.com', 'Invitado123')" \
| python manage.py shell