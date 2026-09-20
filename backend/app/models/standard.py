from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Table, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.db.session import Base

# Association table for standard-product categories
standard_product_categories = Table(
    'standard_product_categories',
    Base.metadata,
    Column('standard_id', Integer, ForeignKey('standards.id'), primary_key=True),
    Column('category', String(100), primary_key=True)
)

class Source(Base):
    __tablename__ = 'sources'

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(50), nullable=False)  # official_bis, government, ministry, etc.
    organization = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False)
    title = Column(String(500), nullable=False)
    publication_date = Column(DateTime, nullable=True)
    last_verified = Column(DateTime, nullable=True)
    authority_level = Column(Integer, nullable=False)  # 1-7, where 1 is highest authority
    checksum = Column(String(64), nullable=False)  # SHA256)
    version = Column(String(50), nullable=True)
    effective_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    standards = relationship("Standard", back_populates="source")
    schemes = relationship("Scheme", back_populates="source")

    # Indexes
    __table_args__ = (
        Index('ix_sources_authority_level', 'authority_level'),
        Index('ix_sources_organization', 'organization'),
    )

class StandardRelationshipType:
    PRIMARY_PRODUCT_STANDARD = "PRIMARY_PRODUCT_STANDARD"
    REFERENCED_STANDARD = "REFERENCED_STANDARD"
    TEST_METHOD_STANDARD = "TEST_METHOD_STANDARD"
    MATERIAL_STANDARD = "MATERIAL_STANDARD"
    COMPONENT_STANDARD = "COMPONENT_STANDARD"
    REGULATORY_DOCUMENT = "REGULATORY_DOCUMENT"

class Standard(Base):
    __tablename__ = 'standards'

    id = Column(Integer, primary_key=True, index=True)
    standard_number = Column(String(50), nullable=False, unique=True)
    title = Column(String(500), nullable=False)
    scope = Column(Text, nullable=True)
    status = Column(String(50), nullable=False)  # active, withdrawn, under_revision
    edition = Column(String(20), nullable=True)
    publication_date = Column(DateTime, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    source_id = Column(Integer, ForeignKey('sources.id'), nullable=True)
    source_url = Column(String(1000), nullable=True)
    relationship_type = Column(String(50), default="PRIMARY_PRODUCT_STANDARD", index=True)
    parent_standard_id = Column(Integer, ForeignKey('standards.id'), nullable=True)
    authority_tier = Column(Integer, default=1)
    is_qco_mandatory = Column(Boolean, default=False)

    # Relationships
    source = relationship("Source", back_populates="standards")
    clauses = relationship("Clause", back_populates="standard", cascade="all, delete-orphan")
    schemes = relationship("Scheme", back_populates="standard")

    # Indexes
    __table_args__ = (
        Index('ix_standards_standard_number', 'standard_number'),
        Index('ix_standards_status', 'status'),
        Index('ix_standards_publication_date', 'publication_date'),
    )

class Clause(Base):
    __tablename__ = 'clauses'

    id = Column(Integer, primary_key=True, index=True)
    standard_id = Column(Integer, ForeignKey('standards.id'), nullable=False)
    clause_number = Column(String(20), nullable=False)
    heading = Column(String(200), nullable=True)
    text = Column(Text, nullable=False)
    page = Column(Integer, nullable=True)
    section = Column(String(100), nullable=True)

    # Vector embedding for semantic search
    embedding = Column(Vector(768), nullable=True)  # Adjust dimension based on embedding model

    # Relationships
    standard = relationship("Standard", back_populates="clauses")

    # Indexes
    __table_args__ = (
        Index('ix_clauses_standard_id', 'standard_id'),
        Index('ix_clauses_clause_number', 'clause_number'),
        # Vector similarity index will be created separately
    )

class Scheme(Base):
    __tablename__ = 'schemes'

    id = Column(Integer, primary_key=True, index=True)
    scheme_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    conditions = Column(Text, nullable=True)  # JSON or text description
    documents_required = Column(Text, nullable=True)  # JSON array
    testing_required = Column(Boolean, default=False)
    source_id = Column(Integer, ForeignKey('sources.id'), nullable=True)
    source_url = Column(String(1000), nullable=True)
    standard_id = Column(Integer, ForeignKey('standards.id'), nullable=True)

    # Relationships
    source = relationship("Source", back_populates="schemes")
    standard = relationship("Standard", back_populates="schemes")

    # Indexes
    __table_args__ = (
        Index('ix_schemes_scheme_name', 'scheme_name'),
        Index('ix_schemes_testing_required', 'testing_required'),
    )

class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    sub_category = Column(String(100), nullable=True)
    materials = Column(Text, nullable=True)  # JSON array
    intended_use = Column(Text, nullable=True)
    technical_attributes = Column(Text, nullable=True)  # JSON object
    market = Column(String(100), nullable=True)  # domestic, international, etc.
    created_at = Column(DateTime, server_default=func.now())

    # Indexes
    __table_args__ = (
        Index('ix_products_name', 'name'),
        Index('ix_products_category', 'category'),
    )

class ComplianceResult(Base):
    __tablename__ = 'compliance_results'

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    standard_id = Column(Integer, ForeignKey('standards.id'), nullable=False)
    applicability_score = Column(Integer, nullable=False)  # 0-100
    confidence = Column(Integer, nullable=False)  # 0-100
    reasoning = Column(Text, nullable=True)  # JSON array
    supporting_clauses = Column(Text, nullable=True)  # JSON array of clause IDs
    missing_information = Column(Text, nullable=True)  # JSON array
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    product = relationship("Product")
    standard = relationship("Standard")

    # Indexes
    __table_args__ = (
        Index('ix_compliance_results_product_id', 'product_id'),
        Index('ix_compliance_results_standard_id', 'standard_id'),
        Index('ix_compliance_results_applicability_score', 'applicability_score'),
    )

class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=True, default="anonymous")
    action = Column(String(100), nullable=False)
    query = Column(Text, nullable=True)
    selected_model = Column(String(100), nullable=True)
    retrieval_sources = Column(Text, nullable=True)  # JSON array
    citations = Column(Text, nullable=True)  # JSON array
    execution_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index('ix_audit_logs_action', 'action'),
        Index('ix_audit_logs_created_at', 'created_at'),
    )

