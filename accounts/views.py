from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from datetime import datetime, date
from django.contrib.auth import authenticate, login, logout


def calcular_edad(fecha_nacimiento):
    hoy = date.today()
    edad = hoy.year - fecha_nacimiento.year
    if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1
    return edad


from citas.models import Profile


def login_view(request):
    error_message = None

    if request.method == 'POST':
        identificador = request.POST.get('username', '').strip()
        clave = request.POST.get('password')

        # ── Permitir login con username O con email ──
        username_real = identificador
        if '@' in identificador:
            try:
                user_obj = User.objects.get(email__iexact=identificador)
                username_real = user_obj.username
            except User.DoesNotExist:
                username_real = identificador  # dejará fallar el authenticate normalmente

        user = authenticate(request, username=username_real, password=clave)

        if user is not None:
            login(request, user)
            return redirect('citas:home')
        else:
            error_message = "Usuario/correo o contraseña incorrectos."

    return render(request, 'accounts/login.html', {'error': error_message})

def logout_view(request):
    logout(request)
    return redirect('login')

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        genero = request.POST.get('genero')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        fecha_nacimiento = request.POST.get('fecha_nacimiento')
        cedula = request.POST.get('cedula')
        telefono = request.POST.get('telefono')
        direccion = request.POST.get('direccion')
        contacto_emergencia = request.POST.get('contacto_emergencia')
        numero_emergencia = request.POST.get('numero_emergencia')

        errores = []

        if not username:
            errores.append('El usuario es obligatorio.')
        elif User.objects.filter(username=username).exists():
            errores.append('Ese nombre de usuario ya está registrado.')

        if not email:
            errores.append('El correo es obligatorio.')
        elif User.objects.filter(email=email).exists():
            errores.append('Ese correo ya está registrado.')

        if not password1 or not password2:
            errores.append('Debes ingresar y confirmar la contraseña.')
        elif password1 != password2:
            errores.append('Las contraseñas no coinciden.')
        elif len(password1) < 8:
            errores.append('La contraseña debe tener al menos 8 caracteres.')

        fecha_nacimiento_obj = None
        if fecha_nacimiento:
            try:
                fecha_nacimiento_obj = datetime.strptime(fecha_nacimiento, '%d/%m/%Y').date()

                if calcular_edad(fecha_nacimiento_obj) < 18:
                    errores.append('Debes ser mayor de 18 años para registrarte.')
            except ValueError:
                errores.append('La fecha de nacimiento no tiene un formato válido.')
        else:
            errores.append('La fecha de nacimiento es obligatoria.')

        if errores:
            for e in errores:
                messages.error(request, e)
            return render(request, 'accounts/register.html')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name or '',
            last_name=last_name or ''
        )

        profile, created = Profile.objects.get_or_create(user=user)
        profile.cedula = cedula or ''
        profile.phone = telefono or ''
        profile.direccion = direccion or ''
        profile.fecha_nacimiento = fecha_nacimiento_obj
        profile.genero = genero or ''
        profile.contacto_emergencia = contacto_emergencia or ''
        profile.numero_emergencia = numero_emergencia or ''
        profile.save()

        messages.success(request, '¡Cuenta creada con éxito! Ahora puedes iniciar sesión.')
        return redirect('login')

    return render(request, 'accounts/register.html')