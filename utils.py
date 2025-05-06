from flask import request, url_for, session, redirect, flash
from functools import wraps
from models import User
from user_agents import parse
import base64
from io import BytesIO
import qrcode
import uuid

# Decorador de protección de rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar si el usuario está autenticado
        user_email = session.get('user_email')
        if not user_email:
            flash('Por favor, inicia sesión con tu cuenta de Gmail.', 'error')
            return redirect(url_for('login'))

        # Verificar si el email está en la base de datos
        user = User.query.filter_by(email=user_email).first()
        
        if not user_email:
            flash('Tu correo no está registrado en la base de datos.', 'error')
            return redirect(url_for('login'))

        if not user:
            flash('Tu correo Gmail no está registrado en la base de datos.', 'error')
            session.clear()  # Limpiar sesión si el usuario no existe
            session.modified = True
            return redirect(url_for('login'))
        
        # Verificar la estructura del correo corporativo
        if not is_valid_corporate_email(user.corporate_email):
            flash('El correo corporativo no tiene una estructura válida (debe terminar en @miempresa.com).', 'error')
            return redirect(url_for('logout'))

        return f(*args, **kwargs)
    return decorated_function

# Decorador para verificar si el usuario es Admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_email = session.get('user_email')
        if not user_email:
            flash('Debes iniciar sesión para acceder a esta área.', 'error')
            return redirect(url_for('login'))

        user = User.query.filter_by(email=user_email).first()
        if not user or user.role != 'admin':
            flash('No tienes permisos de administrador para acceder a esta área.', 'error')
            return redirect(url_for('create_user'))  # Redirige a una ruta accesible

        return f(*args, **kwargs)
    return decorated_function

# Verifica si el correo termina en @falabella.com.co
def is_valid_corporate_email(email):
    return email.lower().endswith('@falabella.com.co')

# Obtener dirección ip
def get_real_ip():
    if 'X-Forwarded-For' in request.headers:
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

# Obtener informacion del dispositivo
def get_client_info():
    ua_string = request.headers.get('User-Agent')
    user_agent = parse(ua_string)
    device_type = user_agent.device.family
    os = user_agent.os.family
    browser = user_agent.browser.family

    return device_type, os, browser

# Obtenemos el nombre de la página o de la categoría
def get_name_page(url):

    tag = url.split('/')
    string_sl = tag[5]
    sign = '?'
    position_sg = string_sl.find(sign)

    if position_sg != -1 :
        name_tag = string_sl[:position_sg]
        name_url = f"{tag[4]}:{name_tag}"
    else:
        name_url = f"{tag[4]}:{tag[5]}"

    return name_url

# Genera el código QR a partir de una url y convierte el QR a Base64
def generate_qr_code():
   
    # Generar id del qr
    qr_id = str(uuid.uuid4())

    # Generar nueva url de seguimiento
    full_url = url_for('qr', qr_id=qr_id, _external=True)

    # Generar el código QR
    qr = qrcode.QRCode(version=None, box_size=5, border=3)
    qr.add_data(full_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir la imagen a Base64
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
    qr_data = f"data:image/png;base64,{img_str}"

    return qr_id, full_url, qr_data