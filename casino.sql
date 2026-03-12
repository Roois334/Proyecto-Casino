-- ═══════════════════════════════════════════════════════════════════
--  ROYAL SPIN CASINO — Base de Datos MySQL Completa
--  Versión: RoyalCoin Edition
--  
--  INSTRUCCIONES:
--  1. Abre MySQL Workbench, phpMyAdmin o tu terminal MySQL
--  2. Ejecuta este archivo completo
--  3. La BD 'casino' quedará lista con todos los datos iniciales
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. CREAR Y SELECCIONAR BASE DE DATOS ──────────────────────────
CREATE DATABASE IF NOT EXISTS casino
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE casino;

-- ── 2. ELIMINAR TABLAS EN ORDEN CORRECTO (por FK) ─────────────────
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS soporte;
DROP TABLE IF EXISTS apuestas;
DROP TABLE IF EXISTS retiros;
DROP TABLE IF EXISTS depositos;
DROP TABLE IF EXISTS promociones;
DROP TABLE IF EXISTS juegos;
DROP TABLE IF EXISTS usuarios;
SET FOREIGN_KEY_CHECKS = 1;

-- ═══════════════════════════════════════════════════════════════════
--  TABLA: usuarios
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE usuarios (
    id               INT            PRIMARY KEY AUTO_INCREMENT,
    nombre           VARCHAR(100)   NOT NULL,
    cedula           VARCHAR(20),
    email            VARCHAR(120)   UNIQUE NOT NULL,
    password         VARCHAR(255)   NOT NULL,
    fecha_nacimiento DATE           NOT NULL,
    rol              VARCHAR(20)    DEFAULT 'jugador',
    saldo            DECIMAL(10,2)  DEFAULT 0.00,
    saldo_rsc        DECIMAL(14,4)  DEFAULT 0.0000,
    puntos_vip       INT            DEFAULT 0,
    descripcion      TEXT,
    reset_token      VARCHAR(100),
    reset_expiry     DATETIME,
    fecha_registro   DATETIME       DEFAULT CURRENT_TIMESTAMP,
    activo           TINYINT(1)     DEFAULT 1,
    bloqueado        TINYINT(1)     DEFAULT 0,
    razon_bloqueo    TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═══════════════════════════════════════════════════════════════════
--  TABLA: juegos
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE juegos (
    id                   INT           PRIMARY KEY AUTO_INCREMENT,
    nombre               VARCHAR(100)  NOT NULL,
    descripcion          TEXT,
    icono                VARCHAR(10),
    tipo                 VARCHAR(50),
    rtp                  DECIMAL(4,2)  DEFAULT 96.50,
    apuesta_minima       DECIMAL(10,2) DEFAULT 100.00,
    apuesta_maxima       DECIMAL(14,2) DEFAULT 99999999.00,
    multiplicador_maximo INT           DEFAULT 100,
    activo               TINYINT(1)    DEFAULT 1,
    fecha_creacion       DATETIME      DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═══════════════════════════════════════════════════════════════════
--  TABLA: depositos
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE depositos (
    id               INT            PRIMARY KEY AUTO_INCREMENT,
    usuario_id       INT            NOT NULL,
    monto            DECIMAL(10,2)  NOT NULL,
    metodo           VARCHAR(50)    DEFAULT 'royalcoin',
    estado           VARCHAR(20)    DEFAULT 'pendiente',
    nota             TEXT,
    fecha            DATETIME       DEFAULT CURRENT_TIMESTAMP,
    fecha_resolucion DATETIME,
    admin_id         INT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (admin_id)   REFERENCES usuarios(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═══════════════════════════════════════════════════════════════════
--  TABLA: retiros
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE retiros (
    id               INT            PRIMARY KEY AUTO_INCREMENT,
    usuario_id       INT            NOT NULL,
    monto            DECIMAL(10,2)  NOT NULL,
    metodo           VARCHAR(50)    DEFAULT 'royalcoin',
    cuenta_destino   VARCHAR(100),
    estado           VARCHAR(20)    DEFAULT 'pendiente',
    nota             TEXT,
    fecha            DATETIME       DEFAULT CURRENT_TIMESTAMP,
    fecha_resolucion DATETIME,
    admin_id         INT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (admin_id)   REFERENCES usuarios(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═══════════════════════════════════════════════════════════════════
--  TABLA: apuestas
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE apuestas (
    id             INT            PRIMARY KEY AUTO_INCREMENT,
    usuario_id     INT            NOT NULL,
    juego_id       INT            NOT NULL,
    monto_apostado DECIMAL(10,2)  NOT NULL,
    monto_ganado   DECIMAL(10,2)  DEFAULT 0.00,
    resultado      VARCHAR(200),
    detalles       TEXT,
    fecha          DATETIME       DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (juego_id)   REFERENCES juegos(id)   ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═══════════════════════════════════════════════════════════════════
--  TABLA: promociones
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE promociones (
    id             INT            PRIMARY KEY AUTO_INCREMENT,
    nombre         VARCHAR(100)   NOT NULL,
    descripcion    TEXT,
    tipo           VARCHAR(50),
    porcentaje     INT,
    monto_maximo   DECIMAL(10,2),
    activa         TINYINT(1)     DEFAULT 1,
    fecha_creacion DATETIME       DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═══════════════════════════════════════════════════════════════════
--  TABLA: soporte
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE soporte (
    id              INT          PRIMARY KEY AUTO_INCREMENT,
    usuario_id      INT          NOT NULL,
    asunto          VARCHAR(255),
    mensaje         TEXT,
    estado          VARCHAR(20)  DEFAULT 'abierto',
    respuesta       TEXT,
    fecha_creacion  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    fecha_respuesta DATETIME,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═══════════════════════════════════════════════════════════════════
--  DATOS INICIALES — JUEGOS
-- ═══════════════════════════════════════════════════════════════════
INSERT INTO juegos (id, nombre, descripcion, icono, tipo, rtp, apuesta_minima, apuesta_maxima, multiplicador_maximo, activo)
VALUES
    (1, 'Tragamonedas', 'Gira los rodillos y consigue 3 símbolos iguales.',  '🎰', 'slots',   96.50, 100.00, 99999999.00, 100, 1),
    (2, 'Ruleta',       'Apuesta a número exacto (x36), color, par/impar o alto/bajo.', '🎡', 'rueda',  97.30, 100.00, 99999999.00,  36, 1),
    (3, 'Blackjack',    'Llega a 21 sin pasarte. Supera al crupier.',         '🃏', 'cartas', 99.40, 100.00, 99999999.00,   2, 1),
    (4, 'Dados',        'Elige un número del 1 al 6. Si aciertas, ganas x5.','🎲', 'dados',  97.80, 100.00, 99999999.00,   5, 1);

-- ═══════════════════════════════════════════════════════════════════
--  DATOS INICIALES — PROMOCIONES
-- ═══════════════════════════════════════════════════════════════════
INSERT INTO promociones (nombre, descripcion, tipo, porcentaje, monto_maximo, activa)
VALUES
    ('Bono Bienvenida',  'COP$10.000 gratis al registrarte.',              'bienvenida', 100, 500.00,  1),
    ('Bono Depósito RSC','10% extra en cada depósito con RoyalCoin.',      'deposito',    10, NULL,    1),
    ('Cashback Diario',  'Recupera hasta el 10% de tus pérdidas diarias.', 'cashback',    10, 200.00,  1),
    ('Programa VIP',     '1 punto VIP por cada COP$10 apostado.',          'vip',          5, 1000.00, 1);

-- ═══════════════════════════════════════════════════════════════════
--  DATOS INICIALES — ADMINISTRADOR
--  Contraseña: admin123  (hash bcrypt generado por Flask)
--  ⚠ Si cambias la contraseña en config.py, borra este INSERT
--    y deja que app.py la genere automáticamente al iniciar.
-- ═══════════════════════════════════════════════════════════════════
INSERT INTO usuarios
    (nombre, email, password, fecha_nacimiento, rol, saldo, saldo_rsc, puntos_vip, activo)
VALUES (
    'Administrador',
    'admin@royalspin.com',
    'pbkdf2:sha256:600000$placeholder$hashgeneradoporlaaplicacion',
    '1990-01-01',
    'admin',
    0.00,
    1000000.0000,   -- 1.000.000 RSC iniciales del admin
    0,
    1
);

-- ═══════════════════════════════════════════════════════════════════
--  ÍNDICES PARA MEJOR RENDIMIENTO
-- ═══════════════════════════════════════════════════════════════════
CREATE INDEX idx_depositos_usuario  ON depositos (usuario_id);
CREATE INDEX idx_depositos_estado   ON depositos (estado);
CREATE INDEX idx_retiros_usuario    ON retiros   (usuario_id);
CREATE INDEX idx_retiros_estado     ON retiros   (estado);
CREATE INDEX idx_apuestas_usuario   ON apuestas  (usuario_id);
CREATE INDEX idx_apuestas_juego     ON apuestas  (juego_id);
CREATE INDEX idx_apuestas_fecha     ON apuestas  (fecha);
CREATE INDEX idx_soporte_usuario    ON soporte   (usuario_id);
CREATE INDEX idx_usuarios_email     ON usuarios  (email);
CREATE INDEX idx_usuarios_rol       ON usuarios  (rol);

-- ═══════════════════════════════════════════════════════════════════
--  VERIFICACIÓN FINAL
-- ═══════════════════════════════════════════════════════════════════
SELECT '✅ Base de datos Royal Spin creada exitosamente' AS estado;
SELECT CONCAT('   Tablas creadas: ', COUNT(*)) AS tablas
FROM information_schema.tables
WHERE table_schema = 'casino';

SELECT '' AS '';
SELECT '📋 JUEGOS REGISTRADOS:' AS '';
SELECT id, nombre, rtp, apuesta_minima, activo FROM juegos;

SELECT '' AS '';
SELECT '👤 ADMIN CREADO:' AS '';
SELECT id, nombre, email, rol, saldo_rsc FROM usuarios WHERE rol = 'admin';

SELECT '' AS '';
SELECT '⚠️  IMPORTANTE: Inicia la app (python app.py) para que el admin' AS nota;
SELECT '   quede con la contraseña correcta encriptada por Flask.' AS nota2;
