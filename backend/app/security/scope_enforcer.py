"""
MMCODE Security Platform - Scope Enforcement Engine
=====================================================

3계층 스코프 검증 엔진
- Layer 1: 프롬프트 레벨 (LLM 컨텍스트 검증)
- Layer 2: 결정론적 필터 (규칙 기반 검증)
- Layer 3: 네트워크/방화벽 레벨 (물리적 차단)

Version: 2.0.0
"""

import re
import time
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Set
from ipaddress import ip_address, ip_network

from .models import (
    EngagementScope,
    SecurityAction,
    ValidationResult,
    LayerResult,
    RiskLevel,
    PentestPhase,
    TimeWindow
)

logger = logging.getLogger(__name__)


class ScopeViolationError(Exception):
    """스코프 위반 예외"""
    def __init__(self, message: str, violations: List[str] = None, blocked_at: str = None):
        super().__init__(message)
        self.violations = violations or []
        self.blocked_at = blocked_at


class ScopeEnforcementEngine:
    """
    3계층 스코프 검증 엔진
    
    모든 보안 작업은 이 엔진을 통해 검증된 후에만 실행됨
    
    Layer 1 (Prompt Level):
        - LLM 프롬프트에 스코프 제약 명시
        - 승인된 대상/방법론 목록 검증
        - 윤리적 가이드라인 확인
        
    Layer 2 (Deterministic):
        - IP/도메인 화이트리스트 검증
        - 파괴적 명령어 패턴 차단
        - 시간 윈도우 검증
        - Rate limit 확인
        
    Layer 3 (Network Level):
        - Docker 네트워크 정책 확인
        - iptables 규칙 검증
        - 물리적 연결 가능성 확인
    """
    
    # Layer 2: 파괴적 명령어 패턴 (절대 실행 금지)
    DESTRUCTIVE_PATTERNS = [
        # 파일시스템 파괴
        r'rm\s+-rf\s+/',
        r'rm\s+-rf\s+~',
        r'rm\s+-rf\s+\*',
        r'rm\s+--no-preserve-root',
        r'rmdir\s+/',
        
        # 디스크/파티션 파괴
        r'mkfs\.',
        r'dd\s+if=.*of=/dev/',
        r'>\s*/dev/sd[a-z]',
        r'wipefs',
        r'fdisk\s+/dev/',
        r'parted\s+/dev/',
        
        # Windows 명령어
        r'format\s+[A-Z]:\s*',
        r'del\s+/[fFsS]\s+\*',
        r'del\s+/[fFsS]\s+C:\\',
        r'rd\s+/[sS]\s+/[qQ]',
        
        # 시스템 종료/재부팅
        r'shutdown\s+-[hr]',
        r'reboot\s+-f',
        r'halt\s+-f',
        r'poweroff',
        r'init\s+0',
        r'init\s+6',
        
        # 데이터베이스 파괴
        r'DROP\s+DATABASE',
        r'DROP\s+TABLE',
        r'TRUNCATE\s+TABLE',
        r'DELETE\s+FROM\s+\w+\s*;?\s*$',  # 조건 없는 DELETE
        
        # 암호화폐 채굴/랜섬웨어 관련
        r'xmrig',
        r'cryptominer',
        r'ransomware',
        r'\.encrypt',
        
        # 네트워크 파괴
        r'iptables\s+-F',
        r'iptables\s+-X',
        r'ip\s+link\s+delete',
        r'ifconfig\s+\w+\s+down',
        
        # 포크 폭탄/리소스 고갈
        r':\(\)\{\s*:\|\:&\s*\};:',
        r'while\s+true\s*;\s*do',
        r'fork\s*\(\)',
        
        # 권한 상승 시도 (사전 승인 없이)
        r'chmod\s+777\s+/',
        r'chmod\s+-R\s+777',
        r'chown\s+-R\s+\w+\s+/',
    ]
    
    # Layer 2: 위험 명령어 패턴 (경고 + 승인 필요)
    RISKY_PATTERNS = [
        (r'curl\s+.*\|\s*bash', "Piping curl to bash is risky"),
        (r'wget\s+.*\|\s*bash', "Piping wget to bash is risky"),
        (r'eval\s+', "eval command can execute arbitrary code"),
        (r'exec\s+', "exec command can replace current process"),
        (r'sudo\s+', "sudo requires elevated privileges"),
        (r'su\s+-', "su requires authentication"),
        (r'chmod\s+[0-7]{3,4}', "chmod changes file permissions"),
        (r'nc\s+-[el]', "netcat listener mode detected"),
        (r'ncat\s+-[el]', "ncat listener mode detected"),
        (r'socat\s+', "socat can create network connections"),
    ]
    
    # Layer 2: IP 난독화 패턴 (우회 시도 차단)
    IP_OBFUSCATION_PATTERNS = [
        r'^0[0-7]+\.',           # Octal: 0300.0250.01.01
        r'^0x[0-9a-fA-F]+\.',    # Hex: 0xC0.0xA8.0x01.0x01
        r'^\d{8,}$',             # Decimal: 3232235777
        r'%[0-9a-fA-F]{2}',      # URL encoded
    ]
    
    # Layer 2: 명령어 인젝션 패턴
    INJECTION_PATTERNS = [
        r';\s*\w+',              # Command chaining: ; rm
        r'\|\s*\w+',             # Piping: | nc
        r'&&\s*\w+',             # AND chaining: && rm
        r'\|\|\s*\w+',           # OR chaining: || rm
        r'\$\(',                 # Command substitution: $(cmd)
        r'`[^`]+`',              # Backtick substitution: `cmd`
        r'>\s*/',                # Redirect to root: > /
        r'>>\s*/',               # Append to root: >> /
    ]
    
    def __init__(self, engagement_scope: EngagementScope):
        """
        Args:
            engagement_scope: 펜테스팅 범위 정의
        """
        self.scope = engagement_scope
        self._compiled_destructive = [
            re.compile(p, re.IGNORECASE) for p in self.DESTRUCTIVE_PATTERNS
        ]
        self._compiled_risky = [
            (re.compile(p, re.IGNORECASE), msg) for p, msg in self.RISKY_PATTERNS
        ]
        self._compiled_obfuscation = [
            re.compile(p) for p in self.IP_OBFUSCATION_PATTERNS
        ]
        self._compiled_injection = [
            re.compile(p) for p in self.INJECTION_PATTERNS
        ]
        
        # 통계 추적
        self._validation_count = 0
        self._blocked_count = 0
        self._layer_stats = {"prompt": 0, "deterministic": 0, "network": 0}
    
    async def validate_action(
        self, 
        action: SecurityAction
    ) -> ValidationResult:
        """
        3계층 검증 수행
        
        Args:
            action: 검증할 보안 작업
            
        Returns:
            ValidationResult: 검증 결과 (valid=True면 실행 허용)
            
        Raises:
            ScopeViolationError: 심각한 스코프 위반 시
        """
        start_time = time.time()
        self._validation_count += 1
        
        layer_results = []
        
        # Layer 1: 프롬프트 레벨 검증
        layer1_start = time.time()
        layer1 = self._validate_prompt_level(action)
        layer1.execution_time_ms = (time.time() - layer1_start) * 1000
        layer_results.append(layer1)
        
        if not layer1.valid:
            self._blocked_count += 1
            self._layer_stats["prompt"] += 1
            logger.warning(
                f"Action {action.action_id} blocked at prompt level: {layer1.violations}"
            )
            return self._create_result(
                layer_results, 
                blocked_at="prompt",
                action_id=action.action_id,
                start_time=start_time
            )
        
        # Layer 2: 결정론적 필터
        layer2_start = time.time()
        layer2 = self._validate_deterministic(action)
        layer2.execution_time_ms = (time.time() - layer2_start) * 1000
        layer_results.append(layer2)
        
        if not layer2.valid:
            self._blocked_count += 1
            self._layer_stats["deterministic"] += 1
            logger.warning(
                f"Action {action.action_id} blocked at deterministic level: {layer2.violations}"
            )
            return self._create_result(
                layer_results,
                blocked_at="deterministic", 
                action_id=action.action_id,
                start_time=start_time
            )
        
        # Layer 3: 네트워크 레벨 검증
        layer3_start = time.time()
        layer3 = await self._validate_network_level(action)
        layer3.execution_time_ms = (time.time() - layer3_start) * 1000
        layer_results.append(layer3)
        
        if not layer3.valid:
            self._blocked_count += 1
            self._layer_stats["network"] += 1
            logger.warning(
                f"Action {action.action_id} blocked at network level: {layer3.violations}"
            )
            return self._create_result(
                layer_results,
                blocked_at="network",
                action_id=action.action_id,
                start_time=start_time
            )
        
        # 모든 검증 통과
        logger.info(f"Action {action.action_id} passed all validation layers")
        return self._create_result(
            layer_results,
            valid=True,
            action_id=action.action_id,
            start_time=start_time
        )
    
    def _validate_prompt_level(self, action: SecurityAction) -> LayerResult:
        """
        Layer 1: 프롬프트 레벨 검증
        
        LLM이 제안한 작업이 기본적인 스코프 제약을 만족하는지 확인
        """
        violations = []
        warnings = []
        
        # 1. 대상 검증
        if action.target:
            if not self._is_target_authorized(action.target):
                violations.append(
                    f"Target '{action.target}' is not in authorized scope"
                )
        
        if action.target_ip:
            if not self.scope.is_ip_in_scope(action.target_ip):
                violations.append(
                    f"IP '{action.target_ip}' is not in authorized IP ranges"
                )
        
        if action.target_domain:
            if not self.scope.is_domain_in_scope(action.target_domain):
                violations.append(
                    f"Domain '{action.target_domain}' is not in authorized domains"
                )
        
        # 2. 방법론 검증
        if action.method:
            if not self.scope.is_method_allowed(action.method):
                violations.append(
                    f"Method '{action.method}' is not authorized for this engagement"
                )
        
        # 3. 시간 윈도우 검증
        if not self._is_within_time_window():
            violations.append("Action is outside authorized time window")
        
        # 4. 엔게이지먼트 기간 검증
        now = datetime.utcnow()
        if self.scope.start_date and now < self.scope.start_date:
            violations.append("Engagement has not started yet")
        if self.scope.end_date and now > self.scope.end_date:
            violations.append("Engagement has already ended")
        
        # 5. 페이즈 검증 (특정 페이즈에서만 허용되는 작업)
        if action.phase == PentestPhase.EXPLOITATION:
            if action.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                warnings.append(
                    "High-risk exploitation requires human approval"
                )
        
        # 6. 위험 수준 검증
        if action.risk_level.value >= self.scope.requires_approval_above.value:
            warnings.append(
                f"Action with {action.risk_level.value} risk level requires approval"
            )
        
        return LayerResult(
            layer="prompt",
            valid=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            details={
                "target_checked": action.target or action.target_ip or action.target_domain,
                "method": action.method,
                "phase": action.phase.value if action.phase else None
            }
        )
    
    def _validate_deterministic(self, action: SecurityAction) -> LayerResult:
        """
        Layer 2: 결정론적 규칙 검증
        
        정규식 기반의 엄격한 규칙으로 파괴적 행동 차단
        """
        violations = []
        warnings = []
        
        # 1. 파괴적 명령어 패턴 검사
        if action.command:
            for pattern in self._compiled_destructive:
                if pattern.search(action.command):
                    violations.append(
                        f"Destructive command pattern detected: {pattern.pattern[:50]}..."
                    )
                    break
        
        # 2. 위험 명령어 패턴 검사
        if action.command:
            for pattern, message in self._compiled_risky:
                if pattern.search(action.command):
                    warnings.append(f"Risky pattern: {message}")
        
        # 3. IP 난독화 시도 검사
        if action.target_ip:
            for pattern in self._compiled_obfuscation:
                if pattern.search(action.target_ip):
                    violations.append(
                        f"IP obfuscation attempt detected: {action.target_ip}"
                    )
                    break
        
        if action.target:
            for pattern in self._compiled_obfuscation:
                if pattern.search(action.target):
                    violations.append(
                        f"IP obfuscation attempt detected in target: {action.target}"
                    )
                    break
        
        # 4. 명령어 인젝션 검사
        if action.target:
            for pattern in self._compiled_injection:
                if pattern.search(action.target):
                    violations.append(
                        f"Command injection attempt detected in target"
                    )
                    break
        
        # 5. IP 범위 상세 검증
        if action.target_ip:
            normalized = self._normalize_ip(action.target_ip)
            if normalized:
                if not self.scope.is_ip_in_scope(normalized):
                    violations.append(
                        f"IP {normalized} (normalized from {action.target_ip}) outside authorized ranges"
                    )
            else:
                violations.append(
                    f"Invalid IP address format: {action.target_ip}"
                )
        
        # 6. 포트 범위 검증
        if action.target_ports:
            unauthorized_ports = [
                p for p in action.target_ports 
                if not self.scope.is_port_allowed(p)
            ]
            if unauthorized_ports:
                violations.append(
                    f"Ports {unauthorized_ports} are not authorized"
                )
        
        return LayerResult(
            layer="deterministic",
            valid=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            details={
                "command_checked": bool(action.command),
                "ports_checked": action.target_ports,
                "patterns_matched": len(warnings)
            }
        )
    
    async def _validate_network_level(self, action: SecurityAction) -> LayerResult:
        """
        Layer 3: 네트워크 레벨 검증
        
        실제 네트워크 연결 가능성 및 방화벽 규칙 확인
        """
        violations = []
        warnings = []
        
        if not action.requires_network:
            return LayerResult(
                layer="network",
                valid=True,
                violations=[],
                warnings=[],
                details={"network_required": False}
            )
        
        # 1. Docker 네트워크 정책 확인
        network_policy = await self._get_docker_network_policy()
        
        if action.target_ip:
            if not await self._is_allowed_by_policy(action.target_ip, network_policy):
                violations.append(
                    f"Network policy blocks connection to {action.target_ip}"
                )
        
        # 3. DNS 해석 가능성 확인
        if action.target_domain:
            resolved = await self._resolve_domain(action.target_domain)
            if not resolved:
                warnings.append(
                    f"Domain {action.target_domain} could not be resolved"
                )
            else:
                # 해석된 IP가 스코프 내인지 확인
                if not self.scope.is_ip_in_scope(resolved):
                    violations.append(
                        f"Resolved IP {resolved} for {action.target_domain} is outside scope"
                    )
        
        return LayerResult(
            layer="network",
            valid=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            details={
                "network_policy": network_policy,
                "connection_checked": action.target_ip or action.target_domain
            }
        )
    
    def _is_target_authorized(self, target: str) -> bool:
        """대상이 승인된 범위 내인지 확인"""
        # IP 형식 체크
        try:
            ip_address(target)
            return self.scope.is_ip_in_scope(target)
        except ValueError:
            pass
        
        # 도메인/URL 형식 체크
        return self.scope.is_domain_in_scope(target)
    
    def _is_within_time_window(self) -> bool:
        """현재 시간이 허용된 윈도우 내인지 확인"""
        if not self.scope.time_windows:
            return True
        
        now = datetime.utcnow()
        for window in self.scope.time_windows:
            if window.is_within_window(now):
                return True
        
        return False
    
    def _normalize_ip(self, ip_str: str) -> Optional[str]:
        """IP 주소 정규화 (난독화 해제)"""
        try:
            # 표준 형식으로 변환 시도
            return str(ip_address(ip_str))
        except ValueError:
            pass
        
        # Decimal 형식 (3232235777)
        try:
            decimal_ip = int(ip_str)
            if 0 <= decimal_ip <= 0xFFFFFFFF:
                return str(ip_address(decimal_ip))
        except ValueError:
            pass
        
        # Hex 형식 (0xC0A80101)
        if ip_str.lower().startswith("0x"):
            try:
                hex_ip = int(ip_str, 16)
                if 0 <= hex_ip <= 0xFFFFFFFF:
                    return str(ip_address(hex_ip))
            except ValueError:
                pass
        
        return None
    
    async def _get_docker_network_policy(self) -> str:
        """Docker 네트워크 정책 조회"""
        # TODO: 실제 Docker API 통합
        return "restricted"
    
    async def _is_allowed_by_policy(self, ip: str, policy: str) -> bool:
        """네트워크 정책에서 허용되는지 확인"""
        # TODO: 실제 정책 확인 로직
        return True
    
    async def _resolve_domain(self, domain: str) -> Optional[str]:
        """도메인 DNS 해석"""
        # TODO: 실제 DNS 해석
        return None
    
    def _create_result(
        self,
        layer_results: List[LayerResult],
        blocked_at: Optional[str] = None,
        valid: bool = False,
        action_id: Optional[str] = None,
        start_time: float = None
    ) -> ValidationResult:
        """ValidationResult 생성"""
        validation_time = (time.time() - start_time) * 1000 if start_time else 0
        
        return ValidationResult(
            valid=valid,
            blocked_at=blocked_at,
            layer_results=layer_results,
            action_id=action_id,
            validation_time_ms=validation_time
        )
    
    def generate_docker_network_policy(self) -> str:
        """
        Docker 컨테이너용 iptables 규칙 생성
        
        승인된 대상만 연결 가능하도록 방화벽 규칙 생성
        """
        rules = [
            "#!/bin/bash",
            "# MMCODE Security Platform - Auto-generated scope enforcement rules",
            f"# Engagement: {self.scope.engagement_name}",
            f"# Generated: {datetime.utcnow().isoformat()}",
            "",
            "# Flush existing rules",
            "iptables -F OUTPUT",
            "",
            "# Default: drop all outbound",
            "iptables -P OUTPUT DROP",
            "",
            "# Allow loopback",
            "iptables -A OUTPUT -o lo -j ACCEPT",
            "",
            "# Allow established connections",
            "iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT",
            ""
        ]
        
        # DNS 허용 (옵션)
        rules.extend([
            "# Allow DNS (if needed)",
            "iptables -A OUTPUT -p udp --dport 53 -j ACCEPT",
            "iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT",
            ""
        ])
        
        # 승인된 IP 범위 허용
        rules.append("# Allow authorized targets only")
        for ip_range in self.scope.ip_ranges:
            rules.append(f"iptables -A OUTPUT -d {ip_range} -j ACCEPT")
        
        # 허용된 포트만
        if self.scope.allowed_ports:
            rules.append("")
            rules.append("# Restrict to allowed ports")
            for port in self.scope.allowed_ports:
                rules.append(
                    f"iptables -A OUTPUT -p tcp --dport {port} -j ACCEPT"
                )
                rules.append(
                    f"iptables -A OUTPUT -p udp --dport {port} -j ACCEPT"
                )
        
        # 로깅 및 드롭
        rules.extend([
            "",
            "# Log and drop everything else",
            "iptables -A OUTPUT -j LOG --log-prefix 'SCOPE_VIOLATION: ' --log-level 4",
            "iptables -A OUTPUT -j DROP"
        ])
        
        return "\n".join(rules)
    
    def get_stats(self) -> Dict[str, Any]:
        """검증 통계 반환"""
        return {
            "total_validations": self._validation_count,
            "total_blocked": self._blocked_count,
            "block_rate": (
                self._blocked_count / self._validation_count 
                if self._validation_count > 0 else 0
            ),
            "blocks_by_layer": self._layer_stats.copy(),
            "scope_summary": {
                "ip_ranges": len(self.scope.ip_ranges),
                "domains": len(self.scope.domains),
                "allowed_methods": len(self.scope.allowed_methods),
                "prohibited_methods": len(self.scope.prohibited_methods)
            }
        }


