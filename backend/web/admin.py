from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from functools import wraps
from models import db, User, Image, Video, Song, VideoIklan, Product, Like, Comment, ViewCount, ModerationAction, Order, Payment
from sqlalchemy import exc as sa_exc
from datetime import datetime, timedelta
import json
import os
from werkzeug.utils import secure_filename

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Configuration for file uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
UPLOAD_FOLDER = 'static/uploads/proof_images'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('web_pages.login'))
        
        user = db.session.get(User, session['user_id'])
        if not user or user.role != 'admin':
            flash('Anda tidak memiliki akses ke halaman admin!', 'error')
            return redirect(url_for('web_pages.home'))
        
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@admin_required
def dashboard():
    # Statistik user
    total_users = User.query.count()
    active_users = User.query.filter(User.role.in_(['free', 'premium', 'premier'])).count()
    premium_users = User.query.filter(User.role.in_(['premium', 'premier'])).count()
    new_users_today = User.query.filter(
        User.created_at >= datetime.utcnow().date()
    ).count()
    
    # Statistik konten
    total_images = Image.query.count()
    total_videos = Video.query.count()
    total_songs = Song.query.count()
    total_video_iklan = VideoIklan.query.count()
    
    # Statistik payment
    total_payments = Payment.query.count()
    successful_payments = Payment.query.filter(Payment.status == 'success').count()
    pending_payments = Payment.query.filter(Payment.status == 'pending').count()
    failed_payments = Payment.query.filter(Payment.status == 'failed').count()
    refunded_payments = Payment.query.filter(Payment.status == 'refunded').count()
    
    # User activity (7 hari terakhir)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_users = User.query.filter(
        User.created_at >= seven_days_ago
    ).order_by(User.created_at.desc()).limit(5).all()
    
    # Recent payments - with proper relationship loading
    recent_payments = Payment.query.options(
        db.joinedload(Payment.order).joinedload(Order.user)
    ).order_by(Payment.created_at.desc()).limit(5).all()
    
    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'premium_users': premium_users,
        'new_users_today': new_users_today,
        'total_images': total_images,
        'total_videos': total_videos,
        'total_songs': total_songs,
        'total_video_iklan': total_video_iklan,
        'total_payments': total_payments,
        'successful_payments': successful_payments,
        'pending_payments': pending_payments,
        'failed_payments': failed_payments,
        'refunded_payments': refunded_payments
    }
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         recent_users=recent_users,
                         recent_payments=recent_payments)

@admin_bp.route('/users')
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filter dan search
    search = request.args.get('search', '')
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')
    
    query = User.query
    
    if search:
        query = query.filter(
            (User.username.contains(search)) |
            (User.email.contains(search))
        )
    
    if role_filter:
        query = query.filter(User.role == role_filter)
    
    if status_filter == 'active':
        query = query.filter(User.role.in_(['free', 'premium', 'premier']))
    elif status_filter == 'inactive':
        query = query.filter(User.role == 'admin')
    
    # Pagination
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/users.html', users=users, search=search, role_filter=role_filter, status_filter=status_filter)

@admin_bp.route('/users/<int:user_id>')
@admin_required
def user_detail(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('User tidak ditemukan!', 'error')
        return redirect(url_for('admin.users'))
    
    # Get user content
    images = Image.query.filter_by(user_id=user_id).order_by(Image.created_at.desc()).limit(10).all()
    videos = Video.query.filter_by(user_id=user_id).order_by(Video.created_at.desc()).limit(10).all()
    songs = Song.query.filter_by(user_id=user_id).order_by(Song.created_at.desc()).limit(10).all()
    orders = []
    
    return render_template('admin/user_detail.html', 
                         user=user, 
                         images=images, 
                         videos=videos, 
                         songs=songs, 
                         orders=orders)


@admin_bp.route('/users/<int:user_id>/toggle_status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User tidak ditemukan'})
    
    try:
        if user.role == 'admin':
            user.role = 'free'
        else:
            user.role = 'admin'
        
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': f'Status user berhasil diubah menjadi {user.role}',
            'new_role': user.role
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# Orders route removed

@admin_bp.route('/payment')
@admin_required
def payment():
    """Payment management page"""
    
    # Get payment statistics from database
    total_payments = Payment.query.count()
    successful_payments = Payment.query.filter_by(status='success').count()
    pending_payments = Payment.query.filter_by(status='pending').count()
    failed_payments = Payment.query.filter_by(status='failed').count()
    
    # Get recent payments with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filter
    status_filter = request.args.get('status', '')
    date_filter = request.args.get('date', '')
    
    # Build query
    query = Payment.query.join(Order).join(User).join(Product)
    
    # Apply status filter
    if status_filter:
        query = query.filter(Payment.status == status_filter)
    
    # Apply date filter
    if date_filter:
        today = datetime.utcnow().date()
        if date_filter == 'today':
            query = query.filter(db.func.date(Payment.created_at) == today)
        elif date_filter == 'week':
            week_ago = today - timedelta(days=7)
            query = query.filter(db.func.date(Payment.created_at) >= week_ago)
        elif date_filter == 'month':
            month_ago = today - timedelta(days=30)
            query = query.filter(db.func.date(Payment.created_at) >= month_ago)
    
    # Order by created_at descending
    query = query.order_by(Payment.created_at.desc())
    
    # Paginate
    payments = query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    return render_template('admin/payment.html', 
                         payments=payments, 
                         status_filter=status_filter, 
                         date_filter=date_filter,
                         total_payments=total_payments,
                         successful_payments=successful_payments,
                         pending_payments=pending_payments,
                         failed_payments=failed_payments)

