from flask import request, render_template, make_response, session, url_for, redirect, flash
from authlib.integrations.flask_client import OAuth
from flask_login import LoginManager, UserMixin, login_manager, login_user, logout_user, login_required
from models import QRCode, Scan, User, db # Importamos modelos de db
from utils import get_real_ip, get_client_info, get_name_page, generate_qr_code, login_required, admin_required# Importamos funciones
from forms import UserForm


def init_routes(app): # Función para inicializar las rutas

    # Url para generar código QR 
    @app.route('/', methods=['GET', 'POST'])
    def main():
        qr_data = None
        
        if request.method == 'POST':
            text = request.form.get('text')
            if text:

                qr_id, full_url, qr_data = generate_qr_code()
                name_url = get_name_page(text)

                # Guardar qr en base de datos
                qr_code = QRCode(id=qr_id, url=text, tag=name_url, track_url=full_url, qr_image=qr_data)
                db.session.add(qr_code)
                db.session.commit()

                return redirect(url_for('qr_stats', qr_id=qr_id))
                
        return render_template('index.html', qr_data=qr_data)

    @app.route('/create', methods=['GET', 'POST'])
    @login_required
    def create_user():
        form = UserForm()
        if form.validate_on_submit():
            user = User(name=form.name.data, email=form.email.data, corporate_email=form.corporate_email.data)
            try:
                db.session.add(user)
                db.session.commit()
                flash('Usuario creado exitosamente!', 'success')
            except Exception as e:
                db.session.rollback()
                # Verifica si el error es por un email duplicado
                if 'UNIQUE constraint failed' in str(e):
                    flash('El email ya está en uso.', 'error')
                else:
                    flash(f'Error al crear el usuario: {str(e)}', 'error')
                return redirect(url_for('create_user'))

        data = User.query.all()
        user_email = session.get('user_email')
        current_user = User.query.filter_by(email=user_email).first()
        user_role = current_user.role if current_user else 'user'
        users = data
        return render_template('user_create.html', form=form, users=users, user_role=user_role)

    # Url para ver estadisticas del código generado
    @app.route('/qr/stats/<qr_id>')
    @login_required
    def qr_stats(qr_id):
        data = QRCode.query.get_or_404(qr_id)
        scan_count = Scan.query.filter_by(qr_id=qr_id).count()
        scan_all = Scan.query.filter_by(qr_id=qr_id).limit(100).all()
        qr_data = data
        return render_template('qr_stats.html', data=qr_data, scan_count=scan_count, scan_all=scan_all)

    #Url para ver listado de los códigos QR creados
    @app.route('/qrcodes')
    def qr_codes_list():
        data = QRCode.query.all()
        qr_list = data
        return render_template('qr_list.html', data=qr_list)

    # Url para trackeo de código QR
    @app.route('/qr/<qr_id>', methods=['GET'])
    def qr(qr_id):
        user_agent = request.headers
        print(user_agent)
        
        # Obtenemos la dirección ip del dispositivo
        ip_address = get_real_ip()

        # Creamos cookie para registrar escaneo del QR
        visited = request.cookies.get(f'unique_visited_{qr_id}')
        data = QRCode.query.get_or_404(qr_id)
        qr_data = data

        # Cuenta cuando el qr es escaneado
        if not visited:

            if qr_data is None:
                return "Código QR no encontrado"

            device_type, os, browser = get_client_info()
            scan = Scan(qr_id=qr_id, device_type=device_type, os=os, browser=browser, ip_address=ip_address)
            db.session.add(scan)
            db.session.commit()

            response = make_response(redirect(qr_data.track_url))
            response.set_cookie(f'unique_visited_{qr_id}', 'true', max_age=60*60*24*365)
            return response
        
        return redirect(qr_data.url)

    @app.route('/qr/delete/<qr_id>', methods=['POST'])
    @login_required
    def  delete_qr(qr_id):
        qr = QRCode.query.get_or_404(qr_id)
        db.session.delete(qr)
        db.session.commit()

        return redirect(url_for('qr_codes_list'))

    @app.route('/create/delete/<id>', methods=['POST'])
    @login_required
    @admin_required
    def delete_user(id):
        user = User.query.get_or_404(id)
        db.session.delete(user)
        db.session.commit()
        flash('Usuario eliminado exitosamente', 'success')
        return redirect(url_for('create_user'))
    