class EvaluationRecord(Base):
    __tablename__ = 'evaluation_records'

    id = Column(Integer, primary_key=True, index=True)
    benchmark_name = Column(String(200), nullable=False)
    precision_at_1 = Column(Integer, nullable=True)  # percentage 0-100
    precision_at_3 = Column(Integer, nullable=True)
    recall_at_3 = Column(Integer, nullable=True)
    mrr = Column(Integer, nullable=True)
    groundedness = Column(Integer, nullable=True)
    citation_accuracy = Column(Integer, nullable=True)
    abstention_accuracy = Column(Integer, nullable=True)
    sample_count = Column(Integer, nullable=False, default=0)
    details = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime, server_default=func.now())

class LaboratoryRecord(Base):
    __tablename__ = 'laboratories'

    id = Column(Integer, primary_key=True, index=True)
    lab_name = Column(String(300), nullable=False)
    address = Column(String(500), nullable=False)
    location = Column(String(200), nullable=False)
    contact_person = Column(String(200), nullable=True)
    phone = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True)
    website = Column(String(300), nullable=True)
    accreditation_body = Column(String(100), default="NABL")
    accreditation_number = Column(String(100), nullable=True)
    is_bis_recognized = Column(Boolean, default=True)
    bis_recognition_number = Column(String(100), nullable=True)
    accredited_scopes = Column(Text, nullable=True)  # JSON list
    testing_facilities = Column(Text, nullable=True)  # JSON list
    geographical_coverage = Column(String(200), default="All India")
    sample_collection_facility = Column(Boolean, default=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    source_url = Column(String(1000), nullable=True)
    verified_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class DiscoveredDocument(Base):
    """Dynamic cache of verified official web documents and standards publications"""
    __tablename__ = 'discovered_documents'

    id = Column(Integer, primary_key=True, index=True)
    source_url = Column(String(1000), nullable=False, unique=True, index=True)
    domain = Column(String(200), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    publisher = Column(String(200), nullable=True)
    publication_date = Column(DateTime, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    version = Column(String(50), nullable=True)
    checksum = Column(String(64), nullable=False, index=True)
    authority_level = Column(Integer, default=5, index=True)  # 1=BIS, 2=Gov, 3=ISO, 4=Reputable, 5=Web
    file_type = Column(String(20), default="html")  # html, pdf, doc
    content_text = Column(Text, nullable=False)
    structured_metadata = Column(Text, nullable=True)  # JSON
    extracted_clauses = Column(Text, nullable=True)  # JSON array of extracted clauses
    retrieved_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())

class ResearchSession(Base):
    """Immutable audit trail and research graph for open-world product investigations"""
    __tablename__ = 'research_sessions'

    id = Column(Integer, primary_key=True, index=True)
    session_uuid = Column(String(64), unique=True, index=True)
    query = Column(Text, nullable=False)
    normalized_product = Column(String(300), nullable=True, index=True)
    product_understanding = Column(Text, nullable=True)  # JSON
    search_plan = Column(Text, nullable=True)  # JSON
    sources_investigated = Column(Text, nullable=True)  # JSON
    documents_used = Column(Text, nullable=True)  # JSON
    applicable_standards = Column(Text, nullable=True)  # JSON
    rejected_candidates = Column(Text, nullable=True)  # JSON
    research_graph = Column(Text, nullable=True)  # JSON
    overall_assessment = Column(Text, nullable=True)
    execution_time_seconds = Column(Integer, nullable=True)
    model_used = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class CertificationEvidence(Base):
    """Authoritative certification and mandatory QCO evidence"""
    __tablename__ = 'certification_evidence'

    id = Column(Integer, primary_key=True, index=True)
    standard_id = Column(Integer, ForeignKey('standards.id'), nullable=False, index=True)
    scheme_name = Column(String(200), nullable=True)
    license_status = Column(String(50), default="NOT_VERIFIED")  # VERIFIED, NOT_VERIFIED, EXEMPT
    mandatory_status = Column(String(50), default="NOT_VERIFIED")  # MANDATORY, VOLUNTARY, NOT_VERIFIED
    qco_order_number = Column(String(200), nullable=True)
    gazette_url = Column(String(1000), nullable=True)
    effective_date = Column(DateTime, nullable=True)
    evidence_text = Column(Text, nullable=True)
    authority_tier = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())

class TestingEvidence(Base):
    """Authoritative testing requirements and methods linked to standard clauses"""
    __tablename__ = 'testing_evidence'

    id = Column(Integer, primary_key=True, index=True)
    standard_id = Column(Integer, ForeignKey('standards.id'), nullable=False, index=True)
    test_name = Column(String(300), nullable=False)
    test_method = Column(String(300), nullable=True)
    clause_number = Column(String(50), nullable=True)
    is_mandatory = Column(Boolean, default=False)
    evidence_text = Column(Text, nullable=True)
    source_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class LaboratoryEvidence(Base):
    """BIS recognized testing laboratory evidence with verified scope"""
    __tablename__ = 'laboratory_evidence'

    id = Column(Integer, primary_key=True, index=True)
    standard_id = Column(Integer, ForeignKey('standards.id'), nullable=True, index=True)
    lab_name = Column(String(300), nullable=False)
    location = Column(String(200), nullable=False)
    address = Column(String(500), nullable=True)
    recognized_scope = Column(Text, nullable=True)
    bis_recognition_number = Column(String(100), nullable=True)
    source_url = Column(String(1000), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class CitationRecord(Base):
    """Immutable audit trail of factual claims linked to verified sources"""
    __tablename__ = 'citations'

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), nullable=True, index=True)
    claim_text = Column(Text, nullable=False)
    source_url = Column(String(1000), nullable=False)
    title = Column(String(500), nullable=True)
    publisher = Column(String(200), nullable=True)
    clause_reference = Column(String(100), nullable=True)
    evidence_text = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class ProductSession(Base):
    """Production-grade persistent product analysis session and audit state"""
    __tablename__ = 'product_sessions'

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True)  # e.g., BC-2026-000184
    product_description = Column(Text, nullable=False)
    location = Column(String(200), nullable=True)
    status = Column(String(50), default="ANALYZING")  # ANALYZING, NEEDS_CLARIFICATION, READY, NO_VERIFIED_STANDARD_FOUND
    product_profile = Column(Text, nullable=True)  # JSON representation of extracted ProductProfile
    clarification_history = Column(Text, nullable=True)  # JSON array of questions/answers
    applicable_standards = Column(Text, nullable=True)  # JSON array
    rejected_candidates = Column(Text, nullable=True)  # JSON array with failing_constraint
    certification_findings = Column(Text, nullable=True)  # JSON object
    testing_findings = Column(Text, nullable=True)  # JSON array
    laboratory_recommendations = Column(Text, nullable=True)  # JSON array
    evidence_claims = Column(Text, nullable=True)  # JSON array
    execution_time_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class ClarificationRecord(Base):
    """Dynamically generated questions and user answers for session ambiguity resolution"""
    __tablename__ = 'clarification_records'

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), ForeignKey('product_sessions.session_id'), nullable=False, index=True)
    question = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)  # Why this question is required to distinguish standards
    candidate_standard_numbers = Column(Text, nullable=True)  # JSON list of plausible standards
    user_answer = Column(Text, nullable=True)
    is_answered = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    answered_at = Column(DateTime, nullable=True)

