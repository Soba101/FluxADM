"""
Notification Service - Handle email, Slack, and other notifications
"""
import smtplib
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
import structlog
import requests

from config import get_settings

logger = structlog.get_logger(__name__)


class NotificationService:
    """
    Handle various types of notifications for FluxADM
    Supports email, Slack, and future notification channels
    """
    
    def __init__(self):
        self.settings = get_settings()
    
    async def send_cr_status_notification(self, cr_data: Dict[str, Any], 
                                        recipients: List[str], 
                                        notification_type: str = "status_update") -> bool:
        """
        Send change request status notification
        
        Args:
            cr_data: Change request information
            recipients: List of email addresses or user IDs
            notification_type: Type of notification (status_update, approval_request, etc.)
            
        Returns:
            Success status
        """
        try:
            # Prepare notification content
            subject, body = self._prepare_cr_notification_content(cr_data, notification_type)
            
            # Send email notifications
            email_success = await self._send_email_notifications(recipients, subject, body)
            
            # Send Slack notification if configured
            slack_success = True
            if self.settings.SLACK_WEBHOOK_URL:
                slack_success = await self._send_slack_notification(cr_data, notification_type)
            
            logger.info("CR notification sent", 
                       cr_id=cr_data.get('id'),
                       notification_type=notification_type,
                       recipients_count=len(recipients),
                       email_success=email_success,
                       slack_success=slack_success)
            
            return email_success and slack_success
            
        except Exception as e:
            logger.error("CR notification failed", 
                        cr_id=cr_data.get('id'),
                        notification_type=notification_type,
                        error=str(e))
            return False
    
    async def send_approval_request(self, cr_data: Dict[str, Any], 
                                  approver_emails: List[str], 
                                  approval_stage: Dict[str, Any]) -> bool:
        """Send approval request notification"""
        
        try:
            subject = f"Approval Required: {cr_data.get('title', 'Change Request')}"
            
            body = self._generate_approval_email_body(cr_data, approval_stage)
            
            success = await self._send_email_notifications(approver_emails, subject, body)
            
            # Send Slack notification for urgent requests
            if cr_data.get('priority') in ['high', 'critical'] and self.settings.SLACK_WEBHOOK_URL:
                await self._send_slack_approval_request(cr_data, approval_stage)
            
            return success
            
        except Exception as e:
            logger.error("Approval request notification failed", 
                        cr_id=cr_data.get('id'), 
                        error=str(e))
            return False
    
    async def send_quality_alert(self, cr_data: Dict[str, Any], 
                               quality_issues: List[Dict[str, Any]]) -> bool:
        """Send quality issue alert"""
        
        try:
            subject = f"Quality Issues Detected: {cr_data.get('title', 'Change Request')}"
            
            body = self._generate_quality_alert_body(cr_data, quality_issues)
            
            # Send to submitter and quality team
            recipients = [cr_data.get('submitter_email', '')]
            if self.settings.get('QUALITY_TEAM_EMAIL'):
                recipients.append(self.settings.QUALITY_TEAM_EMAIL)
            
            # Filter out empty emails
            recipients = [email for email in recipients if email]
            
            if recipients:
                success = await self._send_email_notifications(recipients, subject, body)
                
                # Send Slack alert for critical issues
                critical_issues = [issue for issue in quality_issues 
                                 if issue.get('severity') == 'critical']
                if critical_issues and self.settings.SLACK_WEBHOOK_URL:
                    await self._send_slack_quality_alert(cr_data, critical_issues)
                
                return success
            
            return True  # No recipients, consider successful
            
        except Exception as e:
            logger.error("Quality alert notification failed", 
                        cr_id=cr_data.get('id'), 
                        error=str(e))
            return False
    
    async def send_escalation_notification(self, cr_data: Dict[str, Any], 
                                         escalation_reason: str,
                                         escalated_to: List[str]) -> bool:
        """Send escalation notification"""
        
        try:
            subject = f"ESCALATED: {cr_data.get('title', 'Change Request')}"
            
            body = f"""
            <h2>Change Request Escalation</h2>
            
            <p><strong>CR Number:</strong> {cr_data.get('cr_number', 'N/A')}</p>
            <p><strong>Title:</strong> {cr_data.get('title', 'N/A')}</p>
            <p><strong>Priority:</strong> {cr_data.get('priority', 'N/A')}</p>
            <p><strong>Current Status:</strong> {cr_data.get('status', 'N/A')}</p>
            
            <h3>Escalation Reason:</h3>
            <p>{escalation_reason}</p>
            
            <h3>Required Action:</h3>
            <p>This change request requires immediate attention and approval.</p>
            
            <p>Please review and take appropriate action at your earliest convenience.</p>
            
            <p><em>This is an automated notification from FluxADM.</em></p>
            """
            
            success = await self._send_email_notifications(escalated_to, subject, body)
            
            # Always send Slack notification for escalations
            if self.settings.SLACK_WEBHOOK_URL:
                await self._send_slack_escalation_notification(cr_data, escalation_reason)
            
            return success
            
        except Exception as e:
            logger.error("Escalation notification failed", 
                        cr_id=cr_data.get('id'), 
                        error=str(e))
            return False
    
    def _prepare_cr_notification_content(self, cr_data: Dict[str, Any], 
                                       notification_type: str) -> tuple[str, str]:
        """Prepare email subject and body for CR notifications"""
        
        cr_number = cr_data.get('cr_number', 'N/A')
        title = cr_data.get('title', 'Change Request')
        status = cr_data.get('status', 'Unknown')
        
        if notification_type == "status_update":
            subject = f"Status Update: {title}"
            body = f"""
            <h2>Change Request Status Update</h2>
            
            <p><strong>CR Number:</strong> {cr_number}</p>
            <p><strong>Title:</strong> {title}</p>
            <p><strong>New Status:</strong> {status}</p>
            <p><strong>Priority:</strong> {cr_data.get('priority', 'N/A')}</p>
            <p><strong>Risk Level:</strong> {cr_data.get('risk_level', 'N/A')}</p>
            
            <h3>Description:</h3>
            <p>{cr_data.get('description', 'No description provided')[:500]}...</p>
            
            <p><em>This is an automated notification from FluxADM.</em></p>
            """
        
        elif notification_type == "completion":
            subject = f"Completed: {title}"
            body = f"""
            <h2>Change Request Completed</h2>
            
            <p><strong>CR Number:</strong> {cr_number}</p>
            <p><strong>Title:</strong> {title}</p>
            <p><strong>Completion Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            
            <p>The change request has been successfully completed.</p>
            
            <p><em>This is an automated notification from FluxADM.</em></p>
            """
        
        else:  # Default
            subject = f"Notification: {title}"
            body = f"""
            <h2>Change Request Notification</h2>
            
            <p><strong>CR Number:</strong> {cr_number}</p>
            <p><strong>Title:</strong> {title}</p>
            <p><strong>Status:</strong> {status}</p>
            
            <p><em>This is an automated notification from FluxADM.</em></p>
            """
        
        return subject, body
    
    def _generate_approval_email_body(self, cr_data: Dict[str, Any], 
                                    approval_stage: Dict[str, Any]) -> str:
        """Generate email body for approval requests"""
        
        return f"""
        <h2>Approval Request</h2>
        
        <p><strong>CR Number:</strong> {cr_data.get('cr_number', 'N/A')}</p>
        <p><strong>Title:</strong> {cr_data.get('title', 'N/A')}</p>
        <p><strong>Priority:</strong> {cr_data.get('priority', 'N/A')}</p>
        <p><strong>Risk Level:</strong> {cr_data.get('risk_level', 'N/A')}</p>
        <p><strong>Approval Stage:</strong> {approval_stage.get('stage_name', 'N/A')}</p>
        
        <h3>Description:</h3>
        <p>{cr_data.get('description', 'No description provided')}</p>
        
        <h3>Business Justification:</h3>
        <p>{cr_data.get('business_justification', 'Not provided')}</p>
        
        <h3>Risk Assessment:</h3>
        <p><strong>Risk Score:</strong> {cr_data.get('risk_score', 'N/A')}/9</p>
        
        <h3>Action Required:</h3>
        <p>Please review this change request and provide your approval or rejection with comments.</p>
        
        <p><strong>Due Date:</strong> {approval_stage.get('due_date', 'Not specified')}</p>
        
        <p><em>This is an automated notification from FluxADM.</em></p>
        """
    
    def _generate_quality_alert_body(self, cr_data: Dict[str, Any], 
                                   quality_issues: List[Dict[str, Any]]) -> str:
        """Generate email body for quality alerts"""
        
        issues_html = ""
        for issue in quality_issues[:10]:  # Limit to 10 issues
            issues_html += f"""
            <li><strong>{issue.get('severity', 'unknown').upper()}:</strong> 
                {issue.get('title', 'Unknown issue')} - 
                {issue.get('description', 'No description')}</li>
            """
        
        return f"""
        <h2>Quality Issues Detected</h2>
        
        <p><strong>CR Number:</strong> {cr_data.get('cr_number', 'N/A')}</p>
        <p><strong>Title:</strong> {cr_data.get('title', 'N/A')}</p>
        <p><strong>Quality Score:</strong> {cr_data.get('quality_score', 'N/A')}/100</p>
        
        <h3>Issues Found:</h3>
        <ul>
        {issues_html}
        </ul>
        
        <h3>Recommended Actions:</h3>
        <p>Please review and address the quality issues before proceeding with the change request.</p>
        
        <p><em>This is an automated notification from FluxADM.</em></p>
        """
    
    async def _send_email_notifications(self, recipients: List[str], 
                                       subject: str, body: str) -> bool:
        """Send email notifications using SMTP"""
        
        if not self.settings.EMAIL_SMTP_HOST or not recipients:
            logger.info("Email not configured or no recipients", 
                       smtp_host=self.settings.EMAIL_SMTP_HOST,
                       recipients_count=len(recipients))
            return True  # Consider successful if not configured
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.settings.EMAIL_FROM
            msg['To'] = ', '.join(recipients)
            
            # Add HTML body
            html_part = MIMEText(body, 'html')
            msg.attach(html_part)
            
            # Send email
            server = smtplib.SMTP(self.settings.EMAIL_SMTP_HOST, self.settings.EMAIL_SMTP_PORT)
            
            if self.settings.EMAIL_SMTP_USER and self.settings.EMAIL_SMTP_PASSWORD:
                server.starttls()
                server.login(self.settings.EMAIL_SMTP_USER, self.settings.EMAIL_SMTP_PASSWORD)
            
            text = msg.as_string()
            server.sendmail(self.settings.EMAIL_FROM, recipients, text)
            server.quit()
            
            logger.info("Email notification sent successfully", 
                       recipients_count=len(recipients))
            return True
            
        except Exception as e:
            logger.error("Email notification failed", 
                        recipients_count=len(recipients),
                        error=str(e))
            return False
    
    async def _send_slack_notification(self, cr_data: Dict[str, Any], 
                                     notification_type: str) -> bool:
        """Send Slack notification"""
        
        if not self.settings.SLACK_WEBHOOK_URL:
            return True  # Consider successful if not configured
        
        try:
            # Prepare Slack message
            color = self._get_slack_color(cr_data.get('priority', 'medium'))
            
            message = {
                "text": f"FluxADM: Change Request {notification_type.replace('_', ' ').title()}",
                "attachments": [
                    {
                        "color": color,
                        "fields": [
                            {
                                "title": "CR Number",
                                "value": cr_data.get('cr_number', 'N/A'),
                                "short": True
                            },
                            {
                                "title": "Title",
                                "value": cr_data.get('title', 'N/A'),
                                "short": True
                            },
                            {
                                "title": "Priority",
                                "value": cr_data.get('priority', 'N/A'),
                                "short": True
                            },
                            {
                                "title": "Status",
                                "value": cr_data.get('status', 'N/A'),
                                "short": True
                            }
                        ],
                        "footer": "FluxADM",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            # Send to Slack
            response = requests.post(
                self.settings.SLACK_WEBHOOK_URL,
                json=message,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Slack notification sent successfully")
                return True
            else:
                logger.error("Slack notification failed", 
                           status_code=response.status_code,
                           response=response.text)
                return False
                
        except Exception as e:
            logger.error("Slack notification failed", error=str(e))
            return False
    
    async def _send_slack_approval_request(self, cr_data: Dict[str, Any], 
                                         approval_stage: Dict[str, Any]) -> bool:
        """Send Slack notification for approval requests"""
        
        try:
            message = {
                "text": "🔔 Approval Request - FluxADM",
                "attachments": [
                    {
                        "color": "warning",
                        "fields": [
                            {
                                "title": "CR Number",
                                "value": cr_data.get('cr_number', 'N/A'),
                                "short": True
                            },
                            {
                                "title": "Priority",
                                "value": cr_data.get('priority', 'N/A'),
                                "short": True
                            },
                            {
                                "title": "Title",
                                "value": cr_data.get('title', 'N/A'),
                                "short": False
                            },
                            {
                                "title": "Approval Stage",
                                "value": approval_stage.get('stage_name', 'N/A'),
                                "short": True
                            },
                            {
                                "title": "Due Date",
                                "value": approval_stage.get('due_date', 'Not specified'),
                                "short": True
                            }
                        ],
                        "footer": "FluxADM",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            response = requests.post(
                self.settings.SLACK_WEBHOOK_URL,
                json=message,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error("Slack approval notification failed", error=str(e))
            return False
    
    async def _send_slack_quality_alert(self, cr_data: Dict[str, Any], 
                                       critical_issues: List[Dict[str, Any]]) -> bool:
        """Send Slack notification for quality alerts"""
        
        try:
            issues_text = "\n".join([
                f"• {issue.get('title', 'Unknown issue')}" 
                for issue in critical_issues[:5]
            ])
            
            message = {
                "text": "⚠️ Critical Quality Issues Detected - FluxADM",
                "attachments": [
                    {
                        "color": "danger",
                        "fields": [
                            {
                                "title": "CR Number",
                                "value": cr_data.get('cr_number', 'N/A'),
                                "short": True
                            },
                            {
                                "title": "Quality Score",
                                "value": f"{cr_data.get('quality_score', 'N/A')}/100",
                                "short": True
                            },
                            {
                                "title": "Critical Issues",
                                "value": issues_text,
                                "short": False
                            }
                        ],
                        "footer": "FluxADM",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            response = requests.post(
                self.settings.SLACK_WEBHOOK_URL,
                json=message,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error("Slack quality alert failed", error=str(e))
            return False
    
    async def _send_slack_escalation_notification(self, cr_data: Dict[str, Any], 
                                                 escalation_reason: str) -> bool:
        """Send Slack notification for escalations"""
        
        try:
            message = {
                "text": "🚨 Change Request Escalated - FluxADM",
                "attachments": [
                    {
                        "color": "danger",
                        "fields": [
                            {
                                "title": "CR Number",
                                "value": cr_data.get('cr_number', 'N/A'),
                                "short": True
                            },
                            {
                                "title": "Priority",
                                "value": cr_data.get('priority', 'N/A'),
                                "short": True
                            },
                            {
                                "title": "Title",
                                "value": cr_data.get('title', 'N/A'),
                                "short": False
                            },
                            {
                                "title": "Escalation Reason",
                                "value": escalation_reason,
                                "short": False
                            }
                        ],
                        "footer": "FluxADM",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            response = requests.post(
                self.settings.SLACK_WEBHOOK_URL,
                json=message,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error("Slack escalation notification failed", error=str(e))
            return False
    
    def _get_slack_color(self, priority: str) -> str:
        """Get Slack attachment color based on priority"""
        colors = {
            'critical': 'danger',
            'high': 'warning', 
            'medium': 'good',
            'low': '#439FE0'
        }
        return colors.get(priority.lower(), 'good')