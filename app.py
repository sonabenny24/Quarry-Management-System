import os
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from config import Config
from models import db, User, DealerProfile, Driver, Material, DealerStock, Order, DriverPass, Payment, Complaint, Feedback, Review
from auth_helpers import login_required, get_current_user

app = Flask(__name__) 
app.config.from_object(Config)
db.init_app(app)

# Helper function to auto-update expired driver passes
def update_expired_passes():
    today = date.today()
    expired_passes = DriverPass.query.filter(
        DriverPass.valid_until < today,
        DriverPass.pass_status == 'Issued'
    ).all()
    if expired_passes:
        for dp in expired_passes:
            dp.pass_status = 'Expired'
        db.session.commit()

# Context Processor for Templates
@app.context_processor
def inject_user():
    user = get_current_user()
    return dict(current_user=user, today_date=date.today().strftime('%Y-%m-%d'))

# ---------------------------------------------------------
# AUTHENTICATION ROUTES
# ---------------------------------------------------------
@app.route('/')
def index():
    user = get_current_user()
    if user:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if user.role == 'dealer' and user.status == 'pending':
                flash('Your dealer registration is currently pending admin approval.', 'warning')
                return render_template('auth/login.html')
            elif user.role == 'dealer' and user.status == 'rejected':
                flash('Your dealer registration has been rejected by the admin.', 'danger')
                return render_template('auth/login.html')
            
            session['user_id'] = user.user_id
            session['role'] = user.role
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('auth/login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not identifier or not new_password:
            flash('Please fill in all required fields.', 'warning')
            return render_template('auth/forgot_password.html')

        if new_password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return render_template('auth/forgot_password.html')

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user:
            user.set_password(new_password)
            db.session.commit()
            flash('Password reset successful! You can now log in with your new password.', 'success')
            return redirect(url_for('login'))
        else:
            flash('No account found with that username or email address.', 'danger')

    return render_template('auth/forgot_password.html')

@app.route('/register/client', methods=['GET', 'POST'])
def register_client():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or Email already registered.', 'danger')
            return render_template('auth/register_client.html')

        user = User(
            username=username,
            email=email,
            role='client',
            name=name,
            phone=phone,
            address=address,
            status='active'
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Client account registered successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('auth/register_client.html')

@app.route('/register/dealer', methods=['GET', 'POST'])
def register_dealer():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        company_name = request.form.get('company_name')
        license_no = request.form.get('license_no')
        quarry_location = request.form.get('quarry_location')

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or Email already registered.', 'danger')
            return render_template('auth/register_dealer.html')

        user = User(
            username=username,
            email=email,
            role='dealer',
            name=name,
            phone=phone,
            address=address,
            status='pending' # Requires admin approval
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        dealer_profile = DealerProfile(
            dealer_id=user.user_id,
            company_name=company_name,
            license_no=license_no,
            quarry_location=quarry_location
        )
        db.session.add(dealer_profile)
        db.session.commit()

        flash('Dealer registration submitted successfully! Awaiting Admin approval.', 'info')
        return redirect(url_for('login'))

    return render_template('auth/register_dealer.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required()
def dashboard():
    user = get_current_user()
    if user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif user.role == 'dealer':
        return redirect(url_for('dealer_dashboard'))
    elif user.role == 'client':
        return redirect(url_for('client_dashboard'))
    elif user.role == 'driver':
        return redirect(url_for('driver_dashboard'))
    return redirect(url_for('login'))

# ---------------------------------------------------------
# ADMIN MODULE
# ---------------------------------------------------------
@app.route('/admin/dashboard')
@login_required(roles='admin')
def admin_dashboard():
    total_dealers = User.query.filter_by(role='dealer', status='approved').count()
    pending_dealers = User.query.filter_by(role='dealer', status='pending').count()
    total_clients = User.query.filter_by(role='client').count()
    total_orders = Order.query.count()
    total_materials = Material.query.count()
    open_complaints = Complaint.query.filter_by(status='Open').count()

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                           total_dealers=total_dealers,
                           pending_dealers=pending_dealers,
                           total_clients=total_clients,
                           total_orders=total_orders,
                           total_materials=total_materials,
                           open_complaints=open_complaints,
                           recent_orders=recent_orders)

@app.route('/admin/dealers')
@login_required(roles='admin')
def admin_dealers():
    pending_dealers = User.query.filter_by(role='dealer', status='pending').all()
    approved_dealers = User.query.filter_by(role='dealer', status='approved').all()
    rejected_dealers = User.query.filter_by(role='dealer', status='rejected').all()
    return render_template('admin/dealers.html',
                           pending_dealers=pending_dealers,
                           approved_dealers=approved_dealers,
                           rejected_dealers=rejected_dealers)

@app.route('/admin/dealers/approve/<int:dealer_id>', methods=['POST'])
@login_required(roles='admin')
def approve_dealer(dealer_id):
    dealer = User.query.get_or_404(dealer_id)
    dealer.status = 'approved'
    db.session.commit()
    flash(f'Dealer {dealer.name} approved successfully!', 'success')
    return redirect(url_for('admin_dealers'))

@app.route('/admin/dealers/reject/<int:dealer_id>', methods=['POST'])
@login_required(roles='admin')
def reject_dealer(dealer_id):
    dealer = User.query.get_or_404(dealer_id)
    dealer.status = 'rejected'
    db.session.commit()
    flash(f'Dealer {dealer.name} has been rejected.', 'info')
    return redirect(url_for('admin_dealers'))

@app.route('/admin/clients')
@login_required(roles='admin')
def admin_clients():
    clients = User.query.filter_by(role='client').all()
    return render_template('admin/clients.html', clients=clients)

@app.route('/admin/materials', methods=['GET', 'POST'])
@login_required(roles='admin')
def admin_materials():
    if request.method == 'POST':
        dealer_id = request.form.get('dealer_id', type=int)
        name = request.form.get('name', '').strip()
        unit = request.form.get('unit', '').strip()
        description = request.form.get('description', '').strip()
        stock_qty_str = request.form.get('stock_quantity', '0').strip()
        
        try:
            stock_quantity = float(stock_qty_str) if stock_qty_str else 0.0
        except ValueError:
            stock_quantity = 0.0

        if not dealer_id or not name or not unit:
            flash('Dealer, Material Name, and Unit are required fields.', 'danger')
            return redirect(url_for('admin_materials'))

        dealer = User.query.filter_by(user_id=dealer_id, role='dealer', status='approved').first()
        if not dealer:
            flash('Selected dealer is invalid or not approved.', 'danger')
            return redirect(url_for('admin_materials'))

        mat = Material(
            dealer_id=dealer_id,
            name=name,
            unit=unit,
            description=description
        )
        db.session.add(mat)
        db.session.flush()

        existing_stock = DealerStock.query.filter_by(dealer_id=dealer_id, material_id=mat.material_id).first()
        if existing_stock:
            existing_stock.quantity = stock_quantity
        else:
            new_stock = DealerStock(
                dealer_id=dealer_id,
                material_id=mat.material_id,
                quantity=stock_quantity,
                price_per_unit=0.0
            )
            db.session.add(new_stock)

        db.session.commit()
        flash(f'New material "{name}" added successfully for {dealer.name}.', 'success')
        return redirect(url_for('admin_materials'))

    selected_dealer_id = request.args.get('dealer_id', type=int)
    approved_dealers = User.query.filter_by(role='dealer', status='approved').order_by(User.name.asc()).all()

    if selected_dealer_id:
        target_dealers = [d for d in approved_dealers if d.user_id == selected_dealer_id]
    else:
        target_dealers = approved_dealers

    dealer_sections = []
    for dealer in target_dealers:
        materials_with_stock = db.session.query(
            Material,
            db.func.coalesce(DealerStock.quantity, 0.0).label('stock_quantity')
        ).outerjoin(
            DealerStock,
            (DealerStock.material_id == Material.material_id) & (DealerStock.dealer_id == Material.dealer_id)
        ).filter(
            Material.dealer_id == dealer.user_id
        ).order_by(Material.material_id.asc()).all()

        materials_list = []
        for mat, qty in materials_with_stock:
            materials_list.append({
                'material_id': mat.material_id,
                'name': mat.name,
                'unit': mat.unit,
                'description': mat.description,
                'stock_quantity': qty
            })

        dealer_sections.append({
            'dealer': dealer,
            'materials': materials_list,
            'total_count': len(materials_list)
        })

    return render_template(
        'admin/materials.html',
        dealer_sections=dealer_sections,
        approved_dealers=approved_dealers,
        selected_dealer_id=selected_dealer_id
    )

@app.route('/admin/materials/delete/<int:material_id>', methods=['POST'])
@login_required(roles='admin')
def delete_material(material_id):
    mat = Material.query.get_or_404(material_id)
    DealerStock.query.filter_by(material_id=material_id).delete()
    db.session.delete(mat)
    db.session.commit()
    flash('Material deleted successfully.', 'info')
    return redirect(url_for('admin_materials'))

@app.route('/admin/complaints', methods=['GET', 'POST'])
@login_required(roles='admin')
def admin_complaints():
    if request.method == 'POST':
        complaint_id = request.form.get('complaint_id')
        reply = request.form.get('admin_reply')
        comp = Complaint.query.get_or_404(complaint_id)
        comp.admin_reply = reply
        comp.status = 'Replied'
        db.session.commit()
        flash('Reply sent to client successfully.', 'success')
        return redirect(url_for('admin_complaints'))

    complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return render_template('admin/complaints.html', complaints=complaints)

@app.route('/admin/feedback')
@login_required(roles='admin')
def admin_feedback():
    feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template('admin/feedback.html', feedbacks=feedbacks, reviews=reviews)


# ---------------------------------------------------------
# DEALER MODULE
# ---------------------------------------------------------
@app.route('/dealer/dashboard')
@login_required(roles='dealer')
def dealer_dashboard():
    user = get_current_user()
    update_expired_passes()

    total_stock_items = DealerStock.query.filter_by(dealer_id=user.user_id).count()
    total_drivers = Driver.query.filter_by(dealer_id=user.user_id).count()
    pending_orders = Order.query.filter_by(dealer_id=user.user_id, status='Pending').count()
    approved_orders = Order.query.filter_by(dealer_id=user.user_id, status='Approved').count()
    active_passes = DriverPass.query.filter_by(dealer_id=user.user_id, pass_status='Issued').count()

    recent_orders = Order.query.filter_by(dealer_id=user.user_id).order_by(Order.created_at.desc()).limit(5).all()

    return render_template('dealer/dashboard.html',
                           total_stock_items=total_stock_items,
                           total_drivers=total_drivers,
                           pending_orders=pending_orders,
                           approved_orders=approved_orders,
                           active_passes=active_passes,
                           recent_orders=recent_orders)

@app.route('/dealer/stock', methods=['GET', 'POST'])
@login_required(roles='dealer')
def dealer_stock():
    user = get_current_user()
    if request.method == 'POST':
        material_id = request.form.get('material_id')
        quantity = float(request.form.get('quantity'))
        price_per_unit = float(request.form.get('price_per_unit'))

        existing_stock = DealerStock.query.filter_by(dealer_id=user.user_id, material_id=material_id).first()
        if existing_stock:
            existing_stock.quantity = quantity
            existing_stock.price_per_unit = price_per_unit
            flash('Stock updated successfully.', 'success')
        else:
            stock = DealerStock(
                dealer_id=user.user_id,
                material_id=material_id,
                quantity=quantity,
                price_per_unit=price_per_unit
            )
            db.session.add(stock)
            flash('Stock item added successfully.', 'success')
        db.session.commit()
        return redirect(url_for('dealer_stock'))

    stocks = DealerStock.query.filter_by(dealer_id=user.user_id).all()
    materials = Material.query.all()
    return render_template('dealer/stock.html', stocks=stocks, materials=materials)

@app.route('/dealer/stock/delete/<int:stock_id>', methods=['POST'])
@login_required(roles='dealer')
def delete_stock(stock_id):
    user = get_current_user()
    stock = DealerStock.query.filter_by(stock_id=stock_id, dealer_id=user.user_id).first_or_404()
    db.session.delete(stock)
    db.session.commit()
    flash('Stock item deleted.', 'info')
    return redirect(url_for('dealer_stock'))

@app.route('/dealer/drivers', methods=['GET', 'POST'])
@login_required(roles='dealer')
def dealer_drivers():
    user = get_current_user()
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        license_number = request.form.get('license_number')
        vehicle_number = request.form.get('vehicle_number')

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or Email already exists.', 'danger')
            return redirect(url_for('dealer_drivers'))

        driver_user = User(
            username=username,
            email=email,
            role='driver',
            name=name,
            phone=phone,
            status='active'
        )
        driver_user.set_password(password)
        db.session.add(driver_user)
        db.session.flush()

        driver = Driver(
            user_id=driver_user.user_id,
            dealer_id=user.user_id,
            license_number=license_number,
            vehicle_number=vehicle_number
        )
        db.session.add(driver)
        db.session.commit()
        flash('New driver added successfully!', 'success')
        return redirect(url_for('dealer_drivers'))

    drivers = Driver.query.filter_by(dealer_id=user.user_id).all()
    return render_template('dealer/drivers.html', drivers=drivers)

@app.route('/dealer/drivers/delete/<int:driver_id>', methods=['POST'])
@login_required(roles='dealer')
def delete_driver(driver_id):
    user = get_current_user()
    driver = Driver.query.filter_by(driver_id=driver_id, dealer_id=user.user_id).first_or_404()
    driver_user = User.query.get(driver.user_id)
    db.session.delete(driver)
    if driver_user:
        db.session.delete(driver_user)
    db.session.commit()
    flash('Driver record deleted.', 'info')
    return redirect(url_for('dealer_drivers'))

@app.route('/dealer/orders')
@login_required(roles='dealer')
def dealer_orders():
    user = get_current_user()
    orders = Order.query.filter_by(dealer_id=user.user_id).order_by(Order.created_at.desc()).all()
    drivers = Driver.query.filter_by(dealer_id=user.user_id).all()
    return render_template('dealer/orders.html', orders=orders, drivers=drivers)

@app.route('/dealer/orders/approve/<int:order_id>', methods=['POST'])
@login_required(roles='dealer')
def approve_order(order_id):
    user = get_current_user()
    order = Order.query.filter_by(order_id=order_id, dealer_id=user.user_id).first_or_404()
    
    # Check inventory
    stock = DealerStock.query.filter_by(dealer_id=user.user_id, material_id=order.material_id).first()
    if not stock or stock.quantity < order.quantity:
        flash(f'Insufficient stock for {order.material.name}. Available: {stock.quantity if stock else 0} Tons.', 'danger')
        return redirect(url_for('dealer_orders'))

    order.status = 'Approved'
    db.session.commit()
    flash(f'Order #{order.order_id} approved successfully.', 'success')
    return redirect(url_for('dealer_orders'))

@app.route('/dealer/orders/reject/<int:order_id>', methods=['POST'])
@login_required(roles='dealer')
def reject_order(order_id):
    user = get_current_user()
    order = Order.query.filter_by(order_id=order_id, dealer_id=user.user_id).first_or_404()
    order.status = 'Rejected'
    db.session.commit()
    flash(f'Order #{order.order_id} rejected.', 'info')
    return redirect(url_for('dealer_orders'))

@app.route('/dealer/orders/allocate_driver/<int:order_id>', methods=['POST'])
@login_required(roles='dealer')
def allocate_driver(order_id):
    user = get_current_user()
    order = Order.query.filter_by(order_id=order_id, dealer_id=user.user_id).first_or_404()
    driver_id = request.form.get('driver_id')
    
    driver = Driver.query.filter_by(driver_id=driver_id, dealer_id=user.user_id).first_or_404()
    order.allocated_driver_id = driver.driver_id
    if order.status == 'Approved':
        order.status = 'Driver Allocated'
    db.session.commit()
    flash(f'Driver {driver.user.name} allocated to Order #{order.order_id}.', 'success')
    return redirect(url_for('dealer_orders'))

# ---------------------------------------------------------
# DEALER MODULE – DRIVER PASS MANAGEMENT
# ---------------------------------------------------------

# Helper API endpoint for dynamic dropdown fetching in Driver Pass Creation
@app.route('/dealer/api/order_info/<int:order_id>')
@login_required(roles='dealer')
def api_order_info(order_id):
    user = get_current_user()
    order = Order.query.filter_by(order_id=order_id, dealer_id=user.user_id).first()
    if not order:
        return jsonify({'error': 'Order not found'}), 404

    driver_info = None
    if order.allocated_driver:
        driver_info = {
            'driver_id': order.allocated_driver.driver_id,
            'driver_name': order.allocated_driver.user.name,
            'vehicle_number': order.allocated_driver.vehicle_number,
            'license_number': order.allocated_driver.license_number
        }

    return jsonify({
        'order_id': order.order_id,
        'client_name': order.client.name,
        'material_name': order.material.name,
        'quantity': order.quantity,
        'unit': order.material.unit,
        'delivery_address': order.delivery_address,
        'status': order.status,
        'driver': driver_info
    })

@app.route('/dealer/api/driver_info/<int:driver_id>')
@login_required(roles='dealer')
def api_driver_info(driver_id):
    user = get_current_user()
    driver = Driver.query.filter_by(driver_id=driver_id, dealer_id=user.user_id).first()
    if not driver:
        return jsonify({'error': 'Driver not found'}), 404

    return jsonify({
        'driver_id': driver.driver_id,
        'driver_name': driver.user.name,
        'vehicle_number': driver.vehicle_number,
        'license_number': driver.license_number
    })

@app.route('/dealer/driver_pass')
@login_required(roles='dealer')
def dealer_driver_pass_list():
    user = get_current_user()
    update_expired_passes()

    # Search / Filter Parameters
    search_order_id = request.args.get('order_id', '').strip()
    search_driver_id = request.args.get('driver_id', '').strip()
    search_client = request.args.get('client_name', '').strip()
    search_status = request.args.get('pass_status', '').strip()

    query = DriverPass.query.filter_by(dealer_id=user.user_id)

    if search_order_id:
        query = query.filter(DriverPass.order_id == search_order_id)
    if search_driver_id:
        query = query.filter(DriverPass.driver_id == search_driver_id)
    if search_status:
        query = query.filter(DriverPass.pass_status == search_status)
    if search_client:
        query = query.join(Order, DriverPass.order_id == Order.order_id)\
                     .join(User, Order.client_id == User.user_id)\
                     .filter(User.name.ilike(f'%{search_client}%'))

    passes = query.order_by(DriverPass.pass_id.desc()).all()
    drivers = Driver.query.filter_by(dealer_id=user.user_id).all()

    return render_template('dealer/driver_passes.html',
                           passes=passes,
                           drivers=drivers,
                           search_order_id=search_order_id,
                           search_driver_id=search_driver_id,
                           search_client=search_client,
                           search_status=search_status)

@app.route('/dealer/driver_pass/create', methods=['GET', 'POST'])
@login_required(roles='dealer')
def create_driver_pass():
    user = get_current_user()
    update_expired_passes()

    if request.method == 'POST':
        order_id = request.form.get('order_id')
        driver_id = request.form.get('driver_id')
        valid_until_str = request.form.get('valid_until')
        remarks = request.form.get('remarks', '')

        # Validations
        if not order_id or not driver_id or not valid_until_str:
            flash('Order ID, Driver, and Valid Until date are required.', 'danger')
            return redirect(url_for('create_driver_pass'))

        order = Order.query.filter_by(order_id=order_id, dealer_id=user.user_id).first()
        if not order:
            flash('Invalid Order ID selected.', 'danger')
            return redirect(url_for('create_driver_pass'))

        # Only approved/eligible orders can be selected
        if order.status not in ['Approved', 'Driver Allocated', 'Pass Issued', 'Out for Delivery']:
            flash('Only approved or active orders can be issued a Driver Pass.', 'danger')
            return redirect(url_for('create_driver_pass'))

        driver = Driver.query.filter_by(driver_id=driver_id, dealer_id=user.user_id).first()
        if not driver:
            flash('Invalid Driver selected. Driver must belong to your dealership.', 'danger')
            return redirect(url_for('create_driver_pass'))

        # Prevent duplicate active passes for the same order
        existing_pass = DriverPass.query.filter_by(order_id=order.order_id)\
                                        .filter(DriverPass.pass_status.in_(['Issued'])).first()
        if existing_pass:
            flash(f'An active Driver Pass (Pass #{existing_pass.pass_id}) already exists for Order #{order.order_id}.', 'warning')
            return redirect(url_for('create_driver_pass'))

        issue_date = date.today()
        try:
            valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format for Valid Until.', 'danger')
            return redirect(url_for('create_driver_pass'))

        if valid_until < issue_date:
            flash('Valid Until date cannot be earlier than the Issue Date.', 'danger')
            return redirect(url_for('create_driver_pass'))

        # Create new DriverPass
        new_pass = DriverPass(
            order_id=order.order_id,
            driver_id=driver.driver_id,
            dealer_id=user.user_id,
            issue_date=issue_date,
            valid_until=valid_until,
            pass_status='Issued',
            remarks=remarks
        )

        # Update order allocated driver & status
        order.allocated_driver_id = driver.driver_id
        order.status = 'Pass Issued'

        db.session.add(new_pass)
        db.session.commit()

        flash(f'Driver Pass #{new_pass.pass_id} generated successfully!', 'success')
        return redirect(url_for('view_driver_pass', pass_id=new_pass.pass_id))

    # GET Request: Fetch eligible approved orders and dealer's drivers
    eligible_orders = Order.query.filter_by(dealer_id=user.user_id)\
                                  .filter(Order.status.in_(['Approved', 'Driver Allocated', 'Pass Issued']))\
                                  .order_by(Order.order_id.desc()).all()
    
    # Filter out orders that already have an active 'Issued' pass
    available_orders = []
    for ord_obj in eligible_orders:
        has_issued_pass = DriverPass.query.filter_by(order_id=ord_obj.order_id, pass_status='Issued').first()
        if not has_issued_pass:
            available_orders.append(ord_obj)

    drivers = Driver.query.filter_by(dealer_id=user.user_id).all()
    default_issue_date = date.today().strftime('%Y-%m-%d')
    default_valid_until = (date.today() + timedelta(days=2)).strftime('%Y-%m-%d')

    return render_template('dealer/create_pass.html',
                           orders=available_orders,
                           drivers=drivers,
                           issue_date=default_issue_date,
                           valid_until=default_valid_until)

@app.route('/dealer/driver_pass/view/<int:pass_id>')
@login_required(roles=['dealer', 'admin', 'driver'])
def view_driver_pass(pass_id):
    user = get_current_user()
    update_expired_passes()

    driver_pass = DriverPass.query.get_or_404(pass_id)

    # Security verification
    if user.role == 'dealer' and driver_pass.dealer_id != user.user_id:
        flash('Unauthorized access to driver pass.', 'danger')
        return redirect(url_for('dealer_driver_pass_list'))
    elif user.role == 'driver':
        if not user.driver_profile or driver_pass.driver_id != user.driver_profile.driver_id:
            flash('Unauthorized access to driver pass.', 'danger')
            return redirect(url_for('driver_passes'))

    return render_template('dealer/view_pass.html', pass_item=driver_pass)

@app.route('/dealer/driver_pass/update_status/<int:pass_id>', methods=['POST'])
@login_required(roles='dealer')
def update_pass_status(pass_id):
    user = get_current_user()
    driver_pass = DriverPass.query.filter_by(pass_id=pass_id, dealer_id=user.user_id).first_or_404()
    
    new_status = request.form.get('pass_status')
    if new_status in ['Issued', 'Completed', 'Expired']:
        driver_pass.pass_status = new_status
        if new_status == 'Completed':
            driver_pass.order.status = 'Completed'
        db.session.commit()
        flash(f'Driver Pass #{driver_pass.pass_id} status updated to {new_status}.', 'success')
    else:
        flash('Invalid status option selected.', 'danger')

    return redirect(url_for('dealer_driver_pass_list'))

@app.route('/dealer/payments')
@login_required(roles='dealer')
def dealer_payments():
    user = get_current_user()
    payments = Payment.query.join(Order).filter(Order.dealer_id == user.user_id).all()
    return render_template('dealer/payments.html', payments=payments)

@app.route('/dealer/reviews')
@login_required(roles='dealer')
def dealer_reviews():
    user = get_current_user()
    reviews = Review.query.filter_by(dealer_id=user.user_id).order_by(Review.created_at.desc()).all()
    return render_template('dealer/reviews.html', reviews=reviews)


# ---------------------------------------------------------
# CLIENT MODULE
# ---------------------------------------------------------
@app.route('/client/dashboard')
@login_required(roles='client')
def client_dashboard():
    user = get_current_user()
    orders = Order.query.filter_by(client_id=user.user_id).order_by(Order.created_at.desc()).all()
    active_orders = [o for o in orders if o.status not in ['Completed', 'Rejected']]
    completed_orders = [o for o in orders if o.status == 'Completed']

    return render_template('client/dashboard.html',
                           orders=orders,
                           active_orders=active_orders,
                           completed_orders=completed_orders)

@app.route('/client/browse')
@login_required(roles='client')
def client_browse():
    dealers = User.query.filter_by(role='dealer', status='approved').all()
    materials = Material.query.all()

    dealer_id = request.args.get('dealer_id', type=int)
    material_id = request.args.get('material_id', type=int)

    query = DealerStock.query.join(User, DealerStock.dealer_id == User.user_id)\
                             .filter(User.status == 'approved')
    if dealer_id:
        query = query.filter(DealerStock.dealer_id == dealer_id)
    if material_id:
        query = query.filter(DealerStock.material_id == material_id)

    available_stocks = query.all()

    return render_template('client/browse.html',
                           dealers=dealers,
                           materials=materials,
                           available_stocks=available_stocks,
                           selected_dealer_id=dealer_id,
                           selected_material_id=material_id)

@app.route('/client/place_order', methods=['GET', 'POST'])
@login_required(roles='client')
def place_order():
    user = get_current_user()
    if request.method == 'POST':
        stock_id = request.form.get('stock_id')
        quantity = float(request.form.get('quantity'))
        delivery_address = request.form.get('delivery_address')
        requested_date_str = request.form.get('requested_date')

        stock = DealerStock.query.get_or_404(stock_id)

        if quantity <= 0:
            flash('Quantity must be greater than zero.', 'danger')
            return redirect(url_for('place_order', stock_id=stock_id))

        if quantity > stock.quantity:
            flash(f'Requested quantity ({quantity} Tons) exceeds available dealer stock ({stock.quantity} Tons).', 'danger')
            return redirect(url_for('place_order', stock_id=stock_id))

        unit_price = stock.price_per_unit
        total_price = quantity * unit_price
        req_date = datetime.strptime(requested_date_str, '%Y-%m-%d').date()

        order = Order(
            client_id=user.user_id,
            dealer_id=stock.dealer_id,
            material_id=stock.material_id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
            delivery_address=delivery_address,
            requested_date=req_date,
            status='Pending'
        )
        db.session.add(order)
        db.session.commit()

        flash(f'Order request submitted successfully! Total amount: ₹{total_price:,.2f}', 'success')
        return redirect(url_for('client_dashboard'))

    stock_id = request.args.get('stock_id', type=int)
    selected_stock = DealerStock.query.get(stock_id) if stock_id else None
    all_stocks = DealerStock.query.join(User).filter(User.status == 'approved').all()

    return render_template('client/place_order.html',
                           selected_stock=selected_stock,
                           all_stocks=all_stocks,
                           default_date=(date.today() + timedelta(days=1)).strftime('%Y-%m-%d'))

@app.route('/client/order/<int:order_id>', methods=['GET', 'POST'])
@login_required(roles='client')
def client_order_detail(order_id):
    user = get_current_user()
    order = Order.query.filter_by(order_id=order_id, client_id=user.user_id).first_or_404()

    if request.method == 'POST':
        # Payment submission logic
        # Ensure the order has been approved by the dealer before accepting payment
        allowed_payment_statuses = ['Approved', 'Driver Allocated', 'Pass Issued', 'Out for Delivery', 'Delivered', 'Completed']
        if order.status not in allowed_payment_statuses:
            flash('Payment is not allowed until the dealer approves your order.', 'warning')
            return redirect(url_for('client_order_detail', order_id=order.order_id))

        # Prevent duplicate payments
        if order.payments:
            flash('This order has already been paid.', 'info')
            return redirect(url_for('client_order_detail', order_id=order.order_id))

        payment_method = request.form.get('payment_method')
        txn_ref = f'TXN-{datetime.now().strftime("%Y%m%d%H%M%S")}'

        payment = Payment(
            order_id=order.order_id,
            amount=order.total_price,
            payment_method=payment_method,
            payment_status='Paid',
            transaction_ref=txn_ref
        )
        order.status = 'Paid'

        # Decrement stock
        stock = DealerStock.query.filter_by(dealer_id=order.dealer_id, material_id=order.material_id).first()
        if stock:
            stock.quantity = max(0.0, stock.quantity - order.quantity)

        db.session.add(payment)
        db.session.commit()

        flash(f'Payment of ₹{order.total_price:,.2f} recorded successfully! Receipt #{txn_ref}', 'success')
        return redirect(url_for('client_order_detail', order_id=order.order_id))

    return render_template('client/order_detail.html', order=order)

@app.route('/client/invoice/<int:order_id>')
@login_required(roles=['client', 'dealer', 'admin'])
def view_invoice(order_id):
    user = get_current_user()
    order = Order.query.get_or_404(order_id)

    if user.role == 'client' and order.client_id != user.user_id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('client_dashboard'))
    elif user.role == 'dealer' and order.dealer_id != user.user_id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dealer_dashboard'))

    return render_template('client/invoice.html', order=order)

@app.route('/client/complaints', methods=['GET', 'POST'])
@login_required(roles='client')
def client_complaints():
    user = get_current_user()
    if request.method == 'POST':
        subject = request.form.get('subject')
        message = request.form.get('message')

        comp = Complaint(
            client_id=user.user_id,
            subject=subject,
            message=message,
            status='Open'
        )
        db.session.add(comp)
        db.session.commit()
        flash('Complaint submitted to System Admin.', 'success')
        return redirect(url_for('client_complaints'))

    complaints = Complaint.query.filter_by(client_id=user.user_id).order_by(Complaint.created_at.desc()).all()
    return render_template('client/complaints.html', complaints=complaints)

@app.route('/client/feedback', methods=['GET', 'POST'])
@login_required(roles='client')
def client_feedback():
    user = get_current_user()
    if request.method == 'POST':
        action_type = request.form.get('action_type')

        if action_type == 'review':
            dealer_id = request.form.get('dealer_id')
            rating = int(request.form.get('rating'))
            comment = request.form.get('comment')

            rev = Review(
                client_id=user.user_id,
                dealer_id=dealer_id,
                rating=rating,
                comment=comment
            )
            db.session.add(rev)
            flash('Dealer review submitted.', 'success')
        elif action_type == 'feedback':
            rating = int(request.form.get('rating', 5))
            message = request.form.get('message')

            fb = Feedback(
                client_id=user.user_id,
                message=message,
                rating=rating
            )
            db.session.add(fb)
            flash('System feedback submitted.', 'success')

        db.session.commit()
        return redirect(url_for('client_feedback'))

    dealers = User.query.filter_by(role='dealer', status='approved').all()
    my_reviews = Review.query.filter_by(client_id=user.user_id).all()
    my_feedback = Feedback.query.filter_by(client_id=user.user_id).all()

    return render_template('client/feedback.html', dealers=dealers, my_reviews=my_reviews, my_feedback=my_feedback)


# ---------------------------------------------------------
# DRIVER MODULE
# ---------------------------------------------------------
@app.route('/driver/dashboard')
@login_required(roles='driver')
def driver_dashboard():
    user = get_current_user()
    driver = Driver.query.filter_by(user_id=user.user_id).first_or_404()

    assigned_orders = Order.query.filter_by(allocated_driver_id=driver.driver_id)\
                                 .order_by(Order.created_at.desc()).all()

    pending_deliveries = [o for o in assigned_orders if o.status in ['Approved', 'Driver Allocated', 'Pass Issued', 'Out for Delivery']]
    completed_deliveries = [o for o in assigned_orders if o.status in ['Delivered', 'Completed', 'Paid']]

    return render_template('driver/dashboard.html',
                           driver=driver,
                           assigned_orders=assigned_orders,
                           pending_deliveries=pending_deliveries,
                           completed_deliveries=completed_deliveries)

@app.route('/driver/passes')
@login_required(roles='driver')
def driver_passes():
    user = get_current_user()
    update_expired_passes()

    driver = Driver.query.filter_by(user_id=user.user_id).first_or_404()

    passes = DriverPass.query.filter_by(driver_id=driver.driver_id)\
                            .order_by(DriverPass.pass_id.desc()).all()

    return render_template('driver/driver_passes.html', driver=driver, passes=passes)

@app.route('/driver/confirm_delivery/<int:order_id>', methods=['POST'])
@login_required(roles='driver')
def confirm_delivery(order_id):
    user = get_current_user()
    driver = Driver.query.filter_by(user_id=user.user_id).first_or_404()
    order = Order.query.filter_by(order_id=order_id, allocated_driver_id=driver.driver_id).first_or_404()

    order.status = 'Delivered'

    # Update associated Driver Pass status to Completed
    associated_pass = DriverPass.query.filter_by(order_id=order.order_id).first()
    if associated_pass:
        associated_pass.pass_status = 'Completed'

    db.session.commit()
    flash(f'Delivery for Order #{order.order_id} confirmed as DELIVERED! Driver pass updated to Completed.', 'success')
    return redirect(url_for('driver_dashboard'))

# Application Runner
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
