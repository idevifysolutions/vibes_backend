# app/services/notification_service.py
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from app.models.inventory import InventoryAlert, AlertNotification
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.models.users import User
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Get email configuration from environment variables
EMAIL_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('SMTP_PORT', 587))
EMAIL_HOST_USER = os.getenv('SMTP_USERNAME')
EMAIL_HOST_PASSWORD = os.getenv('SMTP_PASSWORD')
EMAIL_FROM = os.getenv('SMTP_FROM_EMAIL')
# EMAIL_ENABLED = os.getenv('EMAIL_ENABLED', 'True') == 'True'


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
    
    def send_alert_notifications(self, alert: InventoryAlert):
        """Send notifications through all configured channels"""
        recipients = self._get_alert_recipients(alert)
        
        logger.info(f"Sending notifications for alert {alert.id} to {len(recipients)} recipients")
        
        for recipient in recipients:
            # In-app notification (always sent)
            self._create_in_app_notification(alert, recipient)
            
            # Email notification
            if recipient.email and self._should_send_email(alert, recipient):
                self._send_email_notification(alert, recipient)
            
            # SMS notification (optional)
            if recipient.mobile_no and self._should_send_sms(alert, recipient):
                self._send_sms_notification(alert, recipient)
    
    def _get_alert_recipients(self, alert: InventoryAlert) -> List[User]:
        """Determine who should receive this alert"""
        # Get users with inventory management permissions
        # Adjust based on your user/role system
        recipients = self.db.query(User).filter(
            User.tenant_id == alert.tenant_id,
            User.is_active == True,
            # Add role-based filtering here
            # Example: User.role.in_(['admin', 'manager', 'inventory_manager'])
        ).all()
        
        logger.info(f"Found {len(recipients)} recipients for tenant {alert.tenant_id}")
        return recipients
    
    def _create_in_app_notification(self, alert: InventoryAlert, user: User):
        """Create in-app notification record"""
        try:
            notification = AlertNotification(
                tenant_id=alert.tenant_id,
                alert_id=alert.id,
                channel="in_app",
                recipient_user_id=user.id,
                status="sent",
                sent_at=datetime.now()
            )
            self.db.add(notification)
            self.db.commit()
            logger.debug(f"In-app notification created for user {user.id}")
        except Exception as e:
            logger.error(f"Failed to create in-app notification: {str(e)}")
            self.db.rollback()
    
    def _send_email_notification(self, alert: InventoryAlert, user: User):
        """Send email notification"""
        
        # Check if email is enabled
        # if not EMAIL_ENABLED:
        #     logger.warning("Email notifications are disabled in environment variables")
        #     return
        
        # Validate email configuration
        if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
            logger.error("Email credentials not configured. Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env")
            return
        
        try:
            logger.info(f"Attempting to send email to {user.email} for alert {alert.id}")
            
            # Build email message
            msg = MIMEMultipart()
            msg['From'] = EMAIL_FROM or EMAIL_HOST_USER
            msg['To'] = user.email
            msg['Subject'] = f"[{alert.priority.upper()}] {alert.alert_type.value.replace('_', ' ').title()}"
            
            # Create HTML body
            body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .header {{ background-color: #f8f9fa; padding: 20px; border-bottom: 3px solid #007bff; }}
                    .content {{ padding: 20px; }}
                    .alert-box {{ 
                        background-color: #fff3cd; 
                        border-left: 4px solid #ffc107; 
                        padding: 15px; 
                        margin: 20px 0; 
                    }}
                    .critical {{ background-color: #f8d7da; border-left-color: #dc3545; }}
                    .high {{ background-color: #fff3cd; border-left-color: #ffc107; }}
                    .medium {{ background-color: #d1ecf1; border-left-color: #17a2b8; }}
                    .detail {{ margin: 10px 0; }}
                    .label {{ font-weight: bold; color: #666; }}
                    .button {{ 
                        display: inline-block; 
                        padding: 10px 20px; 
                        background-color: #007bff; 
                        color: white; 
                        text-decoration: none; 
                        border-radius: 5px; 
                        margin: 20px 0; 
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>🔔 Inventory Alert Notification</h2>
                </div>
                <div class="content">
                    <div class="alert-box {alert.priority}">
                        <h3>{alert.message}</h3>
                    </div>
                    
                    <div class="detail">
                        <span class="label">Alert Type:</span> 
                        {alert.alert_type.value.replace('_', ' ').title()}
                    </div>
                    
                    <div class="detail">
                        <span class="label">Priority:</span> 
                        <strong>{alert.priority.upper()}</strong>
                    </div>
                    
                    <div class="detail">
                        <span class="label">Current Quantity:</span> 
                        {alert.current_quantity}
                    </div>
                    
                    <div class="detail">
                        <span class="label">Threshold Value:</span> 
                        {alert.threshold_value}
                    </div>
                    
                    {f'<div class="detail"><span class="label">Affected Dishes:</span> {alert.affected_dishes}</div>' if alert.affected_dishes else ''}
                    
                    <div class="alert-box">
                        <strong>📌 Suggested Action:</strong><br>
                        {alert.suggested_action}
                    </div>
                    
                    <a href="https://yourapp.com/alerts/{alert.id}" class="button">
                        View Alert Details
                    </a>
                    
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
                    
                    <p style="color: #666; font-size: 12px;">
                        This is an automated notification from your Inventory Management System.<br>
                        Alert generated on {alert.alert_date.strftime('%B %d, %Y at %I:%M %p')}
                    </p>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # Send email via SMTP
            logger.debug(f"Connecting to SMTP server {EMAIL_HOST}:{EMAIL_PORT}")
            server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
            server.starttls()
            
            logger.debug(f"Logging in as {EMAIL_HOST_USER}")
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            
            logger.debug(f"Sending message to {user.email}")
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✓ Email sent successfully to {user.email}")
            
            # Log successful delivery
            notification = AlertNotification(
                tenant_id=alert.tenant_id,
                alert_id=alert.id,
                channel="email",
                recipient_user_id=user.id,
                recipient_contact=user.email,
                status="sent",
                sent_at=datetime.now()
            )
            self.db.add(notification)
            self.db.commit()
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = "SMTP Authentication failed. Check your EMAIL_HOST_USER and EMAIL_HOST_PASSWORD"
            logger.error(f"✗ {error_msg}: {str(e)}")
            self._log_failed_notification(alert, user, "email", error_msg)
            
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error occurred: {str(e)}"
            logger.error(f"✗ Failed to send email to {user.email}: {error_msg}")
            self._log_failed_notification(alert, user, "email", error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"✗ Failed to send email to {user.email}: {error_msg}")
            self._log_failed_notification(alert, user, "email", error_msg)
    
    def _log_failed_notification(self, alert: InventoryAlert, user: User, channel: str, error_message: str):
        """Log failed notification delivery"""
        try:
            notification = AlertNotification(
                tenant_id=alert.tenant_id,
                alert_id=alert.id,
                channel=channel,
                recipient_user_id=user.id,
                recipient_contact=user.email if channel == "email" else user.mobile_no,
                status="failed",
                error_message=error_message,
                sent_at=datetime.now()
            )
            self.db.add(notification)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log notification failure: {str(e)}")
            self.db.rollback()
    
    def _send_sms_notification(self, alert: InventoryAlert, user: User):
        """Send SMS notification using Twilio or similar service"""
        # TODO: Implement SMS sending logic
        # Example using Twilio:
        # from twilio.rest import Client
        # client = Client(account_sid, auth_token)
        # message = client.messages.create(
        #     body=f"Alert: {alert.message}",
        #     from_='+1234567890',
        #     to=user.mobile_no
        # )
        logger.info(f"SMS notification not implemented yet for user {user.id}")
        pass
    
    def _should_send_email(self, alert: InventoryAlert, user: User) -> bool:
        """Check if email should be sent based on user preferences"""
        # Check if user has valid email
        if not user.email:
            return False
        
        # You can add more checks here:
        # - User email notification preferences
        # - Notification frequency limits
        # - Time-based restrictions (e.g., quiet hours)
        
        # For now, send email to all users with valid email addresses
        return True
    
    def _should_send_sms(self, alert: InventoryAlert, user: User) -> bool:
        """Check if SMS should be sent (typically only for critical alerts)"""
        # Only send SMS for critical priority alerts
        if alert.priority != "critical":
            return False
        
        # Check if user has valid mobile number
        if not user.mobile_no:
            return False
        
        # You can add more checks here:
        # - User SMS notification preferences
        # - SMS quota limits
        
        return True