# Вычисление варианта
# a = 568 % 45
# print(a)

from flask import Flask, render_template, request, redirect, url_for, session, current_app, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import sqlite3
from os import path

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'секретно-секретный секрет')
app.config['DB_TYPE'] = os.getenv('DB_TYPE', 'postgres')


def db_connect():
    if current_app.config['DB_TYPE'] == 'postgres':
        conn = psycopg2.connect(
            host='127.0.0.1',
            database='nikita_rgz',
            user='nikita_rgz',
            password='123'
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
    else:
        dir_path = path.dirname(path.realpath(__file__))
        db_path = path.join(dir_path, "database.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

    return conn, cur


def db_close(conn, cur):
    conn.commit()
    cur.close()
    conn.close()


# Главная страница
@app.route('/')
def main():
    return render_template('main.html')


# Страница входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'cadrovik' and password == 'cadrovik_password':
            session['logged_in'] = True
            return redirect(url_for('main'))
        else:
            return render_template('login.html', error='Неверный логин или пароль')
    return render_template('login.html')


# Выход из аккаунта кадровика
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('main'))


# Список сотрудников
@app.route('/employees')
def employees():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'name')  # По умолчанию сортировка по имени
    order = request.args.get('order', 'asc')  # По умолчанию сортировка по возрастанию
    gender = request.args.get('gender', '')
    probation = request.args.get('probation', '')

    conn, cur = db_connect()

    # Поиск и сортировка
    if current_app.config['DB_TYPE'] == 'postgres':
        query = """
            SELECT * FROM employees
            WHERE (name ILIKE %s OR position ILIKE %s OR phone ILIKE %s OR email ILIKE %s)
        """
        params = [f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%']
    else:
        query = """
            SELECT * FROM employees
            WHERE (LOWER(name) LIKE ? OR LOWER(position) LIKE ? OR LOWER(phone) LIKE ? OR LOWER(email) LIKE ?)
        """
        params = [f'%{search.lower()}%', f'%{search.lower()}%', f'%{search.lower()}%', f'%{search.lower()}%']

    # Условие для поиска по полу
    if gender:
        if current_app.config['DB_TYPE'] == 'postgres':
            query += " AND gender = %s"
        else:
            query += " AND gender = ?"
        params.append(gender)

    # Условие для поиска по испытательному сроку
    if probation == 'true':
        query += " AND probation = TRUE"
    elif probation == 'false':
        query += " AND probation = FALSE"

    # Сортировка и пагинация
    if current_app.config['DB_TYPE'] == 'postgres':
        query += f"""
            ORDER BY {sort_by} {order}
            LIMIT 20 OFFSET %s
        """
        params.append((page - 1) * 20)
    else:
        query += f"""
            ORDER BY {sort_by} {order}
            LIMIT 20 OFFSET ?
        """
        params.append((page - 1) * 20)

    cur.execute(query, params)
    employees = cur.fetchall()

    # Получение общего количества сотрудников для пагинации
    if current_app.config['DB_TYPE'] == 'postgres':
        count_query = """
            SELECT COUNT(*) AS count FROM employees
            WHERE (name ILIKE %s OR position ILIKE %s OR phone ILIKE %s OR email ILIKE %s)
        """
        count_params = [f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%']
    else:
        count_query = """
            SELECT COUNT(*) AS count FROM employees
            WHERE (LOWER(name) LIKE ? OR LOWER(position) LIKE ? OR LOWER(phone) LIKE ? OR LOWER(email) LIKE ?)
        """
        count_params = [f'%{search.lower()}%', f'%{search.lower()}%', f'%{search.lower()}%', f'%{search.lower()}%']

    if gender:
        if current_app.config['DB_TYPE'] == 'postgres':
            count_query += " AND gender = %s"
        else:
            count_query += " AND gender = ?"
        count_params.append(gender)

    if probation == 'true':
        count_query += " AND probation = TRUE"
    elif probation == 'false':
        count_query += " AND probation = FALSE"

    cur.execute(count_query, count_params)
    count_result = cur.fetchone()

    # Проверяем, что результат не None
    if count_result is None:
        total_count = 0
    else:
        total_count = count_result['count']

    db_close(conn, cur)

    return render_template('employees.html', employees=employees, search=search, sort_by=sort_by, order=order,
                           logged_in=session.get('logged_in', False), page=page, total_pages=(total_count // 20) + 1,
                           gender=gender, probation=probation)


# Добавление сотрудника
@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        position = request.form['position']
        gender = request.form['gender']
        phone = request.form['phone']
        email = request.form['email']
        probation = request.form.get('probation') == 'on'
        hire_date = request.form['hire_date']

        conn, cur = db_connect()
        if current_app.config['DB_TYPE'] == 'postgres':
            cur.execute("""
                INSERT INTO employees (name, position, gender, phone, email, probation, hire_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (name, position, gender, phone, email, probation, hire_date))
        else:
            cur.execute("""
                INSERT INTO employees (name, position, gender, phone, email, probation, hire_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, position, gender, phone, email, probation, hire_date))
        db_close(conn, cur)

        return redirect(url_for('employees'))

    return render_template('edit_employee.html', action='add', logged_in=session.get('logged_in', False))


# Редактирование сотрудника
@app.route('/edit_employee/<int:id>', methods=['GET', 'POST'])
def edit_employee(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn, cur = db_connect()
    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("SELECT * FROM employees WHERE id = %s", (id,))
    else:
        cur.execute("SELECT * FROM employees WHERE id = ?", (id,))
    employee = cur.fetchone()

    if request.method == 'POST':
        name = request.form['name']
        position = request.form['position']
        gender = request.form['gender']
        phone = request.form['phone']
        email = request.form['email']
        probation = request.form.get('probation') == 'on'
        hire_date = request.form['hire_date']

        if current_app.config['DB_TYPE'] == 'postgres':
            cur.execute("""
                UPDATE employees
                SET name = %s, position = %s, gender = %s, phone = %s, email = %s, probation = %s, hire_date = %s
                WHERE id = %s
            """, (name, position, gender, phone, email, probation, hire_date, id))
        else:
            cur.execute("""
                UPDATE employees
                SET name = ?, position = ?, gender = ?, phone = ?, email = ?, probation = ?, hire_date = ?
                WHERE id = ?
            """, (name, position, gender, phone, email, probation, hire_date, id))
        db_close(conn, cur)

        return redirect(url_for('employees'))

    return render_template('edit_employee.html', action='edit', employee=employee, logged_in=session.get('logged_in', False))


# Удаление сотрудника
@app.route('/delete_employee/<int:id>')
def delete_employee(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn, cur = db_connect()
    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("DELETE FROM employees WHERE id = %s", (id,))
    else:
        cur.execute("DELETE FROM employees WHERE id =?", (id,))
    db_close(conn, cur)

    return redirect(url_for('employees'))


# JSON-RPC API
@app.route('/json-rpc-api/', methods=['POST'])
def api():
    data = request.json
    id = data['id']

    conn, cur = db_connect()

    if data['method'] == 'get_employees':
        page = data['params'].get('page', 1)
        search = data['params'].get('search', '')
        sort_by = data['params'].get('sort_by', 'name')
        order = data['params'].get('order', 'asc')
        gender = data['params'].get('gender', '')
        probation = data['params'].get('probation', '')

        # Поиск и сортировка
        if current_app.config['DB_TYPE'] == 'postgres':
            query = """
                SELECT * FROM employees
                WHERE (name ILIKE %s OR position ILIKE %s OR phone ILIKE %s OR email ILIKE %s)
            """
            params = [f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%']
        else:
            query = """
                SELECT * FROM employees
                WHERE (LOWER(name) LIKE ? OR LOWER(position) LIKE ? OR LOWER(phone) LIKE ? OR LOWER(email) LIKE ?)
            """
            params = [f'%{search.lower()}%', f'%{search.lower()}%', f'%{search.lower()}%', f'%{search.lower()}%']

        # Условие для поиска по полу
        if gender:
            if current_app.config['DB_TYPE'] == 'postgres':
                query += " AND gender = %s"
            else:
                query += " AND gender = ?"
            params.append(gender)

        # Условие для поиска по испытательному сроку
        if probation == 'true':
            query += " AND probation = TRUE"
        elif probation == 'false':
            query += " AND probation = FALSE"

        # Сортировка и пагинация
        if current_app.config['DB_TYPE'] == 'postgres':
            query += f"""
                ORDER BY {sort_by} {order}
                LIMIT 20 OFFSET %s
            """
            params.append((page - 1) * 20)
        else:
            query += f"""
                ORDER BY {sort_by} {order}
                LIMIT 20 OFFSET ?
            """
            params.append((page - 1) * 20)

        cur.execute(query, params)
        employees = cur.fetchall()

        db_close(conn, cur)
        return {
            'jsonrpc': '2.0',
            'result': employees,
            'id': id
        }

    if data['method'] == 'add_employee':
        if not session.get('logged_in'):
            db_close(conn, cur)
            return {
                'jsonrpc': '2.0',
                'error': {
                    'code': 1,
                    'message': 'Unauthorized'
                },
                'id': id
            }

        name = data['params'].get('name')
        position = data['params'].get('position')
        gender = data['params'].get('gender')
        phone = data['params'].get('phone')
        email = data['params'].get('email')
        probation = data['params'].get('probation', False)
        hire_date = data['params'].get('hire_date')

        if current_app.config['DB_TYPE'] == 'postgres':
            cur.execute("""
                INSERT INTO employees (name, position, gender, phone, email, probation, hire_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (name, position, gender, phone, email, probation, hire_date))
        else:
            cur.execute("""
                INSERT INTO employees (name, position, gender, phone, email, probation, hire_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, position, gender, phone, email, probation, hire_date))

        db_close(conn, cur)
        return {
            'jsonrpc': '2.0',
            'result': 'success',
            'id': id
        }

    if data['method'] == 'edit_employee':
        if not session.get('logged_in'):
            db_close(conn, cur)
            return {
                'jsonrpc': '2.0',
                'error': {
                    'code': 1,
                    'message': 'Unauthorized'
                },
                'id': id
            }

        id = data['params'].get('id')
        name = data['params'].get('name')
        position = data['params'].get('position')
        gender = data['params'].get('gender')
        phone = data['params'].get('phone')
        email = data['params'].get('email')
        probation = data['params'].get('probation', False)
        hire_date = data['params'].get('hire_date')

        if current_app.config['DB_TYPE'] == 'postgres':
            cur.execute("""
                UPDATE employees
                SET name = %s, position = %s, gender = %s, phone = %s, email = %s, probation = %s, hire_date = %s
                WHERE id = %s
            """, (name, position, gender, phone, email, probation, hire_date, id))
        else:
            cur.execute("""
                UPDATE employees
                SET name = ?, position = ?, gender = ?, phone = ?, email = ?, probation = ?, hire_date = ?
                WHERE id = ?
            """, (name, position, gender, phone, email, probation, hire_date, id))

        db_close(conn, cur)
        return {
            'jsonrpc': '2.0',
            'result': 'success',
            'id': id
        }

    if data['method'] == 'delete_employee':
        if not session.get('logged_in'):
            db_close(conn, cur)
            return {
                'jsonrpc': '2.0',
                'error': {
                    'code': 1,
                    'message': 'Unauthorized'
                },
                'id': id
            }

        id = data['params'].get('id')

        if current_app.config['DB_TYPE'] == 'postgres':
            cur.execute("DELETE FROM employees WHERE id = %s", (id,))
        else:
            cur.execute("DELETE FROM employees WHERE id = ?", (id,))

        db_close(conn, cur)
        return {
            'jsonrpc': '2.0',
            'result': 'success',
            'id': id
        }

    db_close(conn, cur)
    return {
        'jsonrpc': '2.0',
        'error': {
            'code': -32601,
            'message': 'Method not found'
        },
        'id': id
    }