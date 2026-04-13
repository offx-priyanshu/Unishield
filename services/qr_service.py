import qrcode
import os
from flask import current_app

class QRService:
    @staticmethod
    def generate_qr(data, filename):
        """
        Generates a QR code for the given data and saves it.
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        
        # Ensure uploads folder exists
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        filepath = os.path.join(upload_folder, filename)
        img.save(filepath)
        return filepath
