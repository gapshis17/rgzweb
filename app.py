from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import func,text

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///initiatives.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Импортируем модели
from models import User, Initiative, Vote

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    initiatives = Initiative.query.order_by(Initiative.date_created.desc()).paginate(page=page, per_page=20)
    return render_template('index.html', initiatives=initiatives)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            flash('Username and password are required')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Login successful')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out')
    return redirect(url_for('index'))

@app.route('/create_initiative', methods=['GET', 'POST'])
def create_initiative():
    if 'user_id' not in session:
        flash('You need to login first')
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        new_initiative = Initiative(title=title, content=content, user_id=session['user_id'])
        db.session.add(new_initiative)
        db.session.commit()
        flash('Initiative created successfully')
        return redirect(url_for('index'))
    return render_template('create_initiative.html')

@app.route('/vote/<int:initiative_id>/<string:action>')
def vote(initiative_id, action):
    if 'user_id' not in session:
        flash('Вы должны войти, чтобы голосовать')
        return redirect(url_for('login'))

    initiative = Initiative.query.get(initiative_id)
    if not initiative:
        flash('Инициатива не найдена')
        return redirect(url_for('index'))

    # Проверяем, голосовал ли пользователь за эту инициативу
    vote = Vote.query.filter_by(user_id=session['user_id'], initiative_id=initiative_id).first()

    if action == 'add':
        # Если пользователь уже голосовал, обновляем голос
        if vote:
            vote.vote_value = 1
        else:
            # Если пользователь еще не голосовал, создаем новый голос
            new_vote = Vote(user_id=session['user_id'], initiative_id=initiative_id, vote_value=1)
            db.session.add(new_vote)
    elif action == 'subtract':
        # Если пользователь уже голосовал, обновляем голос
        if vote:
            vote.vote_value = -1
        else:
            # Если пользователь еще не голосовал, создаем новый голос
            new_vote = Vote(user_id=session['user_id'], initiative_id=initiative_id, vote_value=-1)
            db.session.add(new_vote)

        # Сохраняем изменения, чтобы обновить данные в базе
        db.session.commit()

        # Подсчитываем количество отрицательных голосов через SQL-запрос
        negative_votes_count = Vote.query.filter_by(initiative_id=initiative_id, vote_value=-1).count()

        # Проверяем, достигло ли количество отрицательных голосов 10
        if negative_votes_count >= 10:
            # Удаляем инициативу напрямую через SQL-запрос
            db.session.execute(text("DELETE FROM initiative WHERE id = :initiative_id"), {"initiative_id": initiative_id})
            db.session.commit()
            flash('Инициатива удалена из-за превышения отрицательных голосов')
            return redirect(url_for('index'))
    else:
        flash('Неверное действие')
        return redirect(url_for('index'))

    # Сохраняем изменения
    db.session.commit()

    flash('Голос учтен')

    # Возвращаемся на ту же страницу и позицию
    page = request.args.get('page', 1, type=int)
    return redirect(url_for('index', page=page))

@app.route('/admin')
def admin():
    if 'user_id' not in session or session['user_id'] != 1:
        flash('You do not have permission to access this page')
        return redirect(url_for('index'))
    users = User.query.all()
    initiatives = Initiative.query.all()
    return render_template('admin.html', users=users, initiatives=initiatives)

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'user_id' not in session or session['user_id'] != 1:
        flash('You do not have permission to access this page')
        return redirect(url_for('index'))
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully')
    return redirect(url_for('admin'))

@app.route('/delete_initiative/<int:initiative_id>')
def delete_initiative(initiative_id):
    if 'user_id' not in session:
        flash('Вы должны войти, чтобы удалить инициативу')
        return redirect(url_for('login'))

    initiative = Initiative.query.get(initiative_id)
    if not initiative:
        flash('Инициатива не найдена')
        return redirect(url_for('index'))

    # Проверяем, что текущий пользователь является создателем инициативы или администратором
    if initiative.user_id != session['user_id'] and session['user_id'] != 1:
        flash('Вы не можете удалить эту инициативу')
        return redirect(url_for('index'))

    # Удаляем инициативу
    db.session.delete(initiative)
    db.session.commit()
    flash('Инициатива удалена')

    # Проверяем, откуда был выполнен запрос на удаление
    if request.referrer and '/admin' in request.referrer:
        return redirect(url_for('admin'))  # Остаемся в админ-панели
    else:
        return redirect(url_for('index'))  # Остаемся на главной странице