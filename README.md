# ♠ Royal Spin — Casino Virtual v3

## Inicio rápido
```bash
pip install -r requirements.txt
python app.py
# → http://localhost:5000
```

## Credenciales
| Rol | Email | Contraseña |
|-----|-------|-----------|
| Admin | admin@royalspin.com | admin123 |
| Jugador | Bairon Lozano (existente) | (la tuya) |

## Problemas resueltos en v3
- ✅ BD: INSERT OR IGNORE evita duplicar los 4 juegos al reiniciar
- ✅ BD: columnas reset_token y reset_expiry añadidas automáticamente
- ✅ Saldo actualizado en navbar en tiempo real tras cada apuesta
- ✅ Solo 4 juegos (duplicados eliminados de la BD)
- ✅ Blackjack interactivo: Pedir carta / Plantarse / Doblar
- ✅ Crupier juega hasta 17 con reglas reales
- ✅ Blackjack natural paga ×2.5
- ✅ Al login → redirige a /juegos directamente
- ✅ Reset de contraseña por email (Gmail + clave de app)
- ✅ Paleta negro/dorado/rojo en todo el proyecto

## Configurar email (reset de contraseña)
En `config.py` ya están tus credenciales:
```python
MAIL_CONFIG = {
    'remitente': 'baironlozano334@gmail.com',
    'password':  'kujtklomjsawbxox',
    'nombre':    'Royal Spin Casino'
}
```

## Juegos
| Juego | Tipo | RTP | Mín | Máx |
|-------|------|-----|-----|-----|
| 🎰 Tragamonedas | slots | 96.5% | $1 | $500 |
| 🎡 Ruleta | rueda | 97.3% | $1 | $1000 |
| 🃏 Blackjack | cartas | 99.4% | $5 | $1000 |
| 🎲 Dados | dados | 97.8% | $1 | $500 |
