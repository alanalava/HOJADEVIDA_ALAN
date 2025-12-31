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

# 1. Usuario Jandry (Crea solo si no existe)
echo "from django.contrib.auth import get_user_model; \
User = get_user_model(); \
User.objects.filter(username='Jandry').exists() or \
User.objects.create_superuser('Jandry', 'Jandry@gmail.com', 'NCQM200406')" \
| python manage.py shell

# 2. Usuario Alan (Crea o ACTUALIZA la contraseña siempre)
# Esto garantiza que puedas entrar con 'Alan2025' aunque el usuario ya existiera
echo "from django.contrib.auth import get_user_model; \
User = get_user_model(); \
user, created = User.objects.get_or_create(username='Alan', defaults={'email': 'alan@gmail.com'}); \
user.set_password('Alan2025'); \
user.is_superuser = True; \
user.is_staff = True; \
user.save()" \
| python manage.py shell