@admin_bp.route('/payment/add', methods=['GET', 'POST'])
@admin_required
def add_payment():
    """Tambah payment baru"""
    if request.method == 'POST':
        try:
            # Get form data
            order_id = request.form.get('order_id')
            amount = request.form.get('amount')
            method = request.form.get('method')
            status = request.form.get('status')
            proof_image_url = request.form.get('proof_image_url')
            
            # Handle file upload if provided
            proof_image = None
            if 'proof_image' in request.files:
                file = request.files['proof_image']
                if file and file.filename != '' and allowed_file(file.filename):
                    # Create upload directory if it doesn't exist
                    upload_path = os.path.join(current_app.root_path, UPLOAD_FOLDER)
                    os.makedirs(upload_path, exist_ok=True)
                    
                    # Generate secure filename
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    name, ext = os.path.splitext(filename)
                    filename = f"{name}_{timestamp}{ext}"
                    
                    # Save file
                    file_path = os.path.join(upload_path, filename)
                    file.save(file_path)
                    
                    # Set proof image URL
                    proof_image = f"/{UPLOAD_FOLDER}/{filename}"
            
            # Use uploaded file URL or provided URL
            final_proof_image = proof_image or proof_image_url
            
            # Validate required fields
            if not order_id or not amount:
                flash('Order ID dan Amount harus diisi!', 'error')
                return redirect(url_for('admin.add_payment'))
            
            # Check if order exists
            order = Order.query.get(order_id)
            if not order:
                flash('Order tidak ditemukan!', 'error')
                return redirect(url_for('admin.add_payment'))
            
            # Create new payment
            payment = Payment(
                order_id=order_id,
                amount=float(amount),
                method=method or 'bank_transfer',
                proof_image=final_proof_image,
                status=status or 'pending',
                verified_by=session.get('username') if status == 'success' else None,
                verified_at=datetime.utcnow() if status == 'success' else None
            )
            
            db.session.add(payment)
            
            # Tambahkan kredit ke user jika status success
            if status == 'success':
                user = order.user
                product = order.product
                if user and product:
                    user.kredit += product.kredit
                
                # Update order status
                order.status = 'paid'
            
            db.session.commit()
            
            flash('Payment berhasil ditambahkan!', 'success')
            return redirect(url_for('admin.payment'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('admin.add_payment'))
    
    # GET request - show form
    orders = Order.query.all()
    return render_template('admin/add_payment.html', orders=orders)

@admin_bp.route('/payment/<int:payment_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_payment(payment_id):
    """Edit payment"""
    payment = Payment.query.get_or_404(payment_id)
    
    if request.method == 'POST':
        try:
            # Get form data
            amount = request.form.get('amount')
            method = request.form.get('method')
            status = request.form.get('status')
            proof_image_url = request.form.get('proof_image_url')
            
            # Handle file upload if provided
            proof_image = None
            if 'proof_image' in request.files:
                file = request.files['proof_image']
                if file and file.filename != '' and allowed_file(file.filename):
                    # Create upload directory if it doesn't exist
                    upload_path = os.path.join(current_app.root_path, UPLOAD_FOLDER)
                    os.makedirs(upload_path, exist_ok=True)
                    
                    # Generate secure filename
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    name, ext = os.path.splitext(filename)
                    filename = f"{name}_{timestamp}{ext}"
                    
                    # Save file
                    file_path = os.path.join(upload_path, filename)
                    file.save(file_path)
                    
                    # Set proof image URL
                    proof_image = f"/{UPLOAD_FOLDER}/{filename}"
            
            # Use uploaded file URL or provided URL
            final_proof_image = proof_image or proof_image_url
            
            # Validate required fields
            if not amount:
                flash('Amount harus diisi!', 'error')
                return redirect(url_for('admin.edit_payment', payment_id=payment_id))
            
            # Update payment
            payment.amount = float(amount)
            payment.method = method or 'bank_transfer'
            payment.status = status or 'pending'
            payment.proof_image = final_proof_image
            
            # Update verification info if status changed to success
            if status == 'success' and payment.status != 'success':
                payment.verified_by = session.get('username')
                payment.verified_at = datetime.utcnow()
                
                # Tambahkan kredit ke user dan upgrade ke premium saat status diubah ke success
                user = payment.order.user
                product = payment.order.product
                if user and product:
                    user.kredit += product.kredit
                    # Upgrade user dari free ke premium
                    if user.role == 'free':
                        user.role = 'premium'
                
                # Update order status
                payment.order.status = 'paid'
            
            db.session.commit()
            
            flash('Payment berhasil diupdate!', 'success')
            return redirect(url_for('admin.payment'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('admin.edit_payment', payment_id=payment_id))
    
    # GET request - show form
    return render_template('admin/edit_payment.html', payment=payment)

@admin_bp.route('/payment/<int:payment_id>/approve', methods=['POST'])
@admin_required
def approve_payment(payment_id):
    """Approve payment"""
    try:
        payment = Payment.query.get_or_404(payment_id)
        
        if payment.status != 'pending':
            return jsonify({'success': False, 'message': 'Payment tidak dalam status pending'})
        
        payment.status = 'success'
        payment.verified_by = session.get('username')
        payment.verified_at = datetime.utcnow()
        
        # Update order status
        payment.order.status = 'paid'
        
        # Tambahkan kredit ke user dan upgrade ke premium
        user = payment.order.user
        product = payment.order.product
        if user and product:
            user.kredit += product.kredit
            # Upgrade user dari free ke premium
            if user.role == 'free':
                user.role = 'premium'
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Payment berhasil diapprove'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@admin_bp.route('/payment/<int:payment_id>/reject', methods=['POST'])
@admin_required
def reject_payment(payment_id):
    """Reject payment"""
    try:
        payment = Payment.query.get_or_404(payment_id)
        
        if payment.status != 'pending':
            return jsonify({'success': False, 'message': 'Payment tidak dalam status pending'})
        
        payment.status = 'failed'
        payment.verified_by = session.get('username')
        payment.verified_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Payment berhasil direject'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@admin_bp.route('/payment/<int:payment_id>/refund', methods=['POST'])
@admin_required
def refund_payment(payment_id):
    """Refund payment"""
    try:
        payment = Payment.query.get_or_404(payment_id)
        
        if payment.status != 'success':
            return jsonify({'success': False, 'message': 'Hanya payment yang berhasil yang bisa direfund'})
        
        # Create refund record (you might want to create a separate Refund model)
        # For now, we'll just change the status
        payment.status = 'refunded'
        payment.verified_by = session.get('username')
        payment.verified_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Payment berhasil direfund'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@admin_bp.route('/payment/<int:payment_id>/update-status', methods=['POST'])
@admin_required
def update_payment_status(payment_id):
    """Update payment status directly"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'message': 'Status tidak boleh kosong'})
        
        payment = Payment.query.get_or_404(payment_id)
        old_status = payment.status
        
        # Update payment status
        payment.status = new_status
        payment.verified_by = session.get('username')
        payment.verified_at = datetime.utcnow()
        
        # Jika status berubah ke success, tambahkan kredit ke user dan upgrade ke premium
        if new_status == 'success' and old_status != 'success':
            user = payment.order.user
            product = payment.order.product
            if user and product:
                user.kredit += product.kredit
                # Upgrade user dari free ke premium
                if user.role == 'free':
                    user.role = 'premium'
            
            # Update order status
            payment.order.status = 'paid'
        
        # Jika status berubah dari success ke status lain, kurangi kredit dan downgrade ke free (untuk refund)
        elif old_status == 'success' and new_status != 'success':
            user = payment.order.user
            product = payment.order.product
            if user and product:
                user.kredit = max(0, user.kredit - product.kredit)  # Pastikan kredit tidak negatif
                # Downgrade user dari premium ke free jika kredit habis
                if user.kredit == 0 and user.role == 'premium':
                    user.role = 'free'
            
            # Update order status
            payment.order.status = 'pending'
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Status payment berhasil diubah dari {old_status} ke {new_status}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@admin_bp.route('/upload/proof-image', methods=['POST'])
@admin_required
def upload_proof_image():
    """Upload proof image for payment"""
    try:
        if 'proof_image' not in request.files:
            return jsonify({'success': False, 'message': 'Tidak ada file yang dipilih'})
        
        file = request.files['proof_image']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Tidak ada file yang dipilih'})
        
        if file and allowed_file(file.filename):
            # Create upload directory if it doesn't exist
            upload_path = os.path.join(current_app.root_path, UPLOAD_FOLDER)
            os.makedirs(upload_path, exist_ok=True)
            
            # Generate secure filename
            filename = secure_filename(file.filename)
            # Add timestamp to avoid conflicts
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{timestamp}{ext}"
            
            # Save file
            file_path = os.path.join(upload_path, filename)
            file.save(file_path)
            
            # Return relative URL
            relative_url = f"/{UPLOAD_FOLDER}/{filename}"
            
            return jsonify({
                'success': True, 
                'message': 'File berhasil diupload',
                'file_url': relative_url
            })
        else:
            return jsonify({'success': False, 'message': 'Format file tidak didukung. Gunakan PNG, JPG, JPEG, GIF, atau WEBP'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# ==================== USER CRUD ROUTES ====================

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    """Tambah user baru"""
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role', 'free')
            
            # Validate required fields
            if not username or not email or not password:
                flash('Username, email, dan password harus diisi!', 'error')
                return redirect(url_for('admin.add_user'))
            
            # Check if username or email already exists
            if User.query.filter_by(username=username).first():
                flash('Username sudah digunakan!', 'error')
                return redirect(url_for('admin.add_user'))
            
            if User.query.filter_by(email=email).first():
                flash('Email sudah digunakan!', 'error')
                return redirect(url_for('admin.add_user'))
            
            # Create new user
            user = User(
                username=username,
                email=email,
                role=role
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            flash('User berhasil ditambahkan!', 'success')
            return redirect(url_for('admin.users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('admin.add_user'))
    
    return render_template('admin/add_user.html')

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit user"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            role = request.form.get('role')
            password = request.form.get('password')
            kredit = request.form.get('kredit')
            
            # Validate required fields
            if not username or not email:
                flash('Username dan email harus diisi!', 'error')
                return redirect(url_for('admin.edit_user', user_id=user_id))
            
            # Validate kredit field
            if kredit is not None:
                try:
                    kredit_value = int(kredit)
                    if kredit_value < 0:
                        flash('Kredit tidak boleh negatif!', 'error')
                        return redirect(url_for('admin.edit_user', user_id=user_id))
                except ValueError:
                    flash('Kredit harus berupa angka!', 'error')
                    return redirect(url_for('admin.edit_user', user_id=user_id))
            else:
                kredit_value = user.kredit  # Keep current value if not provided
            
            # Check if username or email already exists (excluding current user)
            existing_user = User.query.filter_by(username=username).first()
            if existing_user and existing_user.id != user_id:
                flash('Username sudah digunakan!', 'error')
                return redirect(url_for('admin.edit_user', user_id=user_id))
            
            existing_email = User.query.filter_by(email=email).first()
            if existing_email and existing_email.id != user_id:
                flash('Email sudah digunakan!', 'error')
                return redirect(url_for('admin.edit_user', user_id=user_id))
            
            # Update user
            user.username = username
            user.email = email
            user.role = role
            user.kredit = kredit_value
            
            if password:
                user.set_password(password)
            
            db.session.commit()
            
            flash('User berhasil diupdate!', 'success')
            return redirect(url_for('admin.users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('admin.edit_user', user_id=user_id))
    
    return render_template('admin/user_edit.html', user=user)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Hapus user"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent admin from deleting themselves
        if user.id == session.get('user_id'):
            return jsonify({'success': False, 'message': 'Tidak dapat menghapus akun sendiri'})
        
        # Delete user and related data
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'User berhasil dihapus'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# ==================== PRODUCT CRUD ROUTES ====================

@admin_bp.route('/products')
@admin_required
def products():
    """Daftar semua products"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get filter parameters
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    sort = request.args.get('sort', 'newest')
    
    # Build query
    query = Product.query
    
    # Apply search filter
    if search:
        query = query.filter(Product.name.contains(search))
    
    # Apply status filter
    if status == 'active':
        query = query.filter(Product.is_active == True)
    elif status == 'inactive':
        query = query.filter(Product.is_active == False)
    
    # Apply sorting
    if sort == 'newest':
        query = query.order_by(Product.created_at.desc())
    elif sort == 'oldest':
        query = query.order_by(Product.created_at.asc())
    elif sort == 'name_asc':
        query = query.order_by(Product.name.asc())
    elif sort == 'name_desc':
        query = query.order_by(Product.name.desc())
    elif sort == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.created_at.desc())
    
    products = query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    return render_template('admin/products.html', products=products)

@admin_bp.route('/products/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    """Tambah product baru"""
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            price = request.form.get('price')
            kredit = request.form.get('kredit')
            
            # Validate required fields
            if not name or not price:
                flash('Nama dan harga harus diisi!', 'error')
                return redirect(url_for('admin.add_product'))
            
            # Create new product
            product = Product(
                name=name,
                price=int(price),
                kredit=int(kredit) if kredit else 0
            )
            
            db.session.add(product)
            db.session.commit()
            
            flash('Product berhasil ditambahkan!', 'success')
            return redirect(url_for('admin.products'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('admin.add_product'))
    
    return render_template('admin/add_product.html')

@admin_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    """Edit product"""
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            price = request.form.get('price')
            kredit = request.form.get('kredit')
            
            # Validate required fields
            if not name or not price:
                flash('Nama dan harga harus diisi!', 'error')
                return redirect(url_for('admin.edit_product', product_id=product_id))
            
            # Update product
            product.name = name
            product.price = int(price)
            product.kredit = int(kredit) if kredit else 0
            
            db.session.commit()
            
            flash('Product berhasil diupdate!', 'success')
            return redirect(url_for('admin.products'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('admin.edit_product', product_id=product_id))
    
    return render_template('admin/edit_product.html', product=product)

@admin_bp.route('/products/<int:product_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_product_status(product_id):
    """Toggle status product (aktif/nonaktif)"""
    try:
        product = Product.query.get_or_404(product_id)
        
        # Toggle status
        product.is_active = not product.is_active
        db.session.commit()
        
        status_text = 'diaktifkan' if product.is_active else 'dinonaktifkan'
        return jsonify({'success': True, 'message': f'Product berhasil {status_text}'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@admin_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@admin_required
def delete_product(product_id):
    """Hapus product"""
    try:
        product = Product.query.get_or_404(product_id)
        
        # Check if product has orders
        if Order.query.filter_by(product_id=product_id).first():
            return jsonify({'success': False, 'message': 'Tidak dapat menghapus product yang sudah memiliki order'})
        
        db.session.delete(product)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Product berhasil dihapus'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# ==================== ORDER CRUD ROUTES ====================

@admin_bp.route('/orders')
@admin_required
def orders():
    """Daftar semua orders"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filter
    status_filter = request.args.get('status', '')
    
    query = Order.query.join(User).join(Product)
    
    if status_filter:
        query = query.filter(Order.status == status_filter)
    
    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    return render_template('admin/orders.html', orders=orders, status_filter=status_filter)

@admin_bp.route('/orders/add', methods=['GET', 'POST'])
@admin_required
def add_order():
    """Tambah order baru"""
    if request.method == 'POST':
        try:
            user_id = request.form.get('user_id')
            product_id = request.form.get('product_id')
            total_amount = request.form.get('total_amount')
            status = request.form.get('status', 'pending')
            
            # Validate required fields
            if not user_id or not product_id or not total_amount:
                flash('User, product, dan total amount harus diisi!', 'error')
                return redirect(url_for('admin.add_order'))
            
            # Check if user and product exist
            user = User.query.get(user_id)
            if not user:
                flash('User tidak ditemukan!', 'error')
                return redirect(url_for('admin.add_order'))
            
            product = Product.query.get(product_id)
            if not product:
                flash('Product tidak ditemukan!', 'error')
                return redirect(url_for('admin.add_order'))
            
            # Create new order
            order = Order(
                user_id=int(user_id),
                product_id=int(product_id),
                total_amount=int(total_amount),
                status=status
            )
            
            # Status paid akan langsung menambahkan kredit ke user
            if status == 'paid':
                # Tambahkan kredit ke user
                user = User.query.get(user_id)
                if user:
                    user.kredit += product.kredit
            
            db.session.add(order)
            db.session.commit()
            
            flash('Order berhasil ditambahkan!', 'success')
            return redirect(url_for('admin.orders'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('admin.add_order'))
    
    # GET request - show form
    users = User.query.all()
    products = Product.query.all()
    return render_template('admin/add_order.html', users=users, products=products)

@admin_bp.route('/orders/<int:order_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_order(order_id):
    """Edit order"""
    order = Order.query.get_or_404(order_id)
    
    if request.method == 'POST':
        try:
            user_id = request.form.get('user_id')
            product_id = request.form.get('product_id')
            total_amount = request.form.get('total_amount')
            status = request.form.get('status')
            
            # Validate required fields
            if not user_id or not product_id or not total_amount:
                flash('User, product, dan total amount harus diisi!', 'error')
                return redirect(url_for('admin.edit_order', order_id=order_id))
            
            # Update order
            order.user_id = int(user_id)
            order.product_id = int(product_id)
            order.total_amount = int(total_amount)
            order.status = status
            
            # Update kredit if status changed to paid
            if status == 'paid' and order.status != 'paid':
                product = Product.query.get(product_id)
                user = User.query.get(order.user_id)
                if user and product:
                    user.kredit += product.kredit
            
            db.session.commit()
            
            flash('Order berhasil diupdate!', 'success')
            return redirect(url_for('admin.orders'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('admin.edit_order', order_id=order_id))
    
    # GET request - show form
    users = User.query.all()
    products = Product.query.all()
    return render_template('admin/edit_order.html', order=order, users=users, products=products)

@admin_bp.route('/orders/<int:order_id>/delete', methods=['POST'])
@admin_required
def delete_order(order_id):
    """Hapus order"""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Check if order has payments
        if Payment.query.filter_by(order_id=order_id).first():
            return jsonify({'success': False, 'message': 'Tidak dapat menghapus order yang sudah memiliki payment'})
        
        db.session.delete(order)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Order berhasil dihapus'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# ==================== CONTENT CRUD ROUTES ====================

@admin_bp.route('/content/images')
@admin_required
def content_images():
    """Daftar semua images"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    images = Image.query.join(User).order_by(Image.created_at.desc()).paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    return render_template('admin/content_images.html', images=images)

@admin_bp.route('/content/videos')
@admin_required
def content_videos():
    """Daftar semua videos"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    videos = Video.query.join(User).order_by(Video.created_at.desc()).paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    return render_template('admin/content_videos.html', videos=videos)

@admin_bp.route('/content/songs')
@admin_required
def content_songs():
    """Daftar semua songs"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    songs = Song.query.join(User).order_by(Song.created_at.desc()).paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    return render_template('admin/content_songs.html', songs=songs)

@admin_bp.route('/content/images/<int:image_id>/delete', methods=['POST'])
@admin_required
def delete_image(image_id):
    """Hapus image"""
    try:
        image = Image.query.get_or_404(image_id)
        
        db.session.delete(image)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Image berhasil dihapus'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@admin_bp.route('/content/videos/<int:video_id>/delete', methods=['POST'])
@admin_required
def delete_video(video_id):
    """Hapus video"""
    try:
        video = Video.query.get_or_404(video_id)
        
        db.session.delete(video)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Video berhasil dihapus'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@admin_bp.route('/content/songs/<int:song_id>/delete', methods=['POST'])
@admin_required
def delete_song(song_id):
    """Hapus song"""
    try:
        song = Song.query.get_or_404(song_id)
        
        db.session.delete(song)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Song berhasil dihapus'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@admin_bp.route('/analytics')
@admin_required
def analytics():
    # User growth chart data (30 hari terakhir)
    dates = []
    user_counts = []
    
    for i in range(30):
        date = datetime.utcnow() - timedelta(days=i)
        count = User.query.filter(
            User.created_at <= date
        ).count()
        dates.append(date.strftime('%Y-%m-%d'))
        user_counts.append(count)
    
    dates.reverse()
    user_counts.reverse()
    
    # Content creation chart data
    content_data = {
        'images': Image.query.count(),
        'videos': Video.query.count(),
        'songs': Song.query.count(),
        'video_iklan': VideoIklan.query.count()
    }
    
    # Revenue data (30 hari terakhir)
    revenue_dates = []
    revenue_amounts = []
    
    for i in range(30):
        date = datetime.utcnow() - timedelta(days=i)
        revenue = 0  # Order functionality removed
        
        revenue_dates.append(date.strftime('%Y-%m-%d'))
        revenue_amounts.append(revenue)
    
    revenue_dates.reverse()
    revenue_amounts.reverse()
    
    return render_template('admin/analytics.html',
                         dates=json.dumps(dates),
                         user_counts=json.dumps(user_counts),
                         content_data=content_data,
                         revenue_dates=json.dumps(revenue_dates),
                         revenue_amounts=json.dumps(revenue_amounts))

@admin_bp.route('/settings')
@admin_required
def settings():
    return render_template('admin/settings.html')

@admin_bp.route('/api/stats')
@admin_required
def api_stats():
    """API endpoint untuk mendapatkan statistik real-time"""
    try:
        # Real-time stats
        online_users = User.query.filter(
            User.last_seen >= datetime.utcnow() - timedelta(minutes=5)
        ).count() if hasattr(User, 'last_seen') else 0
        
        today_revenue = 0  # Order functionality removed
        today_orders = 0   # Order functionality removed
        
        return jsonify({
            'success': True,
            'data': {
                'online_users': online_users,
                'today_revenue': today_revenue,
                'today_orders': today_orders
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/monitoring-post')
@admin_required
def monitoring_post():
    """Halaman monitoring post - mengambil data dari postingan yang sudah ada"""
    try:
        # Helper: determine if a content is deactivated
        def is_deactivated(content_type, content_obj, content_id_str):
            # Prefer model's is_active when available
            if hasattr(content_obj, 'is_active') and getattr(content_obj, 'is_active') is not None:
                return not bool(getattr(content_obj, 'is_active'))
            # Fallback to ModerationAction record
            action = ModerationAction.query.filter_by(
                content_type=content_type,
                content_id=content_id_str,
                action='deactivate'
            ).first()
            return bool(action and action.active)

        # Helper: determine if a content has been reported
        def is_reported(content_type, content_id_str):
            action = ModerationAction.query.filter_by(
                content_type=content_type,
                content_id=content_id_str,
                action='report'
            ).first()
            return bool(action and action.active)
        # Ambil data langsung dari tabel seperti di home page
        images = Image.query.order_by(Image.created_at.desc()).all()
        videos = Video.query.order_by(Video.created_at.desc()).all()
        songs = Song.query.order_by(Song.created_at.desc()).all()
        video_iklan = VideoIklan.query.order_by(VideoIklan.created_at.desc()).all()
        
        posts = []
        total_posts = 0
        violating_posts = 0
        good_posts = 0
        recommended_posts = 0
        
        # Process Images
        for img in images:
            user = User.query.get(img.user_id) if img.user_id else None
            if user:
                if is_deactivated('image', img, str(img.id)):
                    continue
                status_value = 'good'
                if is_reported('image', str(img.id)):
                    status_value = 'reported'
                posts.append({
                    'id': f'img_{img.id}',
                    'user_id': user.id,
                    'title': f'AI Generated Image - {img.caption[:30] if img.caption else "Untitled"}...',
                    'content': img.caption or 'Image generated by AI',
                    'content_type': 'image',
                    'content_id': str(img.id),
                    'status': status_value,  # Adjusted by moderation state
                    'created_at': img.created_at or datetime.now(),
                    'user': user
                })
                total_posts += 1
                good_posts += 1
        
        # Process Videos
        for vid in videos:
            user = User.query.get(vid.user_id) if vid.user_id else None
            if user:
                if is_deactivated('video', vid, str(vid.id)):
                    continue
                status_value = 'good'
                if is_reported('video', str(vid.id)):
                    status_value = 'reported'
                posts.append({
                    'id': f'vid_{vid.id}',
                    'user_id': user.id,
                    'title': f'AI Generated Video - {vid.caption[:30] if vid.caption else "Untitled"}...',
                    'content': vid.caption or 'Video generated by AI',
                    'content_type': 'video',
                    'content_id': str(vid.id),
                    'status': status_value,
                    'created_at': vid.created_at or datetime.now(),
                    'user': user
                })
                total_posts += 1
                good_posts += 1
        
        # Process Songs
        for song in songs:
            user = User.query.get(song.user_id) if song.user_id else None
            if user:
                if is_deactivated('song', song, str(song.id)):
                    continue
                status_value = 'recommended'
                if is_reported('song', str(song.id)):
                    status_value = 'reported'
                posts.append({
                    'id': f'song_{song.id}',
                    'user_id': user.id,
                    'title': f'AI Generated Song - {song.title[:30] if song.title else "Untitled"}...',
                    'content': song.title or 'Song generated by AI',
                    'content_type': 'song',
                    'content_id': str(song.id),
                    'status': status_value,
                    'created_at': song.created_at or datetime.now(),
                    'user': user
                })
                total_posts += 1
                recommended_posts += 1
        
        # Process Video Iklan
        for vik in video_iklan:
            user = User.query.get(vik.user_id) if vik.user_id else None
            if user:
                if is_deactivated('video_iklan', vik, str(vik.id)):
                    continue
                status_value = 'good'
                if is_reported('video_iklan', str(vik.id)):
                    status_value = 'reported'
                posts.append({
                    'id': f'vik_{vik.id}',
                    'user_id': user.id,
                    'title': f'AI Generated Video Iklan - {vik.caption[:30] if vik.caption else "Untitled"}...',
                    'content': vik.caption or 'Video iklan generated by AI',
                    'content_type': 'video_iklan',
                    'content_id': str(vik.id),
                    'status': status_value,
                    'created_at': vik.created_at or datetime.now(),
                    'user': user
                })
                total_posts += 1
                good_posts += 1
        
        # Sort posts by created_at (newest first)
        posts.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Filter berdasarkan request parameters
        status_filter = request.args.get('status', 'all')
        content_type_filter = request.args.get('content_type', 'all')
        user_filter = request.args.get('user', 'all')
        date_filter = request.args.get('date', 'all')
        
        if status_filter != 'all':
            posts = [p for p in posts if p['status'] == status_filter]
        
        if content_type_filter != 'all':
            posts = [p for p in posts if p['content_type'] == content_type_filter]
        
        if user_filter != 'all':
            posts = [p for p in posts if p['user'].username == user_filter]
        
        if date_filter != 'all':
            now = datetime.now()
            if date_filter == 'today':
                posts = [p for p in posts if p['created_at'].date() == now.date()]
            elif date_filter == 'week':
                week_ago = now - timedelta(days=7)
                posts = [p for p in posts if p['created_at'] >= week_ago]
            elif date_filter == 'month':
                month_ago = now - timedelta(days=30)
                posts = [p for p in posts if p['created_at'] >= month_ago]
        
        # Update stats berdasarkan filter
        if status_filter == 'all' and content_type_filter == 'all' and user_filter == 'all' and date_filter == 'all':
            # Gunakan stats asli jika tidak ada filter
            stats = {
                'total_posts': total_posts,
                'violating_posts': violating_posts,
                'good_posts': good_posts,
                'recommended_posts': recommended_posts
            }
        else:
            # Hitung stats berdasarkan filter
            filtered_total = len(posts)
            filtered_violating = len([p for p in posts if p['status'] == 'violating'])
            filtered_good = len([p for p in posts if p['status'] == 'good'])
            filtered_recommended = len([p for p in posts if p['status'] == 'recommended'])
            
            stats = {
                'total_posts': filtered_total,
                'violating_posts': filtered_violating,
                'good_posts': filtered_good,
                'recommended_posts': filtered_recommended
            }
        
        return render_template('admin/monitoring_post.html', posts=posts, stats=stats)
        
    except Exception as e:
        print(f"Error in monitoring_post: {e}")
        # Fallback: return empty data
        stats = {
            'total_posts': 0, 'violating_posts': 0, 'good_posts': 0, 'recommended_posts': 0
        }
        return render_template('admin/monitoring_post.html', posts=[], stats=stats)

@admin_bp.route('/api/favorite/toggle', methods=['POST'])
@admin_required
def toggle_favorite():
    """API endpoint untuk toggle favorite status"""
    try:
        data = request.get_json()
        content_type = data.get('content_type')
        content_id = data.get('content_id')
        reason = data.get('reason', '')
        
        # Validate input
        if not content_type or not content_id:
            return jsonify({'success': False, 'error': 'Missing content_type or content_id'})
        
        # Get content based on type
        if content_type == 'image':
            content = Image.query.get(content_id)
        elif content_type == 'video':
            content = Video.query.get(content_id)
        elif content_type == 'song':
            content = Song.query.get(content_id)
        else:
            return jsonify({'success': False, 'error': 'Invalid content_type'})
        
        if not content:
            return jsonify({'success': False, 'error': 'Content not found'})
        
        # Toggle favorite status
        content.is_favorite = not content.is_favorite
        
        # Update whitelist reason if provided
        if reason:
            content.whitelist_reason = reason
        elif not content.is_favorite:
            # Clear reason when removing from favorite
            content.whitelist_reason = None
        
        # Save to database
        db.session.commit()
        
        return jsonify({
            'success': True,
            'is_favorite': content.is_favorite,
            'message': f'Content {"added to" if content.is_favorite else "removed from"} favorites'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/api/content/view', methods=['POST'])
def increment_view():
    """Increment view count for content"""
    try:
        data = request.get_json()
        content_type = data.get('content_type')
        content_id = data.get('content_id')
        
        if not content_type or not content_id:
            return jsonify({'success': False, 'error': 'Missing content_type or content_id'})
        
        # Get content and increment view count
        if content_type == 'image':
            content = Image.query.get(content_id)
        elif content_type == 'video':
            content = Video.query.get(content_id)
        elif content_type == 'song':
            content = Song.query.get(content_id)
        else:
            return jsonify({'success': False, 'error': 'Invalid content_type'})
        
        if not content:
            return jsonify({'success': False, 'error': 'Content not found'})
        
        # Increment view count
        if hasattr(content, 'view_count'):
            content.view_count = (content.view_count or 0) + 1
        else:
            # Fallback if view_count column doesn't exist
            content.view_count = 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'view_count': content.view_count,
            'message': 'View count incremented'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/api/favorite/export', methods=['GET'])
@admin_required
def export_favorites():
    """Export favorite content to CSV"""
    try:
        # Get filter parameters
        filter_type = request.args.get('filter_type', 'all')
        content_type_filter = request.args.get('content_type', 'all')
        favorite_filter = request.args.get('favorite', 'all')
        
        # Get all content
        images = Image.query.all()
        videos = Video.query.all()
        songs = Song.query.all()
        
        all_content = []
        
        # Process Images
        for img in images:
            like_count = Like.query.filter_by(
                content_type='image', 
                content_id=str(img.id)
            ).count()
            
            # Gunakan field view_count yang sudah ada di model
            view_count = getattr(img, 'view_count', 0) or 0
            user = User.query.get(img.user_id) if img.user_id else None
            
            all_content.append({
                'id': f'img_{img.id}',
                'content_id': img.id,
                'content_type': 'image',
                'title': img.caption or f'AI Generated Image {img.id}',
                'url': img.image_url,
                'user': user.username if user else 'Unknown',
                'like_count': like_count,
                'view_count': view_count,
                'is_favorite': img.is_favorite,
                'whitelist_reason': img.whitelist_reason,
                'created_at': img.created_at or datetime.now(),
                'engagement_score': like_count + (view_count * 0.1)
            })
        
        # Process Videos
        for vid in videos:
            like_count = Like.query.filter_by(
                content_type='video', 
                content_id=str(vid.id)
            ).count()
            
            # Gunakan field view_count yang sudah ada di model
            view_count = getattr(vid, 'view_count', 0) or 0
            user = User.query.get(vid.user_id) if vid.user_id else None
            
            all_content.append({
                'id': f'vid_{vid.id}',
                'content_id': vid.id,
                'content_type': 'video',
                'title': vid.caption or f'AI Generated Video {vid.id}',
                'url': vid.video_url,
                'user': user.username if user else 'Unknown',
                'like_count': like_count,
                'view_count': view_count,
                'is_favorite': vid.is_favorite,
                'whitelist_reason': vid.whitelist_reason,
                'created_at': vid.created_at or datetime.now(),
                'engagement_score': like_count + (view_count * 0.1)
            })
        
        # Process Songs
        for song in songs:
            like_count = Like.query.filter_by(
                content_type='song', 
                content_id=str(song.id)
            ).count()
            
            # Gunakan field view_count yang sudah ada di model
            view_count = getattr(song, 'view_count', 0) or 0
            user = User.query.get(song.user_id) if song.user_id else None
            
            all_content.append({
                'id': f'song_{song.id}',
                'content_id': song.id,
                'content_type': 'song',
                'title': song.title or f'AI Generated Song {song.id}',
                'url': song.audio_url,
                'user': user.username if user else 'Unknown',
                'like_count': like_count,
                'view_count': view_count,
                'is_favorite': song.is_favorite,
                'whitelist_reason': song.whitelist_reason,
                'created_at': song.created_at or datetime.now(),
                'engagement_score': like_count + (view_count * 0.1)
            })
        
        # Apply filters
        if content_type_filter != 'all':
            all_content = [c for c in all_content if c['content_type'] == content_type_filter]
        
        if favorite_filter == 'favorite':
            all_content = [c for c in all_content if c['is_favorite']]
        elif favorite_filter == 'not_favorite':
            all_content = [c for c in all_content if not c['is_favorite']]
        
        if filter_type == 'most_likes':
            all_content.sort(key=lambda x: x['like_count'], reverse=True)
            all_content = all_content[:50]
        elif filter_type == 'most_views':
            all_content.sort(key=lambda x: x['view_count'], reverse=True)
            all_content = all_content[:50]
        elif filter_type == 'manual_whitelist':
            all_content = [c for c in all_content if c['is_favorite'] and c['whitelist_reason']]
        elif filter_type == 'high_engagement':
            all_content = [c for c in all_content if c['engagement_score'] >= 10]
        elif filter_type == 'auto_favorite':
            all_content = [c for c in all_content if c['like_count'] >= 5 or c['view_count'] >= 20]
        
        # Generate CSV
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Content Type', 'Content ID', 'Title', 'User', 'Likes', 'Views', 
            'Engagement Score', 'Is Favorite', 'Whitelist Reason', 'Created At', 'URL'
        ])
        
        # Write data
        for item in all_content:
            writer.writerow([
                item['content_type'],
                item['content_id'],
                item['title'],
                item['user'],
                item['like_count'],
                item['view_count'],
                f"{item['engagement_score']:.1f}",
                'Yes' if item['is_favorite'] else 'No',
                item['whitelist_reason'] or '',
                item['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                item['url']
            ])
        
        # Create response
        from flask import Response
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=favorites_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/api/favorite/bulk-action', methods=['POST'])
@admin_required
def bulk_favorite_action():
    """API endpoint untuk bulk favorite actions"""
    try:
        data = request.get_json()
        action = data.get('action')  # 'favorite' or 'unfavorite'
        content_ids = data.get('content_ids', [])
        reason = data.get('reason', '')
        
        if not action or not content_ids:
            return jsonify({'success': False, 'error': 'Missing action or content_ids'})
        
        success_count = 0
        error_count = 0
        
        for item in content_ids:
            content_type = item.get('content_type')
            content_id = item.get('content_id')
            
            if not content_type or not content_id:
                error_count += 1
                continue
            
            # Get content
            if content_type == 'image':
                content = Image.query.get(content_id)
            elif content_type == 'video':
                content = Video.query.get(content_id)
            elif content_type == 'song':
                content = Song.query.get(content_id)
            else:
                error_count += 1
                continue
            
            if not content:
                error_count += 1
                continue
            
            # Apply action
            if action == 'favorite':
                content.is_favorite = True
                if reason:
                    content.whitelist_reason = reason
            elif action == 'unfavorite':
                content.is_favorite = False
                content.whitelist_reason = None
            
            success_count += 1
        
        # Commit all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully processed {success_count} items, {error_count} errors',
            'success_count': success_count,
            'error_count': error_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/favorite-management')
@admin_required
def favorite_management():
    """Halaman manajemen favorite - mengelola konten favorite berdasarkan kriteria"""
    try:
        # Get filter type from request
        filter_type = request.args.get('filter_type', 'all')
        
        # Ambil semua konten dengan informasi like dan view
        images = Image.query.all()
        videos = Video.query.all()
        songs = Song.query.all()
        
        # Kumpulkan semua konten dalam satu list
        all_content = []
        
        # Process Images
        for img in images:
            # Hitung jumlah like untuk image ini
            like_count = Like.query.filter_by(
                content_type='image', 
                content_id=str(img.id)
            ).count()
            
            # Gunakan field view_count yang sudah ada di model
            view_count = getattr(img, 'view_count', 0) or 0
            
            user = User.query.get(img.user_id) if img.user_id else None
            
            all_content.append({
                'id': f'img_{img.id}',
                'content_id': img.id,
                'content_type': 'image',
                'title': img.caption or f'AI Generated Image {img.id}',
                'url': img.image_url,
                'user': user,
                'like_count': like_count,
                'view_count': view_count,
                'is_favorite': img.is_favorite,
                'whitelist_reason': img.whitelist_reason,
                'created_at': img.created_at or datetime.now(),
                'engagement_score': like_count + (view_count * 0.1)  # Scoring system
            })
        
        # Process Videos
        for vid in videos:
            like_count = Like.query.filter_by(
                content_type='video', 
                content_id=str(vid.id)
            ).count()
            
            # Gunakan field view_count yang sudah ada di model
            view_count = getattr(vid, 'view_count', 0) or 0
            
            user = User.query.get(vid.user_id) if vid.user_id else None
            
            all_content.append({
                'id': f'vid_{vid.id}',
                'content_id': vid.id,
                'content_type': 'video',
                'title': vid.caption or f'AI Generated Video {vid.id}',
                'url': vid.video_url,
                'user': user,
                'like_count': like_count,
                'view_count': view_count,
                'is_favorite': vid.is_favorite,
                'whitelist_reason': vid.whitelist_reason,
                'created_at': vid.created_at or datetime.now(),
                'engagement_score': like_count + (view_count * 0.1)
            })
        
        # Process Songs
        for song in songs:
            like_count = Like.query.filter_by(
                content_type='song', 
                content_id=str(song.id)
            ).count()
            
            # Gunakan field view_count yang sudah ada di model
            view_count = getattr(song, 'view_count', 0) or 0
            
            user = User.query.get(song.user_id) if song.user_id else None
            
            all_content.append({
                'id': f'song_{song.id}',
                'content_id': song.id,
                'content_type': 'song',
                'title': song.title or f'AI Generated Song {song.id}',
                'url': song.audio_url,
                'user': user,
                'like_count': like_count,
                'view_count': view_count,
                'is_favorite': song.is_favorite,
                'whitelist_reason': song.whitelist_reason,
                'created_at': song.created_at or datetime.now(),
                'engagement_score': like_count + (view_count * 0.1)
            })
        
        # Filter berdasarkan request parameters
        sort_by = request.args.get('sort_by', 'created_at')
        content_type_filter = request.args.get('content_type', 'all')
        favorite_filter = request.args.get('favorite', 'all')
        
        # Apply content type filter
        if content_type_filter != 'all':
            all_content = [c for c in all_content if c['content_type'] == content_type_filter]
        
        # Apply favorite filter
        if favorite_filter == 'favorite':
            all_content = [c for c in all_content if c['is_favorite']]
        elif favorite_filter == 'not_favorite':
            all_content = [c for c in all_content if not c['is_favorite']]
        
        # Apply filter type (most likes, most views, manual whitelist)
        if filter_type == 'most_likes':
            # Sort by likes and take top 50
            all_content.sort(key=lambda x: x['like_count'], reverse=True)
            all_content = all_content[:50]
        elif filter_type == 'most_views':
            # Sort by views and take top 50
            all_content.sort(key=lambda x: x['view_count'], reverse=True)
            all_content = all_content[:50]
        elif filter_type == 'manual_whitelist':
            # Show only manually whitelisted content
            all_content = [c for c in all_content if c['is_favorite'] and c['whitelist_reason']]
        elif filter_type == 'high_engagement':
            # Show content with high engagement score
            all_content = [c for c in all_content if c['engagement_score'] >= 10]
        elif filter_type == 'auto_favorite':
            # Show content that should be auto-favorited based on criteria
            all_content = [c for c in all_content if c['like_count'] >= 5 or c['view_count'] >= 20]
        
        # Sort content
        if sort_by == 'likes':
            all_content.sort(key=lambda x: x['like_count'], reverse=True)
        elif sort_by == 'views':
            all_content.sort(key=lambda x: x['view_count'], reverse=True)
        elif sort_by == 'engagement':
            all_content.sort(key=lambda x: x['engagement_score'], reverse=True)
        elif sort_by == 'created_at':
            all_content.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = 20
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_content = all_content[start_idx:end_idx]
        
        # Calculate stats
        total_content = len(all_content)
        favorite_content = len([c for c in all_content if c['is_favorite']])
        high_engagement = len([c for c in all_content if c['engagement_score'] >= 10])
        
        stats = {
            'total_content': total_content,
            'favorite_content': favorite_content,
            'high_engagement': high_engagement,
            'images': len([c for c in all_content if c['content_type'] == 'image']),
            'videos': len([c for c in all_content if c['content_type'] == 'video']),
            'songs': len([c for c in all_content if c['content_type'] == 'song'])
        }
        
        return render_template('admin/favorite_management.html', 
                             content=paginated_content, 
                             stats=stats,
                             sort_by=sort_by,
                             content_type_filter=content_type_filter,
                             favorite_filter=favorite_filter,
                             page=page,
                             total_pages=(total_content + per_page - 1) // per_page)
        
    except Exception as e:
        print(f"Error in favorite_management: {e}")
        stats = {
            'total_content': 0, 'favorite_content': 0, 'high_engagement': 0,
            'images': 0, 'videos': 0, 'songs': 0
        }
        return render_template('admin/favorite_management.html', 
                             content=[], 
                             stats=stats,
                             sort_by='created_at',
                             content_type_filter='all',
                             favorite_filter='all',
                             page=1,
                             total_pages=1)








# ==============================
# APIs used by Monitoring Post
# ==============================

def _get_content_by_type_and_id(content_type: str, content_id: str):
    """Helper function to fetch content instance by type and id."""
    if content_type == 'image':
        return Image.query.get(content_id)
    if content_type == 'video':
        return Video.query.get(content_id)
    if content_type == 'song':
        return Song.query.get(content_id)
    if content_type == 'video_iklan':
        return VideoIklan.query.get(content_id)
    return None


@admin_bp.route('/api/content/detail', methods=['GET'])
@admin_required
def api_content_detail():
    """Return minimal details for a content item so the Edit modal can be prefilled."""
    content_type = request.args.get('content_type')
    content_id = request.args.get('content_id')

    if not content_type or not content_id:
        return jsonify({'success': False, 'error': 'Missing content_type or content_id'}), 400

    content = _get_content_by_type_and_id(content_type, content_id)
    if not content:
        return jsonify({'success': False, 'error': 'Content not found'}), 404

    # Normalize fields
    if content_type == 'song':
        title = getattr(content, 'title', '') or ''
        caption = getattr(content, 'lyrics', '') or ''
    else:
        title = getattr(content, 'caption', '') or ''
        caption = getattr(content, 'caption', '') or ''

    return jsonify({'success': True, 'data': {
        'content_type': content_type,
        'content_id': str(content_id),
        'title': title,
        'caption': caption
    }})


@admin_bp.route('/api/content/update', methods=['POST'])
@admin_required
def api_content_update():
    """Update editable fields for a content item from Monitoring Post page."""
    try:
        data = request.get_json() or {}
        content_type = data.get('content_type')
        content_id = data.get('content_id')
        title = (data.get('title') or '').strip()
        caption = (data.get('caption') or '').strip()

        if not content_type or not content_id:
            return jsonify({'success': False, 'error': 'Missing content_type or content_id'}), 400

        content = _get_content_by_type_and_id(content_type, content_id)
        if not content:
            return jsonify({'success': False, 'error': 'Content not found'}), 404

        # Apply updates per type while keeping schema intact
        if content_type == 'song':
            if title:
                content.title = title
            if caption:
                content.lyrics = caption
        else:
            if title or caption:
                content.caption = title or caption

        db.session.commit()
        return jsonify({'success': True, 'message': 'Content updated'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/content/delete', methods=['POST'])
@admin_required
def api_content_delete():
    """Delete a content item and related rows used in engagement.

    JSON body: { content_type, content_id }
    """
    try:
        data = request.get_json() or {}
        content_type = data.get('content_type')
        content_id = data.get('content_id')

        if not content_type or not content_id:
            return jsonify({'success': False, 'error': 'Missing content_type or content_id'}), 400

        content = _get_content_by_type_and_id(content_type, content_id)
        if not content:
            return jsonify({'success': False, 'error': 'Content not found'}), 404

        # Clean up likes/comments/view_counts referencing this content
        Like.query.filter_by(content_type=content_type, content_id=str(content_id)).delete()
        Comment.query.filter_by(content_type=content_type, content_id=str(content_id)).delete()
        ViewCount.query.filter_by(content_type=content_type, content_id=str(content_id)).delete()

        db.session.delete(content)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Content deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/content/deactivate', methods=['POST'])
@admin_required
def api_content_deactivate():
    """Toggle deactivate/activate for a content item and record the action."""
    try:
        data = request.get_json() or {}
        content_type = data.get('content_type')
        content_id = data.get('content_id')

        if not content_type or not content_id:
            return jsonify({'success': False, 'error': 'Missing content_type or content_id'}), 400

        content = _get_content_by_type_and_id(content_type, content_id)
        if not content:
            return jsonify({'success': False, 'error': 'Content not found'}), 404

        # Try to toggle is_active if exists, otherwise store in ModerationAction.active
        if hasattr(content, 'is_active'):
            content.is_active = not bool(getattr(content, 'is_active'))
            new_state = content.is_active
        else:
            # Ensure table exists (first run on new DB)
            try:
                ModerationAction.__table__.create(db.engine, checkfirst=True)
            except Exception:
                pass
            action = ModerationAction.query.filter_by(content_type=content_type, content_id=str(content_id), action='deactivate').first()
            if not action:
                action = ModerationAction(content_type=content_type, content_id=str(content_id), action='deactivate', active=True)
                db.session.add(action)
                new_state = False
            else:
                action.active = not action.active
                new_state = not action.active  # active False means deactivated

        db.session.commit()
        return jsonify({'success': True, 'deactivated': not new_state})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/content/report', methods=['POST'])
@admin_required
def api_content_report():
    """Create or update a report reason for a content item."""
    try:
        data = request.get_json() or {}
        content_type = data.get('content_type')
        content_id = data.get('content_id')
        reason = (data.get('reason') or '').strip()

        if not content_type or not content_id:
            return jsonify({'success': False, 'error': 'Missing content_type or content_id'}), 400
        if not reason:
            return jsonify({'success': False, 'error': 'Reason is required'}), 400

        # Ensure table exists before using it
        try:
            ModerationAction.__table__.create(db.engine, checkfirst=True)
        except Exception:
            pass
        action = ModerationAction.query.filter_by(content_type=content_type, content_id=str(content_id), action='report').first()
        if not action:
            action = ModerationAction(content_type=content_type, content_id=str(content_id), action='report', reason=reason, active=True)
            db.session.add(action)
        else:
            action.reason = reason
            action.active = True

        db.session.commit()
        return jsonify({'success': True, 'message': 'Report submitted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