class QCORecord(Base):
    """Authoritative Quality Control Orders (QCO) issued by Government Ministries"""
    __tablename__ = 'qco_orders'

    id = Column(Integer, primary_key=True, index=True)
    standard_number = Column(String(50), nullable=False, index=True)
    ministry = Column(String(200), nullable=False)  # e.g., DPIIT, Ministry of Steel, MeitY
    order_title = Column(String(500), nullable=False)
    gazette_number = Column(String(200), nullable=True)
    notification_date = Column(DateTime, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    is_mandatory = Column(Boolean, default=True)
    scheme = Column(String(100), default="Scheme-I (ISI Mark)")
    exemptions = Column(Text, nullable=True)
    source_url = Column(String(1000), nullable=False)
    evidence_text = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class TestRequirementRecord(Base):
    """Structured testing requirement from official standard / Scheme of Testing and Inspection"""
    __tablename__ = 'test_requirements'

    id = Column(Integer, primary_key=True, index=True)
    standard_number = Column(String(50), nullable=False, index=True)
    test_name = Column(String(300), nullable=False)
    purpose = Column(Text, nullable=True)
    requirement_criterion = Column(Text, nullable=False)
    test_method = Column(String(200), nullable=True)
    clause_number = Column(String(50), nullable=True)
    is_mandatory = Column(Boolean, default=True)
    frequency = Column(String(100), nullable=True)
    sample_requirement = Column(String(200), nullable=True)
    source_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime, server_default=func.now())