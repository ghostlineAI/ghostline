"""
Safety Service for mental health content validation.

Provides:
- Content screening for potentially harmful advice
- Crisis language detection
- Medical advice boundary checking
- Disclaimer enforcement

This is especially important for the mental health book use case.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class SafetyFlag(str, Enum):
    """Types of safety concerns."""
    CRISIS_LANGUAGE = "crisis_language"
    MEDICAL_ADVICE = "medical_advice"
    SUICIDE_MENTION = "suicide_mention"
    SELF_HARM = "self_harm"
    DRUG_RECOMMENDATION = "drug_recommendation"
    DIAGNOSIS_CLAIM = "diagnosis_claim"
    THERAPY_SUBSTITUTE = "therapy_substitute"
    TRIGGER_CONTENT = "trigger_content"


@dataclass
class SafetyFinding:
    """A safety concern found in content."""
    flag: SafetyFlag
    severity: str  # low, medium, high, critical
    location: str  # Where in the text
    matched_text: str
    recommendation: str


@dataclass
class SafetyCheckResult:
    """Result from a safety check."""
    is_safe: bool
    findings: list[SafetyFinding] = field(default_factory=list)
    requires_disclaimer: bool = False
    suggested_disclaimer: Optional[str] = None
    
    def get_critical_findings(self) -> list[SafetyFinding]:
        """Get only critical/high severity findings."""
        return [f for f in self.findings if f.severity in ("critical", "high")]
    
    def get_summary(self) -> str:
        """Get a summary of findings."""
        if self.is_safe and not self.findings:
            return "Content passed safety check."
        
        lines = [f"Safety check: {'PASSED' if self.is_safe else 'FAILED'}"]
        
        for finding in self.findings:
            lines.append(f"  [{finding.severity.upper()}] {finding.flag.value}: {finding.matched_text[:50]}...")
        
        if self.requires_disclaimer:
            lines.append(f"  Disclaimer required: {self.suggested_disclaimer[:100]}...")
        
        return "\n".join(lines)


class SafetyService:
    """
    Service for validating mental health content safety.
    
    This service screens content for:
    - Crisis language that could indicate or trigger harm
    - Medical advice that should come from professionals
    - Content that could substitute for proper therapy
    - Trigger content that needs warnings
    
    It does NOT censor content, but flags concerns for review
    and suggests appropriate disclaimers.
    """
    
    # Crisis/harm patterns (these should trigger immediate flags)
    CRISIS_PATTERNS = [
        (r'\b(kill|end)\s+(my|your)?self\b', SafetyFlag.SUICIDE_MENTION, "critical"),
        (r'\b(suicide|suicidal)\b', SafetyFlag.SUICIDE_MENTION, "high"),
        (r'\b(cut|cutting|hurt)\s+(my|your)?self\b', SafetyFlag.SELF_HARM, "high"),
        (r'\bself[\s-]?harm\b', SafetyFlag.SELF_HARM, "high"),
        (r'\bwant\s+to\s+die\b', SafetyFlag.CRISIS_LANGUAGE, "critical"),
        (r'\b(no|not)\s+worth\s+living\b', SafetyFlag.CRISIS_LANGUAGE, "high"),
    ]
    
    # Medical advice patterns (should include disclaimers)
    MEDICAL_PATTERNS = [
        (r'\byou\s+should\s+(take|start|stop)\s+\w*\s*(medication|medicine|drug|pill)', SafetyFlag.DRUG_RECOMMENDATION, "high"),
        (r'\b(increase|decrease|adjust)\s+your\s+(dose|dosage|medication)', SafetyFlag.DRUG_RECOMMENDATION, "high"),
        (r'\byou\s+(have|are|suffer\s+from)\s+(depression|anxiety|bipolar|schizophrenia|ptsd|ocd)', SafetyFlag.DIAGNOSIS_CLAIM, "medium"),
        (r'\bthis\s+(is|means)\s+you\s+are\s+(depressed|anxious|mentally\s+ill)', SafetyFlag.DIAGNOSIS_CLAIM, "medium"),
        (r'\binstead\s+of\s+(therapy|counseling|seeing\s+a\s+therapist)', SafetyFlag.THERAPY_SUBSTITUTE, "medium"),
        (r'\byou\s+don\'?t\s+need\s+(therapy|a\s+therapist|professional\s+help)', SafetyFlag.THERAPY_SUBSTITUTE, "high"),
    ]
    
    # Trigger content patterns (may need content warnings)
    TRIGGER_PATTERNS = [
        (r'\b(graphic|detailed)\s+(description|account)\s+of\s+(trauma|abuse|violence)', SafetyFlag.TRIGGER_CONTENT, "medium"),
        (r'\b(childhood|sexual|physical)\s+(abuse|trauma)', SafetyFlag.TRIGGER_CONTENT, "low"),
        (r'\b(eating\s+disorder|anorexia|bulimia)\b', SafetyFlag.TRIGGER_CONTENT, "low"),
    ]
    
    # Standard disclaimers
    MENTAL_HEALTH_DISCLAIMER = """
IMPORTANT DISCLAIMER: This content is for informational and educational purposes only. 
It is not intended to be a substitute for professional medical advice, diagnosis, or treatment. 
If you are experiencing a mental health crisis, please contact a mental health professional 
or call a crisis helpline immediately. In the US, you can call 988 (Suicide & Crisis Lifeline) 
or text HOME to 741741 (Crisis Text Line).
"""
    
    MEDICAL_DISCLAIMER = """
