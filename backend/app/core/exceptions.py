"""
Custom Application Exceptions for BIS-Compass.
"""

class ComplianceResearchException(Exception):
    """Base exception for compliance research pipeline errors"""
    pass

class AIServiceUnavailableException(ComplianceResearchException):
    """Raised when NVIDIA NIM or configured AI reasoning provider is unavailable"""
    pass

class EvidenceVerificationException(ComplianceResearchException):
    """Raised when evidence fails authoritative validation gates"""
    pass
