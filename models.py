from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'admin', 'dealer', 'client', 'driver'
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='active') # 'pending', 'approved', 'rejected' for dealers
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    dealer_profile = db.relationship('DealerProfile', backref='user', uselist=False, cascade="all, delete-orphan")
    driver_profile = db.relationship('Driver', foreign_keys='Driver.user_id', backref='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class DealerProfile(db.Model):
    __tablename__ = 'dealer'
    
    dealer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    license_no = db.Column(db.String(50), nullable=False)
    quarry_location = db.Column(db.String(200), nullable=False)

class Driver(db.Model):
    __tablename__ = 'driver'
    
    driver_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, unique=True)
    dealer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    license_number = db.Column(db.String(50), nullable=False)
    vehicle_number = db.Column(db.String(50), nullable=False)

    dealer = db.relationship('User', foreign_keys=[dealer_id], backref='managed_drivers')

class Material(db.Model):
    __tablename__ = 'material'
    
    material_id = db.Column(db.Integer, primary_key=True)
    dealer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    unit = db.Column(db.String(20), default='Ton')
    description = db.Column(db.Text, nullable=True)

    dealer = db.relationship('User', foreign_keys=[dealer_id], backref=db.backref('materials', lazy=True))

class DealerStock(db.Model):
    __tablename__ = 'dealer_stock'
    
    stock_id = db.Column(db.Integer, primary_key=True)
    dealer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('material.material_id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0.0)
    price_per_unit = db.Column(db.Float, nullable=False, default=0.0)

    dealer = db.relationship('User', backref='stocks')
    material = db.relationship('Material', backref='dealer_stocks')

class Order(db.Model):
    __tablename__ = 'orders'
    
    order_id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    dealer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('material.material_id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    delivery_address = db.Column(db.Text, nullable=False)
    requested_date = db.Column(db.Date, nullable=False)
    allocated_driver_id = db.Column(db.Integer, db.ForeignKey('driver.driver_id'), nullable=True)
    status = db.Column(db.String(30), default='Pending') # Pending, Approved, Rejected, Pass Issued, Out for Delivery, Delivered, Completed, Paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    client = db.relationship('User', foreign_keys=[client_id], backref='client_orders')
    dealer = db.relationship('User', foreign_keys=[dealer_id], backref='dealer_orders')
    material = db.relationship('Material', backref='orders')
    allocated_driver = db.relationship('Driver', backref='assigned_orders')

class DriverPass(db.Model):
    __tablename__ = 'driver_pass'
    
    pass_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.driver_id'), nullable=False)
    dealer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    valid_until = db.Column(db.Date, nullable=False)
    pass_status = db.Column(db.String(20), default='Issued') # Issued, Completed, Expired
    remarks = db.Column(db.Text, nullable=True)

    order = db.relationship('Order', backref=db.backref('driver_passes', lazy=True))
    driver = db.relationship('Driver', backref=db.backref('driver_passes', lazy=True))
    dealer = db.relationship('User', foreign_keys=[dealer_id], backref=db.backref('dealer_passes', lazy=True))

class Payment(db.Model):
    __tablename__ = 'payment'
    
    payment_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), default='Online / UPI / Card')
    payment_status = db.Column(db.String(20), default='Paid')
    transaction_ref = db.Column(db.String(100), nullable=True)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)

    order = db.relationship('Order', backref='payments')

class Complaint(db.Model):
    __tablename__ = 'complaint'
    
    complaint_id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Open') # Open, Replied, Closed
    admin_reply = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    client = db.relationship('User', backref='complaints')

class Feedback(db.Model):
    __tablename__ = 'feedback'
    
    feedback_id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    client = db.relationship('User', backref='feedbacks')

class Review(db.Model):
    __tablename__ = 'review'
    
    review_id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    dealer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    rating = db.Column(db.Integer, default=5)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    client = db.relationship('User', foreign_keys=[client_id], backref='given_reviews')
    dealer = db.relationship('User', foreign_keys=[dealer_id], backref='received_reviews')
