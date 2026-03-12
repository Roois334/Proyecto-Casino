from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
from config import Config
import os, random, json
import pymysql
import pymysql.cursors
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config.from_object(Config)

# ─── FILTRO FORMATO PESOS COLOMBIANOS
@app.template_filter("cop")
def formato_cop(value):
    try:
        v = float(value or 0)
        if v == int(v):
            formatted = "{:,.0f}".format(int(v)).replace(",", ".")
            return formatted
        else:
            int_part = int(v)
            dec_part = round((v - int_part) * 100)
            formatted_int = "{:,.0f}".format(int_part).replace(",", ".")
            return f"{formatted_int},{dec_part:02d}"
    except:
        return str(value)

# ─── FILTRO PARA FECHAS MYSQL ────────────────────────────────────────────────
@app.template_filter("fecha")
def formato_fecha(value, fmt="%Y-%m-%d"):
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime(fmt)
    return str(value)[:10]

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
SESSION_DIR = os.path.join(BASE_DIR, 'flask_session')
os.makedirs(SESSION_DIR, exist_ok=True)

# ─── CONEXIÓN MYSQL ───────────────────────────────────────────────────────────

def get_db():
    conn = pymysql.connect(
        host        = app.config['MYSQL_HOST'],
        user        = app.config['MYSQL_USER'],
        password    = app.config['MYSQL_PASSWORD'],
        database    = app.config['MYSQL_DB'],
        charset     = 'utf8mb4',
        cursorclass = pymysql.cursors.DictCursor,
        connect_timeout = 10
    )
    return conn

