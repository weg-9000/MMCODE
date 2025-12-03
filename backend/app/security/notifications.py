"""
MMCODE Security Platform - Approval Notification System
======================================================

승인 워크플로우 알림 시스템
- 이메일 알림
- Slack 통합
- Webhook 알림
- SMS 알림 (선택)

Version: 1.0.0
"""

import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .approval_workflow import ApprovalRequest, NotificationChannel

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    """알림 설정"""
    # Email settings
    smtp_server: str = "localhost"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    from_email: str = "security@mmcode.ai"
    
    # Slack settings
    slack_webhook_url: Optional[str] = None
    slack_channel: str = "#security-approvals"
    slack_bot_token: Optional[str] = None
    
    # Webhook settings
    webhook_urls: List[str] = None
    webhook_timeout: int = 30
    
    # Approver mappings
    approver_contacts: Dict[str, Dict[str, str]] = None  # role -> {email, slack_user_id, phone}
    
    # SMS 설정 (선택적)
    sms_config: Optional['SMSConfig'] = None
    
    def __post_init__(self):
        if self.webhook_urls is None:
            self.webhook_urls = []
        if self.approver_contacts is None:
            self.approver_contacts = {
                "security_analyst": {
                    "email": "analyst@mmcode.ai",
                    "slack_user_id": "@security-analyst",
                    "phone": "+821012345678"
                },
                "security_lead": {
                    "email": "lead@mmcode.ai", 
                    "slack_user_id": "@security-lead",
                    "phone": "+821023456789"
                },
                "security_manager": {
                    "email": "manager@mmcode.ai",
                    "slack_user_id": "@security-manager",
                    "phone": "+821034567890"
                },
                "ciso": {
                    "email": "ciso@mmcode.ai",
                    "slack_user_id": "@ciso",
                    "phone": "+821045678901"
                }
            }


@dataclass
class SMSConfig:
    """SMS 알림 설정"""
    # AWS SNS 설정
    aws_region: str = "ap-northeast-2"  # 서울 리전
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    
    # Twilio 대안 설정 (선택)
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from_number: Optional[str] = None
    
    # SMS 설정
    sender_id: str = "MMCODE"  # 발신자 ID (일부 국가에서 지원)
    message_type: str = "Transactional"  # Transactional or Promotional
    max_price: str = "0.50"  # USD per message
    
    # 수신자 매핑
    approver_phones: Dict[str, str] = None  # role -> phone number
    
    def __post_init__(self):
        if self.approver_phones is None:
            self.approver_phones = {
                "security_analyst": "+821012345678",
                "security_lead": "+821023456789",
                "security_manager": "+821034567890",
                "ciso": "+821045678901"
            }
    


