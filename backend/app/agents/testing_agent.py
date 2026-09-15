from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
import re
from app.services.standards.matching_engine import get_standards_matching_engine, StandardMatch
from app.services.retrieval.hybrid_retriever import get_hybrid_retriever
from app.services.products.product_understanding import ProductUnderstanding
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.standard import Scheme, Standard, Source

logger = logging.getLogger(__name__)

@dataclass
class TestingRequirement:
    """Represents a testing requirement for product certification"""
    test_type: str  # e.g., "Type Test", "Routine Test", "Sample Test", "Temperature Rise Test"
    description: str
    is_mandatory: bool
    source_reference: Dict[str, Any]  # Standard/clause reference
    details: Dict[str, Any] = None  # Additional details like sample size, duration, equipment
    test_method: Optional[str] = None  # Specific test method reference (e.g., "IS 12345:2020")
    acceptable_standards: Optional[List[str]] = None  # Acceptable result criteria

@dataclass
class LaboratoryInfo:
    """Information about a BIS-recognized laboratory"""
    lab_id: int
    lab_name: str
    address: str
    contact_person: str
    phone: str
    email: str
    website: Optional[str]
    accreditation_number: str
    accreditation_body: str  # e.g., "NABL"
    accredited_scopes: List[str]  # List of tests the lab is accredited for
    is_bis_recognized: bool
    testing_facilities: List[str]  # Specific facilities available
    geographical_coverage: str  # e.g., "Northern India", "All India"
    sample_collection_facility: bool
    report_turnaround_time: Optional[str]  # Typical time for test reports

@dataclass
class TestingInformation:
    """Complete testing information for a product-standard pair"""
    standard_id: int
    standard_number: str
    testing_requirements: List[TestingRequirement]
    recommended_laboratories: List[LaboratoryInfo]
    sample_requirements: Dict[str, Any]  # Sample size, preparation, sealing, etc.
    test_procedures: List[Dict[str, Any]]  # Step-by-step test procedures
    applicable_clauses: List[Dict[str, Any]]  # Relevant standard clauses
    estimated_testing_time: str  # Estimated duration for complete testing
    estimated_cost_range: Optional[str]  # Cost range if available
    confidence: float
    sources: List[Dict[str, Any]]

