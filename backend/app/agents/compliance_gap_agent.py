from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging
import re
from app.services.standards.matching_engine import get_standards_matching_engine, StandardMatch
from app.services.retrieval.hybrid_retriever import get_hybrid_retriever
from app.services.products.product_understanding import ProductUnderstanding
from app.services.documents.ingestion_service import DocumentIngestionService, ProcessedDocument
from app.db.session import get_db
from app.models.standard import Standard, Clause
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class ComplianceRequirement:
    """Represents a specific requirement from a standard"""
    requirement_id: str
    description: str
    requirement_type: str  # e.g., "Design", "Testing", "Marking", "Documentation", "Process"
    is_mandatory: bool
    source_reference: Dict[str, Any]  # Standard/clause reference
    details: Dict[str, Any] = None  # Specific details like dimensions, materials, etc.


@dataclass
class GapAnalysisResult:
    """Result of comparing a document/product against standard requirements (Section 40)"""
    standard_id: int
    standard_number: str
    standard_title: str
    fulfilled_requirements: List[ComplianceRequirement]
    missing_requirements: List[ComplianceRequirement]
    partial_requirements: List[ComplianceRequirement]  # Partially addressed
    verified_requirements_count: int = 0
    satisfied_count: int = 0
    potential_gaps_count: int = 0
    not_assessable_count: int = 0
    calculation_basis: str = ""
    compliance_percentage: float = 0.0  # 0-100
    confidence: float = 0.0  # 0-1
    risk_level: str = "Low"  # "Low", "Medium", "High", "Critical"
    recommendations: List[str] = field(default_factory=list)
    source_documents: List[Dict[str, Any]] = field(default_factory=list)  # Documents used for analysis
    timestamp: str = field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())


@dataclass
class DocumentAnalysisContext:
    """Context for analyzing a document against standards"""
    document_content: str
    document_metadata: Dict[str, Any]  # Title, source, date, etc.
    product_understanding: Optional[ProductUnderstanding] = None
    target_standard_ids: Optional[List[int]] = None


