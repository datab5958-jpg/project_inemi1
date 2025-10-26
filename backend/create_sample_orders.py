#!/usr/bin/env python3
"""
Script untuk membuat sample data orders dan payments
"""

from app import app
from models import db, User, Product, Order, Payment
from datetime import datetime, date, timedelta
import random

def create_sample_orders():
    """Membuat sample data orders dan payments"""
    with app.app_context():
        try:
            print("🔄 Membuat sample data orders dan payments...")
            
            # Get users and products
            users = User.query.limit(5).all()
            products = Product.query.limit(3).all()
            
            if not users:
                print("❌ Tidak ada user untuk membuat sample data")
                return
                
            if not products:
                print("❌ Tidak ada product untuk membuat sample data")
                return
            
            # Create sample orders and payments
            for i in range(10):
                # Random user and product
                user = random.choice(users)
                product = random.choice(products)
                
                # Random amount
                amount = random.randint(50000, 500000)
                
                # Random status
                statuses = ['pending', 'paid', 'failed', 'cancelled']
                order_status = random.choice(statuses)
                
                # Create order
                order = Order(
                    user_id=user.id,
                    product_id=product.id,
                    total_amount=amount,
                    status=order_status
                )
                
                db.session.add(order)
                db.session.flush()  # Get the order_id
                
                # Create payment for this order
                payment_statuses = ['pending', 'success', 'failed']
                payment_status = random.choice(payment_statuses)
                
                payment = Payment(
                    order_id=order.order_id,
                    amount=amount,
                    method='bank_transfer',
                    proof_image=f'/uploads/proof_{i+1}.jpg' if payment_status == 'success' else None,
                    status=payment_status,
                    verified_by='admin' if payment_status == 'success' else None,
                    verified_at=datetime.utcnow() if payment_status == 'success' else None
                )
                
                db.session.add(payment)
            
            db.session.commit()
            print("✅ Sample data berhasil dibuat")
            
            # Show statistics
            total_orders = Order.query.count()
            total_payments = Payment.query.count()
            pending_payments = Payment.query.filter_by(status='pending').count()
            success_payments = Payment.query.filter_by(status='success').count()
            
            print(f"\n📊 Statistik:")
            print(f"  Total Orders: {total_orders}")
            print(f"  Total Payments: {total_payments}")
            print(f"  Pending Payments: {pending_payments}")
            print(f"  Success Payments: {success_payments}")
            
        except Exception as e:
            print(f"❌ Error creating sample data: {e}")
            db.session.rollback()

if __name__ == "__main__":
    create_sample_orders()
