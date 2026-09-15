"""
BIS Compass Application Package
"""

# Import agents
from .agents import (
    CertificationAgent,
    get_certification_agent,
    CertificationInfo,
    CertificationRequirement,
    CertificationProcess,
    TestingAgent,
    get_testing_agent,
    TestingInformation,
    TestingRequirement,
    LaboratoryInfo,
    LaboratoryAgent,
    get_laboratory_agent,
    Laboratory,
    LabSearchCriteria,
    LabTestScope,
    ComplianceGapAgent,
    get_compliance_gap_agent,
    ComplianceRequirement,
    GapAnalysisResult,
    DocumentAnalysisContext,
    CitationVerificationAgent,
    get_citation_verification_agent,
    Citation,
    Claim,
    VerificationResult,
    OrchestratorAgent,
    get_orchestrator_agent,
    OrchestrationInput,
    OrchestrationResult
)

# Import services
from .services import (
    get_web_retrieval_service,
    WebRetrievalService,
    WebSearchResult
)

# Import evaluation module
from .evaluation import (
    RAGEvaluator,
    EvaluationResult,
    GroundTruth,
    RetrievalResult,
    GenerationResult,
    RAGEvaluationRunner,
    EvaluationConfig,
    EvaluationReport,
    quick_evaluate,
    TestDatasetManager,
    TestDataset,
    create_sample_bis_dataset,
    save_sample_dataset
)

# Import core modules
from .core import config

# Import models
from .models import standard

# Import ingestion (placeholder for now)

__all__ = [
    # Agents
    "CertificationAgent",
    "get_certification_agent",
    "CertificationInfo",
    "CertificationRequirement",
    "CertificationProcess",
    "TestingAgent",
    "get_testing_agent",
    "TestingInformation",
    "TestingRequirement",
    "LaboratoryInfo",
    "LaboratoryAgent",
    "get_laboratory_agent",
    "Laboratory",
    "LabSearchCriteria",
    "LabTestScope",
    "ComplianceGapAgent",
    "get_compliance_gap_agent",
    "ComplianceRequirement",
    "GapAnalysisResult",
    "DocumentAnalysisContext",
    "CitationVerificationAgent",
    "get_citation_verification_agent",
    "Citation",
    "Claim",
    "VerificationResult",
    "OrchestratorAgent",
    "get_orchestrator_agent",
    "OrchestrationInput",
    "OrchestrationResult",

    # Services
    "get_web_retrieval_service",
    "WebRetrievalService",
    "WebSearchResult",

    # Evaluation
    "RAGEvaluator",
    "EvaluationResult",
    "GroundTruth",
    "RetrievalResult",
    "GenerationResult",
    "RAGEvaluationRunner",
    "EvaluationConfig",
    "EvaluationReport",
    "quick_evaluate",
    "TestDatasetManager",
    "TestDataset",
    "create_sample_bis_dataset",
    "save_sample_dataset",

    # Core
    "config",

    # Models
    "standard"
]