class TestingAgent:
    """Agent responsible for extracting test requirements and laboratory information for BIS certification"""

    def __init__(self):
        self.standards_matching_engine = get_standards_matching_engine()
        self.hybrid_retriever_factory = get_hybrid_retriever

    async def get_testing_information(
        self,
        product_understanding: ProductUnderstanding,
        standard_id: int,
        standard_number: Optional[str] = None
    ) -> TestingInformation:
        """
        Get testing information for a product and standard

        Args:
            product_understanding: Structured product information
            standard_id: ID of the standard to check for testing requirements
            standard_number: Optional standard number (e.g. 'IS 17526:2021')

        Returns:
            TestingInformation object with testing details
        """
        try:
            logger.info(f"Getting testing info for product: {product_understanding.product_name}, standard ID: {standard_id}, standard: {standard_number}")

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

                # Get hybrid retriever for searching testing-specific information
                retriever = self.hybrid_retriever_factory(db)

                # Search for testing requirements
                testing_query = f"""
                test requirements testing procedures sample size {standard.standard_number}
                {product_understanding.product_name} {product_understanding.category}
                """
                testing_results = await retriever.hybrid_search(
                    query=testing_query,
                    limit=10,
                    min_confidence=0.3,
                    filters={"standard_id": standard_id}
                )

                # Search for test methods
                test_method_query = f"""
                test method procedure {standard.standard_number}
                {product_understanding.intended_use} {product_understanding.category}
                """
                test_method_results = await retriever.hybrid_search(
                    query=test_method_query,
                    limit=8,
                    min_confidence=0.3,
                    filters={"standard_id": standard_id}
                )

                # Search for laboratory information
                lab_query = f"""
                BIS recognized laboratory testing facility {standard.standard_number}
                {product_understanding.category} accredited lab
                """
                lab_results = await retriever.hybrid_search(
                    query=lab_query,
                    limit=8,
                    min_confidence=0.3,
                    filters={"standard_id": standard_id}
                )

                # Process the results
                testing_info = await self._process_testing_data(
                    standard,
                    testing_results,
                    test_method_results,
                    lab_results,
                    product_understanding,
                    db
                )

                return testing_info

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error getting testing info: {str(e)}")
            # Return basic testing info on failure
            return self._create_fallback_testing_info(product_understanding, standard_id, standard_number)

    async def _process_testing_data(
        self,
        standard: Standard,
        testing_results: List[Dict[str, Any]],
        test_method_results: List[Dict[str, Any]],
        lab_results: List[Dict[str, Any]],
        product_understanding: ProductUnderstanding,
        db: Session
    ) -> TestingInformation:
        """Process testing data from search results"""

        # Extract testing requirements
        testing_requirements = self._extract_testing_requirements(
            testing_results, test_method_results, standard, product_understanding
        )

        # Extract laboratory information
        recommended_laboratories = self._extract_laboratory_info(
            lab_results, standard, product_understanding
        )

        # Extract sample requirements
        sample_requirements = self._extract_sample_requirements(
            testing_results, test_method_results, standard
        )

        # Extract test procedures
        test_procedures = self._extract_test_procedures(
            test_method_results, testing_results, standard
        )

        # Get applicable clauses
        applicable_clauses = self._extract_applicable_clauses(
            testing_results, test_method_results, standard
        )

        # Estimate testing time and cost
        estimated_testing_time = self._estimate_testing_time(testing_requirements)
        estimated_cost_range = self._estimate_cost_range(testing_requirements, standard)

        # Calculate confidence
        confidence = self._calculate_testing_confidence(
            testing_results, test_method_results, lab_results
        )

        # Prepare sources
        sources = self._prepare_sources(
            testing_results, test_method_results, lab_results, standard
        )

        return TestingInformation(
            standard_id=standard.id,
            standard_number=standard.standard_number,
            testing_requirements=testing_requirements,
            recommended_laboratories=recommended_laboratories,
            sample_requirements=sample_requirements,
            test_procedures=test_procedures,
            applicable_clauses=applicable_clauses,
            estimated_testing_time=estimated_testing_time,
            estimated_cost_range=estimated_cost_range,
            confidence=confidence,
            sources=sources
        )

    def _extract_testing_requirements(
        self,
        testing_results: List[Dict[str, Any]],
        test_method_results: List[Dict[str, Any]],
        standard: Standard,
        product_understanding: ProductUnderstanding
    ) -> List[TestingRequirement]:
        """Extract testing requirements from search results"""
        try:
            testing_requirements = []

            # Process testing results for requirement extraction
            for result in testing_results:
                text = result.get("text", "")
                heading = result.get("heading", "")

                # Check if this result contains testing requirement information
                testing_keywords = [
                    "test", "testing", "examination", "evaluation",
                    "requirement", "shall be tested", "must undergo",
                    "type test", "routine test", "sample test"
                ]

                if any(keyword in (text + heading).lower() for keyword in testing_keywords):
                    # Determine test type
                    test_type = self._determine_test_type(text, heading)

                    # Extract details
                    details = self._extract_test_details(text, heading)

                    requirement = TestingRequirement(
                        test_type=test_type,
                        description=f"{heading}: {text[:200]}{'...' if len(text) > 200 else ''}",
                        is_mandatory=self._is_mandatory_test(text, heading),
                        source_reference={
                            "standard_id": result.get("standard_id"),
                            "clause_id": result.get("clause_id"),
                            "clause_number": result.get("clause_number"),
                            "page": result.get("page")
                        },
                        details=details,
                        test_method=details.get("test_method") if details else None,
                        acceptable_standards=details.get("acceptable_criteria") if details else None
                    )
                    testing_requirements.append(requirement)

            # Add standard-specific testing requirements based on product category
            standard_requirements = self._get_standard_specific_testing(
                standard, product_understanding
            )
            testing_requirements.extend(standard_requirements)

            # If no specific testing requirements found, add general ones
            if not testing_requirements:
                testing_requirements = self._get_general_testing_requirements(standard)

            # Deduplicate requirements
            testing_requirements = self._deduplicate_testing_requirements(testing_requirements)

            return testing_requirements

        except Exception as e:
            logger.error(f"Error extracting testing requirements: {str(e)}")
            return self._get_general_testing_requirements(standard)

    def _determine_test_type(self, text: str, heading: str) -> str:
        """Determine the type of test from text"""
        text_lower = (text + heading).lower()

        if "type test" in text_lower or "type-test" in text_lower:
            return "Type Test"
        elif "routine test" in text_lower or "routine-test" in text_lower:
            return "Routine Test"
        elif "sample test" in text_lower or "sample-test" in text_lower:
            return "Sample Test"
        elif "temperature rise" in text_lower:
            return "Temperature Rise Test"
        elif "insulation resistance" in text_lower or "ir test" in text_lower:
            return "Insulation Resistance Test"
        elif "earth continuity" in text_lower or "ec test" in text_lower:
            return "Earth Continuity Test"
        elif "leakage current" in text_lower:
            return "Leakage Current Test"
        elif "mechanical strength" in text_lower:
            return "Mechanical Strength Test"
        elif "heating" in text_lower or "thermal" in text_lower:
            return "Heating Test"
        elif "voltage withstand" in text_lower or "hipot" in text_lower:
            return "Voltage Withstand Test"
        elif "protection against electric shock" in text_lower:
            return "Electric Shock Protection Test"
        elif "ingress protection" in text_lower or "ip test" in text_lower:
            return "Ingress Protection Test"
        elif "endurance" in text_lower:
            return "Endurance Test"
        else:
            return "Performance Test"

    def _extract_test_details(self, text: str, heading: str) -> Dict[str, Any]:
        """Extract detailed information about the test"""
        details = {}
        text_lower = (text + heading).lower()

        # Extract sample size information
        import re
        sample_patterns = [
            r'(\d+)\s*(?:samples?|specimens?|units?)',
            r'minimum\s+(\d+)\s*(?:samples?|specimens?|units?)',
            r'at\s+least\s+(\d+)\s*(?:samples?|specimens?|units?)'
        ]

        for pattern in sample_patterns:
            match = re.search(pattern, text_lower)
            if match:
                details["sample_size"] = int(match.group(1))
                break

        # Extract test duration
        duration_patterns = [
            r'(\d+)\s*(?:hours?|hrs?|days?|minutes?|min)',
            r'duration\s*:?\s*(\d+)\s*(?:hours?|hrs?|days?|min)'
        ]

        for pattern in duration_patterns:
            match = re.search(pattern, text_lower)
            if match:
                details["duration"] = match.group(0)
                break

        # Extract test method/reference
        method_patterns = [
            r'(?:is\s*:?\s*)?(\d{2,5}:\d{4})',  # IS XXXXX:YYYY
            r'(?:test\s+method\s*:?\s*)([^,\.]+)',
            r'(?:ref\s*:?\s*)([^,\.]+)'
        ]

        for pattern in method_patterns:
            match = re.search(pattern, text_lower)
            if match:
                details["test_method"] = match.group(1).strip().upper()
                break

        # Extract acceptable criteria
        criteria_patterns = [
            r'(?:shall\s+not\s+exceed|maximum|≤)\s*([^,\.]+)',
            r'(?:shall\s+be|minimum|≥)\s*([^,\.]+)',
            r'(?:acceptable\s+criteria\s*:?\s*)([^,\.]+)'
        ]

        for pattern in criteria_patterns:
            match = re.search(pattern, text_lower)
            if match:
                if "acceptable_criteria" not in details:
                    details["acceptable_criteria"] = []
                details["acceptable_criteria"].append(match.group(1).strip())

        # Extract equipment required
        equipment_keywords = ["equipment", "apparatus", "instrument", "device", "machine"]
        if any(keyword in text_lower for keyword in equipment_keywords):
            details["equipment_required"] = True

        return details if details else None

    def _is_mandatory_test(self, text: str, heading: str) -> bool:
        """Determine if a test is mandatory"""
        text_lower = (text + heading).lower()
        mandatory_indicators = [
            "shall", "must", "required", "mandatory", "compulsory",
            "is required", "are required", "shall be carried out"
        ]
        return any(indicator in text_lower for indicator in mandatory_indicators)

    def _get_standard_specific_testing(
        self,
        standard: Standard,
        product_understanding: ProductUnderstanding
    ) -> List[TestingRequirement]:
        """Get standard-specific testing requirements based on standard type"""
        requirements = []

        # Get standard scope/title for context
        standard_text = f"{standard.title} {standard.scope or ''}".lower()
        product_category = product_understanding.category.lower()

        # Electrical/electronic products
        if any(keyword in standard_text for keyword in ["electric", "electrical", "electronics"]):
            if any(keyword in product_category for keyword in ["switch", "socket", "accessory"]):
                requirements.extend([
                    TestingRequirement(
                        test_type="Temperature Rise Test",
                        description="Temperature rise test at rated current as per IS 3854",
                        is_mandatory=True,
                        source_reference={"standard_id": standard.id},
                        details={"test_method": "IS 3854", "duration": "1 hour minimum"}
                    ),
                    TestingRequirement(
                        test_type="Mechanical Strength Test",
                        description="Mechanical strength test of terminals and enumeration",
                        is_mandatory=True,
                        source_reference={"standard_id": standard.id}
                    ),
                    TestingRequirement(
                        test_type="Electric Strength Test",
                        description="Electric strength test (high voltage test)",
                        is_mandatory=True,
                        source_reference={"standard_id": standard.id},
                        details={"test_method": "HV Test", "voltage": "1.5 kV for 1 minute"}
                    )
                ])
            elif any(keyword in product_category for keyword in ["cable", "wire", "conductor"]):
                requirements.extend([
                    TestingRequirement(
                        test_type="Conductor Resistance Test",
                        description="DC resistance test of conductor",
                        is_mandatory=True,
                        source_reference={"standard_id": standard.id}
                    ),
                    TestingRequirement(
                        test_type="Insulation Resistance Test",
                        description="Insulation resistance test between conductor and sheath",
                        is_mandatory=True,
                        source_reference={"standard_id": standard.id},
                        details={"test_method": "IR Test", "voltage": "500V DC"}
                    ),
                    TestingRequirement(
                        test_type="High Voltage Test",
                        description="High voltage test (HV test) on complete cable",
                        is_mandatory=True,
                        source_reference={"standard_id": standard.id}
                    )
                ])

        # Mechanical products
        elif any(keyword in standard_text for keyword in ["mechanical", "metal", "steel", "pipe"]):
            if "pipe" in product_category or "tube" in product_category:
                requirements.extend([
                    TestingRequirement(
                        test_type="Hydrostatic Test",
                        description="Hydrostatic pressure test on pipes",
                        is_mandatory=True,
                        source_reference={"standard_id": standard.id},
                        details={"pressure": "1.5 times working pressure", "duration": "5 seconds"}
                    ),
                    TestingRequirement(
                        test_type="Bend Test",
                        description="Bend test to check ductility",
                        is_mandatory=True,
                        source_reference={"standard_id": standard.id}
                    ),
                    TestingRequirement(
                        test_type="Flattening Test",
                        description="Flattening test for weld integrity",
                        is_mandatory=True,
                        source_reference={"standard_id": standard.id}
                    )
                ])

        # Chemical products
        elif any(keyword in standard_text for keyword in ["chemical", "polymer", "plastic"]):
            requirements.extend([
                TestingRequirement(
                    test_type="Melt Flow Index Test",
                    description="Melt flow index test for polymers",
                    is_mandatory=True,
                    source_reference={"standard_id": standard.id}
                ),
                TestingRequirement(
                    test_type="Density Test",
                    description="Density test of plastic material",
                    is_mandatory=True,
                    source_reference={"standard_id": standard.id}
                )
            ])

        return requirements

    def _get_general_testing_requirements(self, standard: Standard) -> List[TestingRequirement]:
        """Get general testing requirements when specific ones not found"""
        std_num = standard.standard_number if standard else ""
        if not std_num or std_num.lower() in ["unknown", "none", ""]:
            desc_type = "Testing method could not be verified from the authoritative sources retrieved."
            desc_routine = "Routine production testing requirements could not be verified."
        else:
            clean_num = std_num.strip()
            if not clean_num.upper().startswith("IS"):
                clean_num = f"IS {clean_num}"
            desc_type = f"Complete type testing as per {clean_num}"
            desc_routine = f"Routine tests during production as per {clean_num}"

        return [
            TestingRequirement(
                test_type="Type Test",
                description=desc_type,
                is_mandatory=True,
                source_reference={"standard_id": standard.id if standard else 0},
                details={
                    "sample_size": "As per standard requirements",
                    "test_types": ["Visual inspection", "Dimensional check", "Performance test"]
                }
            ),
            TestingRequirement(
                test_type="Routine Test",
                description=desc_routine,
                is_mandatory=True,
                source_reference={"standard_id": standard.id if standard else 0}
            )
        ]

    def _deduplicate_testing_requirements(
        self,
        requirements: List[TestingRequirement]
    ) -> List[TestingRequirement]:
        """Remove duplicate testing requirements"""
        seen = set()
        unique_requirements = []

        for req in requirements:
            # Create a key based on test type and description
            key = (req.test_type, req.description[:50])  # First 50 chars of description
            if key not in seen:
                seen.add(key)
                unique_requirements.append(req)

        return unique_requirements

    def _extract_laboratory_info(
        self,
        lab_results: List[Dict[str, Any]],
        standard: Standard,
        product_understanding: ProductUnderstanding
    ) -> List[LaboratoryInfo]:
        """Extract laboratory information from search results"""
        try:
            laboratories = []

            for result in lab_results:
                text = result.get("text", "")
                heading = result.get("heading", "")

                # Check if this result contains laboratory information
                lab_keywords = [
                    "laboratory", "lab", "testing facility", "test house",
                    "accredited", "recognized", "approved", "bis recognized"
                ]

                if any(keyword in (text + heading).lower() for keyword in lab_keywords):
                    lab = self._parse_laboratory_info(result, standard)
                    if lab:
                        laboratories.append(lab)

            # If no specific labs found, add some well-known BIS-recognized labs
            if not laboratories:
                laboratories = self._get_default_laboratories(product_understanding.category)

            return laboratories[:5]  # Limit to top 5 laboratories

        except Exception as e:
            logger.error(f"Error extracting laboratory info: {str(e)}")
            return self._get_default_laboratories(product_understanding.category)

    def _parse_laboratory_info(
        self,
        result: Dict[str, Any],
        standard: Standard
    ) -> Optional[LaboratoryInfo]:
        """Parse laboratory information from search result"""
        try:
            text = result.get("text", "")
            heading = result.get("heading", "")

            # Extract lab name (usually in heading or first part of text)
            lab_name = heading if heading and len(heading) > 5 else text.split('.')[0][:100]

            # Extract address information
            address = ""
            address_patterns = [
                r'address\s*:?\s*([^,\n]+(?:,[^,\n]+){1,3})',
                r'located\s+at\s*:?\s*([^,\n]+(?:,[^,\n]+){1,3})',
                r'([^,\n]+,\s*[^,\n]+,\s*[^,\n]+)'  # Simple city, state pattern
            ]

            for pattern in address_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    address = match.group(1).strip()
                    break

            # Extract contact information
            contact_person = ""
            phone = ""
            email = ""

            # Contact person
            contact_patterns = [
                r'contact\s*:?\s*([^,\n]+)',
                r'person\s*:?\s*([^,\n]+)',
                r'(\w+\s+\w+).*?(?:manager|engineer|officer)'
            ]

            for pattern in contact_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    contact_person = match.group(1).strip()
                    break

            # Phone
            phone_patterns = [
                r'phone\s*:?\s*(\+?\d[\d\s\-\(\)]{8,})',
                r'tel\s*:?\s*(\+?\d[\d\s\-\(\)]{8,})',
                r'(\+91[\-\s]?\d{3}[\-\s]?\d{3}[\-\s]?\d{4})'
            ]

            for pattern in phone_patterns:
                match = re.search(pattern, text)
                if match:
                    phone = match.group(1).strip()
                    break

            # Email
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            email_match = re.search(email_pattern, text)
            if email_match:
                email = email_match.group(0)

            # Accreditation
            accreditation_number = ""
            accreditation_body = "NABL"  # Default for India
            accredited_scopes = []

            accred_patterns = [
                r'accreditation\s*[no\.]*\s*:?\s*([^,\n]+)',
                r'accredited\s+by\s+([^,\n]+)',
                r'(?:is\s+)?([^,\n]*nab[lL][^,\n]*)'
            ]

            for pattern in accred_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    accreditation_number = match.group(1).strip()
                    if "nabl" in match.group(0).lower():
                        accreditation_body = "NABL"
                    break

            # Determine accredited scopes based on standard and result text
            std_num = getattr(standard, 'standard_number', getattr(standard, 'number', ''))
            standard_text = f"{standard.title} {std_num}".lower()
            result_text = text.lower()

            if any(keyword in result_text for keyword in ["electrical", "electric"]):
                accredited_scopes = ["Electrical Testing", "Safety Testing"]
            elif any(keyword in result_text for keyword in ["mechanical", "metal"]):
                accredited_scopes = ["Mechanical Testing", "Material Testing"]
            elif any(keyword in result_text for keyword in ["chemical", "polymer"]):
                accredited_scopes = ["Chemical Testing", "Polymer Testing"]
            else:
                accredited_scopes = ["General Testing"]

            # Testing facilities
            testing_facilities = []
            facility_keywords = ["laboratory", "facility", "equipment", "instrument"]
            for keyword in facility_keywords:
                if keyword in result_text:
                    testing_facilities.append(f"{keyword.title()} Testing Facility")

            if not testing_facilities:
                testing_facilities = ["Standard Testing Facilities"]

            return LaboratoryInfo(
                lab_id=hash(lab_name + address) % 10000,  # Simple ID generation
                lab_name=lab_name[:100] if lab_name else "Unnamed Laboratory",
                address=address[:200] if address else "Address not specified",
                contact_person=contact_person[:100] if contact_person else "Contact not specified",
                phone=phone[:20] if phone else "Phone not specified",
                email=email[:100] if email else "Email not specified",
                website="",  # Would need more sophisticated parsing
                accreditation_number=accreditation_number[:50] if accreditation_number else "Not specified",
                accreditation_body=accreditation_body,
                accredited_scopes=accredited_scopes,
                is_bis_recognized="bis" in text.lower() or "recognized" in text.lower(),
                testing_facilities=testing_facilities,
                geographical_coverage="All India",  # Default assumption
                sample_collection_facility=True,  # Assume available unless specified otherwise
                report_turnaround_time="7-15 days"  # Typical range
            )

        except Exception as e:
            logger.error(f"Error parsing laboratory info: {str(e)}")
            return None

    def _get_default_laboratories(self, category: str) -> List[LaboratoryInfo]:
        """Never fabricate default laboratories (Rule 0 & Section 37)"""
        return []

    def _extract_sample_requirements(
        self,
        testing_results: List[Dict[str, Any]],
        test_method_results: List[Dict[str, Any]],
        standard: Standard
    ) -> Dict[str, Any]:
        """Extract sample requirements for testing"""
        try:
            sample_req = {
                "sample_size": "As per standard requirements",
                "sample_preparation": "Standard conditioning required",
                "sealing_requirements": "Samples shall be sealed and marked",
                "identification": "Each sample shall be uniquely identified",
                "storage": "Store in standard atmospheric conditions unless specified otherwise"
            }

            # Look for specific sample information in results
            all_results = testing_results + test_method_results
            for result in all_results:
                text = result.get("text", "").lower()
                heading = result.get("heading", "").lower()
                combined = text + " " + heading

                # Sample size
                import re
                size_match = re.search(r'(\d+)\s*(?:samples?|specimens?|units?)\s*(?:shall|must|should)', combined)
                if size_match:
                    sample_req["sample_size"] = f"{size_match.group(1)} samples"

                # Conditioning
                if "condition" in combined or "conditioning" in combined:
                    cond_match = re.search(r'condition(?:ed|ing)\s+[^,\.]+', combined)
                    if cond_match:
                        sample_req["sample_preparation"] = cond_match.group(0).strip().title()

                # Sealing
                if "seal" in combined or "sealed" in combined:
                    sample_req["sealing_requirements"] = "Samples shall be properly sealed as per standard"

            return sample_req

        except Exception as e:
            logger.error(f"Error extracting sample requirements: {str(e)}")
            return {
                "sample_size": "As per standard requirements",
                "sample_preparation": "Standard conditioning required",
                "sealing_requirements": "Samples shall be sealed and marked",
                "identification": "Each sample shall be uniquely identified"
            }

    def _extract_test_procedures(
        self,
        test_method_results: List[Dict[str, Any]],
        testing_results: List[Dict[str, Any]],
        standard: Standard
    ) -> List[Dict[str, Any]]:
        """Extract step-by-step test procedures"""
        try:
            procedures = []

            # Look for procedural information in test method results
            for result in test_method_results:
                text = result.get("text", "")
                heading = result.get("heading", "")

                # Check if this contains procedural information
                proc_keywords = [
                    "procedure", "step", "method", "process",
                    "shall be", "procedure is", "test procedure"
                ]

                if any(keyword in (text + heading).lower() for keyword in proc_keywords):
                    # Extract procedure steps (simple approach - split by sentences)
                    sentences = [s.strip() for s in text.split('.') if s.strip() and len(s.strip()) > 20]
                    if sentences:
                        procedure = {
                            "test_type": self._determine_test_type(text, heading),
                            "description": heading if heading else "Test Procedure",
                            "steps": sentences[:5],  # Limit to first 5 meaningful sentences
                            "reference": {
                                "standard_id": result.get("standard_id"),
                                "clause_number": result.get("clause_number"),
                                "page": result.get("page")
                            }
                        }
                        procedures.append(procedure)

            # If no specific procedures found, add general ones
            if not procedures:
                procedures = [
                    {
                        "test_type": "Visual Inspection",
                        "description": "Visual examination of the product",
                        "steps": [
                            "Clean the product surface if necessary",
                            "Examine under adequate lighting (minimum 200 lux)",
                            "Check for visible defects, damages, or irregularities",
                            "Verify markings and labels are legible and correct",
                            "Document observations with photographs if required"
                        ],
                        "reference": {"standard_id": standard.id}
                    },
                    {
                        "test_type": "Dimensional Check",
                        "description": "Verification of critical dimensions",
                        "steps": [
                            "Calibrate measuring instruments before use",
                            "Measure at specified environmental conditions",
                            "Take multiple measurements at different points",
                            "Calculate average and compare with tolerance limits",
                            "Record all measurements with units"
                        ],
                        "reference": {"standard_id": standard.id}
                    }
                ]

            return procedures

        except Exception as e:
            logger.error(f"Error extracting test procedures: {str(e)}")
            return [{
                "test_type": "General Testing",
                "description": "Standard test procedure",
                "steps": ["Follow standard test procedure as specified in the relevant standard"],
                "reference": {"standard_id": standard.id}
            }]

    def _extract_applicable_clauses(
        self,
        testing_results: List[Dict[str, Any]],
        test_method_results: List[Dict[str, Any]],
        standard: Standard
    ) -> List[Dict[str, Any]]:
        """Extract applicable standard clauses for testing"""
        try:
            clauses = []

            # Combine all results to find testing-related clauses
            all_results = testing_results + test_method_results

            for result in all_results:
                text = result.get("text", "").lower()
                heading = result.get("heading", "").lower()
                combined = text + " " + heading

                # Check if this result is related to testing
                testing_indicators = [
                    "test", "testing", "examine", "measure", "check",
                    "verify", "determine", "assess", "evaluate"
                ]

                if any(indicator in combined for indicator in testing_indicators):
                    clause_info = {
                        "clause_id": result.get("clause_id"),
                        "clause_number": result.get("clause_number"),
                        "heading": result.get("heading"),
                        "text_preview": (result.get("text", "")[:150] + "...")
                                       if len(result.get("text", "")) > 150
                                       else result.get("text", ""),
                        "relevance_score": result.get("combined_score", 0.0),
                        "test_relevance": "High" if any(word in combined
                                                      for word in ["test", "testing", "examine"])
                                        else "Medium"
                    }
                    clauses.append(clause_info)

            # Sort by relevance score
            clauses.sort(key=lambda x: x["relevance_score"], reverse=True)

            # Limit to top clauses
            return clauses[:10]

        except Exception as e:
            logger.error(f"Error extracting applicable clauses: {str(e)}")
            return [{
                "clause_id": None,
                "clause_number": "General",
                "heading": "Testing Requirements",
                "text_preview": "Refer to the complete standard for testing requirements",
                "relevance_score": 0.5,
                "test_relevance": "Medium"
            }]

    def _estimate_testing_time(self, testing_requirements: List[TestingRequirement]) -> str:
        """Estimate total testing time based on requirements"""
        try:
            if not testing_requirements:
                return "2-4 weeks"

            # Simple estimation based on test types
            time_mapping = {
                "Type Test": "1-2 weeks",
                "Routine Test": "2-4 days",
                "Sample Test": "3-5 days",
                "Temperature Rise Test": "1-2 days",
                "Insulation Resistance Test": "4-8 hours",
                "Earth Continuity Test": "2-4 hours",
                "Leakage Current Test": "4-8 hours",
                "Mechanical Strength Test": "1-2 days",
                "Heating Test": "1-3 days",
                "Voltage Withstand Test": "1 day",
                "Electric Shock Protection Test": "1 day",
                "Ingress Protection Test": "1-2 days",
                "Endurance Test": "1-4 weeks",
                "Performance Test": "3-7 days",
                "Visual Inspection": "4-8 hours",
                "Dimensional Check": "1-2 days"
            }

            # Calculate estimated time
            total_days = 0
            for req in testing_requirements:
                test_type = req.test_type
                if test_type in time_mapping:
                    time_str = time_mapping[test_type]
                    # Extract number of days (simplified)
                    if "week" in time_str:
                        weeks = float(time_str.split('-')[0]) if '-' in time_str else float(time_str.split()[0])
                        total_days += weeks * 7
                    elif "day" in time_str:
                        days = float(time_str.split('-')[0]) if '-' in time_str else float(time_str.split()[0])
                        total_days += days
                    elif "hour" in time_str:
                        hours = float(time_str.split('-')[0]) if '-' in time_str else float(time_str.split()[0])
                        total_days += hours / 8  # Convert hours to working days

            # Add buffer for setup, reporting, etc.
            total_days = max(total_days, 3)  # Minimum 3 days
            total_days = total_days * 1.3  # 30% buffer

            # Convert back to readable format
            if total_days >= 14:
                weeks = total_days / 7
                return f"{weeks:.1f}-{weeks*1.3:.1f} weeks"
            elif total_days >= 3:
                return f"{total_days:.0f}-{total_days*1.3:.0f} days"
            else:
                hours = total_days * 8
                return f"{hours:.0f}-{hours*1.3:.0f} hours"

        except Exception as e:
            logger.error(f"Error estimating testing time: {str(e)}")
            return "2-4 weeks"

    def _estimate_cost_range(
        self,
        testing_requirements: List[TestingRequirement],
        standard: Standard
    ) -> Optional[str]:
        """Estimate testing cost range"""
        try:
            # This would ideally come from a database or external API
            # For now, return a placeholder based on standard type and test complexity

            if not testing_requirements:
                return "₹15,000 - ₹50,000"

            # Simple cost estimation
            base_cost = 10000  # Base cost in INR
            cost_per_test = {
                "Type Test": 8000,
                "Routine Test": 3000,
                "Sample Test": 4000,
                "Temperature Rise Test": 5000,
                "Insulation Resistance Test": 2000,
                "Earth Continuity Test": 1500,
                "Leakage Current Test": 2500,
                "Mechanical Strength Test": 4000,
                "Heating Test": 3000,
                "Voltage Withstand Test": 2000,
                "Electric Shock Protection Test": 2500,
                "Ingress Protection Test": 3000,
                "Endurance Test": 10000,
                "Performance Test": 5000,
                "Visual Inspection": 1000,
                "Dimensional Check": 2000
            }

            total_cost = base_cost
            for req in testing_requirements:
                test_type = req.test_type
                if test_type in cost_per_test:
                    total_cost += cost_per_test[test_type]
                else:
                    total_cost += 3000  # Default for unknown test types

            # Add variability (±30%)
            min_cost = int(total_cost * 0.7)
            max_cost = int(total_cost * 1.3)

            return f"₹{min_cost:,} - ₹{max_cost:,}"

        except Exception as e:
            logger.error(f"Error estimating cost range: {str(e)}")
            return None

    def _calculate_testing_confidence(
        self,
        testing_results: List[Dict[str, Any]],
        test_method_results: List[Dict[str, Any]],
        lab_results: List[Dict[str, Any]]
    ) -> float:
        """Calculate confidence in testing information"""
        try:
            # Start with base confidence
            base_confidence = 0.4

            # Boost from having results
            result_bonus = 0.0
            if testing_results:
                result_bonus += 0.2
            if test_method_results:
                result_bonus += 0.15
            if lab_results:
                result_bonus += 0.15

            # Boost from high-quality scores
            quality_bonus = 0.0
            all_results = testing_results + test_method_results + lab_results
            if all_results:
                avg_score = sum(r.get("combined_score", 0.0) for r in all_results) / len(all_results)
                quality_bonus = avg_score * 0.2  # Up to 0.2 bonus

            confidence = base_confidence + result_bonus + quality_bonus
            return min(max(confidence, 0.0), 1.0)

        except Exception as e:
            logger.error(f"Error calculating testing confidence: {str(e)}")
            return 0.5

    def _prepare_sources(
        self,
        testing_results: List[Dict[str, Any]],
        test_method_results: List[Dict[str, Any]],
        lab_results: List[Dict[str, Any]],
        standard: Standard
    ) -> List[Dict[str, Any]]:
        """Prepare source information for the testing info"""
        try:
            sources = []

            # Add standard as source
            sources.append({
                "type": "standard",
                "standard_id": standard.id,
                "standard_number": standard.standard_number,
                "title": standard.title,
                "relevance": "Primary standard for testing requirements"
            })

            # Add top results from each search as sources
            all_results = (
                testing_results[:3] +
                test_method_results[:3] +
                lab_results[:3]
            )

            for result in all_results:
                source_type = "test_result"
                if result in lab_results:
                    source_type = "lab_result"
                elif result in test_method_results:
                    source_type = "method_result"

                sources.append({
                    "type": source_type,
                    "standard_id": result.get("standard_id"),
                    "clause_id": result.get("clause_id"),
                    "clause_number": result.get("clause_number"),
                    "text_preview": (result.get("text", "")[:100] + "...")
                                   if len(result.get("text", "")) > 100
                                   else result.get("text", ""),
                    "relevance_score": result.get("combined_score", 0.0),
                    "source_type": result.get("source_type"),
                    "organization": result.get("organization"),
                    "lab_name": result.get("heading", "")[:100] if source_type == "lab_result" else None
                })

            return sources

        except Exception as e:
            logger.error(f"Error preparing sources: {str(e)}")
            return [{
                "type": "standard",
                "standard_id": standard.id,
                "standard_number": standard.standard_number,
                "title": standard.title
            }]

    def _create_fallback_testing_info(
        self,
        product_understanding: ProductUnderstanding,
        standard_id: int,
        standard_number: Optional[str] = None
    ) -> TestingInformation:
        """Safe abstention when testing evidence cannot be verified (Rule 0 & Section 36)"""
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

        return TestingInformation(
            standard_id=standard_id,
            standard_number=std_num,
            testing_requirements=[],
            recommended_laboratories=[],
            sample_requirements={},
            test_procedures=[],
            applicable_clauses=[],
            estimated_testing_time="Not verified from retrieved authoritative evidence",
            estimated_cost_range=None,
            confidence=0.0,
            sources=[]
        )

# Global agent instance
_testing_agent: Optional[TestingAgent] = None

def get_testing_agent() -> TestingAgent:
    """Get or create testing agent instance"""
    global _testing_agent
    if _testing_agent is None:
        _testing_agent = TestingAgent()
    return _testing_agent