from app import db
from datetime import datetime
import pytz

# Modelo tabla qrcodes
class QRCode(db.Model):
    id = db.Column(db.String(100), primary_key=True)
    url = db.Column(db.Text, nullable=False)
    tag = db.Column(db.Text, nullable=False)
    track_url = db.Column(db.Text, nullable=False)
    qr_image = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(pytz.timezone('America/Bogota')))
    scans = db.relationship('Scan', backref='qrcode', lazy=True, cascade='all, delete') # Relación con eliminación en cascada

# Modelo para la tabla scans
class Scan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_id = db.Column(db.String(36), db.ForeignKey('qr_code.id'), nullable=False)
    device_type = db.Column(db.String(50))
    os = db.Column(db.String(50))
    browser = db.Column(db.String(50))
    ip_address = db.Column(db.String(45))  # Soporta IPv4 e IPv6
    scanned_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(pytz.timezone('America/Bogota')))