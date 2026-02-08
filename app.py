from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pushkar_secret_key_2026' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' 
login_manager.login_message_category = 'info' 

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(60), nullable=False) 
    products = db.relationship('Product', backref='owner', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# --- AUTH ROUTES ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('That username is already taken. Try another one.', 'danger')
            return redirect(url_for('register'))
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            login_user(user) 
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed. Please check your credentials.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user() 
    flash('You have logged out successfully.', 'info')
    return redirect(url_for('login'))

# --- INVENTORY ROUTES ---
@app.route('/')
@login_required 
def dashboard():
    search = request.args.get('search')
    if search:
        products = Product.query.filter(Product.name.ilike(f'%{search}%'), Product.user_id == current_user.id).all()
    else:
        products = Product.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', products=products)

@app.route('/add', methods=['GET', 'POST'])
@login_required 
def add_product():
    if request.method == 'POST':
        new_item = Product(
            name=request.form['name'],
            description=request.form['description'],
            quantity=int(request.form['quantity']),
            price=float(request.form['price']),
            user_id=current_user.id
        )
        db.session.add(new_item)
        db.session.commit()
        flash('New item added to your inventory.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_product.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required 
def edit_product(id):
    item = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        item.name = request.form['name']
        item.description = request.form['description']
        item.quantity = int(request.form['quantity'])
        item.price = float(request.form['price'])
        db.session.commit()
        flash('Item details updated.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_product.html', product=item)

@app.route('/delete/<int:id>', methods=['POST'])
@login_required 
def delete_product(id):
    item = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash('Item removed from registry.', 'info')
    return redirect(url_for('dashboard'))

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)