class EmailNotificationHandler:
    """이메일 알림 핸들러"""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
    
    async def send_notification(
        self,
        request: ApprovalRequest,
        notification_type: str
    ) -> bool:
        """
        이메일 알림 발송
        
        Args:
            request: 승인 요청
            notification_type: 알림 유형 (approval_request, approval_result, timeout)
            
        Returns:
            bool: 발송 성공 여부
        """
        try:
            # 수신자 결정
            recipient_email = self._get_recipient_email(request)
            if not recipient_email:
                logger.warning(f"No email configured for role {request.required_approver_role}")
                return False
            
            # 이메일 내용 생성
            subject, body = self._generate_email_content(request, notification_type)
            
            # 이메일 발송
            await self._send_email(recipient_email, subject, body)
            
            logger.info(f"Email notification sent for request {request.request_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False
    
    def _get_recipient_email(self, request: ApprovalRequest) -> Optional[str]:
        """수신자 이메일 주소 확인"""
        role_config = self.config.approver_contacts.get(request.required_approver_role)
        if role_config:
            return role_config.get("email")
        return None
    
    def _generate_email_content(
        self,
        request: ApprovalRequest,
        notification_type: str
    ) -> tuple[str, str]:
        """이메일 제목과 내용 생성"""
        
        if notification_type == "approval_request":
            subject = f"[URGENT] Security Action Approval Required - {request.action.action_type}"
            body = self._generate_approval_request_body(request)
            
        elif notification_type == "approval_result":
            status = "APPROVED" if request.status.value == "approved" else "DENIED"
            subject = f"[INFO] Security Action {status} - {request.action.action_type}"
            body = self._generate_approval_result_body(request)
            
        elif notification_type == "timeout":
            subject = f"[WARNING] Security Action Approval Timeout - {request.action.action_type}"
            body = self._generate_timeout_body(request)
            
        else:
            subject = f"[INFO] Security Action Notification - {request.action.action_type}"
            body = f"Approval request {request.request_id} status update: {notification_type}"
        
        return subject, body
    
    def _generate_approval_request_body(self, request: ApprovalRequest) -> str:
        """승인 요청 이메일 본문 생성"""
        risk_level = request.risk_assessment.risk_level.value.upper()
        risk_score = request.risk_assessment.risk_score
        
        body = f"""
SECURITY ACTION APPROVAL REQUIRED

Request ID: {request.request_id}
Requested by: {request.requested_by}
Requested at: {request.requested_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

=== ACTION DETAILS ===
Type: {request.action.action_type}
Target: {request.action.target or 'N/A'}
Tool: {request.action.tool_name or 'N/A'}
Phase: {request.action.phase.value}

=== RISK ASSESSMENT ===
Risk Level: {risk_level}
Risk Score: {risk_score:.2f}/1.0
Impact: {request.risk_assessment.impact_assessment}
Likelihood: {request.risk_assessment.likelihood}

Risk Factors:
"""
        
        for factor in request.risk_assessment.risk_factors:
            body += f"• {factor}\n"
        
        if request.risk_assessment.recommended_conditions:
            body += f"\n=== RECOMMENDED CONDITIONS ===\n"
            for condition in request.risk_assessment.recommended_conditions:
                body += f"• {condition}\n"
        
        if request.justification:
            body += f"\n=== JUSTIFICATION ===\n{request.justification}\n"
        
        timeout_str = request.timeout_at.strftime('%Y-%m-%d %H:%M:%S UTC')
        body += f"""
=== APPROVAL REQUIRED ===
Required Role: {request.required_approver_role}
Timeout: {timeout_str}

Please review this request and provide approval or denial through the MMCODE Security Platform.

This is an automated message from MMCODE Security Platform.
"""
        
        return body
    
    def _generate_approval_result_body(self, request: ApprovalRequest) -> str:
        """승인 결과 이메일 본문 생성"""
        status = "APPROVED" if request.status.value == "approved" else "DENIED"
        
        body = f"""
SECURITY ACTION {status}

Request ID: {request.request_id}
Action: {request.action.action_type}
Target: {request.action.target or 'N/A'}
Requested by: {request.requested_by}
"""
        
        if request.status.value == "approved":
            body += f"""
Approved by: {request.approved_by}
Approved at: {request.approved_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
            if request.approval_conditions_accepted:
                body += f"\nAccepted Conditions:\n"
                for condition in request.approval_conditions_accepted:
                    body += f"• {condition}\n"
        else:
            body += f"""
Denied by: {request.approved_by or 'System'}
Reason: {request.denial_reason or 'No reason provided'}
"""
        
        body += f"""
This is an automated message from MMCODE Security Platform.
"""
        
        return body
    
    def _generate_timeout_body(self, request: ApprovalRequest) -> str:
        """타임아웃 이메일 본문 생성"""
        return f"""
SECURITY ACTION APPROVAL TIMEOUT

Request ID: {request.request_id}
Action: {request.action.action_type}
Target: {request.action.target or 'N/A'}
Requested by: {request.requested_by}
Risk Level: {request.risk_assessment.risk_level.value.upper()}

The approval request has timed out without a response.
Timeout occurred at: {request.timeout_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

The action has been automatically denied for security purposes.

This is an automated message from MMCODE Security Platform.
"""
    
    async def _send_email(self, recipient: str, subject: str, body: str):
        """실제 이메일 발송"""
        def send_sync():
            msg = MIMEMultipart()
            msg['From'] = self.config.from_email
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                if self.config.smtp_use_tls:
                    server.starttls()
                if self.config.smtp_username and self.config.smtp_password:
                    server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(msg)
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, send_sync)


class SlackNotificationHandler:
    """Slack 알림 핸들러"""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
    
    async def send_notification(
        self,
        request: ApprovalRequest,
        notification_type: str
    ) -> bool:
        """
        Slack 알림 발송
        
        Args:
            request: 승인 요청
            notification_type: 알림 유형
            
        Returns:
            bool: 발송 성공 여부
        """
        try:
            if not self.config.slack_webhook_url:
                logger.warning("Slack webhook URL not configured")
                return False
            
            # Slack 메시지 생성
            message = self._generate_slack_message(request, notification_type)
            
            # Slack 발송
            await self._send_slack_message(message)
            
            logger.info(f"Slack notification sent for request {request.request_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
            return False
    
    def _generate_slack_message(
        self,
        request: ApprovalRequest,
        notification_type: str
    ) -> Dict[str, Any]:
        """Slack 메시지 생성"""
        
        risk_level = request.risk_assessment.risk_level.value
        risk_color = {
            "low": "#36a64f",      # Green
            "medium": "#ffae42",   # Yellow
            "high": "#ff6b35",     # Orange
            "critical": "#e01e5a"  # Red
        }.get(risk_level, "#36a64f")
        
        if notification_type == "approval_request":
            return self._generate_approval_request_slack(request, risk_color)
        elif notification_type == "approval_result":
            return self._generate_approval_result_slack(request)
        elif notification_type == "timeout":
            return self._generate_timeout_slack(request)
        else:
            return {
                "text": f"Security action notification: {request.request_id}",
                "channel": self.config.slack_channel
            }
    
    def _generate_approval_request_slack(
        self,
        request: ApprovalRequest,
        risk_color: str
    ) -> Dict[str, Any]:
        """승인 요청 Slack 메시지"""
        
        # Mention approver if configured
        mention = ""
        role_config = self.config.approver_contacts.get(request.required_approver_role)
        if role_config and role_config.get("slack_user_id"):
            mention = f" {role_config['slack_user_id']}"
        
        risk_factors_text = "\n".join([f"• {factor}" for factor in request.risk_assessment.risk_factors])
        
        timeout_timestamp = int(request.timeout_at.timestamp())
        
        return {
            "channel": self.config.slack_channel,
            "text": f"🚨 Security Action Approval Required{mention}",
            "attachments": [
                {
                    "color": risk_color,
                    "title": f"Approval Request: {request.action.action_type}",
                    "title_link": f"https://mmcode.ai/approvals/{request.request_id}",
                    "fields": [
                        {
                            "title": "Request ID",
                            "value": request.request_id,
                            "short": True
                        },
                        {
                            "title": "Risk Level",
                            "value": f"{request.risk_assessment.risk_level.value.upper()} ({request.risk_assessment.risk_score:.2f})",
                            "short": True
                        },
                        {
                            "title": "Target",
                            "value": request.action.target or "N/A",
                            "short": True
                        },
                        {
                            "title": "Tool",
                            "value": request.action.tool_name or "N/A",
                            "short": True
                        },
                        {
                            "title": "Requested by",
                            "value": request.requested_by,
                            "short": True
                        },
                        {
                            "title": "Timeout",
                            "value": f"<!date^{timeout_timestamp}^{{date_short_pretty}} {{time}}|{request.timeout_at.strftime('%Y-%m-%d %H:%M UTC')}>",
                            "short": True
                        },
                        {
                            "title": "Risk Factors",
                            "value": risk_factors_text,
                            "short": False
                        }
                    ],
                    "footer": "MMCODE Security Platform",
                    "ts": int(request.requested_at.timestamp())
                }
            ]
        }
    
    def _generate_approval_result_slack(self, request: ApprovalRequest) -> Dict[str, Any]:
        """승인 결과 Slack 메시지"""
        
        if request.status.value == "approved":
            color = "#36a64f"  # Green
            emoji = "✅"
            status_text = "APPROVED"
        else:
            color = "#e01e5a"  # Red
            emoji = "❌"
            status_text = "DENIED"
        
        return {
            "channel": self.config.slack_channel,
            "text": f"{emoji} Security Action {status_text}",
            "attachments": [
                {
                    "color": color,
                    "title": f"Request {status_text}: {request.action.action_type}",
                    "fields": [
                        {
                            "title": "Request ID",
                            "value": request.request_id,
                            "short": True
                        },
                        {
                            "title": "Action",
                            "value": request.action.action_type,
                            "short": True
                        },
                        {
                            "title": "Processed by" if request.status.value == "approved" else "Denied by",
                            "value": request.approved_by or "System",
                            "short": True
                        }
                    ],
                    "footer": "MMCODE Security Platform",
                    "ts": int((request.approved_at or datetime.utcnow()).timestamp())
                }
            ]
        }
    
    def _generate_timeout_slack(self, request: ApprovalRequest) -> Dict[str, Any]:
        """타임아웃 Slack 메시지"""
        return {
            "channel": self.config.slack_channel,
            "text": "⏰ Security Action Approval Timeout",
            "attachments": [
                {
                    "color": "#ffae42",  # Yellow
                    "title": f"Timeout: {request.action.action_type}",
                    "fields": [
                        {
                            "title": "Request ID",
                            "value": request.request_id,
                            "short": True
                        },
                        {
                            "title": "Risk Level",
                            "value": request.risk_assessment.risk_level.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Requested by",
                            "value": request.requested_by,
                            "short": True
                        }
                    ],
                    "text": "The approval request has timed out and been automatically denied.",
                    "footer": "MMCODE Security Platform",
                    "ts": int(request.timeout_at.timestamp())
                }
            ]
        }
    
    async def _send_slack_message(self, message: Dict[str, Any]):
        """Slack 메시지 발송"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.config.slack_webhook_url,
                json=message,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Slack API error {response.status}: {error_text}")


class WebhookNotificationHandler:
    """웹훅 알림 핸들러"""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
    
    async def send_notification(
        self,
        request: ApprovalRequest,
        notification_type: str
    ) -> bool:
        """
        웹훅 알림 발송
        
        Args:
            request: 승인 요청
            notification_type: 알림 유형
            
        Returns:
            bool: 발송 성공 여부
        """
        try:
            if not self.config.webhook_urls:
                logger.debug("No webhook URLs configured")
                return True
            
            # 웹훅 페이로드 생성
            payload = self._generate_webhook_payload(request, notification_type)
            
            # 모든 웹훅 URL에 발송
            success_count = 0
            for webhook_url in self.config.webhook_urls:
                try:
                    await self._send_webhook(webhook_url, payload)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send webhook to {webhook_url}: {str(e)}")
            
            logger.info(f"Webhook notifications sent: {success_count}/{len(self.config.webhook_urls)}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to send webhook notifications: {str(e)}")
            return False
    
    def _generate_webhook_payload(
        self,
        request: ApprovalRequest,
        notification_type: str
    ) -> Dict[str, Any]:
        """웹훅 페이로드 생성"""
        return {
            "event_type": "approval_notification",
            "notification_type": notification_type,
            "timestamp": datetime.utcnow().isoformat(),
            "request": {
                "request_id": request.request_id,
                "action": {
                    "action_id": request.action.action_id,
                    "action_type": request.action.action_type,
                    "target": request.action.target,
                    "tool_name": request.action.tool_name,
                    "phase": request.action.phase.value,
                    "risk_level": request.action.risk_level.value
                },
                "risk_assessment": {
                    "risk_level": request.risk_assessment.risk_level.value,
                    "risk_score": request.risk_assessment.risk_score,
                    "risk_factors": request.risk_assessment.risk_factors,
                    "impact_assessment": request.risk_assessment.impact_assessment
                },
                "workflow": {
                    "requested_by": request.requested_by,
                    "requested_at": request.requested_at.isoformat(),
                    "required_approver_role": request.required_approver_role,
                    "timeout_at": request.timeout_at.isoformat(),
                    "status": request.status.value,
                    "approved_by": request.approved_by,
                    "approved_at": request.approved_at.isoformat() if request.approved_at else None,
                    "denial_reason": request.denial_reason
                }
            }
        }
    
    async def _send_webhook(self, webhook_url: str, payload: Dict[str, Any]):
        """개별 웹훅 발송"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "MMCODE-Security-Platform/1.0"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.config.webhook_timeout)
            ) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    raise Exception(f"Webhook error {response.status}: {error_text}")


class NotificationManager:
    """통합 알림 관리자"""
    
    def __init__(self, config: NotificationConfig = None):
        """
        Args:
            config: 알림 설정
        """
        self.config = config or NotificationConfig()
        
        # 핸들러 초기화
        self.handlers = {
            NotificationChannel.EMAIL: EmailNotificationHandler(self.config),
            NotificationChannel.SLACK: SlackNotificationHandler(self.config),
            NotificationChannel.WEBHOOK: WebhookNotificationHandler(self.config)
        }
        
        # SMS 핸들러 추가 (옵션)
        sms_config = getattr(self.config, 'sms_config', None)
        if sms_config:
            self.handlers[NotificationChannel.SMS] = SMSNotificationHandler(sms_config)
    
    async def send_notification(
        self,
        request: ApprovalRequest,
        notification_type: str,
        channels: List[NotificationChannel] = None
    ) -> Dict[NotificationChannel, bool]:
        """
        다중 채널 알림 발송
        
        Args:
            request: 승인 요청
            notification_type: 알림 유형
            channels: 발송할 채널 목록 (None이면 설정된 모든 채널)
            
        Returns:
            Dict[NotificationChannel, bool]: 채널별 발송 결과
        """
        if channels is None:
            channels = list(self.handlers.keys())
        
        results = {}
        
        # 병렬 알림 발송
        tasks = []
        for channel in channels:
            handler = self.handlers.get(channel)
            if handler:
                task = asyncio.create_task(
                    handler.send_notification(request, notification_type),
                    name=f"notify_{channel.value}"
                )
                tasks.append((channel, task))
        
        # 모든 알림 완료 대기
        for channel, task in tasks:
            try:
                result = await task
                results[channel] = result
            except Exception as e:
                logger.error(f"Failed to send {channel.value} notification: {str(e)}")
                results[channel] = False
        
        return results
    
    def update_config(self, new_config: NotificationConfig):
        """설정 업데이트"""
        self.config = new_config
        
        # SMS 핸들러 클래스 추가
        
class SMSNotificationHandler:
    """SMS 알림 핸들러 (AWS SNS 기반)"""
    
    def __init__(self, config: SMSConfig):
        self.config = config
        self.sns_client = self._init_sns_client()
        
        # 메시지 템플릿
        self.templates = {
            "approval_request": (
                "[MMCODE] 보안 승인 요청\n"
                "작업: {action_type}\n"
                "대상: {target}\n"
                "위험도: {risk_level}\n"
                "요청자: {requested_by}\n"
                "만료: {timeout_at}\n"
                "승인: {approval_url}"
            ),
            "approval_result": (
                "[MMCODE] 승인 완료\n"
                "요청ID: {request_id}\n"
                "결과: {status}\n"
                "승인자: {approver}"
            ),
            "timeout_warning": (
                "[MMCODE] 승인 만료 경고\n"
                "요청ID: {request_id}\n"
                "남은시간: {remaining_minutes}분\n"
                "즉시 처리 필요"
            ),
            "security_alert": (
                "[MMCODE] 🚨 보안 경고\n"
                "유형: {alert_type}\n"
                "심각도: {severity}\n"
                "즉시 확인 필요"
            )
        }
    
    def _init_sns_client(self):
        """AWS SNS 클라이언트 초기화"""
        try:
            import boto3
            
            if self.config.aws_access_key_id:
                return boto3.client(
                    'sns',
                    region_name=self.config.aws_region,
                    aws_access_key_id=self.config.aws_access_key_id,
                    aws_secret_access_key=self.config.aws_secret_access_key
                )
            else:
                # IAM 역할 사용 (EC2/ECS 환경)
                return boto3.client('sns', region_name=self.config.aws_region)
        except ImportError:
            logger.warning("boto3 not installed, SMS functionality disabled")
            return None
    
    async def send_notification(
        self,
        request: ApprovalRequest,
        notification_type: str
    ) -> bool:
        """
        SMS 알림 발송
        
        Args:
            request: 승인 요청
            notification_type: 알림 유형
            
        Returns:
            bool: 발송 성공 여부
        """
        try:
            if not self.sns_client:
                logger.warning("SNS client not available, skipping SMS notification")
                return False
            
            # 수신자 전화번호 조회
            phone_number = self._get_recipient_phone(request)
            if not phone_number:
                logger.warning(
                    f"No phone number configured for role "
                    f"{request.required_approver_role}"
                )
                return False
            
            # 메시지 생성
            message = self._generate_message(request, notification_type)
            
            # SMS 발송
            await self._send_sms(phone_number, message)
            
            logger.info(
                f"SMS notification sent for request {request.request_id} "
                f"to {self._mask_phone(phone_number)}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS notification: {str(e)}")
            return False
    
    def _get_recipient_phone(self, request: ApprovalRequest) -> Optional[str]:
        """역할에 따른 수신자 전화번호 조회"""
        return self.config.approver_phones.get(request.required_approver_role)
    
    def _generate_message(
        self,
        request: ApprovalRequest,
        notification_type: str
    ) -> str:
        """SMS 메시지 생성 (160자 제한 고려)"""
        template = self.templates.get(notification_type, "")
        
        # 템플릿 변수 치환
        message = template.format(
            request_id=request.request_id[:8],  # 짧게 자름
            action_type=request.action.action_type,
            target=self._truncate(request.action.target, 20),
            risk_level=request.risk_assessment.risk_level.value.upper(),
            requested_by=request.requested_by,
            timeout_at=request.timeout_at.strftime("%m/%d %H:%M"),
            approval_url=self._generate_approval_url(request),
            status=request.status.value if hasattr(request, 'status') else 'N/A',
            approver=getattr(request, 'approved_by', 'N/A')
        )
        
        # 160자 제한 (SMS 1건 기준)
        if len(message) > 160:
            message = message[:157] + "..."
        
        return message
    
    def _truncate(self, text: str, max_len: int) -> str:
        """텍스트 자르기"""
        if not text:
            return "N/A"
        return text[:max_len-2] + ".." if len(text) > max_len else text
    
    def _generate_approval_url(self, request: ApprovalRequest) -> str:
        """짧은 승인 URL 생성"""
        # 실제 구현에서는 URL 단축 서비스 사용 권장
        base_url = os.getenv("APPROVAL_BASE_URL", "https://sec.mmcode.ai")
        return f"{base_url}/a/{request.request_id[:8]}"
    
    def _mask_phone(self, phone: str) -> str:
        """전화번호 마스킹 (로그용)"""
        if len(phone) > 4:
            return phone[:-4] + "****"
        return "****"
    
    async def _send_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """
        AWS SNS를 통한 SMS 발송
        
        국제 전화번호 형식 필요: +821012345678
        """
        import asyncio
        
        def send_sync():
            return self.sns_client.publish(
                PhoneNumber=phone_number,
                Message=message,
                MessageAttributes={
                    'AWS.SNS.SMS.SenderID': {
                        'DataType': 'String',
                        'StringValue': self.config.sender_id
                    },
                    'AWS.SNS.SMS.SMSType': {
                        'DataType': 'String',
                        'StringValue': self.config.message_type
                    },
                    'AWS.SNS.SMS.MaxPrice': {
                        'DataType': 'String',
                        'StringValue': self.config.max_price
                    }
                }
            )
        
        # 비동기 실행
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, send_sync)
        
        return {
            'message_id': response.get('MessageId'),
            'status': 'sent'
        }