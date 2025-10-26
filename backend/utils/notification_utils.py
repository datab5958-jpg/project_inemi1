import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import db, Notification
from datetime import datetime, timezone

def create_notification(sender_id, recipient_id, notification_type, content_type=None, content_id=None, text=None, comment_id=None):
    """Helper function to create notifications"""
    try:
        # For like notifications, we want to allow new notifications when user likes again
        # For other types, we check for duplicates within a time window
        if notification_type == 'like':
            # For likes, check if there's a recent like notification (within last 24 hours)
            from datetime import timedelta
            yesterday = datetime.now() - timedelta(days=1)
            
            existing = Notification.query.filter_by(
                sender_id=sender_id,
                recipient_id=recipient_id,
                notification_type=notification_type,
                content_type=content_type,
                content_id=content_id
            ).filter(Notification.created_at > yesterday).first()
        else:
            # For comments and replies, check for exact duplicates
            existing = Notification.query.filter_by(
                sender_id=sender_id,
                recipient_id=recipient_id,
                notification_type=notification_type,
                content_type=content_type,
                content_id=content_id,
                comment_id=comment_id
            ).first()
        
        if not existing:
            notification = Notification(
                sender_id=sender_id,
                recipient_id=recipient_id,
                notification_type=notification_type,
                content_type=content_type,
                content_id=content_id,
                comment_id=comment_id,
                text=text
            )
            db.session.add(notification)
            db.session.commit()
            print(f"Notification created successfully: {notification_type} from {sender_id} to {recipient_id}")
            return True
        else:
            print(f"Notification already exists: {notification_type} from {sender_id} to {recipient_id}")
            return False
    except Exception as e:
        print(f"Error creating notification: {e}")
        db.session.rollback()
        return False

def delete_notification(sender_id, recipient_id, notification_type, content_type=None, content_id=None, comment_id=None):
    """Helper function to delete notifications (e.g., when user unlikes content)"""
    try:
        notification = Notification.query.filter_by(
            sender_id=sender_id,
            recipient_id=recipient_id,
            notification_type=notification_type,
            content_type=content_type,
            content_id=content_id,
            comment_id=comment_id
        ).first()
        
        if notification:
            db.session.delete(notification)
            db.session.commit()
            print(f"Notification deleted successfully: {notification_type} from {sender_id} to {recipient_id}")
            return True
        else:
            print(f"No notification found to delete: {notification_type} from {sender_id} to {recipient_id}")
            return False
    except Exception as e:
        print(f"Error deleting notification: {e}")
        db.session.rollback()
        return False

def get_time_ago(datetime_obj):
    """Helper function to get time ago string"""
    if not datetime_obj:
        return "Baru saja"
    
    now = datetime.now(timezone.utc)
    if datetime_obj.tzinfo is None:
        datetime_obj = datetime_obj.replace(tzinfo=timezone.utc)
    
    diff = now - datetime_obj
    
    if diff.days > 0:
        return f"{diff.days} hari yang lalu"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} jam yang lalu"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} menit yang lalu"
    else:
        return "Baru saja"
