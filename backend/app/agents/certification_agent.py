from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
from app.services.standards.matching_engine import get_standards_matching_engine, StandardMatch
from app.services.retrieval.hybrid_retriever import get_hybrid_retriever
from app.services.products.product_understanding import ProductUnderstanding
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.standard import Scheme, Standard, Source
from app.agents.testing_agent import get_testing_agent

logger = logging.getLogger(__name__)

@dataclass
class CertificationRequirement:
    """Represents a certification requirement"""
    requirement_type: str  # e.g., "License", "Marking", "Testing", "Factory Audit"
    description: str
    is_mandatory: bool
    source_reference: Dict[str, Any]  # Standard/clause reference
    details: Dict[str, Any] = None

@dataclass
class CertificationProcess:
    """Represents the certification process steps"""
    step_number: int
    step_name: str
    description: str
    estimated_time: Optional[str] = None
    required_documents: List[str] = None
    responsible_party: str = ""  # e.g., "Manufacturer", "BIS", "Laboratory"

@dataclass
class CertificationInfo:
    """Complete certification information for a product-standard pair"""
    standard_id: int
    standard_number: str
    certification_scheme: Optional[str]
    license_required: bool
    marking_requirements: List[CertificationRequirement]
    testing_requirements: List[CertificationRequirement]
    factory_audit_required: bool
    documentation_requirements: List[str]
    certification_process: List[CertificationProcess]
    validity_period: Optional[str]
    renewal_requirements: List[str]
    applicable_products: List[str]
    confidence: float
    sources: List[Dict[str, Any]]

