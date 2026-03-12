import os

class Config:
    SECRET_KEY = 'royal-spin-clave-secreta-2025-casino'
    SESSION_TYPE = 'filesystem'

    # ─── CONFIGURACIÓN MYSQL ────────────────────────────────────────
    # *** CAMBIA ESTOS DATOS POR LOS DE TU SERVIDOR MYSQL ***
    MYSQL_HOST     = 'localhost'
    MYSQL_USER     = 'root'          # <-- tu usuario MySQL
    MYSQL_PASSWORD = '0000'              # <-- tu contraseña MySQL
    MYSQL_DB       = 'casino'        # <-- nombre de la base de datos

    # ─── CONFIGURACIÓN DE CORREO ────────────────────────────────────
    MAIL_CONFIG = {
        'remitente': 'baironlozano334@gmail.com',
        'password':  'kujtklomjsawbxox',
        'nombre':    'Royal Spin Casino'
    }