class ComplianceGapAgent:
    """Agent responsible for analyzing compliance gaps between documents/products and BIS standards"""

    def __init__(self):
        self.standards_matching_engine = get_standards_matching_engine()
        self.hybrid_retriever_factory = get_hybrid_retriever
        self.document_ingestion_service = DocumentIngestionService()

    async def analyze_compliance_gaps(
        self,
        context: DocumentAnalysisContext
    ) -> List[GapAnalysisResult]:
        """
        Analyze compliance gaps between a document/context and BIS standards

        Args:
            context: Analysis context containing document and product understanding

        Returns:
            List of GapAnalysisResult objects for each analyzed standard
        """
        try:
            logger.info(
                f"Analyzing compliance gaps for document: "
                f"{context.document_metadata.get('title', 'Unknown')}"
            )

            # Extract requirements from the document
            document_requirements = await self._extract_requirements_from_document(
                context.document_content,
                context.document_metadata,
                context.product_understanding
            )

            # Determine which standards to analyze
            target_standards = await self._determine_target_standards(
                context.target_standard_ids,
                context.product_understanding,
                document_requirements
            )

            # Analyze gaps for each standard
            gap_results = []
            for standard in target_standards:
                gap_result = await self._analyze_standard_compliance(
                    standard,
                    document_requirements,
                    context.document_content,
                    context.product_understanding
                )
                gap_results.append(gap_result)

            # Sort by compliance percentage (ascending - most gaps first)
            gap_results.sort(key=lambda x: x.compliance_percentage)

            logger.info(f"Compliance gap analysis completed for {len(gap_results)} standards")
            return gap_results

        except Exception as e:
            logger.error(f"Error analyzing compliance gaps: {str(e)}")
            return []

    async def analyze_product_compliance(
        self,
        product_understanding: ProductUnderstanding,
        standard_ids: Optional[List[int]] = None
    ) -> List[GapAnalysisResult]:
        """
        Analyze compliance gaps for a product understanding against standards

        Args:
            product_understanding: Structured product information
            standard_ids: Optional list of standard IDs to check (if None, find applicable)

        Returns:
            List of GapAnalysisResult objects
        """
        try:
            logger.info(
                f"Analyzing product compliance for: {product_understanding.product_name}"
            )

            # Determine target standards
            if standard_ids is None:
                # Find applicable standards via matching engine
                matches = await self.standards_matching_engine.find_applicable_standards(
                    product_understanding,
                    limit=10
                )
                target_standard_ids = [match.standard_id for match in matches]

            # Get standard details
            target_standards = await self._get_standard_details(target_standard_ids)

            # Extract requirements from product understanding
            product_requirements = await self._extract_requirements_from_product(
                product_understanding
            )

            # Analyze gaps for each standard
            gap_results = []
            for standard in target_standards:
                # For product analysis, we use the product understanding as our "document"
                gap_result = await self._analyze_standard_compliance(
                    standard,
                    product_requirements,
                    str(product_understanding.dict()),  # Convert to string for analysis
                    product_understanding
                )
                gap_results.append(gap_result)

            # Sort by compliance percentage (ascending - most gaps first)
            gap_results.sort(key=lambda x: x.compliance_percentage)

            logger.info(f"Product compliance analysis completed for {len(gap_results)} standards")
            return gap_results

        except Exception as e:
            logger.error(f"Error analyzing product compliance: {str(e)}")
            return []

    # ------------------------------------------------------------------
    # Core analysis methods
    # ------------------------------------------------------------------

    async def _analyze_standard_compliance(
        self,
        standard: Standard,
        extracted_requirements: List[ComplianceRequirement],
        source_content: str,
        product_understanding: Optional[ProductUnderstanding] = None
    ) -> GapAnalysisResult:
        """Analyze compliance with a specific standard"""
        try:
            logger.debug(f"Analyzing compliance for standard {standard.standard_number}")

            # Get standard requirements (from database or document retrieval)
            standard_requirements = await self._extract_standard_requirements(standard)

            # Compare requirements
            fulfilled, missing, partial = self._compare_requirements(
                extracted_requirements,
                standard_requirements,
                source_content,
                product_understanding
            )

            # Calculate compliance percentage with explicit mathematical basis (Section 40)
            total_req = len(standard_requirements)
            satisfied_cnt = len(fulfilled)
            gaps_cnt = len(missing)
            partial_cnt = len(partial)
            not_assessable_cnt = 0

            if total_req == 0:
                compliance_percentage = 0.0
                calc_basis = "0 verified requirements extracted from authoritative sources. Compliance percentage cannot be computed."
                confidence = 0.0
            else:
                fulfilled_weight = satisfied_cnt
                partial_weight = partial_cnt * 0.5
                compliance_percentage = round(((fulfilled_weight + partial_weight) / total_req) * 100, 1)
                calc_basis = (
                    f"Verified requirements: {total_req} | Satisfied: {satisfied_cnt} | "
                    f"Partial: {partial_cnt} | Gaps: {gaps_cnt} | "
                    f"Calculation: ({satisfied_cnt} + 0.5 * {partial_cnt}) / {total_req} = {compliance_percentage}%"
                )
                confidence = self._calculate_confidence(
                    extracted_requirements,
                    standard_requirements,
                    source_content
                )

            # Determine risk level
            risk_level = self._determine_risk_level(
                compliance_percentage,
                len(missing),
                len(partial),
                standard_requirements
            )

            # Generate recommendations
            recommendations = self._generate_recommendations(
                missing,
                partial,
                standard,
                product_understanding
            )

            # Prepare source documents info
            source_docs = self._prepare_source_documents_info(
                source_content,
                extracted_requirements
            )

            return GapAnalysisResult(
                standard_id=standard.id,
                standard_number=standard.standard_number,
                standard_title=standard.title,
                fulfilled_requirements=fulfilled,
                missing_requirements=missing,
                partial_requirements=partial,
                verified_requirements_count=total_req,
                satisfied_count=satisfied_cnt,
                potential_gaps_count=gaps_cnt,
                not_assessable_count=not_assessable_cnt,
                calculation_basis=calc_basis,
                compliance_percentage=compliance_percentage,
                confidence=confidence,
                risk_level=risk_level,
                recommendations=recommendations,
                source_documents=source_documents
            )

        except Exception as e:
            logger.error(f"Error analyzing standard compliance: {str(e)}")
            return self._create_fallback_gap_result(standard, str(e))

    async def _extract_requirements_from_document(
        self,
        document_content: str,
        document_metadata: Dict[str, Any],
        product_understanding: Optional[ProductUnderstanding] = None
    ) -> List[ComplianceRequirement]:
        """Extract potential compliance requirements from a document"""
        try:
            requirements = []

            # Split document into logical sections
            sections = self._split_into_sections(document_content)

            for section_title, section_content in sections:
                # Look for requirement indicators in each section
                section_requirements = self._extract_requirements_from_text(
                    section_content,
                    section_title,
                    document_metadata
                )
                requirements.extend(section_requirements)

            # If product understanding provided, enhance with product-specific requirements
            if product_understanding:
                product_reqs = await self._extract_requirements_from_product(
                    product_understanding
                )
                requirements.extend(product_reqs)

            # Deduplicate requirements
            requirements = self._deduplicate_requirements(requirements)

            return requirements

        except Exception as e:
            logger.error(f"Error extracting requirements from document: {str(e)}")
            return []

    async def _extract_requirements_from_product(
        self,
        product_understanding: ProductUnderstanding
    ) -> List[ComplianceRequirement]:
        """Extract implied compliance requirements from product understanding"""
        try:
            requirements = []

            # Material-based requirements
            for material in product_understanding.materials:
                requirements.append(ComplianceRequirement(
                    requirement_id=f"material_{len(requirements)}",
                    description=f"Product contains {material} - verify compliance with material restrictions",
                    requirement_type="Materials",
                    is_mandatory=True,
                    source_reference={
                        "type": "product_understanding",
                        "field": "materials"
                    },
                    details={
                        "material": material,
                        "verification_needed": "Check for restricted substances, food contact approval, etc."
                    }
                ))

            # Intended use requirements
            if product_understanding.intended_use:
                requirements.append(ComplianceRequirement(
                    requirement_id=f"use_{len(requirements)}",
                    description=f"Product intended for {product_understanding.intended_use} use - verify applicable standards",
                    requirement_type="Intended Use",
                    is_mandatory=True,
                    source_reference={
                        "type": "product_understanding",
                        "field": "intended_use"
                    },
                    details={
                        "intended_use": product_understanding.intended_use,
                        "verification_needed": "Verify standards applicable to this use case"
                    }
                ))

            # Technical attributes requirements
            for attr_name, attr_value in product_understanding.technical_attributes.items():
                requirements.append(ComplianceRequirement(
                    requirement_id=f"attr_{len(requirements)}",
                    description=f"Product has {attr_name}: {attr_value} - verify compliance with relevant standards",
                    requirement_type="Technical Specification",
                    is_mandatory=True,
                    source_reference={
                        "type": "product_understanding",
                        "field": f"technical_attributes.{attr_name}"
                    },
                    details={
                        "attribute": attr_name,
                        "value": str(attr_value),
                        "verification_needed": "Check against standard limits and requirements"
                    }
                ))

            # Category-based requirements
            if product_understanding.category:
                requirements.append(ComplianceRequirement(
                    requirement_id=f"category_{len(requirements)}",
                    description=f"Product category: {product_understanding.category} - identify applicable BIS standards",
                    requirement_type="Category",
                    is_mandatory=True,
                    source_reference={
                        "type": "product_understanding",
                        "field": "category"
                    },
                    details={
                        "category": product_understanding.category,
                        "verification_needed": "Determine applicable standards for this product category"
                    }
                ))

            return requirements

        except Exception as e:
            logger.error(f"Error extracting requirements from product: {str(e)}")
            return []

    async def _extract_standard_requirements(
        self,
        standard: Standard
    ) -> List[ComplianceRequirement]:
        """Extract requirements from a standard (via document retrieval or database)"""
        try:
            requirements = []

            # Try to get requirements from database first (clauses with requirement indicators)
            db = next(get_db())
            try:
                clauses = db.query(Clause).filter(Clause.standard_id == standard.id).all()
                for clause in clauses:
                    req = self._clause_to_requirement(clause, standard)
                    if req:
                        requirements.append(req)
            finally:
                db.close()

            # If we found requirements in database, return them
            if requirements:
                return requirements[:50]  # Reasonable limit

            # Otherwise, use document retrieval to find requirement sections
            query = f"""
            requirement specification clause {standard.standard_number}
            shall must required mandatory
            """
            db = next(get_db())
            try:
                retriever = self.hybrid_retriever_factory(db)
                results = await retriever.hybrid_search(
                    query=query,
                    limit=10,
                    min_confidence=0.3,
                    filters={"standard_id": standard.id}
                )
            finally:
                db.close()

            for result in results:
                req = self._search_result_to_requirement(result, standard)
                if req:
                    requirements.append(req)

            # If still no requirements, generate some generic ones based on standard type
            if not requirements:
                requirements = self._generate_generic_requirements(standard)

            return requirements

        except Exception as e:
            logger.error(f"Error extracting standard requirements: {str(e)}")
            return self._generate_generic_requirements(standard)

    # ------------------------------------------------------------------
    # Requirement extraction helpers
    # ------------------------------------------------------------------

    def _split_into_sections(self, content: str) -> List[Tuple[str, str]]:
        """Split document content into logical sections"""
        sections = []

        # Try to split by common section headers
        section_patterns = [
            r'\n\s*(?:CHAPTER|Chapter|chapter)\s+\d+[:\.]?\s*([^\n]+)\n',
            r'\n\s*(?:SECTION|Section|section)\s+\d+[:\.]?\s*([^\n]+)\n',
            r'\n\s*(?:Clause|CLAUSE)\s+\d+[.\s]',
            r'\n\s*\d+\.\d+[\s]',
            r'\n\s*[A-Z][A-Z\s]+:[^\n]*\n'
        ]

        # Simple approach: split by double newline and look for section-like lines
        blocks = re.split(r'\n\s*\n', content)
        current_section = "Introduction"
        current_content = []

        for block in blocks:
            lines = block.split('\n')
            first_line = lines[0].strip() if lines else ""

            # Check if this looks like a section header
            is_header = (
                len(first_line) < 100 and
                (first_line.isupper() or
                 re.match(r'^\d+(\.\d+)*[\s\.]', first_line) or
                 any(keyword in first_line.lower() for keyword in
                     ['section', 'clause', 'chapter', 'part', 'article']))
            )

            if is_header and current_content:
                # Save previous section
                sections.append((current_section, '\n'.join(current_content)))
                current_section = first_line if first_line else "Section"
                current_content = lines[1:] if len(lines) > 1 else []
            else:
                current_content.extend(lines)

        # Don't forget the last section
        if current_content:
            sections.append((current_section, '\n'.join(current_content)))

        # If we didn't find any sections, treat whole document as one section
        if not sections:
            sections = [("Document", content)]

        return sections

    def _extract_requirements_from_text(
        self,
        text: str,
        section_title: str,
        metadata: Dict[str, Any]
    ) -> List[ComplianceRequirement]:
        """Extract requirement statements from text"""
        requirements = []

        # Patterns that indicate requirements
        requirement_patterns = [
            r'(?:shall|must|will|is required to|are required to)\s+([^.!?]+[.!?])',
            r'(?:required|mandatory|compulsory)\s+(?:that\s+)?([^.!?]+[.!?])',
            r'(?:it\s+is\s+required\s+that)\s+([^.!?]+[.!?])',
            r'(?:users?\s+(?:shall|must|should))\s+([^.!?]+[.!?])',
            r'(?:the\s+product\s+(?:shall|must|should))\s+([^.!?]+[.!?])'
        ]

        for pattern in requirement_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                req_text = match.group(1).strip()
                if len(req_text) > 10:  # Filter out trivial matches
                    req_type = self._classify_requirement_type(req_text, section_title)
                    is_mandatory = self._is_mandatory_requirement(req_text)

                    requirements.append(ComplianceRequirement(
                        requirement_id=f"req_{len(requirements)}",
                        description=req_text[:200] + ("..." if len(req_text) > 200 else ""),
                        requirement_type=req_type,
                        is_mandatory=is_mandatory,
                        source_reference={
                            "section": section_title,
                            "document_title": metadata.get("title", "Unknown"),
                            "document_source": metadata.get("source", "Unknown")
                        },
                        details={
                            "extracted_from": req_text,
                            "confidence": 0.8  # Base confidence for regex extraction
                        }
                    ))

        return requirements

    def _classify_requirement_type(self, requirement_text: str, section_title: str) -> str:
        """Classify the type of requirement"""
        text_lower = requirement_text.lower()
        section_lower = section_title.lower()

        # Check for specific keywords
        if any(word in text_lower for word in ['test', 'testing', 'examine', 'measure', 'check']):
            return "Testing"
        elif any(word in text_lower for word in ['mark', 'label', 'logo', 'isi', 'certification']):
            return "Marking"
        elif any(word in text_lower for word in ['document', 'record', 'report', 'certificate']):
            return "Documentation"
        elif any(word in text_lower for word in ['material', 'substance', 'composition', 'ingredient']):
            return "Materials"
        elif any(word in text_lower for word in ['design', 'dimension', 'size', 'weight', 'volume']):
            return "Design"
        elif any(word in text_lower for word in ['process', 'procedure', 'method', 'step']):
            return "Process"
        elif any(word in text_lower for word in ['safety', 'protection', 'hazard', 'risk']):
            return "Safety"
        elif any(word in text_lower for word in ['performance', 'efficiency', 'capacity', 'rating']):
            return "Performance"
        elif any(word in text_lower for word in ['environment', 'eco', 'recycl', 'waste']):
            return "Environmental"
        else:
            # Default based on section title
            if any(word in section_lower for word in ['test', 'testing']):
                return "Testing"
            elif any(word in section_lower for word in ['mark', 'label']):
                return "Marking"
            elif any(word in section_lower for word in ['document', 'record']):
                return "Documentation"
            elif any(word in section_lower for word in ['design', 'dimension']):
                return "Design"
            elif any(word in section_lower for word in ['material']):
                return "Materials"
            else:
                return "General"

    def _is_mandatory_requirement(self, requirement_text: str) -> bool:
        """Determine if a requirement is mandatory"""
        text_lower = requirement_text.lower()
        mandatory_indicators = ['shall', 'must', 'required', 'mandatory', 'compulsory']
        prohibitive_indicators = ['shall not', 'must not', 'prohibited', 'forbidden']

        has_mandatory = any(indicator in text_lower for indicator in mandatory_indicators)
        has_prohibitive = any(indicator in text_lower for indicator in prohibitive_indicators)

        return has_mandatory or has_prohibitive

    def _clause_to_requirement(self, clause: Clause, standard: Standard) -> Optional[ComplianceRequirement]:
        """Convert a database clause to a compliance requirement if it contains requirement language"""
        try:
            text = clause.text.lower()
            heading = (clause.heading or "").lower()
            combined = f"{heading} {text}"

            # Check if this clause contains requirement language
            req_indicators = [
                'shall', 'must', 'required', 'mandatory', 'compulsory',
                'shall not', 'must not', 'prohibited', 'forbidden',
                'is required', 'are required'
            ]

            if any(indicator in combined for indicator in req_indicators):
                req_type = self._classify_requirement_type(
                    clause.text,
                    clause.heading or f"Clause {clause.clause_number}"
                )
                is_mandatory = self._is_mandatory_requirement(combined)

                return ComplianceRequirement(
                    requirement_id=f"clause_{clause.id}",
                    description=f"{clause.heading or f'Clause {clause.clause_number}'}: {clause.text[:150]}{'...' if len(clause.text) > 150 else ''}",
                    requirement_type=req_type,
                    is_mandatory=is_mandatory,
                    source_reference={
                        "standard_id": standard.id,
                        "standard_number": standard.standard_number,
                        "clause_id": clause.id,
                        "clause_number": clause.clause_number,
                        "page": clause.page
                    },
                    details={
                        "clause_heading": clause.heading,
                        "clause_text": clause.text,
                        "extraction_method": "database_clause"
                    }
                )
        except Exception as e:
            logger.debug(f"Error converting clause to requirement: {str(e)}")

        return None

    def _search_result_to_requirement(
        self,
        result: Dict[str, Any],
        standard: Standard
    ) -> Optional[ComplianceRequirement]:
        """Convert a search result to a compliance requirement"""
        try:
            text = result.get("text", "")
            heading = result.get("heading", "")
            combined = f"{heading} {text}".lower()

            # Check if this result contains requirement language
            req_indicators = [
                'shall', 'must', 'required', 'mandatory', 'compulsory',
                'shall not', 'must not', 'prohibited', 'forbidden',
                'is required', 'are required'
            ]

            if any(indicator in combined for indicator in req_indicators):
                req_type = self._classify_requirement_type(
                    text,
                    heading or f"Clause {result.get('clause_number', 'Unknown')}"
                )
                is_mandatory = self._is_mandatory_requirement(combined)

                return ComplianceRequirement(
                    requirement_id=f"search_{hash(text) % 10000}",
                    description=f"{heading}: {text[:150]}{'...' if len(text) > 150 else ''}",
                    requirement_type=req_type,
                    is_mandatory=is_mandatory,
                    source_reference={
                        "standard_id": result.get("standard_id"),
                        "standard_number": result.get("standard_number"),
                        "clause_id": result.get("clause_id"),
                        "clause_number": result.get("clause_number"),
                        "page": result.get("page")
                    },
                    details={
                        "extracted_from": "search_result",
                        "relevance_score": result.get("combined_score", 0.0),
                        "source_type": result.get("source_type"),
                        "organization": result.get("organization")
                    }
                )
        except Exception as e:
            logger.debug(f"Error converting search result to requirement: {str(e)}")

        return None

    def _generate_generic_requirements(self, standard: Standard) -> List[ComplianceRequirement]:
        """Never fabricate generic requirements without authoritative evidence (Rule 0)"""
        return []

    # ------------------------------------------------------------------
    # Comparison and analysis
    # ------------------------------------------------------------------

    def _compare_requirements(
        self,
        extracted_requirements: List[ComplianceRequirement],
        standard_requirements: List[ComplianceRequirement],
        source_content: str,
        product_understanding: Optional[ProductUnderstanding] = None
    ) -> Tuple[
        List[ComplianceRequirement],  # fulfilled
        List[ComplianceRequirement],  # missing
        List[ComplianceRequirement]   # partial
    ]:
        """Compare extracted requirements against standard requirements"""
        fulfilled = []
        missing = []
        partial = []

        # For each standard requirement, check if we have evidence of fulfillment
        for std_req in standard_requirements:
            match_result = self._find_matching_requirement(
                std_req,
                extracted_requirements,
                source_content,
                product_understanding
            )

            if match_result == "fulfilled":
                fulfilled.append(std_req)
            elif match_result == "partial":
                partial.append(std_req)
            else:  # missing or no match
                missing.append(std_req)

        return fulfilled, missing, partial

    def _find_matching_requirement(
        self,
        standard_req: ComplianceRequirement,
        extracted_reqs: List[ComplianceRequirement],
        source_content: str,
        product_understanding: Optional[ProductUnderstanding] = None
    ) -> str:
        """Find if a standard requirement is fulfilled, partially fulfilled, or missing"""
        # Normalize the standard requirement for comparison
        std_text = standard_req.description.lower()
        std_type = standard_req.requirement_type.lower()
        std_details = standard_req.details or {}

        best_match_score = 0.0
        best_match_req = None

        # Check against extracted requirements
        for ext_req in extracted_reqs:
            ext_text = ext_req.description.lower()
            ext_type = ext_req.requirement_type.lower()

            # Type matching
            type_score = 1.0 if std_type == ext_type else (
                0.5 if self._are_related_types(std_type, ext_type) else 0.0
            )

            # Text similarity (simple approach)
            text_score = self._calculate_text_similarity(std_text, ext_text)

            # Combined score
            combined_score = (text_score * 0.7) + (type_score * 0.3)

            if combined_score > best_match_score:
                best_match_score = combined_score
                best_match_req = ext_req

        # Also check source content directly for key phrases
        content_score = self._check_content_for_requirement(
            standard_req,
            source_content,
            product_understanding
        )

        # Use the best score
        final_score = max(best_match_score, content_score)

        # Determine fulfillment status
        if final_score >= 0.8:
            return "fulfilled"
        elif final_score >= 0.5:
            return "partial"
        else:
            return "missing"

    def _are_related_types(self, type1: str, type2: str) -> bool:
        """Check if two requirement types are related"""
        related_groups = [
            {"testing", "examination", "evaluation"},
            {"marking", "labeling", "packaging"},
            {"documentation", "recordkeeping", "reporting"},
            {"materials", "substances", "composition"},
            {"design", "dimensions", "specifications"},
            {"safety", "protection", "hazard"},
            {"performance", "efficiency", "capacity"},
            {"process", "procedure", "method"}
        ]

        for group in related_groups:
            if type1 in group and type2 in group:
                return True
        return False

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity between two strings"""
        if not text1 or not text2:
            return 0.0

        # Simple Jaccard similarity on word sets
        words1 = set(re.findall(r'\b\w+\b', text1.lower()))
        words2 = set(re.findall(r'\b\w+\b', text2.lower()))

        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _check_content_for_requirement(
        self,
        standard_req: ComplianceRequirement,
        source_content: str,
        product_understanding: Optional[ProductUnderstanding] = None
    ) -> float:
        """Check if source content directly addresses a requirement"""
        content_lower = source_content.lower()
        req_text_lower = standard_req.description.lower()
        req_type_lower = standard_req.requirement_type.lower()

        score = 0.0

        # Direct text match
        if req_text_lower in content_lower:
            score += 0.4

        # Requirement type presence
        type_indicators = {
            "testing": ["test", "testing", "examine", "measure", "evaluate"],
            "marking": ["mark", "label", "logo", "isi", "certification"],
            "documentation": ["document", "record", "report", "manual", "certificate"],
            "materials": ["material", "substance", "composition", "ingredient"],
            "design": ["design", "dimension", "size", "weight", "volume", "specification"],
            "safety": ["safety", "protection", "hazard", "risk", "danger"],
            "performance": ["performance", "efficiency", "capacity", "rating", "output"],
            "process": ["process", "procedure", "method", "step", "procedure"]
        }

        if req_type_lower in type_indicators:
            indicators = type_indicators[req_type_lower]
            matches = sum(1 for ind in indicators if ind in content_lower)
            if matches > 0:
                score += min(0.3, matches * 0.1)

        # Check for specific details from standard_req.details
        details = standard_req.details or {}
        for key, value in details.items():
            if isinstance(value, str) and value.lower() in content_lower:
                score += 0.2
                break
            elif isinstance(value, (int, float)) and str(value) in content_lower:
                score += 0.2
                break

        # If product understanding provided, check for consistency
        if product_understanding:
            # Check material consistency
            if req_type_lower == "materials":
                product_materials = [m.lower() for m in product_understanding.materials]
                std_material = details.get("material", "").lower()
                if std_material and std_material in product_materials:
                    score += 0.3

            # Check intended use consistency
            if req_type_lower == "intended use":
                product_use = product_understanding.intended_use.lower()
                if "use" in req_text_lower and product_use in req_text_lower:
                    score += 0.3

        return min(score, 1.0)

    def _deduplicate_requirements(
        self,
        requirements: List[ComplianceRequirement]
    ) -> List[ComplianceRequirement]:
        """Remove duplicate or very similar requirements"""
        if not requirements:
            return requirements

        unique_reqs = []
        seen_signatures = set()

        for req in requirements:
            # Create a signature based on type and key description elements
            signature = (
                req.requirement_type.lower(),
                # Take first 50 chars of description for similarity
                req.description.lower()[:50]
            )

            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_reqs.append(req)

        return unique_reqs

    # ------------------------------------------------------------------
    # Supporting methods
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        extracted_requirements: List[ComplianceRequirement],
        standard_requirements: List[ComplianceRequirement],
        source_content: str
    ) -> float:
        """Calculate confidence in the gap analysis"""
        if not standard_requirements:
            return 0.5

        # Base confidence on amount of source material
        content_factor = min(len(source_content) / 5000, 1.0)  # Normalize to 5k chars

        # Factor in number of extracted requirements vs standard requirements
        if standard_requirements:
            req_ratio = min(len(extracted_requirements) / len(standard_requirements), 1.0)
            req_factor = 0.3 + (0.7 * req_ratio)  # 0.3-1.0 range
        else:
            req_factor = 0.5

        # Factor in source diversity (if we had multiple documents)
        source_factor = 0.8  # Assume decent source for now

        confidence = (content_factor * 0.4) + (req_factor * 0.4) + (source_factor * 0.2)
        return min(max(confidence, 0.0), 1.0)

    def _determine_risk_level(
        self,
        compliance_percentage: float,
        missing_count: int,
        partial_count: int,
        standard_requirements: List[ComplianceRequirement]
    ) -> str:
        """Determine risk level based on compliance analysis"""
        total_req = len(standard_requirements)
        if total_req == 0:
            return "Low"

        missing_ratio = missing_count / total_req if total_req > 0 else 0
        partial_ratio = partial_count / total_req if total_req > 0 else 0

        # Critical: >50% missing mandatory requirements, or any critical missing items
        # High: >30% missing, or significant partial fulfillment issues
        # Medium: 10-30% missing
        # Low: <10% missing

        if missing_ratio > 0.5:
            return "Critical"
        elif missing_ratio > 0.3:
            return "High"
        elif missing_ratio > 0.1:
            return "Medium"
        else:
            # Even if missing is low, check if we have many partials
            if partial_ratio > 0.4:
                return "Medium"
            elif partial_ratio > 0.2:
                return "Low"
            else:
                return "Low"

    def _generate_recommendations(
        self,
        missing_requirements: List[ComplianceRequirement],
        partial_requirements: List[ComplianceRequirement],
        standard: Standard,
        product_understanding: Optional[ProductUnderstanding] = None
    ) -> List[str]:
        """Generate actionable recommendations based on gaps"""
        recommendations = []

        # Group missing requirements by type
        missing_by_type = {}
        for req in missing_requirements:
            req_type = req.requirement_type
            if req_type not in missing_by_type:
                missing_by_type[req_type] = []
            missing_by_type[req_type].append(req)

        # Group partial requirements by type
        partial_by_type = {}
        for req in partial_requirements:
            req_type = req.requirement_type
            if req_type not in partial_by_type:
                partial_by_type[req_type] = []
            partial_by_type[req_type].append(req)

        # Generate recommendations for missing requirements
        for req_type, reqs in missing_by_type.items():
            if len(reqs) == 1:
                recommendations.append(
                    f"Address missing {req_type.lower()} requirement: {reqs[0].description[:100]}..."
                )
            else:
                recommendations.append(
                    f"Address {len(reqs)} missing {req_type.lower()} requirements "
                    f"(e.g., {reqs[0].description[:80]}...)"
                )

        # Generate recommendations for partial requirements
        for req_type, reqs in partial_by_type.items():
            if len(reqs) == 1:
                recommendations.append(
                    f"Complete partial {req_type.lower()} requirement: {reqs[0].description[:100]}..."
                )
            else:
                recommendations.append(
                    f"Complete {len(reqs)} partial {req_type.lower()} requirements "
                    f"(e.g., {reqs[0].description[:80]}...)"
                )

        # Add standard-specific recommendations
        if missing_requirements:
            recommendations.append(
                f"Review complete {standard.standard_number} standard for detailed requirements"
            )

        # Add product-specific recommendations if available
        if product_understanding:
            if product_understanding.missing_information:
                recommendations.append(
                    f"Obtain missing product information: {', '.join(product_understanding.missing_information[:3])}"
                )

        # Limit recommendations to avoid overload
        return recommendations[:8]

    def _prepare_source_documents_info(
        self,
        source_content: str,
        extracted_requirements: List[ComplianceRequirement]
    ) -> List[Dict[str, Any]]:
        """Prepare information about source documents used"""
        return [{
            "type": "analyzed_content",
            "content_length": len(source_content),
            "requirements_extracted": len(extracted_requirements),
            "extraction_method": "text_analysis",
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }]

    def _create_fallback_gap_result(
        self,
        standard: Standard,
        error_message: str
    ) -> GapAnalysisResult:
        """Create a fallback result when analysis fails"""
        return GapAnalysisResult(
            standard_id=standard.id,
            standard_number=standard.standard_number,
            standard_title=standard.title,
            fulfilled_requirements=[],
            missing_requirements=[ComplianceRequirement(
                requirement_id="error",
                description=f"Analysis failed: {error_message}",
                requirement_type="Error",
                is_mandatory=False,
                source_reference={"standard_id": standard.id}
            )],
            partial_requirements=[],
            compliance_percentage=0.0,
            confidence=0.1,
            risk_level="High",
            recommendations=["Manual review required due to analysis error"],
            source_documents=[{
                "type": "error",
                "message": error_message
            }]
        )

    # ------------------------------------------------------------------
    # Helper methods for target determination
    # ------------------------------------------------------------------

    async def _determine_target_standards(
        self,
        target_standard_ids: Optional[List[int]],
        product_understanding: Optional[ProductUnderstanding],
        document_requirements: List[ComplianceRequirement]
    ) -> List[Standard]:
        """Determine which standards to analyze"""
        if target_standard_ids is not None:
            return await self._get_standard_details(target_standard_ids)

        # If we have product understanding, find applicable standards
        if product_understanding:
            matches = await self.standards_matching_engine.find_applicable_standards(
                product_understanding,
                limit=10
            )
            standard_ids = [match.standard_id for match in matches]
            return await self._get_standard_details(standard_ids)

        # If we have document requirements, try to infer standards
        if document_requirements:
            # Extract potential standard references from requirements
            std_refs = self._extract_standard_references_from_requirements(
                document_requirements
            )
            if std_refs:
                # Try to get standards by number
                return await self._get_standards_by_numbers(std_refs[:5])

        # Fallback: return empty list
        return []

    def _extract_standard_references_from_requirements(
        self,
        requirements: List[ComplianceRequirement]
    ) -> List[str]:
        """Extract standard numbers from requirement descriptions/references"""
        std_numbers = []
        pattern = r'IS\s*\d{2,5}(?::\d{4})?|\b\d{2,5}:\d{4}\b'

        for req in requirements:
            # Check description
            matches = re.findall(pattern, req.description)
            std_numbers.extend(matches)

            # Check source reference
            source_ref = req.source_reference
            if isinstance(source_ref, dict):
                std_num = source_ref.get("standard_number")
                if std_num:
                    std_numbers.append(std_num)

        # Clean and deduplicate
        cleaned = []
        for num in std_numbers:
            cleaned_num = re.sub(r'[^\d:]', '', num.upper())
            if cleaned_num and cleaned_num not in cleaned:
                cleaned.append(cleaned_num)

        return cleaned

    async def _get_standard_details(self, standard_ids: List[int]) -> List[Standard]:
        """Get Standard objects from database by ID"""
        if not standard_ids:
            return []

        try:
            db = next(get_db())
            try:
                standards = db.query(Standard).filter(Standard.id.in_(standard_ids)).all()
                return standards
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error getting standard details: {str(e)}")
            return []

    async def _get_standards_by_numbers(self, standard_numbers: List[str]) -> List[Standard]:
        """Get Standard objects by standard number"""
        if not standard_numbers:
            return []

        try:
            db = next(get_db())
            try:
                standards = db.query(Standard).filter(
                    Standard.standard_number.in_(standard_numbers)
                ).all()
                return standards
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error getting standards by numbers: {str(e)}")
            return []


# Global agent instance
_compliance_gap_agent: Optional[ComplianceGapAgent] = None


def get_compliance_gap_agent() -> ComplianceGapAgent:
    """Get or create the compliance gap agent instance"""
    global _compliance_gap_agent
    if _compliance_gap_agent is None:
        _compliance_gap_agent = ComplianceGapAgent()
    return _compliance_gap_agent