from flask import Flask, request, redirect, session, url_for, g
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from authlib.integrations.flask_client import OAuth
from sqlalchemy.engine import url
from models import db, User
from forms import UserForm
import os
from dotenv import load_dotenv

# Cargar variable de entorno
load_dotenv()

app = Flask(__name__)
app.config['TIMEZONE'] = 'America/Bogota'

# configuración SQLAlchemy
app.config['SECRET_KEY'] = 'santa_marta_500'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///qrcodes.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración adicional para sesiones
app.config['SESSION_COOKIE_SECURE'] = False  # Cambia a True en producción con HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Crear base de datos y tablas
db.init_app(app)

with app.app_context():
    db.create_all()

# Configurar protección CSRF
csrf = CSRFProtect(app)

# Configuración OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'email profile'},
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
)

# Rutas autenticación
@app.route('/login')
def login():
    redirect_uri = url_for('auth/callback', _external=True)
    print(f"Redirect URI usado: {redirect_uri}")  # Para depuración
    return google.authorize_redirect(redirect_uri, prompt='consent')

@app.route('/auth/callback')
def auth_callback():
    token = google.authorize_access_token()
    user_info = google.get('userinfo').json()
    session['user_email'] = user_info['email']
    return redirect(url_for('qr_codes_list'))

@app.route('/logout')
def logout():
    session.clear()
    print(f"Sesión después de clear: {session}")
    return redirect(url_for('main'))

@app.before_request
def load_user_role():
    g.user_role = None
    if 'user_email' in session:
        user = User.query.filter_by(email=session['user_email']).first()
        if user:
            g.user_role = user.role

# Middleware para forzar https
@app.before_request
def force_https():
    if request.host_url.startswith('http://') and not app.debug:
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)

# Middleware para agregar Client Hints
@app.after_request
def add_client_hints(response):
    response.headers['Accept-CH'] = 'Sec-CH-UA, Sec-CH-UA-Platform, Sec-CH-UA-Model, Sec-CH-UA-Mobile'
    return response

# Importar rutas de routes.py
from routes import init_routes
init_routes(app)

if __name__ == '__main__':
     port = os.environ.get('PORT', '5000')
     try:
         port = int(port)
     except ValueError:
         print(f"Error: Puerto inválido '{port}'. Usando 5000.")
         port = 5000
     print(f"Puerto configurado: {port}")