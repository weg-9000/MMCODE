"""Quality Assessment - Document quality evaluation and scoring"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ..models.document_models import GeneratedDocument, DocumentationSuite, DocumentType


class QualityAssessment:
    """Evaluates and scores document quality across multiple dimensions"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Quality metrics weights
        self.weights = config.get("quality_weights", {
            "completeness": 0.3,
            "accuracy": 0.25,
            "readability": 0.25,
            "coverage": 0.2
        })
        
        # Quality thresholds
        self.thresholds = config.get("quality_thresholds", {
            "excellent": 0.9,
            "good": 0.8,
            "acceptable": 0.7,
            "poor": 0.5
        })
    
    async def assess_document_quality(self, document: GeneratedDocument) -> float:
        """Assess quality of a single document"""
        
        # Calculate individual quality metrics
        completeness = await self._assess_completeness(document)
        accuracy = await self._assess_accuracy(document)
        readability = await self._assess_readability(document)
        coverage = await self._assess_coverage(document)
        
        # Update document with individual scores
        document.completeness_score = completeness
        document.accuracy_score = accuracy
        document.readability_score = readability
        document.coverage_score = coverage
        
        # Calculate weighted overall score
        overall_score = (
            completeness * self.weights["completeness"] +
            accuracy * self.weights["accuracy"] +
            readability * self.weights["readability"] +
            coverage * self.weights["coverage"]
        )
        
        return min(overall_score, 1.0)
    
    async def assess_suite_quality(self, suite: DocumentationSuite) -> Dict[str, Any]:
        """Assess quality of entire documentation suite"""
        
        if not suite.documents:
            return {
                "overall_score": 0.0,
                "document_scores": {},
                "coverage_analysis": {},
                "recommendations": ["Add documents to the suite"],
                "quality_level": "poor"
            }
        
        document_scores = {}
        total_score = 0.0
        
        # Assess each document
        for doc in suite.documents:
            doc_score = await self.assess_document_quality(doc)
            document_scores[doc.document_id] = {
                "type": doc.document_type.value,
                "title": doc.title,
                "overall_score": doc_score,
                "completeness": doc.completeness_score,
                "accuracy": doc.accuracy_score,
                "readability": doc.readability_score,
                "coverage": doc.coverage_score
            }
            total_score += doc_score
        
        # Calculate suite-level metrics
        overall_score = total_score / len(suite.documents)
        coverage_analysis = await self._assess_suite_coverage(suite)
        recommendations = await self._generate_recommendations(suite, document_scores)
        quality_level = self._determine_quality_level(overall_score)
        
        return {
            "overall_score": overall_score,
            "document_scores": document_scores,
            "coverage_analysis": coverage_analysis,
            "recommendations": recommendations,
            "quality_level": quality_level,
            "assessment_timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics_breakdown": {
                "avg_completeness": sum(doc.completeness_score for doc in suite.documents) / len(suite.documents),
                "avg_accuracy": sum(doc.accuracy_score for doc in suite.documents) / len(suite.documents),
                "avg_readability": sum(doc.readability_score for doc in suite.documents) / len(suite.documents),
                "avg_coverage": sum(doc.coverage_score for doc in suite.documents) / len(suite.documents)
            }
        }
    
    async def _assess_completeness(self, document: GeneratedDocument) -> float:
        """Assess document completeness"""
        score = 0.0
        
        # Content length assessment
        if document.word_count > 0:
            # Base score for having content
            score += 0.3
            
            # Bonus for adequate length (varies by document type)
            min_words = self._get_min_word_count(document.document_type)
            if document.word_count >= min_words:
                score += 0.3
            elif document.word_count >= min_words * 0.7:
                score += 0.2
            elif document.word_count >= min_words * 0.5:
                score += 0.1
        
        # Section completeness
        if document.sections:
            expected_sections = self._get_expected_sections(document.document_type)
            if expected_sections:
                section_ratio = len(document.sections) / len(expected_sections)
                score += min(section_ratio * 0.4, 0.4)
            else:
                score += 0.2  # Bonus for having any sections
        
        return min(score, 1.0)
    
    async def _assess_accuracy(self, document: GeneratedDocument) -> float:
        """Assess document accuracy based on source alignment"""
        score = 0.0
        
        # Source data alignment
        if document.source_analysis:
            score += 0.3  # Has source analysis
        if document.source_architecture:
            score += 0.3  # Has source architecture
        if document.source_stack:
            score += 0.2  # Has source stack
        
        # Template usage (indicates structured approach)
        if document.template_used:
            score += 0.2
        
        return min(score, 1.0)
    
    async def _assess_readability(self, document: GeneratedDocument) -> float:
        """Assess document readability"""
        score = 0.0
        
        if not document.content:
            return 0.0
        
        content = document.content.lower()
        
        # Structure indicators
        structure_indicators = [
            "# ",      # Headers
            "## ",     # Subheaders
            "- ",      # Lists
            "1. ",     # Numbered lists
            "```",     # Code blocks
            "**",      # Bold text
            "*"        # Italic text
        ]
        
        structure_score = 0
        for indicator in structure_indicators:
            if indicator in document.content:
                structure_score += 1
        
        score += min(structure_score / len(structure_indicators), 0.4)
        
        # Length appropriateness (not too short, not too long)
        if document.word_count > 50:
            score += 0.2
        if 100 <= document.word_count <= 5000:
            score += 0.2
        
        # Clear language indicators
        clarity_indicators = ["example", "step", "following", "first", "then", "finally"]
        clarity_score = sum(1 for indicator in clarity_indicators if indicator in content)
        score += min(clarity_score / 10, 0.2)
        
        return min(score, 1.0)
    
    async def _assess_coverage(self, document: GeneratedDocument) -> float:
        """Assess how well document covers expected topics"""
        score = 0.0
        
        if not document.content:
            return 0.0
        
        content = document.content.lower()
        
        # Document type specific coverage
        expected_topics = self._get_expected_topics(document.document_type)
        
        if expected_topics:
            covered_topics = 0
            for topic in expected_topics:
                if topic.lower() in content:
                    covered_topics += 1
            
            coverage_ratio = covered_topics / len(expected_topics)
            score += coverage_ratio * 0.6
        else:
            score += 0.3  # Default coverage if no specific topics
        
        # Source coverage
        if document.source_analysis:
            entities = document.source_analysis.get("entities", [])
            use_cases = document.source_analysis.get("use_cases", [])
            
            # Check if entities are mentioned
            if entities:
                covered_entities = sum(1 for entity in entities if entity.lower() in content)
                entity_coverage = covered_entities / len(entities)
                score += entity_coverage * 0.2
            
            # Check if use cases are addressed
            if use_cases:
                covered_use_cases = sum(1 for uc in use_cases if any(word in content for word in uc.lower().split()[:3]))
                use_case_coverage = covered_use_cases / len(use_cases)
                score += use_case_coverage * 0.2
        
        return min(score, 1.0)
    
    async def _assess_suite_coverage(self, suite: DocumentationSuite) -> Dict[str, Any]:
        """Assess coverage of the entire documentation suite"""
        
        # Required document types for a complete suite
        required_types = [
            DocumentType.README,
            DocumentType.API_DOCUMENTATION,
            DocumentType.TECHNICAL_SPECIFICATION,
            DocumentType.DEPLOYMENT_GUIDE
        ]
        
        # Optional but valuable document types
        optional_types = [
            DocumentType.OPENAPI,
            DocumentType.ERD,
            DocumentType.CONTEXT_DIAGRAM,
            DocumentType.USER_MANUAL
        ]
        
        present_types = [doc.document_type for doc in suite.documents]
        
        # Calculate coverage
        required_coverage = sum(1 for dt in required_types if dt in present_types) / len(required_types)
        optional_coverage = sum(1 for dt in optional_types if dt in present_types) / len(optional_types)
        
        missing_required = [dt.value for dt in required_types if dt not in present_types]
        missing_optional = [dt.value for dt in optional_types if dt not in present_types]
        
        return {
            "required_coverage": required_coverage,
            "optional_coverage": optional_coverage,
            "overall_coverage": (required_coverage * 0.8 + optional_coverage * 0.2),
            "missing_required": missing_required,
            "missing_optional": missing_optional,
            "present_types": [dt.value for dt in present_types],
            "coverage_score": min(required_coverage * 1.2, 1.0)  # Emphasize required docs
        }
    
    async def _generate_recommendations(self, 
                                      suite: DocumentationSuite, 
                                      document_scores: Dict[str, Any]) -> List[str]:
        """Generate recommendations for improving documentation quality"""
        recommendations = []
        
        # Analyze document scores for issues
        low_scoring_docs = {
            doc_id: score for doc_id, score in document_scores.items()
            if score["overall_score"] < self.thresholds["acceptable"]
        }
        
        if low_scoring_docs:
            recommendations.append(f"Improve {len(low_scoring_docs)} documents with scores below 0.7")
        
        # Check for missing document types
        coverage = await self._assess_suite_coverage(suite)
        if coverage["missing_required"]:
            recommendations.append(f"Add missing required documents: {', '.join(coverage['missing_required'])}")
        
        # Specific metric recommendations
        avg_metrics = {
            "completeness": sum(doc.completeness_score for doc in suite.documents) / len(suite.documents),
            "accuracy": sum(doc.accuracy_score for doc in suite.documents) / len(suite.documents),
            "readability": sum(doc.readability_score for doc in suite.documents) / len(suite.documents),
            "coverage": sum(doc.coverage_score for doc in suite.documents) / len(suite.documents)
        }
        
        for metric, score in avg_metrics.items():
            if score < self.thresholds["acceptable"]:
                recommendations.append(f"Improve {metric} across documents (current: {score:.2f})")
        
        # Document-specific recommendations
        for doc in suite.documents:
            if doc.word_count < self._get_min_word_count(doc.document_type):
                recommendations.append(f"Expand {doc.document_type.value} document (currently {doc.word_count} words)")
            
            if doc.completeness_score < 0.7:
                recommendations.append(f"Complete missing sections in {doc.document_type.value}")
        
        # If no specific issues found
        if not recommendations:
            recommendations.append("Documentation quality is good. Consider adding optional documents for completeness.")
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def _determine_quality_level(self, score: float) -> str:
        """Determine quality level based on score"""
        if score >= self.thresholds["excellent"]:
            return "excellent"
        elif score >= self.thresholds["good"]:
            return "good"
        elif score >= self.thresholds["acceptable"]:
            return "acceptable"
        else:
            return "poor"
    
    def _get_min_word_count(self, doc_type: DocumentType) -> int:
        """Get minimum expected word count for document type"""
        word_counts = {
            DocumentType.README: 200,
            DocumentType.API_DOCUMENTATION: 500,
            DocumentType.TECHNICAL_SPECIFICATION: 1000,
            DocumentType.DEPLOYMENT_GUIDE: 300,
            DocumentType.USER_MANUAL: 400,
            DocumentType.OPENAPI: 50,  # JSON content
            DocumentType.ERD: 20,      # Diagram
            DocumentType.CONTEXT_DIAGRAM: 20  # Diagram
        }
        return word_counts.get(doc_type, 100)
    
    def _get_expected_sections(self, doc_type: DocumentType) -> List[str]:
        """Get expected sections for document type"""
        sections = {
            DocumentType.README: [
                "title", "description", "installation", "usage", "features"
            ],
            DocumentType.API_DOCUMENTATION: [
                "overview", "authentication", "endpoints", "examples"
            ],
            DocumentType.TECHNICAL_SPECIFICATION: [
                "overview", "requirements", "architecture", "implementation"
            ],
            DocumentType.DEPLOYMENT_GUIDE: [
                "prerequisites", "installation", "configuration", "deployment"
            ]
        }
        return sections.get(doc_type, [])
    
    def _get_expected_topics(self, doc_type: DocumentType) -> List[str]:
        """Get expected topics for document type coverage assessment"""
        topics = {
            DocumentType.README: [
                "installation", "usage", "features", "requirements", "examples"
            ],
            DocumentType.API_DOCUMENTATION: [
                "authentication", "endpoints", "request", "response", "error"
            ],
            DocumentType.TECHNICAL_SPECIFICATION: [
                "architecture", "database", "security", "performance", "scalability"
            ],
            DocumentType.DEPLOYMENT_GUIDE: [
                "docker", "environment", "configuration", "production", "troubleshooting"
            ],
            DocumentType.OPENAPI: [
                "paths", "components", "schemas", "security"
            ],
            DocumentType.DEPLOYMENT_GUIDE: [
                "prerequisites", "docker", "environment", "production"
            ]
        }
        return topics.get(doc_type, [])
    
    def get_quality_report(self, assessment_result: Dict[str, Any]) -> str:
        """Generate a human-readable quality report"""
        report_lines = []
        
        report_lines.append(f"# Documentation Quality Report")
        report_lines.append(f"**Overall Score**: {assessment_result['overall_score']:.2f}/1.00 ({assessment_result['quality_level'].title()})")
        report_lines.append("")
        
        # Metrics breakdown
        metrics = assessment_result.get('metrics_breakdown', {})
        report_lines.append("## Quality Metrics")
        report_lines.append(f"- **Completeness**: {metrics.get('avg_completeness', 0):.2f}")
        report_lines.append(f"- **Accuracy**: {metrics.get('avg_accuracy', 0):.2f}")
        report_lines.append(f"- **Readability**: {metrics.get('avg_readability', 0):.2f}")
        report_lines.append(f"- **Coverage**: {metrics.get('avg_coverage', 0):.2f}")
        report_lines.append("")
        
        # Coverage analysis
        coverage = assessment_result.get('coverage_analysis', {})
        report_lines.append("## Coverage Analysis")
        report_lines.append(f"- **Required Documents**: {coverage.get('required_coverage', 0):.0%}")
        report_lines.append(f"- **Optional Documents**: {coverage.get('optional_coverage', 0):.0%}")
        
        if coverage.get('missing_required'):
            report_lines.append(f"- **Missing Required**: {', '.join(coverage['missing_required'])}")
        
        report_lines.append("")
        
        # Recommendations
        recommendations = assessment_result.get('recommendations', [])
        if recommendations:
            report_lines.append("## Recommendations")
            for i, rec in enumerate(recommendations, 1):
                report_lines.append(f"{i}. {rec}")
        
        return "\n".join(report_lines)