from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
# --- NEW IMPORTS ---
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your_secret_key' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- NEW: BCRYPT & LOGIN MANAGER SETUP ---
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' 
login_manager.login_message_category = 'info' 

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- NEW: USER MODEL ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(60), nullable=False) 

# --- PRODUCT MODEL ---
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<Product {self.name}>'

# --- NEW: AUTHENTICATION ROUTES ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user) 
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login unsuccessful. Please check username and password.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user() 
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- PROTECTED INVENTORY ROUTES ---

@app.route('/')
@login_required 
def dashboard():
    search_term = request.args.get('search')
    if search_term:
        products = Product.query.filter(Product.name.ilike(f'%{search_term}%')).all()
    else:
        products = Product.query.all()
    return render_template('dashboard.html', products=products)

@app.route('/add', methods=['GET', 'POST'])
@login_required 
def add_product():
    if request.method == 'POST':
        new_product = Product(
            name=request.form['name'],
            description=request.form['description'],
            quantity=int(request.form['quantity']),
            price=float(request.form['price'])
        )
        db.session.add(new_product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_product.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required 
def edit_product(id):
    product_to_edit = Product.query.get_or_404(id)
    if request.method == 'POST':
        product_to_edit.name = request.form['name']
        product_to_edit.description = request.form['description']
        product_to_edit.quantity = int(request.form['quantity'])
        product_to_edit.price = float(request.form['price'])
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_product.html', product=product_to_edit)

@app.route('/delete/<int:id>', methods=['POST'])
@login_required 
def delete_product(id):
    product_to_delete = Product.query.get_or_404(id)
    db.session.delete(product_to_delete)
    db.session.commit()
    flash('Product deleted successfully.', 'danger')
    return redirect(url_for('dashboard'))

# --- CRITICAL FIX FOR DEPLOYMENT ---
# This ensures that database tables are created on the server before the app starts
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)