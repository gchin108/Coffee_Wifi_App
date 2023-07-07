from flask_bootstrap import Bootstrap
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import RegisterForm, LoginForm, CafeForm
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
Bootstrap(app)

print(os.getenv('app_local'))
if os.getenv('app_local') == 'TRUE':
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cafes.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')

db = SQLAlchemy(app)
app.secret_key = secrets.token_hex(16)

# Flask Login
login_manager = LoginManager()
login_manager.init_app(app)


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))

    def __repr__(self):
        return f'<User: {self.name}>'

    def has_the_right_password(self, password):
        return check_password_hash(self.password, password)


class Cafe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    map_url = db.Column(db.String(500), nullable=False)
    street_intersection = db.Column(db.String(250), nullable=False)
    open = db.Column(db.String(500), nullable=False)
    close = db.Column(db.String(250), nullable=False)
    coffee_rating = db.Column(db.String(250), nullable=False)
    wifi_rating = db.Column(db.String(250), nullable=False)
    power_rating = db.Column(db.String(250), nullable=False)

    def __repr__(self):
        return f'<Cafe {self.name}>'


with app.app_context():
    db.create_all()


def admin_only(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            abort(403)  # Return a forbidden status code if the user is not the admin
        return func(*args, **kwargs)

    return decorated_function


@app.route('/')
def home():
    return render_template('index.html')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(str(user_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # Find the user by email
        user = User.query.filter_by(email=email).first()

        if user:
            if user.has_the_right_password(password):
                login_user(user)
                return redirect(url_for('cafes'))
            else:
                flash("Error:Password is incorrect.")
                return redirect(url_for('login'))
        else:
            flash("Error:This email doesn't exist. Please try again.")
            return redirect(url_for('login'))

    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    register_form = RegisterForm()
    if register_form.validate_on_submit():
        new_user = User()
        new_user.email = register_form.email.data
        new_user.password = generate_password_hash(register_form.password.data, method='pbkdf2:sha256', salt_length=8)
        new_user.name = register_form.name.data
        all_users = User.query.all()
        print(all_users)

        if User.query.filter_by(email=register_form.email.data).first():
            flash("Error: This email already exist in our database. Please login")
            return redirect(url_for('login'))
        else:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('cafes'))

    return render_template("register.html", form=register_form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('cafes'))


@app.route('/cafes')
def cafes():
    cafes = Cafe.query.all()
    return render_template('cafes.html', cafes=cafes)


@app.route('/add_cafe', methods=['POST', 'GET'])
@login_required
def add_cafe():
    form = CafeForm()

    if form.validate_on_submit():
        new_cafe = Cafe(
            name=request.form.get('cafe').title(), map_url=request.form.get('map_url'),
            street_intersection=request.form.get('street_intersection'), open=request.form.get('open'),
            close=request.form.get('close'), coffee_rating=request.form.get('coffee_rating'),
            wifi_rating=request.form.get('wifi_rating'), power_rating=request.form.get('power_rating'), )

        print(new_cafe)
        if new_cafe.name == Cafe.query.filter_by(name=new_cafe.name):
            flash(f"{request.form.get('cafe')} cafe already exists. If it's a different location, try to add a "
                  f"location after the cafe name. e.g. {request.form.get('cafe')} Kingsway")
            return redirect('add_cafe')
        else:
            db.session.add(new_cafe)
        try:
            db.session.commit()
        except IntegrityError:
            flash(message=f"{request.form.get('cafe')} cafe already exists. If it's a different location, try to add a "
                          f"location after the cafe name. e.g. {request.form.get('cafe')} Kingsway")
            return redirect(url_for('add_cafe'))
        else:
            return redirect(url_for('cafes'))

    return render_template('add_cafe.html', form=form)


@app.route('/edit-entry/<int:entry_id>', methods=['POST', 'GET'])
@login_required
def edit_entry(entry_id):
    entry = Cafe.query.get(entry_id)
    edit_form = CafeForm(
        cafe=entry.name, map_url=entry.map_url,
        street_intersection=entry.street_intersection, open=entry.open,
        close=entry.close, coffee_rating=entry.coffee_rating,
        wifi_rating=entry.wifi_rating, power_rating=entry.power_rating,
    )
    if edit_form.validate_on_submit():
        entry.name = edit_form.cafe.data.title()
        entry.map_url = edit_form.map_url.data
        entry.street_intersection = edit_form.street_intersection.data
        entry.open = edit_form.open.data
        entry.close = edit_form.close.data
        entry.coffee_rating = edit_form.coffee_rating.data
        entry.wifi_rating = edit_form.wifi_rating.data
        entry.power_rating = edit_form.power_rating.data
        if entry.name == Cafe.query.filter_by(name=entry.name):
            flash(f"{request.form.get('cafe')} cafe already exists. If it's a different location, try to add a "
                  f"location after the cafe name. e.g. {request.form.get('cafe')} Kingsway")
            return redirect('add_cafe')
        try:
            db.session.commit()
        except IntegrityError:
            flash(message=f"{request.form.get('cafe')} cafe already exists. If it's a different location, try to add a "
                          f"location after the cafe name. e.g. {request.form.get('cafe')} Kingsway")
            return redirect(url_for('cafes'))
        else:
            return redirect(url_for('cafes'))
    return render_template("add_cafe.html", form=edit_form, is_edit=True, )


@app.route('/delete-entry/<int:entry_id>')
@admin_only
def delete_entry(entry_id):
    cafe_to_delete = Cafe.query.get(entry_id)
    db.session.delete(cafe_to_delete)
    db.session.commit()
    return redirect(url_for('cafes'))


if __name__ == '__main__':
    app.run(debug=True)
