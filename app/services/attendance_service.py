import io

import qrcode
from flask import current_app, request


def build_attendance_url(request_obj, session_uuid: str) -> str:
    base_url = current_app.config.get('BASE_URL') or request_obj.host_url.rstrip('/')
    return f"{base_url.rstrip('/')}/attend/{session_uuid}"


def generate_qr_image(attendance_url: str) -> io.BytesIO:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(attendance_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#1a237e', back_color='white')

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer
