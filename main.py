import os
import sqlite3
import datetime
import uuid
from flask import Flask, request, jsonify, render_template_string

DB_NAME = "licenses.db"
app = Flask(__name__)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT UNIQUE NOT NULL,
            client_name TEXT,
            expires_at DATETIME NOT NULL,
            is_blocked INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Панель Управления Подписками и Лицензиями</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #121214; color: #e1e1e6; font-family: 'Segoe UI', Roboto, sans-serif; }
        .card { background-color: #202024; border: 1px solid #323238; border-radius: 10px; color: #fff; }
        .table { color: #c4c4cc; }
        .table-dark { background-color: #121214; }
        .form-control, .form-select { background-color: #121214; border: 1px solid #323238; color: #fff; }
        .form-control:focus, .form-select:focus { background-color: #18181b; color: #fff; border-color: #8257e5; box-shadow: 0 0 0 0.25rem rgba(130, 87, 229, 0.25); }
        .btn-purple { background-color: #8257e5; color: #fff; font-weight: 600; }
        .btn-purple:hover { background-color: #996dff; color: #fff; }
        .badge-active { background-color: #04d361; color: #000; font-weight: 600; }
        .badge-expired { background-color: #f75a68; color: #fff; font-weight: 600; }
        .badge-blocked { background-color: #ffcd07; color: #000; font-weight: 600; }
    </style>
</head>
<body class="py-4">
    <div class="container">
        <div class="d-flex justify-content-between align-items-center mb-4 pb-3 border-bottom border-secondary">
            <div>
                <h1 class="h3 mb-0 text-white">🔐 Admin Licensing Panel</h1>
                <small class="text-muted">Панель управления доступом и ключами клиентов</small>
            </div>
            <div>
                <span class="badge bg-success p-2">Сервер Активен (Online)</span>
            </div>
        </div>

        <div class="row g-4">
            <!-- Form Card -->
            <div class="col-md-4">
                <div class="card p-3 shadow">
                    <h5 class="card-title mb-3">Сгенерировать ключ</h5>
                    <form action="/admin/create" method="POST">
                        <div class="mb-3">
                            <label class="form-label">Клиент / Примечание</label>
                            <input type="text" class="form-control" name="client_name" placeholder="Например: Иван (Клиент #1)" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Длительность</label>
                            <input type="number" class="form-control" name="duration" value="30" min="1" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Единица времени</label>
                            <select class="form-select" name="unit">
                                <option value="minutes">Минуты</option>
                                <option value="hours">Часы</option>
                                <option value="days" selected>Дни</option>
                            </select>
                        </div>
                        <button type="submit" class="btn btn-purple w-100">Создать ключ доступа</button>
                    </form>
                </div>
            </div>

            <!-- Table Card -->
            <div class="col-md-8">
                <div class="card p-3 shadow">
                    <h5 class="card-title mb-3">Активные подписки</h5>
                    <div class="table-responsive">
                        <table class="table table-dark table-hover align-middle">
                            <thead>
                                <tr>
                                    <th>Ключ</th>
                                    <th>Клиент</th>
                                    <th>Истекает</th>
                                    <th>Статус</th>
                                    <th>Действие</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for lic in licenses %}
                                <tr>
                                    <td><code class="text-info">{{ lic.key }}</code></td>
                                    <td>{{ lic.client }}</td>
                                    <td><small>{{ lic.expires_at }}</small></td>
                                    <td>
                                        {% if lic.is_blocked %}
                                            <span class="badge badge-blocked">Заблокирован</span>
                                        {% elif lic.is_expired %}
                                            <span class="badge badge-expired">Истёк</span>
                                        {% else %}
                                            <span class="badge badge-active">Активен</span>
                                        {% endif %}
                                    </td>
                                    <td>
                                        <form action="/admin/toggle_block" method="POST" class="d-inline">
                                            <input type="hidden" name="key" value="{{ lic.key }}">
                                            <button type="submit" class="btn btn-sm btn-outline-warning">
                                                {% if lic.is_blocked %}Разблокировать{% else %}Заблокировать{% endif %}
                                            </button>
                                        </form>
                                    </td>
                                </tr>
                                {% else %}
                                <tr>
                                    <td colspan="5" class="text-center text-muted py-4">Нет созданных ключей. Создайте первый ключ слева!</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""


@app.route('/', methods=['GET'])
def index():
    return '<h2 style="font-family:sans-serif; text-align:center; margin-top:50px;">Сервер Лицензирования Работает! <br><br><a href="/admin">Перейти в Панель Администратора</a></h2>'

@app.route('/admin', methods=['GET'])
def admin_panel():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT license_key, client_name, expires_at, is_blocked FROM licenses ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    now = datetime.datetime.utcnow()
    licenses = []
    for r in rows:
        exp_date = datetime.datetime.fromisoformat(r[2])
        licenses.append({
            "key": r[0],
            "client": r[1],
            "expires_at": r[2].replace("T", " ")[:19],
            "is_blocked": bool(r[3]),
            "is_expired": now > exp_date
        })

    return render_template_string(HTML_TEMPLATE, licenses=licenses)

@app.route('/admin/create', methods=['POST'])
def create_license():
    client_name = request.form.get('client_name')
    duration = int(request.form.get('duration', 30))
    unit = request.form.get('unit', 'days')

    now = datetime.datetime.utcnow()
    if unit == 'minutes':
        delta = datetime.timedelta(minutes=duration)
    elif unit == 'hours':
        delta = datetime.timedelta(hours=duration)
    else:
        delta = datetime.timedelta(days=duration)

    expires_at = (now + delta).isoformat()
    license_key = "KEY-" + uuid.uuid4().hex[:12].upper()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO licenses (license_key, client_name, expires_at) VALUES (?, ?, ?)",
                   (license_key, client_name, expires_at))
    conn.commit()
    conn.close()

    return '<script>window.location.href="/admin";</script>'

@app.route('/admin/toggle_block', methods=['POST'])
def toggle_block():
    key = request.form.get('key')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE licenses SET is_blocked = NOT is_blocked WHERE license_key = ?", (key,))
    conn.commit()
    conn.close()
    return '<script>window.location.href="/admin";</script>'

@app.route('/api/check_license', methods=['POST'])
def check_license():
    data = request.json or {}
    key = data.get('license_key')

    if not key:
    return jsonify({"valid": False, "reason": "Ключ не предоставлен"}), 400

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT expires_at, is_blocked FROM licenses WHERE license_key = ?", (key,))
    row = cursor.fetchone()
    conn.close()

    if not row:
    return jsonify({"valid": False, "reason": "Неверный ключ подписки"}), 404

    expires_at = datetime.datetime.fromisoformat(row[0])
    is_blocked = bool(row[1])
    now = datetime.datetime.utcnow()

    if is_blocked:
    return jsonify({"valid": False, "reason": "Доступ заблокирован администратором"}), 403

    if now > expires_at:
    return jsonify({"valid": False, "reason": "Срок действия подписки истёк"}), 403

    time_left = int((expires_at - now).total_seconds())
    return jsonify({
    "valid": True,
    "seconds_left": time_left,
    "expires_at": row[0]
    })


