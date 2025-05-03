from flask import Flask, render_template, request, redirect, make_response, url_for
from flask_sqlalchemy import SQLAlchemy
from user_agents import parse
import base64
from io import BytesIO
import qrcode
import uuid
import os

app = Flask(__name__)

# configuración SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///qrcodes.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Importar modelos después de inicializar db
from models.qr_model import QRCode, Scan

# Crear base de datos y tabla
with app.app_context():
    db.create_all()

# Obtener dirección ip
def get_real_ip():
    if 'X-Forwarded-For' in request.headers:
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

@app.before_request
def force_https():
    if request.host_url.startswith('http://') and not app.debug:
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)

@app.after_request
def add_client_hints(response):
    response.headers['Accept-CH'] = 'Sec-CH-UA, Sec-CH-UA-Platform, Sec-CH-UA-Model, Sec-CH-UA-Mobile'
    return response

@app.route('/', methods=['GET', 'POST'])
def main():
    qr_data = None
    if request.method == 'POST':
        text = request.form.get('text')
        if text:
            # Generar id del qr
            qr_id = 0
            qr_id = str(uuid.uuid4())
            tag = text.split('/')
            name_url = f"{tag[4]}:{tag[5]}"
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

            # Guardar qr en base de datos
            qr_code = QRCode(id=qr_id, url=text, tag=name_url, track_url=full_url, qr_image=qr_data)
            db.session.add(qr_code)
            db.session.commit()

            return redirect(url_for('qr_stats', qr_id=qr_id))
            
    return render_template('index.html', qr_data=qr_data)

# Url para ver estadisticas del código generado
@app.route('/qr/stats/<qr_id>')
def qr_stats(qr_id):
    data = QRCode.query.get_or_404(qr_id)
    scan_count = Scan.query.filter_by(qr_id=qr_id).count()
    scan_all = Scan.query.filter_by(qr_id=qr_id).limit(100).all()
    qr_data = data
    return render_template('qr_stats.html', data=qr_data, scan_count=scan_count, scan_all=scan_all)

@app.route('/qrcodes')
def qr_codes_list():
    data = QRCode.query.all()
    qr_list = data
    return render_template('qr_list.html', data=qr_list)

# Url para trackeo de código QR
@app.route('/qr/<qr_id>', methods=['GET'])
def qr(qr_id):
    # Obtenemos información sobre el SO y la plataforma
    ua_string = request.headers.get('User-Agent')
    user_agent = parse(ua_string)

    ip_address = get_real_ip()
    visited = request.cookies.get(f'unique_visited_{qr_id}')
    data = QRCode.query.get_or_404(qr_id)
    qr_data = data

    # Cuenta cuando el qr es escaneado
    if not visited:

        if qr_data is None:
            return "Código QR no encontrado"

        #Se incrementa el contador cuando la url del qr es visitada
        device_type = user_agent.device.family
        os = user_agent.os.family
        browser = user_agent.browser.family
        scan = Scan(
            qr_id=qr_id,
            device_type=device_type,
            os=os,
            browser=browser,
            ip_address=ip_address
        )
        db.session.add(scan)
        db.session.commit()
        response = make_response(redirect(qr_data.track_url))
        response.set_cookie(f'unique_visited_{qr_id}', 'true', max_age=60*60*24*365)
        return response
    
    return redirect(qr_data.url)

@app.route('/qr/delete/<qr_id>', methods=['POST'])
def  delete_qr(qr_id):
    qr = QRCode.query.get_or_404(qr_id)
    db.session.delete(qr)
    db.session.commit()

    return redirect(url_for('qr_codes_list'))
    
if __name__ == '__main__':
    port = os.environ.get('PORT', '5000')
    try:
        port = int(port)
    except ValueError:
        print(f"Error: Puerto inválido '{port}'. Usando 5000.")
        port = 5000
    print(f"Puerto configurado: {port}")
    app.run(host='0.0.0.0', port=port, debug=True)