def init_db():
    """Crear tablas y datos iniciales si no existen"""
    conn = get_db()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id               INT            PRIMARY KEY AUTO_INCREMENT,
            nombre           VARCHAR(100)   NOT NULL,
            cedula           VARCHAR(20),
            email            VARCHAR(120)   UNIQUE NOT NULL,
            password         VARCHAR(255)   NOT NULL,
            fecha_nacimiento DATE           NOT NULL,
            rol              VARCHAR(20)    DEFAULT 'jugador',
            saldo            DECIMAL(10,2)  DEFAULT 0.00,
            puntos_vip       INT            DEFAULT 0,
            descripcion      TEXT,
            reset_token      VARCHAR(100),
            reset_expiry     DATETIME,
            fecha_registro   DATETIME       DEFAULT CURRENT_TIMESTAMP,
            activo           TINYINT(1)     DEFAULT 1,
            bloqueado        TINYINT(1)     DEFAULT 0,
            razon_bloqueo    TEXT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    try:
        cur.execute("ALTER TABLE usuarios ADD COLUMN saldo_rsc DECIMAL(14,4) DEFAULT 0.0000")
        conn.commit()
    except:
        pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS juegos (
            id                   INT           PRIMARY KEY AUTO_INCREMENT,
            nombre               VARCHAR(100)  NOT NULL,
            descripcion          TEXT,
            icono                VARCHAR(10),
            tipo                 VARCHAR(50),
            rtp                  DECIMAL(4,2)  DEFAULT 96.50,
            apuesta_minima       DECIMAL(6,2)  DEFAULT 1.00,
            apuesta_maxima       DECIMAL(12,2)  DEFAULT 1000.00,
            multiplicador_maximo INT           DEFAULT 100,
            activo               TINYINT(1)    DEFAULT 1,
            fecha_creacion       DATETIME      DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS depositos (
            id               INT            PRIMARY KEY AUTO_INCREMENT,
            usuario_id       INT            NOT NULL,
            monto            DECIMAL(10,2)  NOT NULL,
            metodo           VARCHAR(50)    DEFAULT 'transferencia',
            estado           VARCHAR(20)    DEFAULT 'pendiente',
            nota             TEXT,
            fecha            DATETIME       DEFAULT CURRENT_TIMESTAMP,
            fecha_resolucion DATETIME,
            admin_id         INT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (admin_id)   REFERENCES usuarios(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS retiros (
            id               INT            PRIMARY KEY AUTO_INCREMENT,
            usuario_id       INT            NOT NULL,
            monto            DECIMAL(10,2)  NOT NULL,
            metodo           VARCHAR(50)    DEFAULT 'transferencia',
            cuenta_destino   VARCHAR(100),
            estado           VARCHAR(20)    DEFAULT 'pendiente',
            nota             TEXT,
            fecha            DATETIME       DEFAULT CURRENT_TIMESTAMP,
            fecha_resolucion DATETIME,
            admin_id         INT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (admin_id)   REFERENCES usuarios(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS apuestas (
            id             INT            PRIMARY KEY AUTO_INCREMENT,
            usuario_id     INT            NOT NULL,
            juego_id       INT            NOT NULL,
            monto_apostado DECIMAL(10,2)  NOT NULL,
            monto_ganado   DECIMAL(10,2)  DEFAULT 0.00,
            resultado      VARCHAR(200),
            detalles       TEXT,
            fecha          DATETIME       DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (juego_id)   REFERENCES juegos(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS promociones (
            id             INT            PRIMARY KEY AUTO_INCREMENT,
            nombre         VARCHAR(100)   NOT NULL,
            descripcion    TEXT,
            tipo           VARCHAR(50),
            porcentaje     INT,
            monto_maximo   DECIMAL(10,2),
            activa         TINYINT(1)     DEFAULT 1,
            fecha_creacion DATETIME       DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS soporte (
            id              INT          PRIMARY KEY AUTO_INCREMENT,
            usuario_id      INT          NOT NULL,
            asunto          VARCHAR(255),
            mensaje         TEXT,
            estado          VARCHAR(20)  DEFAULT 'abierto',
            respuesta       TEXT,
            fecha_creacion  DATETIME     DEFAULT CURRENT_TIMESTAMP,
            fecha_respuesta DATETIME,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cur.execute("""
        INSERT INTO juegos (id,nombre,descripcion,icono,tipo,rtp,apuesta_minima,apuesta_maxima,multiplicador_maximo)
        VALUES
        (1,'Tragamonedas','Gira los rodillos y consigue 3 símbolos iguales.','','slots',96.50,100.00,99999999.00,100),
        (2,'Ruleta','Apuesta a número exacto (x36), color, par/impar o alto/bajo.','','rueda',97.30,100.00,99999999.00,36),
        (3,'Blackjack','Llega a 21 sin pasarte. Supera al crupier.','','cartas',99.40,100.00,99999999.00,2),
        (4,'Dados','Elige un número del 1 al 6. Si aciertas, ganas x5.','','dados',97.80,100.00,99999999.00,5),
        (5,'Colores','Elige Rojo o Dorado. Acierta el color y gana x2.','◆','colores',97.10,100.00,99999999.00,2)
        ON DUPLICATE KEY UPDATE nombre=VALUES(nombre),descripcion=VALUES(descripcion),icono=VALUES(icono),tipo=VALUES(tipo),rtp=VALUES(rtp),apuesta_minima=VALUES(apuesta_minima),apuesta_maxima=VALUES(apuesta_maxima),multiplicador_maximo=VALUES(multiplicador_maximo)
    """)
    cur.execute("UPDATE juegos SET activo=0 WHERE id=5")
    cur.execute("UPDATE juegos SET apuesta_minima=100.00,apuesta_maxima=99999999.00 WHERE id=1")
    cur.execute("UPDATE juegos SET apuesta_minima=100.00,apuesta_maxima=99999999.00 WHERE id=2")
    cur.execute("UPDATE juegos SET apuesta_minima=100.00,apuesta_maxima=99999999.00 WHERE id=3")
    cur.execute("UPDATE juegos SET apuesta_minima=100.00,apuesta_maxima=99999999.00 WHERE id=4")

    cur.execute("""
        INSERT IGNORE INTO promociones (nombre,descripcion,tipo,porcentaje,monto_maximo)
        VALUES
        ('Bono Bienvenida','COP$10.000 gratis al registrarte.','bienvenida',100,500.00),
        ('Cashback Diario','Recupera hasta el 10%% de tus pérdidas diarias.','cashback',10,200.00),
        ('Programa VIP','1 punto por cada COP$10 apostado.','vip',5,1000.00)
    """)



    conn.commit()
    cur.close()
    conn.close()

try:
    init_db()
    print("[DB] Conectado a MySQL correctamente ")
except Exception as e:
    print(f"[DB ERROR] No se pudo conectar a MySQL: {e}")
    print("[DB] Verifica MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD y MYSQL_DB en config.py")

# ─── DECORADORES ───────────────────────────────────────────────────────────────

from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario' not in session:
            flash('Debes iniciar sesión primero','error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario' not in session or session['usuario']['rol'] != 'admin':
            flash('Acceso restringido','error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def calcular_edad(fn_str):
    try:
        fn  = datetime.strptime(str(fn_str), '%Y-%m-%d').date()
        hoy = date.today()
        return hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
    except:
        return 0

def sync_saldo_session():
    if 'usuario' in session:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute('SELECT saldo FROM usuarios WHERE id=%s', (session['usuario']['id'],))
        u = cur.fetchone()
        cur.close(); conn.close()
        if u:
            session['usuario']['saldo'] = float(u['saldo'])
            session.modified = True

# ─── RUTAS PÚBLICAS ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'usuario' in session:
        return redirect(url_for('juegos'))
    return render_template('bienvenida.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if 'usuario' in session:
        return redirect(url_for('juegos'))
    if request.method == 'POST':
        usuario  = request.form.get('usuario','').strip()
        password = request.form.get('password','')
        conn = get_db(); cur = conn.cursor()
        cur.execute('SELECT * FROM usuarios WHERE nombre=%s OR email=%s', (usuario, usuario))
        user = cur.fetchone()
        cur.close(); conn.close()
        if user and check_password_hash(user['password'], password):
            if user['bloqueado']:
                flash(f'Cuenta bloqueada: {user["razon_bloqueo"] or "contacta soporte"}','error')
                return render_template('login.html')
            session['usuario'] = {
                'id': user['id'], 'nombre': user['nombre'],
                'email': user['email'], 'rol': user['rol'],
                'saldo': float(user['saldo'])
            }
            flash(f'¡Bienvenido, {user["nombre"]}!','success')
            return redirect(url_for('admin_panel') if user['rol']=='admin' else url_for('juegos'))
        flash('Usuario o contraseña incorrectos','error')
    return render_template('login.html')

@app.route('/registro', methods=['GET','POST'])
def registro():
    if 'usuario' in session:
        return redirect(url_for('juegos'))
    if request.method == 'POST':
        import re
        nombre   = request.form.get('nombre','').strip()
        cedula   = request.form.get('cedula','').strip()
        email    = request.form.get('email','').strip()
        password = request.form.get('password','')
        fn       = request.form.get('fecha_nacimiento','')
        conf     = request.form.get('confirmar_password','')

        if not all([nombre, cedula, email, password, fn]):
            flash('Completa todos los campos','error')
            return render_template('registro.html', max_date=_max_date())
        if re.search(r'\d', nombre):
            flash('El nombre no puede contener números','error')
            return render_template('registro.html', max_date=_max_date())
        if not re.match(r'^\d{5,}$', cedula):
            flash('La cédula solo acepta números, mínimo 5 dígitos','error')
            return render_template('registro.html', max_date=_max_date())
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres','error')
            return render_template('registro.html', max_date=_max_date())
        if password != conf:
            flash('Las contraseñas no coinciden','error')
            return render_template('registro.html', max_date=_max_date())
        if calcular_edad(fn) < 18:
            flash('Debes ser mayor de 18 años','error')
            return render_template('registro.html', max_date=_max_date(), menor_de_edad=True)

        conn = get_db(); cur = conn.cursor()
        cur.execute('SELECT id FROM usuarios WHERE email=%s', (email,))
        if cur.fetchone():
            flash('Este email ya está registrado','error')
            cur.close(); conn.close()
            return render_template('registro.html', max_date=_max_date())
        cur.execute('SELECT id FROM usuarios WHERE cedula=%s', (cedula,))
        if cur.fetchone():
            flash('Esta cédula ya está registrada en el sistema','error')
            cur.close(); conn.close()
            return render_template('registro.html', max_date=_max_date())
        try:
            cur.execute(
                'INSERT INTO usuarios (nombre,cedula,email,password,fecha_nacimiento,rol,saldo,puntos_vip) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                (nombre, cedula, email, generate_password_hash(password), fn, 'jugador', 10000.00, 0)
            )
            conn.commit()
            cur.execute('SELECT * FROM usuarios WHERE email=%s', (email,))
            user = cur.fetchone()
            session['usuario'] = {'id':user['id'],'nombre':user['nombre'],'email':user['email'],'rol':user['rol'],'saldo':10000.00}
            flash('Bienvenido a Royal Spin — Recibiste COP$10.000 de bienvenida','success')
            cur.close(); conn.close()
            return redirect(url_for('juegos'))
        except Exception as e:
            flash(f'Error al registrar: {str(e)}','error')
            cur.close(); conn.close()
    return render_template('registro.html', max_date=_max_date())

def _max_date():
    t = date.today()
    try: return date(t.year-18, t.month, t.day).isoformat()
    except: return date(t.year-18, t.month, 28).isoformat()

# ─── RESET CONTRASEÑA ──────────────────────────────────────────────────────────

@app.route('/forgot-password')
def forgot_password():
    flash('Para recuperar tu contraseña contacta al administrador por soporte.','info')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ─── USUARIO ───────────────────────────────────────────────────────────────────

@app.route('/juegos')
@login_required
def juegos():
    sync_saldo_session()
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM juegos WHERE activo=1 ORDER BY id")
    games = cur.fetchall()
    cur.close(); conn.close()
    return render_template('juegos.html', juegos=games)

@app.route('/dashboard')
@login_required
def dashboard():
    sync_saldo_session()
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM usuarios WHERE id=%s', (session['usuario']['id'],))
    user = cur.fetchone()
    cur.execute('''SELECT COUNT(*) as total_apuestas,
               COALESCE(SUM(monto_apostado),0) as total_apostado,
               COALESCE(SUM(monto_ganado),0) as total_ganado
        FROM apuestas WHERE usuario_id=%s''', (session['usuario']['id'],))
    stats = cur.fetchone()
    cur.execute("SELECT COUNT(*) as c FROM depositos WHERE usuario_id=%s AND estado='pendiente'", (session['usuario']['id'],))
    dep_p = cur.fetchone()
    cur.execute("SELECT COUNT(*) as c FROM retiros WHERE usuario_id=%s AND estado='pendiente'", (session['usuario']['id'],))
    ret_p = cur.fetchone()
    cur.execute('''SELECT a.*, j.nombre as juego_nombre, j.icono
        FROM apuestas a JOIN juegos j ON a.juego_id=j.id
        WHERE a.usuario_id=%s ORDER BY a.fecha DESC LIMIT 5''', (session['usuario']['id'],))
    ultimas = cur.fetchall()
    cur.close(); conn.close()
    return render_template('dashboard.html', user=user, stats=stats,
                           dep_pendientes=dep_p['c'], ret_pendientes=ret_p['c'], ultimas_apuestas=ultimas)

@app.route('/juego/<int:juego_id>')
@login_required
def juego(juego_id):
    if session['usuario'].get('rol') == 'admin':
        flash('Los administradores no pueden jugar. Usa una cuenta de jugador.','error')
        return redirect(url_for('admin_panel'))
    sync_saldo_session()

    if session.get('blackjack_state'):
        session.pop('blackjack_state', None)
        session.modified = True

    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM juegos WHERE id=%s AND activo=1', (juego_id,))
    game = cur.fetchone()
    if not game:
        flash('Juego no disponible','error')
        cur.close(); conn.close()
        return redirect(url_for('juegos'))
    cur.execute('SELECT * FROM usuarios WHERE id=%s', (session['usuario']['id'],))
    user = cur.fetchone()
    cur.close(); conn.close()
    return render_template('juego_detalles.html', juego=game, user=user)

# ─── API JUGAR ─────────────────────────────────────────────────────────────────

@app.route('/api/jugar', methods=['POST'])
@login_required
def api_jugar():
    if session['usuario'].get('rol') == 'admin':
        return jsonify({'error': 'Administradores no pueden jugar'}), 403
    data     = request.get_json()
    juego_id = data.get('juego_id')
    apuesta  = float(data.get('apuesta', 0))
    extra    = data.get('extra', {})
    accion   = data.get('accion', 'jugar')

    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM usuarios WHERE id=%s', (session['usuario']['id'],))
    user = cur.fetchone()
    cur.execute('SELECT * FROM juegos WHERE id=%s AND activo=1', (juego_id,))
    game = cur.fetchone()

    if not game:
        cur.close(); conn.close()
        return jsonify({'error':'Juego no disponible'}), 400

    saldo_actual = float(user['saldo'])

    apuesta_min_real = 100.0
    apuesta_max_real = saldo_actual

    # ══ BLACKJACK INTERACTIVO ══
    if game['tipo'] == 'cartas':
        bj = session.get('blackjack_state')

        def carta_val(c):
            if c in ['J','Q','K']: return 10
            if c == 'A': return 11
            return int(c) if str(c).isdigit() else 0

        def calc_suma(mano):
            s = sum(carta_val(c) for c in mano)
            ases = mano.count('A')
            while s > 21 and ases > 0:
                s -= 10; ases -= 1
            return s

        cartas_baraja = ['2','3','4','5','6','7','8','9','10','J','Q','K','A'] * 4
        random.shuffle(cartas_baraja)

        if accion == 'jugar':
            if apuesta < apuesta_min_real:
                cur.close(); conn.close()
                return jsonify({'error':f'Apuesta mínima COP$100'}), 400
            if saldo_actual < apuesta:
                cur.close(); conn.close()
                return jsonify({'error':'Saldo insuficiente'}), 400

            mano_j = [random.choice(cartas_baraja), random.choice(cartas_baraja)]
            mano_c = [random.choice(cartas_baraja), random.choice(cartas_baraja)]
            suma_j = calc_suma(mano_j)

            nuevo_saldo = saldo_actual - apuesta
            cur.execute('UPDATE usuarios SET saldo=%s WHERE id=%s', (nuevo_saldo, session['usuario']['id']))
            conn.commit()
            session['usuario']['saldo'] = nuevo_saldo
            session.modified = True

            puede_split = (carta_val(mano_j[0]) == carta_val(mano_j[1])) and (saldo_actual >= apuesta * 2)
            if suma_j == 21:
                suma_c_final = calc_suma(mano_c)
                if suma_c_final == 21:
                    ganancia = apuesta; msg = 'Empate - Blackjack mutuo'
                else:
                    ganancia = apuesta * 2.5; msg = 'BLACKJACK NATURAL! Pago x2.5'
                nuevo_saldo2 = nuevo_saldo + ganancia
                cur.execute('UPDATE usuarios SET saldo=%s WHERE id=%s', (nuevo_saldo2, session['usuario']['id']))
                cur.execute('INSERT INTO apuestas (usuario_id,juego_id,monto_apostado,monto_ganado,resultado,detalles) VALUES (%s,%s,%s,%s,%s,%s)',
                            (session['usuario']['id'],juego_id,apuesta,ganancia,msg,json.dumps({'mano_j':mano_j,'mano_c':mano_c})))
                cur.execute('UPDATE usuarios SET puntos_vip=puntos_vip+%s WHERE id=%s', (int(apuesta/10), session['usuario']['id']))
                conn.commit()
                session['usuario']['saldo'] = nuevo_saldo2
                session.pop('blackjack_state', None)
                cur.close(); conn.close()
                return jsonify({'estado':'blackjack','mano_jugador':mano_j,'mano_crupier':mano_c,'suma_j':suma_j,'suma_c':calc_suma(mano_c),'resultado':msg,'nuevo_saldo':nuevo_saldo2,'gano':ganancia>apuesta,'ganancia':ganancia,'terminado':True,'puede_split':False})

            session['blackjack_state'] = {'mano_j':mano_j,'mano_c':mano_c,'apuesta':apuesta,'saldo_pre':saldo_actual}
            session.modified = True
            cur.close(); conn.close()
            return jsonify({'estado':'jugando','mano_jugador':mano_j,'mano_crupier_visible':[mano_c[0],'back'],'suma_j':suma_j,'suma_c_visible':carta_val(mano_c[0]),'nuevo_saldo':nuevo_saldo,'terminado':False,'puede_split':puede_split})

        elif accion == 'pedir':
            if not bj:
                cur.close(); conn.close()
                return jsonify({'error':'No hay partida activa'}), 400
            nueva_carta = random.choice(cartas_baraja)
            en_split = bj.get('en_split', False)

            if en_split and 'split_mano' in bj:
                bj['split_mano'].append(nueva_carta)
                suma_j = calc_suma(bj['split_mano'])
                session['blackjack_state'] = bj
                session.modified = True
                if suma_j > 21:
                    apuesta_bj = bj.get('split_apuesta', bj['apuesta'])
                    mano_c = bj['mano_c']
                    while calc_suma(mano_c) < 17:
                        mano_c.append(random.choice(cartas_baraja))
                    suma_c = calc_suma(mano_c)
                    mano_j1_ref = bj['mano_j']
                    suma_m1 = calc_suma(mano_j1_ref)
                    es_bj_m1 = len(mano_j1_ref) == 2 and suma_m1 == 21
                    es_bj_crupier_m2 = len(mano_c) == 2 and suma_c == 21
                    if suma_m1 > 21: g1 = 0
                    elif es_bj_m1 and es_bj_crupier_m2: g1 = apuesta_bj
                    elif es_bj_m1: g1 = apuesta_bj * 2.5
                    elif suma_c > 21: g1 = apuesta_bj * 2
                    elif suma_m1 > suma_c: g1 = apuesta_bj * 2
                    elif suma_m1 == suma_c: g1 = apuesta_bj
                    else: g1 = 0
                    ganancia = g1
                    msg = f'Mano 2 bust! Mano 1: {"Gana" if g1>0 else "Pierde"}'
                    nuevo_saldo2 = float(session['usuario']['saldo']) + ganancia
                    cur.execute('UPDATE usuarios SET saldo=%s, puntos_vip=puntos_vip+%s WHERE id=%s',
                                (nuevo_saldo2, int(apuesta_bj/10), session['usuario']['id']))
                    cur.execute('INSERT INTO apuestas (usuario_id,juego_id,monto_apostado,monto_ganado,resultado,detalles) VALUES (%s,%s,%s,%s,%s,%s)',
                                (session['usuario']['id'],juego_id,apuesta_bj*2,ganancia,msg,json.dumps({'split':True,'mano_j':bj['mano_j'],'split_mano':bj['split_mano'],'mano_c':mano_c})))
                    conn.commit()
                    session['usuario']['saldo'] = nuevo_saldo2
                    session.pop('blackjack_state', None)
                    cur.close(); conn.close()
                    return jsonify({'estado':'terminado','mano_jugador':bj['mano_j'],'mano_crupier':mano_c,'suma_j':calc_suma(bj['mano_j']),'suma_j2':suma_j,'suma_c':suma_c,'resultado':msg,'nuevo_saldo':nuevo_saldo2,'gano':ganancia>0,'ganancia':ganancia,'terminado':True,'split_mano':bj['split_mano']})
                cur.close(); conn.close()
                return jsonify({'estado':'split_jugando','mano_jugador':bj['split_mano'],'suma_j':suma_j,'suma_j2':suma_j,'split_mano':bj['split_mano'],'terminado':False,'nuevo_saldo':session['usuario']['saldo'],'en_split':True})
            else:
                if 'split_mano' in bj and not en_split:
                    bj['mano_j'].append(nueva_carta)
                    suma_j = calc_suma(bj['mano_j'])
                    session['blackjack_state'] = bj
                    session.modified = True
                    if suma_j > 21:
                        session['blackjack_state'] = bj
                        session.modified = True
                        cur.close(); conn.close()
                        return jsonify({'estado':'split_mano1_bust','mano_jugador':bj['mano_j'],'suma_j':suma_j,'terminado':True,'nuevo_saldo':session['usuario']['saldo'],'split_mano':bj['split_mano'],'suma_j2':calc_suma(bj['split_mano'])})
                    cur.close(); conn.close()
                    return jsonify({'estado':'split_jugando','mano_jugador':bj['mano_j'],'suma_j':suma_j,'terminado':False,'nuevo_saldo':session['usuario']['saldo'],'en_split':False})
                else:
                    bj['mano_j'].append(nueva_carta)
                    suma_j = calc_suma(bj['mano_j'])
                    session['blackjack_state'] = bj
                    session.modified = True
                    if suma_j > 21:
                        apuesta_bj = bj['apuesta']
                        cur.execute('INSERT INTO apuestas (usuario_id,juego_id,monto_apostado,monto_ganado,resultado,detalles) VALUES (%s,%s,%s,%s,%s,%s)',
                                    (session['usuario']['id'],juego_id,apuesta_bj,0,'Bust - Te pasaste',json.dumps({'mano_j':bj['mano_j'],'mano_c':bj['mano_c']})))
                        cur.execute('UPDATE usuarios SET puntos_vip=puntos_vip+%s WHERE id=%s', (int(apuesta_bj/10), session['usuario']['id']))
                        conn.commit()
                        session.pop('blackjack_state', None)
                        cur.close(); conn.close()
                        return jsonify({'estado':'bust','mano_jugador':bj['mano_j'],'mano_crupier':bj['mano_c'],'suma_j':suma_j,'suma_c':calc_suma(bj['mano_c']),'resultado':'Bust! Te pasaste de 21','nuevo_saldo':session['usuario']['saldo'],'gano':False,'terminado':True})
                    cur.close(); conn.close()
                    return jsonify({'estado':'jugando','mano_jugador':bj['mano_j'],'suma_j':suma_j,'terminado':False,'nuevo_saldo':session['usuario']['saldo']})

        elif accion == 'split':
            if not bj: cur.close(); conn.close(); return jsonify({'error':'No hay partida activa'}), 400
            if saldo_actual < bj['apuesta']: cur.close(); conn.close(); return jsonify({'error':'Saldo insuficiente para split'}), 400
            carta2 = bj['mano_j'].pop(1)
            bj['mano_j'].append(random.choice(cartas_baraja))
            bj['split_mano'] = [carta2, random.choice(cartas_baraja)]
            bj['split_apuesta'] = bj['apuesta']; bj['en_split'] = False
            nsp = saldo_actual - bj['apuesta']
            cur.execute('UPDATE usuarios SET saldo=%s WHERE id=%s', (nsp, session['usuario']['id']))
            conn.commit(); session['usuario']['saldo']=nsp; session['blackjack_state']=bj; session.modified=True
            cur.close(); conn.close()
            return jsonify({'estado':'split','mano_jugador':bj['mano_j'],'split_mano':bj['split_mano'],'mano_crupier_visible':[bj['mano_c'][0],'back'],'suma_j':calc_suma(bj['mano_j']),'suma_j2':calc_suma(bj['split_mano']),'suma_c_visible':carta_val(bj['mano_c'][0]),'nuevo_saldo':nsp,'terminado':False,'en_split':False})

        elif accion == 'split_siguiente':
            if not bj: cur.close(); conn.close(); return jsonify({'error':'No hay partida activa'}), 400
            bj['en_split'] = True; session['blackjack_state']=bj; session.modified=True; cur.close(); conn.close()
            return jsonify({'estado':'split_mano2','mano_jugador':bj['mano_j'],'split_mano':bj['split_mano'],'suma_j':calc_suma(bj['mano_j']),'suma_j2':calc_suma(bj['split_mano']),'nuevo_saldo':session['usuario']['saldo'],'terminado':False,'en_split':True})

        elif accion in ('plantarse','doblar'):
            if not bj:
                cur.close(); conn.close()
                return jsonify({'error':'No hay partida activa'}), 400

            en_split = bj.get('en_split', False)
            tiene_split = 'split_mano' in bj

            if tiene_split and not en_split:
                if accion == 'doblar':
                    if saldo_actual < bj['apuesta']:
                        cur.close(); conn.close()
                        return jsonify({'error':'Saldo insuficiente para doblar'}), 400
                    nc = random.choice(cartas_baraja)
                    bj['mano_j'].append(nc)
                    bj['split_apuesta_m1'] = bj.get('split_apuesta', bj['apuesta']) * 2
                    ns_dbl = saldo_actual - bj.get('split_apuesta', bj['apuesta'])
                    cur.execute('UPDATE usuarios SET saldo=%s WHERE id=%s', (ns_dbl, session['usuario']['id']))
                    conn.commit()
                    session['usuario']['saldo'] = ns_dbl
                    suma_m1 = calc_suma(bj['mano_j'])
                    session['blackjack_state'] = bj
                    session.modified = True
                    cur.close(); conn.close()
                    return jsonify({'estado':'split_mano1_listo','mano_jugador':bj['mano_j'],'split_mano':bj['split_mano'],'suma_j':suma_m1,'suma_j2':calc_suma(bj['split_mano']),'nuevo_saldo':ns_dbl,'terminado':False,'doblado':True})
                session['blackjack_state'] = bj
                session.modified = True
                cur.close(); conn.close()
                return jsonify({'estado':'split_mano1_listo','mano_jugador':bj['mano_j'],'split_mano':bj['split_mano'],'suma_j':calc_suma(bj['mano_j']),'suma_j2':calc_suma(bj['split_mano']),'nuevo_saldo':session['usuario']['saldo'],'terminado':False})

            if tiene_split and en_split:
                mano_j1 = bj['mano_j']
                mano_j2 = bj.get('split_mano', [])
                mano_c = bj['mano_c']
                apuesta_base = bj.get('split_apuesta', bj['apuesta'])
                apuesta_bj = bj.get('split_apuesta_m1', apuesta_base)

                if accion == 'doblar':
                    if saldo_actual < apuesta_bj:
                        cur.close(); conn.close()
                        return jsonify({'error':'Saldo insuficiente para doblar'}), 400
                    nc = random.choice(cartas_baraja)
                    mano_j2.append(nc)
                    apuesta_bj_2 = apuesta_bj * 2
                    ns_dbl = saldo_actual - apuesta_bj
                    cur.execute('UPDATE usuarios SET saldo=%s WHERE id=%s', (ns_dbl, session['usuario']['id']))
                    conn.commit(); session['usuario']['saldo'] = ns_dbl
                else:
                    apuesta_bj_2 = apuesta_bj

                while calc_suma(mano_c) < 17:
                    mano_c.append(random.choice(cartas_baraja))
                suma_c = calc_suma(mano_c)
                suma_j1 = calc_suma(mano_j1)
                suma_j2 = calc_suma(mano_j2)

                def es_blackjack_natural(mano):
                    return len(mano) == 2 and calc_suma(mano) == 21

                def calc_result(suma_j, ap, suma_c, mano=None):
                    es_bj = mano is not None and es_blackjack_natural(mano)
                    es_bj_crupier = es_blackjack_natural(mano_c)
                    if suma_j > 21: return 0, f'Bust'
                    elif es_bj and es_bj_crupier: return ap, f'Empate - Blackjack mutuo ({suma_j})'
                    elif es_bj: return ap * 2.5, f'BLACKJACK! Pago x2.5 ({suma_j})'
                    elif suma_c > 21: return ap*2, f'Ganaste ({suma_j})'
                    elif suma_j > suma_c: return ap*2, f'Ganaste ({suma_j})'
                    elif suma_j == suma_c: return ap, f'Empate ({suma_j})'
                    else: return 0, f'Perdiste ({suma_j})'

                g1, msg1 = calc_result(suma_j1, apuesta_bj, suma_c, mano_j1)
                g2, msg2 = calc_result(suma_j2, apuesta_bj_2, suma_c, mano_j2)
                ganancia_total = g1 + g2
                apuesta_total = apuesta_bj + apuesta_bj_2
                msg_final = f'Mano 1: {msg1}  —  Mano 2: {msg2}'

                nuevo_saldo2 = float(session['usuario']['saldo']) + ganancia_total
                cur.execute('UPDATE usuarios SET saldo=%s, puntos_vip=puntos_vip+%s WHERE id=%s',
                            (nuevo_saldo2, int(apuesta_total/10), session['usuario']['id']))
                cur.execute('INSERT INTO apuestas (usuario_id,juego_id,monto_apostado,monto_ganado,resultado,detalles) VALUES (%s,%s,%s,%s,%s,%s)',
                            (session['usuario']['id'],juego_id,apuesta_total,ganancia_total,msg_final,json.dumps({'split':True,'mano_j1':mano_j1,'mano_j2':mano_j2,'mano_c':mano_c,'suma_c':suma_c})))
                conn.commit()
                session['usuario']['saldo'] = nuevo_saldo2
                session.pop('blackjack_state', None)
                session.modified = True
                cur.close(); conn.close()
                return jsonify({'estado':'terminado','mano_jugador':mano_j1,'split_mano':mano_j2,'mano_crupier':mano_c,'suma_j':suma_j1,'suma_j2':suma_j2,'suma_c':suma_c,'resultado':msg_final,'nuevo_saldo':nuevo_saldo2,'gano':ganancia_total>apuesta_total,'ganancia':ganancia_total,'terminado':True})

            mano_j = bj['mano_j']; mano_c = bj['mano_c']; apuesta_bj = bj['apuesta']
            if accion == 'doblar':
                if saldo_actual < apuesta_bj:
                    cur.close(); conn.close()
                    return jsonify({'error':'Saldo insuficiente para doblar'}), 400
                nueva_carta = random.choice(cartas_baraja)
                mano_j.append(nueva_carta)
                apuesta_bj *= 2
                nuevo_saldo = saldo_actual - (apuesta_bj/2)
                cur.execute('UPDATE usuarios SET saldo=%s WHERE id=%s', (nuevo_saldo, session['usuario']['id']))
                conn.commit()
                session['usuario']['saldo'] = nuevo_saldo
            suma_j = calc_suma(mano_j)
            while calc_suma(mano_c) < 17:
                mano_c.append(random.choice(cartas_baraja))
            suma_c = calc_suma(mano_c)
            if suma_j > 21:
                ganancia = 0; msg = f'Bust ({suma_j}). Perdiste'
            elif suma_c > 21:
                ganancia = apuesta_bj * 2; msg = f'Crupier bust! Tu {suma_j} gana'
            elif suma_j > suma_c:
                ganancia = apuesta_bj * 2; msg = f'Ganaste! {suma_j} vs {suma_c}'
            elif suma_j == suma_c:
                ganancia = apuesta_bj; msg = f'Empate {suma_j} - devuelto'
            else:
                ganancia = 0; msg = f'Perdiste. {suma_j} vs {suma_c}'
            nuevo_saldo2 = session['usuario']['saldo'] + ganancia
            cur.execute('UPDATE usuarios SET saldo=%s, puntos_vip=puntos_vip+%s WHERE id=%s',
                        (nuevo_saldo2, int(apuesta_bj/10), session['usuario']['id']))
            cur.execute('INSERT INTO apuestas (usuario_id,juego_id,monto_apostado,monto_ganado,resultado,detalles) VALUES (%s,%s,%s,%s,%s,%s)',
                        (session['usuario']['id'],juego_id,apuesta_bj,ganancia,msg,json.dumps({'mano_j':mano_j,'mano_c':mano_c,'suma_j':suma_j,'suma_c':suma_c})))
            conn.commit()
            session['usuario']['saldo'] = nuevo_saldo2
            session.pop('blackjack_state', None)
            session.modified = True
            cur.close(); conn.close()
            return jsonify({'estado':'terminado','mano_jugador':mano_j,'mano_crupier':mano_c,'suma_j':suma_j,'suma_c':suma_c,'resultado':msg,'nuevo_saldo':nuevo_saldo2,'gano':ganancia>0,'ganancia':ganancia,'terminado':True})

    # ══ OTROS JUEGOS ══
    if game['tipo'] != 'rueda':
        if apuesta < apuesta_min_real:
            cur.close(); conn.close()
            return jsonify({'error':'Apuesta mínima COP$100'}), 400
        if saldo_actual < apuesta:
            cur.close(); conn.close()
            return jsonify({'error':'Saldo insuficiente'}), 400

    ganancia = 0; resultado = ''; detalles = {}

    if game['tipo'] == 'slots':
        simbolos = ['Q','K','A','H','D','P','7','T']
        pesos    = [28, 22, 18, 13, 9, 6, 3, 1]
        r1 = random.choices(simbolos, weights=pesos)[0]
        r2 = random.choices(simbolos, weights=pesos)[0]
        r3 = random.choices(simbolos, weights=pesos)[0]
        detalles = {'r1':r1,'r2':r2,'r3':r3}
        mults = {'Q':3,'K':4,'A':5,'H':8,'D':15,'P':25,'7':50,'T':100}
        sym_nombres = {'Q':'👸 Reina','K':'👑 Rey','A':'🅰️ As','H':'♥️ Corazón','D':'🍀 Trébol','P':'♠️ Picas','7':'7️⃣ Siete','T':'💎 Diamante'}
        n1 = sym_nombres.get(r1, r1); n2 = sym_nombres.get(r2, r2); n3 = sym_nombres.get(r3, r3)
        if r1==r2==r3:
            m = mults.get(r1,3); ganancia = apuesta*m
            resultado = f'JACKPOT! {n1} — {n2} — {n3} x{m}'
        elif r1==r2 or r2==r3 or r1==r3:
            ganancia = apuesta*1.5; resultado = f'Par! {n1} — {n2} — {n3} x1.5'
        else:
            resultado = f'{n1} — {n2} — {n3} — Sin premio'

    elif game['tipo'] == 'rueda':
        bets_dict = extra.get('bets', {})
        if not bets_dict:
            tipo_ap = extra.get('tipo','rojo')
            bets_dict = {tipo_ap: apuesta}

        numero  = random.randint(0,36)
        rojos   = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
        color   = 'verde' if numero==0 else ('rojo' if numero in rojos else 'negro')
        columna = 0 if numero==0 else ((numero-1)%3+1)
        docena  = 0 if numero==0 else ((numero-1)//12+1)

        total_apostado = sum(float(v) for v in bets_dict.values())
        detalles = {'numero':numero,'color':color,'total_apostado':total_apostado}

        if saldo_actual < total_apostado:
            cur.close(); conn.close()
            return jsonify({'error':'Saldo insuficiente'}), 400

        ganancia = 0
        winning_bets = []
        for tipo_ap, monto_ap in bets_dict.items():
            monto_ap = float(monto_ap)
            g = 0
            if tipo_ap == str(numero):
                g = monto_ap * 36; winning_bets.append(f'Num {numero} x36')
            elif tipo_ap == color:
                g = monto_ap * 2; winning_bets.append(f'{color.capitalize()} x2')
            elif tipo_ap == 'par' and numero != 0 and numero % 2 == 0:
                g = monto_ap * 2; winning_bets.append('Par x2')
            elif tipo_ap == 'impar' and numero % 2 == 1:
                g = monto_ap * 2; winning_bets.append('Impar x2')
            elif tipo_ap == 'bajo' and 1 <= numero <= 18:
                g = monto_ap * 2; winning_bets.append('1-18 x2')
            elif tipo_ap == 'alto' and 19 <= numero <= 36:
                g = monto_ap * 2; winning_bets.append('19-36 x2')
            elif tipo_ap == 'doc1' and docena == 1:
                g = monto_ap * 3; winning_bets.append('1ª Doc x3')
            elif tipo_ap == 'doc2' and docena == 2:
                g = monto_ap * 3; winning_bets.append('2ª Doc x3')
            elif tipo_ap == 'doc3' and docena == 3:
                g = monto_ap * 3; winning_bets.append('3ª Doc x3')
            elif tipo_ap == 'col1' and columna == 1:
                g = monto_ap * 3; winning_bets.append('1ª Col x3')
            elif tipo_ap == 'col2' and columna == 2:
                g = monto_ap * 3; winning_bets.append('2ª Col x3')
            elif tipo_ap == 'col3' and columna == 3:
                g = monto_ap * 3; winning_bets.append('3ª Col x3')
            ganancia += g

        apuesta = total_apostado
        if winning_bets:
            resultado = f'Salió {numero} ({color}) - {", ".join(winning_bets)}'
        else:
            resultado = f'Salió {numero} ({color}) - Sin premio'

    elif game['tipo'] == 'dados':
        num_ap = int(extra.get('numero',1))
        dado   = random.randint(1,6)
        detalles = {'dado':dado,'apostado':num_ap}
        if dado==num_ap:
            ganancia = apuesta*5; resultado = f'Salio {dado}! Acertaste x5'
        else:
            resultado = f'Salio {dado}, apostaste {num_ap}'

    elif game['tipo'] == 'colores':
        color_ap = extra.get('color','rojo')
        opciones = ['rojo','dorado']
        color_res = random.choices(opciones, weights=[50,50])[0]
        detalles = {'color':color_res,'apostado':color_ap}
        if color_res == color_ap:
            ganancia = apuesta * 2
            resultado = f'Salio {color_res.upper()}! Ganaste x2'
        else:
            resultado = f'Salio {color_res.upper()}, apostaste {color_ap.upper()}'

    neto        = ganancia - apuesta
    nuevo_saldo = saldo_actual + neto
    puntos      = int(apuesta/10)

    cur.execute('UPDATE usuarios SET saldo=%s, puntos_vip=puntos_vip+%s WHERE id=%s',
                (nuevo_saldo, puntos, session['usuario']['id']))
    cur.execute('INSERT INTO apuestas (usuario_id,juego_id,monto_apostado,monto_ganado,resultado,detalles) VALUES (%s,%s,%s,%s,%s,%s)',
                (session['usuario']['id'],juego_id,apuesta,ganancia,resultado,json.dumps(detalles)))
    conn.commit()
    session['usuario']['saldo'] = nuevo_saldo
    session.modified = True
    cur.close(); conn.close()

    return jsonify({'ganancia':ganancia,'neto':neto,'nuevo_saldo':nuevo_saldo,'resultado':resultado,'detalles':detalles,'gano':ganancia>0,'terminado':True})

# ─── API SALDO ─────────────────────────────────────────────────────────────────

@app.route('/api/saldo')
@login_required
def api_saldo():
    sync_saldo_session()
    return jsonify({'saldo': session['usuario']['saldo']})

# ─── DEPÓSITOS / RETIROS ───────────────────────────────────────────────────────

@app.route('/depositar', methods=['GET','POST'])
@login_required
def depositar():
    RSC_RATE  = 1000
    RSC_BONUS = 0.10
    if request.method == 'POST':
        try: monto_rsc = float(request.form.get('monto',0))
        except: monto_rsc = 0
        if monto_rsc < 50:
            flash('El mínimo es 50 RSC','error')
            return render_template('depositar.html')
        hash_tx   = request.form.get('comprobante','').strip()
        monto_cop = monto_rsc * RSC_RATE
        bonus_cop = monto_cop * RSC_BONUS
        total_cop = monto_cop + bonus_cop
        nota      = f'RoyalCoin: {monto_rsc:.0f} RSC → COP${monto_cop:,.0f} + bono 10% COP${bonus_cop:,.0f} = COP${total_cop:,.0f}. Hash: {hash_tx}'
        conn = get_db(); cur = conn.cursor()
        cur.execute(
            'INSERT INTO depositos (usuario_id,monto,metodo,estado,nota) VALUES (%s,%s,%s,%s,%s)',
            (session['usuario']['id'], total_cop, 'royalcoin', 'pendiente', nota)
        )
        conn.commit(); cur.close(); conn.close()
        flash(f'🪙 {monto_rsc:.0f} RSC recibidos. Se acreditarán COP${total_cop:,.0f} (incluye bono 10%) tras aprobación del admin.','success')
        return redirect(url_for('historial'))
    return render_template('depositar.html')

@app.route('/retirar', methods=['GET','POST'])
@login_required
def retirar():
    sync_saldo_session()
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM usuarios WHERE id=%s', (session['usuario']['id'],))
    user = cur.fetchone()
    if request.method == 'POST':
        RSC_RATE = 1000.0
        RSC_MIN  = 10
        try: monto_cop = float(request.form.get('monto', 0))
        except: monto_cop = 0
        monto_rsc = monto_cop / RSC_RATE

        if monto_cop <= 0 or monto_rsc < RSC_MIN:
            flash(f'El mínimo de retiro es {RSC_MIN} RSC (COP${RSC_MIN * RSC_RATE:,.0f})','error')
            cur.close(); conn.close()
            return render_template('retirar.html', user=user)
        saldo_actual = float(user['saldo'])
        if saldo_actual < monto_cop:
            rsc_disponible = int(saldo_actual / RSC_RATE)
            flash(f'Saldo insuficiente. Tienes {rsc_disponible:,} RSC disponibles (COP${saldo_actual:,.0f})','error')
            cur.close(); conn.close()
            return render_template('retirar.html', user=user)

        cuenta = request.form.get('cuenta_destino', '').strip()
        nota   = f'Retiro en RoyalCoin: {monto_rsc:.0f} RSC = COP${monto_cop:,.0f}. Nota: {cuenta}'

        cur.execute('UPDATE usuarios SET saldo=saldo-%s WHERE id=%s', (monto_cop, session['usuario']['id']))
        cur.execute(
            'INSERT INTO retiros (usuario_id,monto,metodo,cuenta_destino,estado,nota) VALUES (%s,%s,%s,%s,%s,%s)',
            (session['usuario']['id'], monto_cop, 'royalcoin', cuenta, 'pendiente', nota)
        )
        conn.commit()
        session['usuario']['saldo'] = saldo_actual - monto_cop
        flash(f'🪙 Retiro de {monto_rsc:.0f} RSC (COP${monto_cop:,.0f}) solicitado. El admin lo procesará pronto.','success')
        cur.close(); conn.close()
        return redirect(url_for('historial'))
    cur.close(); conn.close()
    return render_template('retirar.html', user=user)

@app.route('/historial')
@login_required
def historial():
    sync_saldo_session()
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM depositos WHERE usuario_id=%s ORDER BY fecha DESC', (session['usuario']['id'],))
    deps = cur.fetchall()
    cur.execute('SELECT * FROM retiros WHERE usuario_id=%s ORDER BY fecha DESC', (session['usuario']['id'],))
    rets = cur.fetchall()
    cur.execute('''SELECT a.*,j.nombre as juego_nombre,j.icono FROM apuestas a
        JOIN juegos j ON a.juego_id=j.id WHERE a.usuario_id=%s ORDER BY a.fecha DESC LIMIT 200''',
        (session['usuario']['id'],))
    aps = cur.fetchall()
    cur.execute('''SELECT
        COALESCE(SUM(monto_apostado),0) as total_apostado,
        COALESCE(SUM(monto_ganado),0) as total_ganado,
        COALESCE(SUM(CASE WHEN monto_ganado > monto_apostado THEN 1 ELSE 0 END),0) as num_ganancias,
        COALESCE(SUM(CASE WHEN monto_ganado < monto_apostado THEN 1 ELSE 0 END),0) as num_perdidas,
        COALESCE(SUM(CASE WHEN monto_ganado = monto_apostado THEN 1 ELSE 0 END),0) as num_empates,
        COALESCE(SUM(CASE WHEN monto_ganado > monto_apostado THEN monto_ganado - monto_apostado ELSE 0 END),0) as suma_ganancias,
        COALESCE(SUM(CASE WHEN monto_ganado < monto_apostado THEN monto_apostado - monto_ganado ELSE 0 END),0) as suma_perdidas
        FROM apuestas WHERE usuario_id=%s''', (session['usuario']['id'],))
    pnl = cur.fetchone()
    cur.close(); conn.close()
    return render_template('historial.html', depositos=deps, retiros=rets, apuestas=aps, pnl=pnl)

@app.route('/perfil')
@login_required
def perfil():
    sync_saldo_session()
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM usuarios WHERE id=%s', (session['usuario']['id'],))
    user = cur.fetchone()
    cur.execute('''SELECT COUNT(*) as total_apuestas,
               COALESCE(SUM(monto_apostado),0) as total_apostado,
               COALESCE(SUM(monto_ganado),0) as total_ganado
        FROM apuestas WHERE usuario_id=%s''', (session['usuario']['id'],))
    stats = cur.fetchone()
    cur.close(); conn.close()
    return render_template('perfil.html', user=user, stats=stats)

@app.route('/perfil/cambiar-password', methods=['POST'])
@login_required
def cambiar_password():
    actual = request.form.get('password_actual','')
    nueva  = request.form.get('password_nueva','')
    conf   = request.form.get('confirmar_nueva','')
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM usuarios WHERE id=%s', (session['usuario']['id'],))
    user = cur.fetchone()
    if not check_password_hash(user['password'], actual):
        flash('Contraseña actual incorrecta','error'); cur.close(); conn.close()
        return redirect(url_for('perfil'))
    if len(nueva) < 6:
        flash('Mínimo 6 caracteres','error'); cur.close(); conn.close()
        return redirect(url_for('perfil'))
    if nueva != conf:
        flash('Las contraseñas no coinciden','error'); cur.close(); conn.close()
        return redirect(url_for('perfil'))
    cur.execute('UPDATE usuarios SET password=%s WHERE id=%s', (generate_password_hash(nueva), session['usuario']['id']))
    conn.commit(); cur.close(); conn.close()
    flash('¡Contraseña actualizada exitosamente!','success')
    return redirect(url_for('perfil'))

@app.route('/perfil/solicitar-cambio-email', methods=['POST'])
@login_required
def solicitar_cambio_email():
    nuevo_email = request.form.get('nuevo_email','').strip()
    import re
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', nuevo_email):
        flash('Email inválido','error')
        return redirect(url_for('perfil'))
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT id FROM usuarios WHERE email=%s', (nuevo_email,))
    if cur.fetchone():
        flash('Ese email ya está en uso','error'); cur.close(); conn.close()
        return redirect(url_for('perfil'))
    cur.execute('UPDATE usuarios SET email=%s WHERE id=%s', (nuevo_email, session['usuario']['id']))
    conn.commit()
    session['usuario']['email'] = nuevo_email
    session.modified = True
    cur.close(); conn.close()
    flash('¡Correo actualizado exitosamente!','success')
    return redirect(url_for('perfil'))

# ─── ADMIN: CAMBIO DE CONTRASEÑA CON CÓDIGO ────────────────────────────────────

@app.route('/admin/perfil/cambiar-password', methods=['POST'])
@login_required
@admin_required
def admin_cambiar_password():
    actual = request.form.get('password_actual','')
    nueva  = request.form.get('password_nueva','')
    conf   = request.form.get('confirmar_nueva','')
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM usuarios WHERE id=%s', (session['usuario']['id'],))
    user = cur.fetchone()
    if not check_password_hash(user['password'], actual):
        flash('Contraseña actual incorrecta','error'); cur.close(); conn.close()
        return redirect(url_for('admin_perfil'))
    if len(nueva) < 6:
        flash('Mínimo 6 caracteres','error'); cur.close(); conn.close()
        return redirect(url_for('admin_perfil'))
    if nueva != conf:
        flash('Las contraseñas no coinciden','error'); cur.close(); conn.close()
        return redirect(url_for('admin_perfil'))
    cur.execute('UPDATE usuarios SET password=%s WHERE id=%s', (generate_password_hash(nueva), session['usuario']['id']))
    conn.commit(); cur.close(); conn.close()
    flash('Contraseña actualizada exitosamente.','success')
    return redirect(url_for('admin_perfil'))

@app.route('/admin/perfil/solicitar-cambio-email', methods=['POST'])
@login_required
@admin_required
def admin_solicitar_cambio_email():
    nuevo_email = request.form.get('nuevo_email','').strip()
    import re
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', nuevo_email):
        flash('Email inválido','error')
        return redirect(url_for('admin_perfil'))
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT id FROM usuarios WHERE email=%s AND id!=%s', (nuevo_email, session['usuario']['id']))
    if cur.fetchone():
        flash('Ese email ya está en uso','error'); cur.close(); conn.close()
        return redirect(url_for('admin_perfil'))
    cur.execute('UPDATE usuarios SET email=%s WHERE id=%s', (nuevo_email, session['usuario']['id']))
    conn.commit()
    session['usuario']['email'] = nuevo_email
    session.modified = True
    cur.close(); conn.close()
    flash('Correo actualizado exitosamente.','success')
    return redirect(url_for('admin_perfil'))

@app.route('/perfil/actualizar', methods=['POST'])
@login_required
def actualizar_perfil():
    import re
    nombre = request.form.get('nombre','').strip()
    desc   = request.form.get('descripcion','').strip()
    if not nombre or re.search(r'\d',nombre) or len(nombre)<2:
        flash('Nombre inválido (sin números, mínimo 2 letras)','error')
        return redirect(url_for('perfil'))
    conn = get_db(); cur = conn.cursor()
    cur.execute('UPDATE usuarios SET nombre=%s, descripcion=%s WHERE id=%s', (nombre, desc, session['usuario']['id']))
    conn.commit(); cur.close(); conn.close()
    session['usuario']['nombre'] = nombre
    flash('¡Perfil actualizado!','success')
    return redirect(url_for('perfil'))

@app.route('/promociones')
def promociones():
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM promociones WHERE activa=1')
    promos = cur.fetchall()
    cur.close(); conn.close()
    return render_template('promociones.html', promociones=promos)

@app.route('/soporte', methods=['GET','POST'])
@login_required
def soporte():
    if request.method == 'POST':
        a = request.form.get('asunto',''); m = request.form.get('mensaje','')
        if a and m:
            conn = get_db(); cur = conn.cursor()
            cur.execute('INSERT INTO soporte (usuario_id,asunto,mensaje) VALUES (%s,%s,%s)',
                        (session['usuario']['id'],a,m))
            conn.commit(); cur.close(); conn.close()
            flash('Mensaje enviado.','success')
        else:
            flash('Completa todos los campos','error')
    return render_template('soporte.html')

# ─── ADMIN ─────────────────────────────────────────────────────────────────────

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM usuarios WHERE rol='jugador'"); tu = cur.fetchone()['c']
    cur.execute("SELECT COALESCE(SUM(monto),0) as s FROM depositos WHERE estado='aprobado'"); td = cur.fetchone()['s']
    cur.execute("SELECT COALESCE(SUM(monto),0) as s FROM retiros WHERE estado='aprobado'"); tr = cur.fetchone()['s']
    cur.execute("SELECT COUNT(*) as c, COALESCE(SUM(monto_apostado),0) as s FROM apuestas"); ta = cur.fetchone()
    cur.execute("SELECT COUNT(*) as c FROM depositos WHERE estado='pendiente'"); dp = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM retiros WHERE estado='pendiente'"); rp = cur.fetchone()['c']
    cur.execute("SELECT COALESCE(SUM(monto_apostado),0)-COALESCE(SUM(monto_ganado),0) as g FROM apuestas"); gc = float(cur.fetchone()['g'])
    cur.execute("SELECT * FROM usuarios WHERE rol='jugador' ORDER BY fecha_registro DESC LIMIT 10"); us = cur.fetchall()
    cur.execute("SELECT * FROM juegos ORDER BY id"); juegos = cur.fetchall()
    cur.execute("SELECT saldo_rsc FROM usuarios WHERE rol='admin' LIMIT 1"); admin_row = cur.fetchone()
    admin_saldo_rsc = float(admin_row['saldo_rsc']) if admin_row else 0.0
    cur.close(); conn.close()
    return render_template('admin/panel.html', total_usuarios=tu, total_depositos=td, total_retiros=tr,
        total_apuestas=ta, dep_pendientes=dp, ret_pendientes=rp, ganancia_casino=gc, usuarios=us, juegos=juegos,
        admin_saldo_rsc=admin_saldo_rsc)

@app.route('/admin/recargar-rsc', methods=['POST'])
@login_required
@admin_required
def admin_recargar_rsc():
    try: cantidad = float(request.form.get('cantidad', 0))
    except: cantidad = 0
    if cantidad <= 0:
        flash('Cantidad inválida','error')
        return redirect(url_for('admin_panel'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE usuarios SET saldo_rsc=saldo_rsc+%s WHERE rol='admin'", (cantidad,))
    conn.commit(); cur.close(); conn.close()
    flash(f'🪙 Se agregaron {cantidad:,.0f} RSC a tu saldo. Nuevo total disponible.','success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/depositos')
@login_required
@admin_required
def admin_depositos():
    conn = get_db(); cur = conn.cursor()
    cur.execute('''SELECT d.*,u.nombre as usuario_nombre,u.email as usuario_email
        FROM depositos d JOIN usuarios u ON d.usuario_id=u.id
        ORDER BY CASE WHEN d.estado='pendiente' THEN 0 ELSE 1 END, d.fecha DESC''')
    deps = cur.fetchall(); cur.close(); conn.close()
    return render_template('admin/depositos.html', depositos=deps)

@app.route('/admin/deposito/<int:dep_id>/<accion>', methods=['POST'])
@login_required
@admin_required
def admin_resolver_deposito(dep_id, accion):
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM depositos WHERE id=%s', (dep_id,))
    dep = cur.fetchone()
    if dep and dep['estado']=='pendiente':
        estado = 'aprobado' if accion=='aprobar' else 'rechazado'
        cur.execute('UPDATE depositos SET estado=%s,fecha_resolucion=%s,admin_id=%s WHERE id=%s',
                    (estado, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), session['usuario']['id'], dep_id))
        if accion=='aprobar':
            monto_dep = float(dep['monto'])
            cur.execute('UPDATE usuarios SET saldo=saldo+%s WHERE id=%s', (monto_dep, dep['usuario_id']))
        conn.commit()
        flash(f'Depósito #{dep_id} {estado}','success')
    cur.close(); conn.close()
    return redirect(url_for('admin_depositos'))

@app.route('/admin/retiros')
@login_required
@admin_required
def admin_retiros():
    conn = get_db(); cur = conn.cursor()
    cur.execute('''SELECT r.*,u.nombre as usuario_nombre,u.email as usuario_email
        FROM retiros r JOIN usuarios u ON r.usuario_id=u.id
        ORDER BY CASE WHEN r.estado='pendiente' THEN 0 ELSE 1 END, r.fecha DESC''')
    rets = cur.fetchall(); cur.close(); conn.close()
    return render_template('admin/retiros.html', retiros=rets)

@app.route('/admin/retiro/<int:ret_id>/<accion>', methods=['POST'])
@login_required
@admin_required
def admin_resolver_retiro(ret_id, accion):
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM retiros WHERE id=%s', (ret_id,))
    ret = cur.fetchone()
    if ret and ret['estado']=='pendiente':
        monto_ret = float(ret['monto'])
        RSC_RATE  = 1000.0
        rsc_costo = monto_ret / RSC_RATE

        if accion == 'aprobar':
            cur.execute("SELECT saldo_rsc FROM usuarios WHERE rol='admin' LIMIT 1")
            admin_row = cur.fetchone()
            admin_rsc = float(admin_row['saldo_rsc']) if admin_row else 0.0

            if admin_rsc < rsc_costo:
                flash(f'⚠️ No puedes aprobar este retiro. Necesitas {rsc_costo:,.0f} RSC pero solo tienes {admin_rsc:,.0f} RSC. Recarga tu saldo primero.', 'error')
                cur.close(); conn.close()
                return redirect(url_for('admin_retiros'))

            cur.execute('UPDATE retiros SET estado=%s,fecha_resolucion=%s,admin_id=%s WHERE id=%s',
                        ('aprobado', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), session['usuario']['id'], ret_id))
            cur.execute("UPDATE usuarios SET saldo_rsc=saldo_rsc-%s WHERE rol='admin'", (rsc_costo,))
            conn.commit()
            flash(f'✅ Retiro #{ret_id} aprobado — Se descontaron {rsc_costo:,.0f} RSC de tu saldo.', 'success')

        elif accion == 'rechazar':
            cur.execute('UPDATE retiros SET estado=%s,fecha_resolucion=%s,admin_id=%s WHERE id=%s',
                        ('rechazado', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), session['usuario']['id'], ret_id))
            cur.execute('UPDATE usuarios SET saldo=saldo+%s WHERE id=%s', (monto_ret, ret['usuario_id']))
            conn.commit()
            flash(f'Retiro #{ret_id} rechazado — Saldo devuelto al jugador.', 'success')
    cur.close(); conn.close()
    return redirect(url_for('admin_retiros'))

@app.route('/admin/usuario/<int:uid>/reset-password', methods=['POST'])
@login_required
@admin_required
def admin_reset_password(uid):
    nueva = request.form.get('nueva_password','').strip()
    if len(nueva) < 6:
        flash('Mínimo 6 caracteres','error')
        return redirect(url_for('admin_usuario_perfil', uid=uid))
    conn = get_db(); cur = conn.cursor()
    cur.execute('UPDATE usuarios SET password=%s WHERE id=%s', (generate_password_hash(nueva), uid))
    conn.commit(); cur.close(); conn.close()
    flash(f'Contraseña del usuario reseteada exitosamente.','success')
    return redirect(url_for('admin_usuario_perfil', uid=uid))

@app.route('/admin/usuarios')
@login_required
@admin_required
def admin_usuarios():
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM usuarios WHERE rol='jugador' ORDER BY fecha_registro DESC")
    us = cur.fetchall(); cur.close(); conn.close()
    return render_template('admin/usuarios.html', usuarios=us)

@app.route('/admin/usuario/<int:uid>/bloquear', methods=['POST'])
@login_required
@admin_required
def admin_bloquear(uid):
    r = request.form.get('razon','Sin razón')
    conn = get_db(); cur = conn.cursor()
    cur.execute('UPDATE usuarios SET bloqueado=1,razon_bloqueo=%s WHERE id=%s', (r, uid))
    conn.commit(); cur.close(); conn.close()
    flash('Usuario bloqueado','success')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/usuario/<int:uid>/desbloquear', methods=['POST'])
@login_required
@admin_required
def admin_desbloquear(uid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('UPDATE usuarios SET bloqueado=0,razon_bloqueo=NULL WHERE id=%s', (uid,))
    conn.commit(); cur.close(); conn.close()
    flash('Usuario desbloqueado','success')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/usuario/<int:uid>/perfil')
@login_required
@admin_required
def admin_usuario_perfil(uid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM usuarios WHERE id=%s", (uid,))
    u = cur.fetchone()
    if not u:
        cur.close(); conn.close()
        flash('Usuario no encontrado','error')
        return redirect(url_for('admin_usuarios'))
    cur.execute("""SELECT a.*, j.nombre as juego_nombre, j.tipo as juego_tipo
                   FROM apuestas a JOIN juegos j ON a.juego_id=j.id
                   WHERE a.usuario_id=%s ORDER BY a.fecha DESC LIMIT 50""", (uid,))
    apuestas = cur.fetchall()
    cur.execute("""SELECT * FROM depositos WHERE usuario_id=%s ORDER BY fecha DESC LIMIT 20""", (uid,))
    depositos = cur.fetchall()
    cur.execute("""SELECT * FROM retiros WHERE usuario_id=%s ORDER BY fecha DESC LIMIT 20""", (uid,))
    retiros = cur.fetchall()
    cur.execute("""SELECT COUNT(*) as total, COALESCE(SUM(monto_apostado),0) as apostado,
                   COALESCE(SUM(monto_ganado),0) as ganado FROM apuestas WHERE usuario_id=%s""", (uid,))
    stats = cur.fetchone()
    cur.close(); conn.close()
    return render_template('admin/usuario_perfil.html', u=u, apuestas=apuestas,
                           depositos=depositos, retiros=retiros, stats=stats)

@app.route('/admin/juegos')
@login_required
@admin_required
def admin_juegos():
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM juegos')
    js = cur.fetchall(); cur.close(); conn.close()
    return render_template('admin/juegos.html', juegos=js)

@app.route('/admin/juego/<int:jid>/toggle', methods=['POST'])
@login_required
@admin_required
def admin_toggle_juego(jid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT activo FROM juegos WHERE id=%s', (jid,))
    j = cur.fetchone()
    nuevo = 0 if j['activo'] else 1
    cur.execute('UPDATE juegos SET activo=%s WHERE id=%s', (nuevo, jid))
    conn.commit(); cur.close(); conn.close()
    flash(f'Juego {"activado" if nuevo else "desactivado"}','success')
    return redirect(url_for('admin_juegos'))

@app.route('/admin/reportes')
@login_required
@admin_required
def admin_reportes():
    conn = get_db(); cur = conn.cursor()
    cur.execute('''SELECT j.nombre,j.icono,COUNT(*) as total_apuestas,
               COALESCE(SUM(a.monto_apostado),0) as total_apostado,
               COALESCE(SUM(a.monto_ganado),0) as total_ganado,
               COALESCE(SUM(a.monto_apostado),0) - COALESCE(SUM(a.monto_ganado),0) as ganancia_casino
        FROM apuestas a JOIN juegos j ON a.juego_id=j.id GROUP BY j.id ORDER BY total_apostado DESC''')
    apj = cur.fetchall()
    apj_list = []
    for row in apj:
        apj_list.append({
            'nombre': row['nombre'],
            'icono': row['icono'],
            'total_apuestas': int(row['total_apuestas']),
            'total_apostado': float(row['total_apostado'] or 0),
            'total_ganado': float(row['total_ganado'] or 0),
            'ganancia_casino': float(row['ganancia_casino'] or 0),
        })
    cur.execute('''SELECT u.nombre,u.email,u.saldo,u.puntos_vip,
               COUNT(a.id) as total_apuestas,COALESCE(SUM(a.monto_apostado),0) as total_apostado
        FROM usuarios u LEFT JOIN apuestas a ON u.id=a.usuario_id WHERE u.rol='jugador'
        GROUP BY u.id ORDER BY total_apostado DESC LIMIT 10''')
    top = cur.fetchall()
    top_list = []
    for row in top:
        top_list.append({
            'nombre': row['nombre'],
            'email': row['email'],
            'saldo': float(row['saldo'] or 0),
            'puntos_vip': int(row['puntos_vip'] or 0),
            'total_apuestas': int(row['total_apuestas'] or 0),
            'total_apostado': float(row['total_apostado'] or 0),
        })
    cur.execute('''SELECT DATE(fecha) as dia, COUNT(*) as total, COALESCE(SUM(monto_apostado),0) as apostado,
               COALESCE(SUM(monto_ganado),0) as ganado
        FROM apuestas WHERE fecha >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        GROUP BY DATE(fecha) ORDER BY dia ASC''')
    dias_raw = cur.fetchall()
    dias_labels = [str(r['dia']) for r in dias_raw]
    dias_apostado = [float(r['apostado'] or 0) for r in dias_raw]
    dias_ganado = [float(r['ganado'] or 0) for r in dias_raw]
    dias_apuestas_cnt = [int(r['total']) for r in dias_raw]
    cur.execute('''SELECT DATE(fecha_registro) as dia, COUNT(*) as total
        FROM usuarios WHERE fecha_registro >= DATE_SUB(NOW(), INTERVAL 7 DAY) AND rol='jugador'
        GROUP BY DATE(fecha_registro) ORDER BY dia ASC''')
    reg_raw = cur.fetchall()
    reg_labels = [str(r['dia']) for r in reg_raw]
    reg_totales = [int(r['total']) for r in reg_raw]
    cur.execute("SELECT COALESCE(SUM(monto),0) as s FROM depositos WHERE estado='aprobado'")
    total_deps = float(cur.fetchone()['s'] or 0)
    cur.execute("SELECT COALESCE(SUM(monto),0) as s FROM retiros WHERE estado='aprobado'")
    total_rets = float(cur.fetchone()['s'] or 0)
    cur.execute("SELECT COALESCE(SUM(monto_apostado),0) as s FROM apuestas")
    total_apostado_global = float(cur.fetchone()['s'] or 0)
    cur.execute("SELECT COALESCE(SUM(monto_ganado),0) as s FROM apuestas")
    total_ganado_global = float(cur.fetchone()['s'] or 0)
    cur.close(); conn.close()
    import json as _json
    return render_template('admin/reportes.html',
        apuestas_por_juego=apj_list, top_jugadores=top_list,
        dias_labels=_json.dumps(dias_labels), dias_apostado=_json.dumps(dias_apostado),
        dias_ganado=_json.dumps(dias_ganado), dias_apuestas=_json.dumps(dias_apuestas_cnt),
        reg_labels=_json.dumps(reg_labels), reg_totales=_json.dumps(reg_totales),
        total_deps=total_deps, total_rets=total_rets,
        total_apostado_global=total_apostado_global, total_ganado_global=total_ganado_global)

@app.route('/admin/perfil')
@login_required
@admin_required
def admin_perfil():
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM usuarios WHERE id=%s", (session['usuario']['id'],))
    admin_user = cur.fetchone()
    cur.execute("SELECT COUNT(*) as c FROM usuarios WHERE rol='jugador'"); tu = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM depositos WHERE estado='pendiente'"); dp = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM retiros WHERE estado='pendiente'"); rp = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM apuestas"); ta = cur.fetchone()['c']
    cur.execute("SELECT COALESCE(SUM(monto_apostado),0)-COALESCE(SUM(monto_ganado),0) as g FROM apuestas")
    gc = float(cur.fetchone()['g'] or 0)
    cur.close(); conn.close()
    return render_template('admin/perfil.html', admin_user=admin_user,
        total_usuarios=tu, dep_pendientes=dp, ret_pendientes=rp, total_apuestas=ta, ganancia_casino=gc)

@app.errorhandler(404)
def not_found(e): return render_template('404.html'), 404
@app.errorhandler(500)
def server_error(e): return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)