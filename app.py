from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your_secret_key' 
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

# --- UPDATED: USER MODEL ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(60), nullable=False) 
    # Link to products: This allows user.products to return all their assets
    products = db.relationship('Product', backref='owner', lazy=True)

# --- UPDATED: PRODUCT MODEL ---
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    # FOREIGN KEY: Every product now belongs to a specific User ID
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Product {self.name}>'

# --- AUTHENTICATION ROUTES ---
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

# --- UPDATED: PROTECTED INVENTORY ROUTES ---

@app.route('/')
@login_required 
def dashboard():
    search_term = request.args.get('search')
    # LOGIC FIX: Filter by search term AND ensure only current_user's products are shown
    if search_term:
        products = Product.query.filter(
            Product.name.ilike(f'%{search_term}%'),
            Product.user_id == current_user.id
        ).all()
    else:
        # LOGIC FIX: Show only the logged-in user's assets
        products = Product.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', products=products)

@app.route('/add', methods=['GET', 'POST'])
@login_required 
def add_product():
    if request.method == 'POST':
        new_product = Product(
            name=request.form['name'],
            description=request.form['description'],
            quantity=int(request.form['quantity']),
            price=float(request.form['price']),
            # LOGIC FIX: Explicitly tag this product with the current user's ID
            user_id=current_user.id
        )
        db.session.add(new_product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_product.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required 
def edit_product(id):
    # SECURITY FIX: Ensure the product actually belongs to the user before editing
    product_to_edit = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()
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
    # SECURITY FIX: Ensure the product belongs to the user before deleting
    product_to_delete = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(product_to_delete)
    db.session.commit()
    flash('Product deleted successfully.', 'danger')
    return redirect(url_for('dashboard'))

# --- CRITICAL FIX FOR DEPLOYMENT ---
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)