class CertificationAgent:
    """Agent responsible for certification schemes, license requirements, application workflow, and documentation requirements"""

    def __init__(self):
        self.standards_matching_engine = get_standards_matching_engine()
        self.hybrid_retriever_factory = get_hybrid_retriever

    async def get_certification_info(
        self,
        product_understanding: ProductUnderstanding,
        standard_id: int,
        standard_number: Optional[str] = None
    ) -> CertificationInfo:
        """
        Get certification information for a product and standard

        Args:
            product_understanding: Structured product information
            standard_id: ID of the standard to check for certification requirements
            standard_number: Optional standard number (e.g. 'IS 17526:2021')

        Returns:
            CertificationInfo object with certification details
        """
        try:
            logger.info(f"Getting certification info for product: {product_understanding.product_name}, standard ID: {standard_id}, standard: {standard_number}")

            # Get database session
            db = next(get_db())
            try:
                # Get the standard information
                standard = None
                if standard_id > 0:
                    standard = db.query(Standard).filter(Standard.id == standard_id).first()
                if not standard and standard_number:
                    standard = db.query(Standard).filter(Standard.standard_number == standard_number).first()
                if not standard:
                    raise ValueError(f"Standard with ID {standard_id} ({standard_number}) not found")

                # Get hybrid retriever for searching certification-specific information
                retriever = self.hybrid_retriever_factory(db)

                # Search for certification scheme information
                certification_query = f"""
                certification scheme license marking requirements for {standard.standard_number}
                {product_understanding.product_name} {product_understanding.category}
                """
                certification_results = await retriever.hybrid_search(
                    query=certification_query,
                    limit=5,
                    min_confidence=0.3,
                    filters={"standard_id": standard_id}
                )

                # Search for licensing requirements
                license_query = f"""
                license requirement compulsory registration {standard.standard_number}
                {product_understanding.intended_use} {product_understanding.category}
                """
                license_results = await retriever.hybrid_search(
                    query=license_query,
                    limit=5,
                    min_confidence=0.3,
                    filters={"standard_id": standard_id}
                )

                # Search for marking requirements
                marking_query = f"""
                marking labeling requirements {standard.standard_number}
                {product_understanding.product_name} ISI mark
                """
                marking_results = await retriever.hybrid_search(
                    query=marking_query,
                    limit=5,
                    min_confidence=0.3,
                    filters={"standard_id": standard_id}
                )

                # Get scheme information from database
                scheme = db.query(Scheme).filter(Scheme.standard_id == standard_id).first()

                # Process the results
                certification_info = await self._process_certification_data(
                    standard,
                    scheme,
                    certification_results,
                    license_results,
                    marking_results,
                    product_understanding,
                    db
                )

                return certification_info

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error getting certification info: {str(e)}")
            # Return basic certification info on failure
            return self._create_fallback_certification_info(product_understanding, standard_id, standard_number)

    async def _process_certification_data(
        self,
        standard: Standard,
        scheme: Optional[Scheme],
        certification_results: List[Dict[str, Any]],
        license_results: List[Dict[str, Any]],
        marking_results: List[Dict[str, Any]],
        product_understanding: ProductUnderstanding,
        db: Session
    ) -> CertificationInfo:
        """Process certification data from search results and database"""

        # Determine if license is required
        license_required = self._determine_license_required(license_results, standard)

        # Extract marking requirements
        marking_requirements = self._extract_marking_requirements(marking_results, standard)

        # Extract testing requirements (would be enhanced by testing agent)
        testing_requirements = await self._extract_testing_requirements(
            standard, product_understanding, db
        )

        # Determine if factory audit is required
        factory_audit_required = self._determine_factory_audit_required(certification_results, standard)

        # Extract documentation requirements
        documentation_requirements = self._extract_documentation_requirements(certification_results, standard)

        # Build certification process
        certification_process = self._build_certification_process(
            license_required, marking_requirements, testing_requirements, factory_audit_required, documentation_requirements
        )

        # Get scheme information
        certification_scheme = scheme.scheme_name if scheme else None
        validity_period = scheme.conditions if scheme else None  # Simplified

        # Calculate confidence
        confidence = self._calculate_certification_confidence(
            certification_results, license_results, marking_results, scheme
        )

        # Prepare sources
        sources = self._prepare_sources(
            certification_results, license_results, marking_results, scheme, standard
        )

        return CertificationInfo(
            standard_id=standard.id,
            standard_number=standard.standard_number,
            certification_scheme=certification_scheme,
            license_required=license_required,
            marking_requirements=marking_requirements,
            testing_requirements=testing_requirements,
            factory_audit_required=factory_audit_required,
            documentation_requirements=documentation_requirements,
            certification_process=certification_process,
            validity_period=validity_period,
            renewal_requirements=self._get_renewal_requirements(scheme),
            applicable_products=[product_understanding.product_name],
            confidence=confidence,
            sources=sources
        )

    def _determine_license_required(self, license_results: List[Dict[str, Any]], standard: Standard) -> bool:
        """
        Determine if mandatory license is required.
        Strict Rule (Section 34): Standard existence != Mandatory certification.
        Only claim True if explicit Quality Control Order (QCO) or Gazette statutory mandate is verified.
        Otherwise False / Voluntary.
        """
        try:
            if not license_results:
                return False

            for result in license_results:
                text = f"{result.get('text', '')} {result.get('heading', '')}".lower()
                if any(phrase in text for phrase in [
                    "quality control order", "qco", "mandatory under order",
                    "compulsory bis certification", "compulsory registration order",
                    "order published in the gazette of india", "statutory order"
                ]):
                    return True

            return False
        except Exception as e:
            logger.error(f"Error determining license requirement: {str(e)}")
            return False

    def _extract_marking_requirements(self, marking_results: List[Dict[str, Any]], standard: Standard) -> List[CertificationRequirement]:
        """Extract marking requirements from search results"""
        try:
            marking_requirements = []

            for result in marking_results:
                text = result.get("text", "")
                heading = result.get("heading", "")

                # Check if this result contains marking information
                marking_keywords = ["marking", "labeling", "isi mark", "standard mark", "certification mark"]
                if any(keyword in (text + heading).lower() for keyword in marking_keywords):
                    requirement = CertificationRequirement(
                        requirement_type="Marking",
                        description=f"{heading}: {text[:150]}{'...' if len(text) > 150 else ''}",
                        is_mandatory=True,  # Assume mandatory if found in certification context
                        source_reference={
                            "standard_id": result.get("standard_id"),
                            "clause_id": result.get("clause_id"),
                            "clause_number": result.get("clause_number"),
                            "page": result.get("page")
                        },
                        details={
                            "source_type": result.get("source_type"),
                            "organization": result.get("organization"),
                            "relevance_score": result.get("combined_score", 0.0)
                        }
                    )
                    marking_requirements.append(requirement)

            # If no specific marking requirements found, add a general one based on standard
            if not marking_requirements:
                std_num = standard.standard_number if standard else ""
                clean_num = std_num.strip() if std_num else ""
                if clean_num and not clean_num.upper().startswith("IS"):
                    clean_num = f"IS {clean_num}"
                desc = f"Product must bear the standard conformity mark as per {clean_num}" if clean_num else "Conformity marking requirements subject to applicable regulatory notification"

                marking_requirements.append(
                    CertificationRequirement(
                        requirement_type="Marking",
                        description=desc,
                        is_mandatory=False,
                        source_reference={
                            "standard_id": standard.id if standard else 0,
                            "standard_number": std_num
                        }
                    )
                )

            return marking_requirements

        except Exception as e:
            logger.error(f"Error extracting marking requirements: {str(e)}")
            std_num = standard.standard_number if standard else ""
            clean_num = std_num.strip() if std_num else ""
            if clean_num and not clean_num.upper().startswith("IS"):
                clean_num = f"IS {clean_num}"
            desc = f"Conformity marking required as per {clean_num}" if clean_num else "Conformity marking requirements could not be verified from retrieved sources"

            return [
                CertificationRequirement(
                    requirement_type="Marking",
                    description=desc,
                    is_mandatory=False,
                    source_reference={"standard_id": standard.id if standard else 0}
                )
            ]

    async def _extract_testing_requirements(
        self,
        standard: Standard,
        product_understanding: ProductUnderstanding,
        db: Session
    ) -> List[CertificationRequirement]:
        """Extract testing requirements by delegating to the testing agent"""
        try:
            # Get testing agent
            testing_agent = get_testing_agent()

            # Get detailed testing information from the testing agent
            testing_info = await testing_agent.get_testing_information(
                product_understanding, standard.id
            )

            # Convert TestingRequirement objects to CertificationRequirement objects
            certification_requirements = []
            for test_req in testing_info.testing_requirements:
                cert_req = CertificationRequirement(
                    requirement_type=test_req.test_type,
                    description=test_req.description,
                    is_mandatory=test_req.is_mandatory,
                    source_reference=test_req.source_reference,
                    details=test_req.details
                )
                certification_requirements.append(cert_req)

            return certification_requirements

        except Exception as e:
            logger.error(f"Error extracting testing requirements: {str(e)}")
            # Fallback to basic testing requirements on failure
            return self._extract_fallback_testing_requirements(standard)

    def _extract_fallback_testing_requirements(self, standard: Standard) -> List[CertificationRequirement]:
        """Provide fallback testing requirements when testing agent fails"""
        try:
            testing_requirements = []

            # Check if standard mentions testing
            standard_text = f"{standard.title} {standard.scope or ''}".lower()
            testing_keywords = ["test", "testing", "examination", "evaluation"]

            if any(keyword in standard_text for keyword in testing_keywords):
                testing_requirements.append(
                    CertificationRequirement(
                        requirement_type="Testing",
                        description=f"Product samples must be tested as per IS {standard.standard_number}",
                        is_mandatory=True,
                        source_reference={
                            "standard_id": standard.id,
                            "standard_number": standard.standard_number
                        },
                        details={
                            "test_types": ["Type testing", "Factory testing", "Market sample testing"],
                            "sample_size": "As per standard requirements"
                        }
                    )
                )

            # Add common testing requirements
            testing_requirements.append(
                CertificationRequirement(
                    requirement_type="Testing",
                    description="Initial type testing at BIS-recognized laboratory",
                    is_mandatory=True,
                    source_reference={"standard_id": standard.id}
                )
            )

            return testing_requirements

        except Exception as e:
            logger.error(f"Error extracting fallback testing requirements: {str(e)}")
            return []

    def _determine_factory_audit_required(self, certification_results: List[Dict[str, Any]], standard: Standard) -> bool:
        """Determine if factory audit is required"""
        try:
            # Factory audit is typically required for most BIS certification schemes
            # Check for explicit mentions
            audit_keywords = ["factory inspection", "manufacturing", "factory audit", "surveillance"]

            for result in certification_results:
                text = f"{result.get('text', '')} {result.get('heading', '')}".lower()
                if any(keyword in text for keyword in audit_keywords):
                    return True

            # Default to True for most product certifications
            return True

        except Exception as e:
            logger.error(f"Error determining factory audit requirement: {str(e)}")
            return True

    def _extract_documentation_requirements(self, certification_results: List[Dict[str, Any]], standard: Standard) -> List[str]:
        """Extract documentation requirements"""
        try:
            documentation_requirements = []

            # Common documentation requirements for BIS certification
            common_docs = [
                "Application form duly filled",
                "Factory layout plan",
                "List of machinery and equipment",
                "Details of quality control staff",
                "Test report from BIS-recognized laboratory",
                "Sample of the product",
                "Affidavit regarding conformity to standard",
                "Fee payment proof"
            ]

            # Check if any specific documentation is mentioned in results
            for result in certification_results:
                text = result.get("text", "").lower()
                if "document" in text or "requirement" in text:
                    # Extract potential documentation requirements
                    lines = text.split('.')
                    for line in lines:
                        if any(keyword in line for keyword in ["submit", "provide", "furnish", "document"]):
                            cleaned_line = line.strip()
                            if len(cleaned_line) > 10:  # Avoid very short fragments
                                documentation_requirements.append(cleaned_line.capitalize())

            # Add common documentation requirements if none found specifically
            if not documentation_requirements:
                documentation_requirements = common_docs[:6]  # Add first 6 common requirements

            return documentation_requirements

        except Exception as e:
            logger.error(f"Error extracting documentation requirements: {str(e)}")
            return [
                "Application form",
                "Factory details",
                "Test reports",
                "Product samples",
                "Quality control details",
                "Fee payment proof"
            ]

    def _build_certification_process(
        self,
        license_required: bool,
        marking_requirements: List[CertificationRequirement],
        testing_requirements: List[CertificationRequirement],
        factory_audit_required: bool,
        documentation_requirements: Optional[List[str]] = None
    ) -> List[CertificationProcess]:
        """Build the certification process steps"""
        try:
            process = []
            step_number = 1

            # Step 1: Application submission
            process.append(CertificationProcess(
                step_number=step_number,
                step_name="Application Submission",
                description="Submit application form along with required documents and fee",
                estimated_time="1-2 weeks",
                required_documents=["Application form", "Fee payment proof"],
                responsible_party="Manufacturer"
            ))
            step_number += 1

            # Step 2: Document review
            process.append(CertificationProcess(
                step_number=step_number,
                step_name="Document Review",
                description="BIS reviews submitted documents for completeness",
                estimated_time="1 week",
                required_documents=documentation_requirements[:3] if documentation_requirements else [],
                responsible_party="BIS"
            ))
            step_number += 1

            # Step 3: Product testing
            if testing_requirements:
                process.append(CertificationProcess(
                    step_number=step_number,
                    step_name="Product Testing",
                    description="Product samples tested at BIS-recognized laboratory",
                    estimated_time="2-4 weeks",
                    required_documents=["Test samples", "Test request form"],
                    responsible_party="Laboratory"
                ))
                step_number += 1

            # Step 4: Factory inspection
            if factory_audit_required:
                process.append(CertificationProcess(
                    step_number=step_number,
                    step_name="Factory Inspection",
                    description="BIS officials inspect manufacturing facilities and quality control",
                    estimated_time="1-2 weeks",
                    required_documents=["Factory records", "Quality control procedures"],
                    responsible_party="BIS"
                ))
                step_number += 1

            # Step 5: Grant of license
            if license_required:
                process.append(CertificationProcess(
                    step_number=step_number,
                    step_name="Grant of License",
                    description="BIS grants license to use ISI Mark upon satisfactory compliance",
                    estimated_time="1 week",
                    required_documents=["Test reports", "Inspection report"],
                    responsible_party="BIS"
                ))
                step_number += 1

            # Step 6: Marking authorization
            if marking_requirements:
                process.append(CertificationProcess(
                    step_number=step_number,
                    step_name="Marking Authorization",
                    description="Authorization to apply ISI Mark on certified products",
                    estimated_time="Ongoing",
                    required_documents=["License certificate"],
                    responsible_party="BIS/Manufacturer"
                ))
                step_number += 1

            # Step 7: Surveillance (ongoing)
            process.append(CertificationProcess(
                step_number=step_number,
                step_name="Surveillance",
                description="Regular surveillance including factory inspections and market sample testing",
                estimated_time="Ongoing (typically annually)",
                required_documents=["Production records", "Test records"],
                responsible_party="BIS"
            ))

            return process

        except Exception as e:
            logger.error(f"Error building certification process: {str(e)}")
            # Return basic process on error
            return [
                CertificationProcess(
                    step_number=1,
                    step_name="Application",
                    description="Submit application for certification",
                    responsible_party="Manufacturer"
                ),
                CertificationProcess(
                    step_number=2,
                    step_name="Evaluation",
                    description="Product testing and factory inspection",
                    responsible_party="BIS/Laboratory"
                ),
                CertificationProcess(
                    step_number=3,
                    step_name="Certification",
                    description="Grant of license and marking authorization",
                    responsible_party="BIS"
                )
            ]

    def _get_renewal_requirements(self, scheme: Optional[Scheme]) -> List[str]:
        """Get renewal requirements from scheme or defaults"""
        try:
            if scheme and scheme.conditions:
                # Try to extract renewal info from conditions
                conditions_lower = scheme.conditions.lower()
                if "renew" in conditions_lower:
                    # Very basic extraction - in reality would be more sophisticated
                    return ["Periodic renewal as per scheme requirements"]

            # Default renewal requirements
            return [
                "Application for renewal before expiry",
                "Payment of renewal fee",
                "Submission of test reports (if required)",
                "Factory inspection (if applicable)"
            ]

        except Exception as e:
            logger.error(f"Error getting renewal requirements: {str(e)}")
            return ["Refer to specific scheme for renewal requirements"]

    def _calculate_certification_confidence(
        self,
        certification_results: List[Dict[str, Any]],
        license_results: List[Dict[str, Any]],
        marking_results: List[Dict[str, Any]],
        scheme: Optional[Scheme]
    ) -> float:
        """Calculate confidence in certification information"""
        try:
            # Base confidence from having a scheme
            base_confidence = 0.6 if scheme else 0.3

            # Boost from having specific results
            result_bonus = 0.0
            if certification_results:
                result_bonus += 0.1
            if license_results:
                result_bonus += 0.1
            if marking_results:
                result_bonus += 0.1

            # Boost from high-quality scores
            quality_bonus = 0.0
            all_results = certification_results + license_results + marking_results
            if all_results:
                avg_score = sum(r.get("combined_score", 0.0) for r in all_results) / len(all_results)
                quality_bonus = avg_score * 0.2  # Up to 0.2 bonus

            # Penalty for conflicting information (simplified)
            conflict_penalty = 0.0  # Would be more sophisticated in reality

            confidence = base_confidence + result_bonus + quality_bonus - conflict_penalty
            return min(max(confidence, 0.0), 1.0)

        except Exception as e:
            logger.error(f"Error calculating certification confidence: {str(e)}")
            return 0.5

    def _prepare_sources(
        self,
        certification_results: List[Dict[str, Any]],
        license_results: List[Dict[str, Any]],
        marking_results: List[Dict[str, Any]],
        scheme: Optional[Scheme],
        standard: Standard
    ) -> List[Dict[str, Any]]:
        """Prepare source information for the certification info"""
        try:
            sources = []

            # Add standard as source
            sources.append({
                "type": "standard",
                "standard_id": standard.id,
                "standard_number": standard.standard_number,
                "title": standard.title,
                "relevance": "Primary standard"
            })

            # Add scheme as source if available
            if scheme:
                sources.append({
                    "type": "scheme",
                    "scheme_id": scheme.id,
                    "scheme_name": scheme.scheme_name,
                    "relevance": "Certification scheme"
                })

            # Add top results from each search as sources
            all_results = certification_results[:2] + license_results[:2] + marking_results[:2]
            for result in all_results:
                sources.append({
                    "type": "search_result",
                    "standard_id": result.get("standard_id"),
                    "clause_id": result.get("clause_id"),
                    "clause_number": result.get("clause_number"),
                    "text_preview": result.get("text", "")[:100] + "..." if len(result.get("text", "")) > 100 else result.get("text", ""),
                    "relevance_score": result.get("combined_score", 0.0),
                    "source_type": result.get("source_type"),
                    "organization": result.get("organization")
                })

            return sources

        except Exception as e:
            logger.error(f"Error preparing sources: {str(e)}")
            return [
                {
                    "type": "standard",
                    "standard_id": standard.id,
                    "standard_number": standard.standard_number,
                    "title": standard.title
                }
            ]

    def _create_fallback_certification_info(
        self,
        product_understanding: ProductUnderstanding,
        standard_id: int,
        standard_number: Optional[str] = None
    ) -> CertificationInfo:
        """Safe abstention when certification evidence is missing (Section 33, 34, 35)"""
        std_num = standard_number or "Not identified"
        try:
            db = next(get_db())
            try:
                standard = None
                if standard_id > 0:
                    standard = db.query(Standard).filter(Standard.id == standard_id).first()
                if not standard and standard_number:
                    standard = db.query(Standard).filter(Standard.standard_number == standard_number).first()
                if standard:
                    std_num = standard.standard_number
            finally:
                db.close()
        except Exception:
            pass

        return CertificationInfo(
            standard_id=standard_id,
            standard_number=std_num,
            certification_scheme="NOT_VERIFIED",
            license_required=False,
            marking_requirements=[],
            testing_requirements=[],
            factory_audit_required=False,
            documentation_requirements=[],
            certification_process=[],
            validity_period=None,
            renewal_requirements=[],
            applicable_products=[product_understanding.product_name] if product_understanding else [],
            confidence=0.0,
            sources=[]
        )

# Global agent instance
_certification_agent: Optional[CertificationAgent] = None

def get_certification_agent() -> CertificationAgent:
    """Get or create certification agent instance"""
    global _certification_agent
    if _certification_agent is None:
        _certification_agent = CertificationAgent()
    return _certification_agent