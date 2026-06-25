# citas/validators_perfil.py
"""
Validaciones para el formulario de PERFIL (tab 'info').
Reutiliza exactamente las mismas reglas que el formulario de registro
para que el comportamiento sea consistente en todo el sistema.
"""
import re
from datetime import datetime, date

# ──────────────────────────────────────────────────────────────
# REGEX (idénticos a los del registro)
# ──────────────────────────────────────────────────────────────
RE_NOMBRE_APELLIDO   = re.compile(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$')
RE_CEDULA            = re.compile(r'^[0-9]+(-[0-9a-zA-Z]+)?$')
RE_TELEFONO          = re.compile(r'^[+]*[0-9\s-]+$')
RE_CONTACTO_NOMBRE   = re.compile(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$')

GENEROS_VALIDOS = {'Masculino', 'Femenino', 'Otro'}


def _strip_tags(value):
    """Sanitiza HTML/scripts básicos para prevenir XSS en campos de texto libre."""
    if not value:
        return value
    # Elimina cualquier etiqueta tipo <...>
    value = re.sub(r'<[^>]*>', '', value)
    return value.strip()


def validar_info_personal(post_data):
    """
    Valida los campos del tab 'info' del perfil.
    Devuelve (data_limpia: dict, errores: list[str]).
    Si errores está vacío, data_limpia es seguro para guardar.
    """
    errores = {}
    limpio = {}

    # ── Nombres ──
    first_name = post_data.get('first_name', '').strip()
    if not first_name:
        errores['first_name'] = 'El nombre es obligatorio.'
    elif not (2 <= len(first_name) <= 50):
        errores['first_name'] = 'El nombre debe tener entre 2 y 50 caracteres.'
    elif not RE_NOMBRE_APELLIDO.match(first_name):
        errores['first_name'] = 'El nombre solo puede contener letras y espacios.'
    limpio['first_name'] = first_name

    # ── Apellidos ──
    last_name = post_data.get('last_name', '').strip()
    if not last_name:
        errores['last_name'] = 'El apellido es obligatorio.'
    elif not (2 <= len(last_name) <= 50):
        errores['last_name'] = 'El apellido debe tener entre 2 y 50 caracteres.'
    elif not RE_NOMBRE_APELLIDO.match(last_name):
        errores['last_name'] = 'El apellido solo puede contener letras y espacios.'
    limpio['last_name'] = last_name

    # ── Teléfono ──
    phone = post_data.get('phone', '').strip()
    if not phone:
        errores['phone'] = 'El teléfono es obligatorio.'
    elif not (7 <= len(phone) <= 15):
        errores['phone'] = 'El teléfono debe tener entre 7 y 15 caracteres.'
    elif not RE_TELEFONO.match(phone):
        errores['phone'] = 'El teléfono solo puede contener números, espacios, guiones y "+" al inicio.'
    limpio['phone'] = phone

    # ── Fecha de nacimiento (+ regla de edad >= 18) ──
    fecha_str = post_data.get('fecha_nacimiento', '').strip()
    fecha_obj = None
    if not fecha_str:
        errores['fecha_nacimiento'] = 'La fecha de nacimiento es obligatoria.'
    else:
        try:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            if fecha_obj.year < 1900:
                errores['fecha_nacimiento'] = 'La fecha no puede ser anterior al año 1900.'
            else:
                hoy = date.today()
                edad = hoy.year - fecha_obj.year - (
                    (hoy.month, hoy.day) < (fecha_obj.month, fecha_obj.day)
                )
                if edad < 18:
                    errores['fecha_nacimiento'] = 'Debes ser mayor de 18 años para usar la plataforma.'
                elif edad > 100:
                    errores['fecha_nacimiento'] = 'La edad ingresada no es válida (máximo 100 años).'
        except ValueError:
            errores['fecha_nacimiento'] = 'Formato de fecha inválido.'
    limpio['fecha_nacimiento'] = fecha_obj

    # ── Género (lista blanca) ──
    genero = post_data.get('genero', '').strip()
    if genero and genero not in GENEROS_VALIDOS:
        errores['genero'] = 'Género no válido.'
        genero = ''
    limpio['genero'] = genero

    # ── Cédula de identidad ──
    cedula = post_data.get('cedula', '').strip()
    if not cedula:
        errores['cedula'] = 'La cédula de identidad es obligatoria.'
    elif not (5 <= len(cedula) <= 15):
        errores['cedula'] = 'La cédula debe tener entre 5 y 15 caracteres.'
    elif not RE_CEDULA.match(cedula):
        errores['cedula'] = 'Formato de cédula inválido. Ej: 1234567 o 1234567-2A.'
    limpio['cedula'] = cedula

    # ── Dirección (sanitizada contra XSS) ──
    direccion = _strip_tags(post_data.get('direccion', ''))
    if not direccion:
        errores['direccion'] = 'La dirección es obligatoria.'
    elif not (10 <= len(direccion) <= 255):
        errores['direccion'] = 'La dirección debe tener entre 10 y 255 caracteres.'
    limpio['direccion'] = direccion

    # ── Ciudad / País (texto libre simple, sanitizado) ──
    limpio['ciudad'] = _strip_tags(post_data.get('ciudad', ''))
    limpio['pais'] = _strip_tags(post_data.get('pais', ''))
    limpio['codigo_postal'] = post_data.get('codigo_postal', '').strip()

    # ── Contacto de emergencia (nombre) ──
    contacto_emergencia = post_data.get('contacto_emergencia', '').strip()
    if not contacto_emergencia:
        errores['contacto_emergencia'] = 'El contacto de emergencia es obligatorio.'
    elif not (2 <= len(contacto_emergencia) <= 100):
        errores['contacto_emergencia'] = 'Debe tener entre 2 y 100 caracteres.'
    elif not RE_CONTACTO_NOMBRE.match(contacto_emergencia):
        errores['contacto_emergencia'] = 'Solo puede contener letras y espacios.'
    limpio['contacto_emergencia'] = contacto_emergencia

    # ── Número de emergencia (+ validación cruzada con teléfono) ──
    numero_emergencia = post_data.get('numero_emergencia', '').strip()
    if not numero_emergencia:
        errores['numero_emergencia'] = 'El número de emergencia es obligatorio.'
    elif not (7 <= len(numero_emergencia) <= 15):
        errores['numero_emergencia'] = 'Debe tener entre 7 y 15 caracteres.'
    elif not RE_TELEFONO.match(numero_emergencia):
        errores['numero_emergencia'] = 'Solo puede contener números, espacios, guiones y "+" al inicio.'
    elif phone and numero_emergencia == phone:
        errores['numero_emergencia'] = 'El número de emergencia no puede ser igual a tu teléfono personal.'
    limpio['numero_emergencia'] = numero_emergencia

    return limpio, errores