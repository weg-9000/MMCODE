"""
MMCODE Security Platform - PTT Context Manager
=============================================

LLM 컨텍스트 최적화 및 관리
- 컨텍스트 압축 및 요약
- 중요 정보 우선순위 관리
- 토큰 제한 대응

Version: 1.0.0
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

from ..models import TaskNode, SecurityFinding, PentestPhase
from .task_tree import PTTState

logger = logging.getLogger(__name__)


@dataclass
class ContextPriority:
    """컨텍스트 우선순위 설정"""
    critical_findings: float = 1.0
    recent_tasks: float = 0.8
    available_tasks: float = 0.7
    discovered_assets: float = 0.6
    execution_history: float = 0.5
    statistics: float = 0.3


class PTTContextManager:
    """
    PTT 컨텍스트 관리자
    
    LLM 컨텍스트 제한 문제 해결:
    - 중요도 기반 정보 필터링
    - 적응적 압축
    - 단계적 세부정보 제공
    """
    
    def __init__(self, max_context_tokens: int = 4000):
        """
        Args:
            max_context_tokens: 최대 컨텍스트 토큰 수
        """
        self.max_context_tokens = max_context_tokens
        self.priority_config = ContextPriority()
        
        # 압축 레벨별 설정
        self.compression_levels = {
            1: {"token_limit": 4000, "detail_level": "full"},
            2: {"token_limit": 3000, "detail_level": "high"}, 
            3: {"token_limit": 2000, "detail_level": "medium"},
            4: {"token_limit": 1000, "detail_level": "low"},
            5: {"token_limit": 500, "detail_level": "minimal"}
        }
    
    def generate_context(
        self,
        ptt_state: PTTState,
        focus_areas: Optional[List[str]] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        PTT 상태로부터 최적화된 컨텍스트 생성
        
        Args:
            ptt_state: PTT 현재 상태
            focus_areas: 집중할 영역 (findings, tasks, assets 등)
            max_tokens: 최대 토큰 수 (None이면 기본값 사용)
            
        Returns:
            str: 최적화된 컨텍스트
        """
        target_tokens = max_tokens or self.max_context_tokens
        
        # 1단계: 기본 정보 수집
        context_sections = self._collect_base_sections(ptt_state)
        
        # 2단계: 우선순위 기반 필터링
        if focus_areas:
            context_sections = self._filter_by_focus(context_sections, focus_areas)
        
        # 3단계: 토큰 제한에 맞춰 압축
        context = self._compress_to_limit(context_sections, target_tokens)
        
        return context
    
    def _collect_base_sections(self, state: PTTState) -> Dict[str, Dict]:
        """기본 컨텍스트 섹션 수집"""
        sections = {}
        
        # 헤더 정보
        sections["header"] = {
            "content": self._generate_header(state),
            "priority": 1.0,
            "estimated_tokens": 100
        }
        
        # 중요한 발견사항
        critical_findings = [
            f for f in state.findings 
            if f.severity.value in ['critical', 'high']
        ]
        if critical_findings:
            sections["critical_findings"] = {
                "content": self._format_critical_findings(critical_findings),
                "priority": self.priority_config.critical_findings,
                "estimated_tokens": len(critical_findings) * 80
            }
        
        # 최근 완료 작업
        recent_completions = [
            task for task in state.all_nodes.values()
            if (task.status == "completed" and 
                task.completed_at and
                task.completed_at > datetime.utcnow() - timedelta(hours=2))
        ]
        if recent_completions:
            sections["recent_tasks"] = {
                "content": self._format_recent_tasks(recent_completions),
                "priority": self.priority_config.recent_tasks,
                "estimated_tokens": len(recent_completions) * 60
            }
        
        # 사용 가능한 다음 작업
        available_tasks = [
            task for task in state.all_nodes.values()
            if task.status == "available"
        ]
        if available_tasks:
            sections["available_tasks"] = {
                "content": self._format_available_tasks(available_tasks),
                "priority": self.priority_config.available_tasks,
                "estimated_tokens": len(available_tasks) * 70
            }
        
        # 발견된 자산
        if state.discovered_assets:
            sections["discovered_assets"] = {
                "content": self._format_discovered_assets(state.discovered_assets),
                "priority": self.priority_config.discovered_assets,
                "estimated_tokens": len(state.discovered_assets) * 20
            }
        
        # 실행 통계
        sections["statistics"] = {
            "content": self._format_statistics(state),
            "priority": self.priority_config.statistics,
            "estimated_tokens": 150
        }
        
        return sections
    
    def _generate_header(self, state: PTTState) -> str:
        """헤더 정보 생성"""
        total_tasks = len(state.all_nodes)
        completed_tasks = len(state.completed_tasks)
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        header = [
            f"🎯 **Pentesting Task Tree: {state.engagement_scope.engagement_name}**",
            f"📊 Progress: {completed_tasks}/{total_tasks} tasks ({completion_rate:.1f}%)",
            f"🔍 Findings: {len(state.findings)} total"
        ]
        
        if state.findings:
            critical_count = len([f for f in state.findings if f.severity.value == 'critical'])
            high_count = len([f for f in state.findings if f.severity.value == 'high'])
            if critical_count > 0 or high_count > 0:
                header.append(f"⚠️ High-risk findings: {critical_count} critical, {high_count} high")
        
        return "\n".join(header)
    
    def _format_critical_findings(self, findings: List[SecurityFinding]) -> str:
        """중요한 발견사항 포맷팅"""
        if not findings:
            return ""
        
        lines = ["## 🚨 Critical Findings"]
        
        for finding in findings[:5]:  # 최대 5개
            severity_icon = "🔴" if finding.severity.value == 'critical' else "🟠"
            lines.append(
                f"{severity_icon} **{finding.title}** "
                f"({finding.severity.value.upper()})"
            )
            if finding.affected_asset:
                lines.append(f"   📍 Target: {finding.affected_asset}")
            if finding.cvss_score:
                lines.append(f"   📊 CVSS: {finding.cvss_score}")
        
        if len(findings) > 5:
            lines.append(f"... and {len(findings) - 5} more critical findings")
        
        return "\n".join(lines)
    
    def _format_recent_tasks(self, tasks: List[TaskNode]) -> str:
        """최근 완료 작업 포맷팅"""
        if not tasks:
            return ""
        
        lines = ["## ✅ Recently Completed"]
        
        # 시간 순 정렬
        sorted_tasks = sorted(
            tasks, 
            key=lambda t: t.completed_at or datetime.min,
            reverse=True
        )
        
        for task in sorted_tasks[:4]:  # 최대 4개
            phase_icon = self._get_phase_icon(task.phase)
            lines.append(f"{phase_icon} {task.name}")
            if task.findings:
                lines.append(f"   🔍 Findings: {len(task.findings)}")
        
        return "\n".join(lines)
    
    def _format_available_tasks(self, tasks: List[TaskNode]) -> str:
        """사용 가능한 작업 포맷팅"""
        if not tasks:
            return ""
        
        lines = ["## 📋 Available Tasks"]
        
        # 우선순위 순 정렬
        sorted_tasks = sorted(
            tasks,
            key=lambda t: t.priority_score,
            reverse=True
        )
        
        for task in sorted_tasks[:6]:  # 최대 6개
            phase_icon = self._get_phase_icon(task.phase)
            priority = "🔥" if task.priority_score > 0.8 else "📌"
            
            lines.append(
                f"{priority} {task.name} "
                f"({task.phase.value}, priority: {task.priority_score:.1f})"
            )
            
            if task.requires_approval:
                lines.append("   ⚠️ Requires approval")
            
            if task.estimated_duration_seconds:
                duration_min = task.estimated_duration_seconds // 60
                lines.append(f"   ⏱️ Est: {duration_min}min")
        
        return "\n".join(lines)
    
    def _format_discovered_assets(self, assets: Set[str]) -> str:
        """발견된 자산 포맷팅"""
        if not assets:
            return ""
        
        lines = ["## 🌐 Discovered Assets"]
        
        asset_list = list(assets)
        
        # IP와 도메인 분리
        ips = [a for a in asset_list if self._is_ip(a)]
        domains = [a for a in asset_list if not self._is_ip(a)]
        
        if ips:
            lines.append(f"📍 IPs: {', '.join(ips[:5])}")
            if len(ips) > 5:
                lines.append(f"   ... and {len(ips) - 5} more")
        
        if domains:
            lines.append(f"🌍 Domains: {', '.join(domains[:5])}")
            if len(domains) > 5:
                lines.append(f"   ... and {len(domains) - 5} more")
        
        return "\n".join(lines)
    
    def _format_statistics(self, state: PTTState) -> str:
        """통계 정보 포맷팅"""
        total_tasks = len(state.all_nodes)
        completed = len(state.completed_tasks)
        failed = len(state.failed_tasks)
        
        # 페이즈별 분포
        phase_counts = {}
        for task in state.all_nodes.values():
            phase = task.phase.value
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
        
        lines = [
            "## 📊 Statistics",
            f"Tasks: {completed} completed, {failed} failed, {total_tasks - completed - failed} pending"
        ]
        
        if phase_counts:
            phase_summary = ", ".join([
                f"{phase}: {count}" for phase, count in sorted(phase_counts.items())
            ])
            lines.append(f"Phases: {phase_summary}")
        
        return "\n".join(lines)
    
    def _get_phase_icon(self, phase: PentestPhase) -> str:
        """페이즈별 아이콘"""
        icons = {
            PentestPhase.RECONNAISSANCE: "🔍",
            PentestPhase.SCANNING: "📡",
            PentestPhase.ENUMERATION: "📋",
            PentestPhase.VULNERABILITY_ASSESSMENT: "🔍",
            PentestPhase.EXPLOITATION: "💥",
            PentestPhase.POST_EXPLOITATION: "🎯",
            PentestPhase.REPORTING: "📄"
        }
        return icons.get(phase, "📌")
    
    def _is_ip(self, value: str) -> bool:
        """IP 주소 여부 확인"""
        try:
            import ipaddress
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False
    
    def _filter_by_focus(
        self,
        sections: Dict[str, Dict],
        focus_areas: List[str]
    ) -> Dict[str, Dict]:
        """집중 영역에 따른 필터링"""
        if not focus_areas:
            return sections
        
        # 집중 영역별 우선순위 부스트
        focus_boost = {
            "findings": ["critical_findings"],
            "tasks": ["available_tasks", "recent_tasks"],
            "assets": ["discovered_assets"],
            "stats": ["statistics"]
        }
        
        for focus in focus_areas:
            if focus in focus_boost:
                for section_name in focus_boost[focus]:
                    if section_name in sections:
                        sections[section_name]["priority"] *= 1.5
        
        return sections
    
    def _compress_to_limit(
        self,
        sections: Dict[str, Dict],
        target_tokens: int
    ) -> str:
        """토큰 제한에 맞춰 압축"""
        # 우선순위 순 정렬
        sorted_sections = sorted(
            sections.items(),
            key=lambda x: x[1]["priority"],
            reverse=True
        )
        
        result_parts = []
        used_tokens = 0
        
        for section_name, section_data in sorted_sections:
            estimated_tokens = section_data["estimated_tokens"]
            
            if used_tokens + estimated_tokens <= target_tokens:
                # 전체 섹션 포함
                result_parts.append(section_data["content"])
                used_tokens += estimated_tokens
            else:
                # 남은 공간에 맞춰 압축
                remaining_tokens = target_tokens - used_tokens
                if remaining_tokens > 100:  # 최소한의 유용한 정보
                    compressed = self._compress_section(
                        section_data["content"],
                        remaining_tokens
                    )
                    if compressed:
                        result_parts.append(compressed)
                        used_tokens = target_tokens
                break
        
        context = "\n\n".join(result_parts)
        
        # 토큰 사용량 로깅
        logger.info(f"Generated PTT context: ~{used_tokens} tokens, {len(result_parts)} sections")
        
        return context
    
    def _compress_section(self, content: str, max_tokens: int) -> Optional[str]:
        """섹션 압축"""
        lines = content.split('\n')
        
        if not lines:
            return None
        
        # 헤더는 유지
        header = lines[0] if lines[0].startswith('#') else ""
        content_lines = lines[1:] if header else lines
        
        # 토큰 추정 (1 token ≈ 4 characters)
        chars_per_token = 4
        max_chars = max_tokens * chars_per_token
        
        if header:
            max_chars -= len(header) + 2  # 헤더 + 줄바꿈
        
        result_lines = []
        current_chars = 0
        
        for line in content_lines:
            if current_chars + len(line) + 1 <= max_chars:
                result_lines.append(line)
                current_chars += len(line) + 1
            else:
                if result_lines:
                    result_lines.append("... (truncated)")
                break
        
        if header:
            return header + "\n" + "\n".join(result_lines)
        else:
            return "\n".join(result_lines)
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """압축 통계 반환"""
        return {
            "max_context_tokens": self.max_context_tokens,
            "compression_levels": len(self.compression_levels),
            "priority_config": {
                "critical_findings": self.priority_config.critical_findings,
                "recent_tasks": self.priority_config.recent_tasks,
                "available_tasks": self.priority_config.available_tasks,
                "discovered_assets": self.priority_config.discovered_assets,
                "statistics": self.priority_config.statistics
            }
        }