MEDICAL DISCLAIMER: The information in this content should not be considered medical advice. 
Always consult with a qualified healthcare provider before making any changes to medication 
or treatment plans.
"""
    
    def __init__(
        self,
        strict_mode: bool = False,
        require_disclaimer_for_mental_health: bool = True,
    ):
        """
        Initialize the safety service.
        
        Args:
            strict_mode: If True, any finding fails the check
            require_disclaimer_for_mental_health: If True, suggest disclaimers
        """
        self.strict_mode = strict_mode
        self.require_disclaimer = require_disclaimer_for_mental_health
        
        # Compile all patterns
        self.patterns = []
        for pattern, flag, severity in self.CRISIS_PATTERNS + self.MEDICAL_PATTERNS + self.TRIGGER_PATTERNS:
            self.patterns.append((re.compile(pattern, re.IGNORECASE), flag, severity))
    
    def check_content(self, content: str) -> SafetyCheckResult:
        """
        Check content for safety concerns.
        
        Args:
            content: The text content to check
            
        Returns:
            SafetyCheckResult with findings and recommendations
        """
        findings = []
        
        # Check all patterns
        for pattern, flag, severity in self.patterns:
            for match in pattern.finditer(content):
                # Get context around the match
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 50)
                context = content[start:end]
                
                finding = SafetyFinding(
                    flag=flag,
                    severity=severity,
                    location=f"chars {match.start()}-{match.end()}",
                    matched_text=match.group(),
                    recommendation=self._get_recommendation(flag, severity),
                )
                findings.append(finding)
        
        # Determine if safe
        critical_findings = [f for f in findings if f.severity in ("critical", "high")]
        is_safe = len(critical_findings) == 0
        
        if self.strict_mode and findings:
            is_safe = False
        
        # Determine disclaimer needs
        requires_disclaimer = False
        suggested_disclaimer = None
        
        if self.require_disclaimer:
            # Check if content discusses mental health topics
            mental_health_keywords = [
                "mental health", "anxiety", "depression", "therapy",
                "counseling", "stress", "trauma", "coping", "wellness",
                "self-care", "mindfulness", "emotional", "psychological"
            ]
            
            content_lower = content.lower()
            has_mental_health_content = any(kw in content_lower for kw in mental_health_keywords)
            
            if has_mental_health_content:
                requires_disclaimer = True
                suggested_disclaimer = self.MENTAL_HEALTH_DISCLAIMER.strip()
            
            # Check if content mentions medications
            if any(f.flag == SafetyFlag.DRUG_RECOMMENDATION for f in findings):
                requires_disclaimer = True
                suggested_disclaimer = self.MEDICAL_DISCLAIMER.strip()
        
        return SafetyCheckResult(
            is_safe=is_safe,
            findings=findings,
            requires_disclaimer=requires_disclaimer,
            suggested_disclaimer=suggested_disclaimer,
        )
    
    def _get_recommendation(self, flag: SafetyFlag, severity: str) -> str:
        """Get a recommendation for handling a finding."""
        recommendations = {
            SafetyFlag.SUICIDE_MENTION: "Add crisis resources. Consider rewording to focus on hope and recovery.",
            SafetyFlag.SELF_HARM: "Add content warning and crisis resources. Ensure context is supportive.",
            SafetyFlag.CRISIS_LANGUAGE: "Review for tone. Add crisis hotline information.",
            SafetyFlag.DRUG_RECOMMENDATION: "Reword to suggest consulting a healthcare provider. Add medical disclaimer.",
            SafetyFlag.DIAGNOSIS_CLAIM: "Reword to suggest seeing a professional for diagnosis.",
            SafetyFlag.THERAPY_SUBSTITUTE: "Emphasize that content complements, not replaces, professional help.",
            SafetyFlag.TRIGGER_CONTENT: "Add content warning at the beginning of the section.",
            SafetyFlag.MEDICAL_ADVICE: "Add medical disclaimer. Suggest consulting a professional.",
        }
        
        return recommendations.get(flag, "Review content for appropriateness.")
    
    def add_disclaimer(self, content: str, disclaimer_type: str = "mental_health") -> str:
        """
        Add an appropriate disclaimer to content.
        
        Args:
            content: The content to add disclaimer to
            disclaimer_type: Type of disclaimer ("mental_health" or "medical")
            
        Returns:
            Content with disclaimer prepended
        """
        if disclaimer_type == "medical":
            disclaimer = self.MEDICAL_DISCLAIMER
        else:
            disclaimer = self.MENTAL_HEALTH_DISCLAIMER
        
        return f"{disclaimer.strip()}\n\n---\n\n{content}"
    
    def get_crisis_resources(self) -> str:
        """Get formatted crisis resources to append to content."""
        return """
---

If you or someone you know is struggling with mental health or having thoughts of suicide, 
please reach out for help:

- **National Suicide Prevention Lifeline**: 988 (US)
- **Crisis Text Line**: Text HOME to 741741 (US)
- **International Association for Suicide Prevention**: https://www.iasp.info/resources/Crisis_Centres/
- **SAMHSA National Helpline**: 1-800-662-4357 (US)

You are not alone, and help is available.
"""


# Global singleton
_safety_service: Optional[SafetyService] = None


def get_safety_service() -> SafetyService:
    """Get the global safety service instance."""
    global _safety_service
    if _safety_service is None:
        _safety_service = SafetyService()
    return _safety_service


def reset_safety_service():
    """Reset the global service (for testing)."""
    global _safety_service
    _safety_service = None