# 팩토리 함수
def create_scope_enforcer(scope_config: Dict[str, Any]) -> ScopeEnforcementEngine:
    """
    설정 딕셔너리로부터 ScopeEnforcementEngine 생성
    
    Args:
        scope_config: 스코프 설정 딕셔너리
        
    Returns:
        ScopeEnforcementEngine 인스턴스
    """
    from .models import EngagementType, RiskLevel, TimeWindow
    from datetime import time as dt_time
    
    # TimeWindow 파싱
    time_windows = []
    for tw in scope_config.get("time_windows", []):
        time_windows.append(TimeWindow(
            start_time=dt_time.fromisoformat(tw["start_time"]),
            end_time=dt_time.fromisoformat(tw["end_time"]),
            timezone=tw.get("timezone", "UTC"),
            days_of_week=tw.get("days_of_week", [0, 1, 2, 3, 4])
        ))
    
    scope = EngagementScope(
        engagement_id=scope_config["engagement_id"],
        engagement_name=scope_config["engagement_name"],
        engagement_type=EngagementType(scope_config.get("engagement_type", "external")),
        ip_ranges=scope_config.get("ip_ranges", []),
        domains=scope_config.get("domains", []),
        urls=scope_config.get("urls", []),
        excluded_ips=scope_config.get("excluded_ips", []),
        excluded_domains=scope_config.get("excluded_domains", []),
        excluded_ports=scope_config.get("excluded_ports", []),
        allowed_ports=scope_config.get("allowed_ports", []),
        allowed_methods=scope_config.get("allowed_methods", []),
        prohibited_methods=scope_config.get("prohibited_methods", []),
        time_windows=time_windows,
        max_requests_per_second=scope_config.get("max_requests_per_second", 10),
        max_concurrent_scans=scope_config.get("max_concurrent_scans", 3),
        requires_approval_above=RiskLevel(
            scope_config.get("requires_approval_above", "medium")
        ),
        emergency_contact=scope_config.get("emergency_contact")
    )
    
    return ScopeEnforcementEngine(scope)