from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging
import re
from urllib.parse import urlparse
from app.services.web_retrieval import get_web_retrieval_service, WebSearchResult
from app.services.products.product_understanding import ProductUnderstanding
from app.services.standards.matching_engine import get_standards_matching_engine, StandardMatch
from app.services.retrieval.hybrid_retriever import get_hybrid_retriever

logger = logging.getLogger(__name__)

@dataclass
class Citation:
    """A reference to a source"""
    citation_id: str
    text: str  # The citation text as it appears
    type: str  # e.g., "standard", "web", "journal", "report"
    reference: Dict[str, Any]  # Structured reference (URL, DOI, standard number, etc.)
    confidence: float = 0.0  # Confidence in the citation extraction

@dataclass
class Claim:
    """A statement that needs verification"""
    claim_id: str
    text: str  # The claim statement
    citations: List[str] = field(default_factory=list)  # List of citation IDs that support this claim
    context: str = ""  # Surrounding text for context

@dataclass
class VerificationResult:
    """Result of verifying a claim against its citations"""
    claim_id: str
    claim_text: str
    is_verified: bool  # Whether the claim is supported by citations
    confidence: float  # Confidence in the verification (0-1)
    verification_details: List[Dict[str, Any]]  # Details for each citation checked
    overall_assessment: str  # Summary of verification outcome
    recommendations: List[str] = field(default_factory=list)  # Suggestions for improvement

class CitationVerificationAgent:
    """Agent responsible for verifying claims by checking their citations against sources"""

    def __init__(self):
        self.web_retrieval_service = get_web_retrieval_service()
        self.standards_matching_engine = get_standards_matching_engine()
        self.hybrid_retriever_factory = get_hybrid_retriever
        # Known citation patterns
        self.citation_patterns = [
            # Standard format: IS 1234:2020 or IS 1234 (2020)
            (r'IS\s+(\d{2,5})\s*:?\s*(\d{4})', 'standard'),
            # Web URLs
            (r'https?://[^\s\)]+', 'web'),
            # DOI
            (r'doi:\s*10\.\d{4,9}/[-._;()/:A-Z0-9]+', 'doi', re.IGNORECASE),
            # Simple reference: [1], [2,3], etc.
            (r'\[\s*\d+(?:\s*,\s*\d+)*\s*\]', 'reference'),
            # Author year: (Smith, 2020)
            (r'\(\s*[A-Z][a-z]+(?:\s+et\s+al\.)?,\s*\d{4}\s*\)', 'author_year'),
        ]

    async def verify_claims_in_text(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[VerificationResult]:
        """
        Verify claims in a given text by checking their citations

        Args:
            text: Text containing claims and citations
            context: Optional context (product understanding, etc.)

        Returns:
            List of VerificationResult objects
        """
        try:
            logger.info("Verifying claims in text")

            # Extract claims and citations
            claims_with_citations = self._extract_claims_and_citations(text)

            # Verify each claim
            results = []
            for claim_data in claims_with_citations:
                result = await self._verify_claim(
                    claim_data['claim'],
                    claim_data['citations'],
                    context
                )
                results.append(result)

            logger.info(f"Claim verification completed for {len(results)} claims")
            return results

        except Exception as e:
            logger.error(f"Error verifying claims: {str(e)}")
            return []

    async def verify_product_claims(
        self,
        product_understanding: ProductUnderstanding,
        source_text: str
    ) -> List[VerificationResult]:
        """
        Verify claims made about a product in source text

        Args:
            product_understanding: Structured product information
            source_text: Text containing claims about the product

        Returns:
            List of VerificationResult objects
        """
        try:
            logger.info(f"Verifying product claims for: {product_understanding.product_name}")

            # Extract claims from source text that relate to the product
            claims_with_citations = self._extract_product_related_claims(
                source_text,
                product_understanding
            )

            # Verify each claim
            results = []
            for claim_data in claims_with_citations:
                result = await self._verify_claim(
                    claim_data['claim'],
                    claim_data['citations'],
                    {'product_understanding': product_understanding}
                )
                results.append(result)

            logger.info(f"Product claim verification completed for {len(results)} claims")
            return results

        except Exception as e:
            logger.error(f"Error verifying product claims: {str(e)}")
            return []

    # ------------------------------------------------------------------
    # Core verification methods
    # ------------------------------------------------------------------

    async def _verify_claim(
        self,
        claim: Claim,
        citation_ids: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> VerificationResult:
        """Verify a single claim against its citations"""
        try:
            verification_details = []
            supported_citations = 0
            total_citations = len(citation_ids)

            # Get the actual citation objects (in a full system, we'd look these up by ID)
            # For now, we'll work with the citation texts directly from the claim
            citation_texts = claim.citations  # This should be the actual citation texts

            for citation_text in citation_texts:
                # Extract structured citation info
                citation_info = self._parse_citation(citation_text)

                # Verify the citation
                citation_result = await self._verify_citation(
                    citation_info,
                    claim.text,
                    context
                )

                verification_details.append({
                    'citation_text': citation_text,
                    'citation_type': citation_info.get('type', 'unknown'),
                    'is_accessible': citation_result['is_accessible'],
                    'supports_claim': citation_result['supports_claim'],
                    'confidence': citation_result['confidence'],
                    'details': citation_result.get('details', {})
                })

                if citation_result['supports_claim']:
                    supported_citations += 1

            # Determine if claim is verified
            # A claim is verified if at least one citation supports it with good confidence
            is_verified = supported_citations > 0

            # Calculate overall confidence
            if total_citations > 0:
                avg_confidence = sum(d['confidence'] for d in verification_details) / total_citations
                # Boost confidence if we have supporting citations
                support_ratio = supported_citations / total_citations if total_citations > 0 else 0
                confidence = min(avg_confidence + (support_ratio * 0.3), 1.0)
            else:
                confidence = 0.0

            # Generate assessment
            if is_verified and confidence > 0.7:
                assessment = "Claim is well-supported by citations"
            elif is_verified and confidence > 0.4:
                assessment = "Claim has some supporting evidence"
            elif not is_verified and total_citations > 0:
                assessment = "Claim is not supported by available citations"
            else:
                assessment = "No citations found for claim verification"

            # Generate recommendations
            recommendations = self._generate_recommendations(
                claim,
                verification_details,
                is_verified,
                confidence
            )

            return VerificationResult(
                claim_id=claim.claim_id,
                claim_text=claim.text,
                is_verified=is_verified,
                confidence=confidence,
                verification_details=verification_details,
                overall_assessment=assessment,
                recommendations=recommendations
            )

        except Exception as e:
            logger.error(f"Error verifying claim: {str(e)}")
            return VerificationResult(
                claim_id=claim.claim_id,
                claim_text=claim.text,
                is_verified=False,
                confidence=0.0,
                verification_details=[],
                overall_assessment=f"Verification error: {str(e)}",
                recommendations=["Manual verification required due to processing error"]
            )

    async def _verify_citation(
        self,
        citation_info: Dict[str, Any],
        claim_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Verify a single citation"""
        try:
            citation_type = citation_info.get('type', 'unknown')
            reference = citation_info.get('reference', {})

            # Check if citation is accessible
            is_accessible = False
            supports_claim = False
            confidence = 0.0
            details = {}

            if citation_type == 'web':
                url = reference.get('url')
                if url:
                    # Try to fetch the webpage
                    text, status_code, error = self._fetch_web_source(url)
                    is_accessible = (status_code == 200 and error is None)

                    if is_accessible and text:
                        # Check if the text supports the claim
                        support_result = self._check_text_supports_claim(text, claim_text)
                        supports_claim = support_result['supports']
                        confidence = support_result['confidence']
                        details = {
                            'fetch_status': status_code,
                            'content_length': len(text),
                            'support_details': support_result.get('details', {})
                        }
                    else:
                        details = {
                            'fetch_status': status_code,
                            'error': error
                        }

            elif citation_type == 'standard':
                # Verify against BIS standard documents
                std_result = await self._verify_standard_citation(reference, claim_text, context)
                is_accessible = std_result['is_accessible']
                supports_claim = std_result['supports_claim']
                confidence = std_result['confidence']
                details = std_result.get('details', {})

            elif citation_type == 'doi':
                # Verify via DOI resolution (simplified)
                doi_result = await self._verify_doi_citation(reference, claim_text)
                is_accessible = doi_result['is_accessible']
                supports_claim = doi_result['supports_claim']
                confidence = doi_result['confidence']
                details = doi_result.get('details', {})

            else:
                # For other types, we can't easily verify
                is_accessible = True  # Assume accessible if we can't check
                confidence = 0.3  # Low confidence for unverifiable citations
                details = {'note': 'Citation type not automatically verifiable'}

            return {
                'is_accessible': is_accessible,
                'supports_claim': supports_claim,
                'confidence': confidence,
                'details': details
            }

        except Exception as e:
            logger.warning(f"Error verifying citation: {str(e)}")
            return {
                'is_accessible': False,
                'supports_claim': False,
                'confidence': 0.0,
                'details': {'error': str(e)}
            }

    def _fetch_web_source(self, url: str) -> Tuple[Optional[str], int, Optional[str]]:
        """Fetch a web source and return (text, status_code, error)"""
        try:
            # Use the web retrieval service to fetch
            # We'll do a simple request for now
            import requests
            from bs4 import BeautifulSoup

            headers = {'User-Agent': 'BIS-Compass/1.0 (Citation Verification)'}
            response = requests.get(url, headers=headers, timeout=10)
            status_code = response.status_code

            if status_code == 200:
                # Extract text from HTML
                soup = BeautifulSoup(response.content, 'html.parser')
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text(separator=' ', strip=True)
                # Limit length
                if len(text) > 5000:
                    text = text[:5000] + "..."
                return text, status_code, None
            else:
                return None, status_code, f"HTTP {status_code}"

        except requests.exceptions.Timeout:
            return None, 408, "Timeout"
        except requests.exceptions.RequestException as e:
            return None, 0, str(e)
        except Exception as e:
            return None, 0, f"Unexpected error: {e}"

    def _check_text_supports_claim(self, text: str, claim_text: str) -> Dict[str, Any]:
        """Check if text supports a claim"""
        try:
            if not text or not claim_text:
                return {'supports': False, 'confidence': 0.0, 'details': {}}

            text_lower = text.lower()
            claim_lower = claim_text.lower()

            # Simple approach: check for claim keywords in text
            claim_words = set(re.findall(r'\b\w+\b', claim_lower))
            text_words = set(re.findall(r'\b\w+\b', text_lower))

            if not claim_words:
                return {'supports': False, 'confidence': 0.0, 'details': {}}

            # Calculate overlap
            overlap = claim_words.intersection(text_words)
            overlap_ratio = len(overlap) / len(claim_words) if claim_words else 0

            # Also check for negation near key terms
            negation_score = self._check_for_negation(text_lower, claim_lower)

            # Base confidence from word overlap
            confidence = overlap_ratio * 0.7  # Word overlap contributes 70%

            # Adjust for negation
            confidence = max(0.0, confidence - negation_score * 0.5)

            supports = confidence > 0.3  # Threshold for consideration as supporting

            details = {
                'claim_words_found': len(overlap),
                'total_claim_words': len(claim_words),
                'overlap_ratio': overlap_ratio,
                'negation_adjustment': negation_score
            }

            return {
                'supports': supports,
                'confidence': confidence,
                'details': details
            }

        except Exception as e:
            logger.warning(f"Error checking text support: {str(e)}")
            return {'supports': False, 'confidence': 0.0, 'details': {'error': str(e)}}

    def _check_for_negation(self, text: str, claim: str) -> float:
        """Check for negation words near claim keywords"""
        negation_words = ['not', 'no', 'never', 'none', 'nothing', 'nowhere',
                         'neither', 'nor', 'cannot', 'can not', "can't",
                         'won\'t', 'will not', 'did not', 'does not', 'is not',
                         'are not', 'was not', 'were not', 'has not', 'have not']

        # Simple approach: if negation words appear in text, reduce confidence
        # A more sophisticated version would check proximity to claim terms
        negation_count = sum(1 for word in negation_words if word in text)
        # Normalize by text length
        return min(negation_count * 0.1, 0.5)  # Max 0.5 penalty

    async def _verify_standard_citation(
        self,
        reference: Dict[str, Any],
        claim_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Verify a citation to a BIS standard"""
        try:
            standard_number = reference.get('standard_number')
            if not standard_number:
                return {
                    'is_accessible': True,  # Assume we can't check
                    'supports_claim': False,
                    'confidence': 0.1,
                    'details': {'reason': 'No standard number in reference'}
                }

            # Try to get the standard from our standards matching or retrieval
            # This is simplified - in reality we'd fetch the standard document
            db = next(get_db())
            try:
                from app.models.standard import Standard
                standard = db.query(Standard).filter(
                    Standard.standard_number == standard_number
                ).first()
                is_accessible = standard is not None

                if is_accessible and standard:
                    # Check if the standard's content supports the claim
                    # We'd need to get the standard's clauses/text
                    # For now, we'll do a simple check based on title/scope
                    support_result = self._check_standard_supports_claim(
                        standard.title, standard.scope or "", claim_text
                    )
                    supports_claim = support_result['supports']
                    confidence = support_result['confidence']
                    details = {
                        'standard_title': standard.title,
                        'standard_scope': standard.scope,
                        'support_details': support_result.get('details', {})
                    }
                else:
                    supports_claim = False
                    confidence = 0.2  # Low confidence if we can't find the standard
                    details = {'reason': f'Standard {standard_number} not found in database'}

            finally:
                db.close()

            return {
                'is_accessible': is_accessible,
                'supports_claim': supports_claim,
                'confidence': confidence,
                'details': details
            }

        except Exception as e:
            logger.warning(f"Error verifying standard citation: {str(e)}")
            return {
                'is_accessible': False,
                'supports_claim': False,
                'confidence': 0.0,
                'details': {'error': str(e)}
            }

    def _check_standard_supports_claim(
        self,
        title: str,
        scope: str,
        claim_text: str
    ) -> Dict[str, Any]:
        """Check if a standard's title/scope supports a claim"""
        try:
            standard_text = f"{title} {scope}".lower()
            claim_lower = claim_text.lower()

            # Check for keyword overlap
            claim_words = set(re.findall(r'\b\w+\b', claim_lower))
            standard_words = set(re.findall(r'\b\w+\b', standard_text))

            if not claim_words:
                return {'supports': False, 'confidence': 0.0, 'details': {}}

            overlap = claim_words.intersection(standard_words)
            overlap_ratio = len(overlap) / len(claim_words) if claim_words else 0

            confidence = overlap_ratio * 0.8  # Standards are authoritative sources
            supports = confidence > 0.4

            details = {
                'claim_words_found': len(overlap),
                'total_claim_words': len(claim_words),
                'overlap_ratio': overlap_ratio,
                'standard_text_checked': standard_text[:100] + "..." if len(standard_text) > 100 else standard_text
            }

            return {
                'supports': supports,
                'confidence': confidence,
                'details': details
            }

        except Exception as e:
            return {'supports': False, 'confidence': 0.0, 'details': {'error': str(e)}}

    async def _verify_doi_citation(
        self,
        reference: Dict[str, Any],
        claim_text: str
    ) -> Dict[str, Any]:
        """Verify a DOI citation (simplified)"""
        # For now, we'll treat DOI as accessible if it looks valid
        doi = reference.get('doi')
        if doi and doi.startswith('10.'):
            # In reality, we'd resolve the DOI and check the content
            # For now, return moderate confidence
            return {
                'is_accessible': True,
                'supports_claim': False,  # We can't easily check without fetching
                'confidence': 0.3,
                'details': {
                    'doi': doi,
                    'note': 'DOI format valid but content not checked'
                }
            }
        else:
            return {
                'is_accessible': False,
                'supports_claim': False,
                'confidence': 0.0,
                'details': {'reason': 'Invalid DOI format'}
            }

    # ------------------------------------------------------------------
    # Claim and citation extraction
    # ------------------------------------------------------------------

    def _extract_claims_and_citations(self, text: str) -> List[Dict[str, Any]]:
        """Extract claims and their associated citations from text"""
        try:
            # Split text into sentences
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]

            results = []

            for i, sentence in enumerate(sentences):
                # Find citations in this sentence
                citations = self._extract_citations_from_text(sentence)

                # If we found citations, treat the sentence as a claim
                if citations:
                    # Clean up the sentence to get the claim text (remove citations)
                    claim_text = self._remove_citations_from_text(sentence)

                    if claim_text.strip():
                        claim = Claim(
                            claim_id=f"claim_{len(results)}",
                            text=claim_text.strip(),
                            citations=[cite['text'] for cite in citations],
                            context=self._get_sentence_context(sentences, i)
                        )

                        results.append({
                            'claim': claim,
                            'citations': [cite['text'] for cite in citations]
                        })

            return results

        except Exception as e:
            logger.error(f"Error extracting claims and citations: {str(e)}")
            return []

    def _extract_product_related_claims(
        self,
        text: str,
        product_understanding: ProductUnderstanding
    ) -> List[Dict[str, Any]]:
        """Extract claims that are related to a specific product"""
        try:
            # First extract all claims
            all_claims = self._extract_claims_and_citations(text)

            # Filter for claims that mention the product or are in context of the product
            product_name_lower = product_understanding.product_name.lower()
            category_lower = product_understanding.category.lower() if product_understanding.category else ""

            filtered_claims = []

            for claim_data in all_claims:
                claim_text = claim_data['claim'].text.lower()
                context = claim_data['claim'].context.lower()

                # Check if claim mentions the product name or category
                if (product_name_lower in claim_text or
                    (category_lower and category_lower in claim_text) or
                    product_name_lower in context or
                    (category_lower and category_lower in context)):
                    filtered_claims.append(claim_data)

            return filtered_claims

        except Exception as e:
            logger.error(f"Error extracting product-related claims: {str(e)}")
            return []

    def _extract_citations_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract citations from text using patterns"""
        citations = []

        for pattern_info in self.citation_patterns:
            if len(pattern_info) == 3:
                pattern, citation_type, flags = pattern_info
            else:
                pattern, citation_type = pattern_info
                flags = 0

            matches = re.finditer(pattern, text, flags)
            for match in matches:
                citation_text = match.group(0)
                reference = self._parse_citation_reference(citation_text, citation_type)

                citations.append({
                    'text': citation_text,
                    'type': citation_type,
                    'reference': reference,
                    'confidence': 0.8  # Base confidence for pattern match
                })

        # Deduplicate citations (same text)
        seen = set()
        unique_citations = []
        for cite in citations:
            if cite['text'] not in seen:
                seen.add(cite['text'])
                unique_citations.append(cite)

        return unique_citations

    def _parse_citation(self, citation_text: str) -> Dict[str, Any]:
        """Parse a citation text into structured info"""
        # Try each pattern to see what type of citation this is
        for pattern_info in self.citation_patterns:
            if len(pattern_info) == 3:
                pattern, citation_type, flags = pattern_info
            else:
                pattern, citation_type = pattern_info
                flags = 0

            match = re.search(pattern, citation_text, flags)
            if match:
                reference = self._parse_citation_reference(citation_text, citation_type)
                return {
                    'text': citation_text,
                    'type': citation_type,
                    'reference': reference,
                    'confidence': 0.8
                }

        # If no pattern matches, treat as generic text citation
        return {
            'text': citation_text,
            'type': 'text',
            'reference': {'raw_text': citation_text},
            'confidence': 0.3
        }

    def _parse_citation_reference(
        self,
        citation_text: str,
        citation_type: str
    ) -> Dict[str, Any]:
        """Parse reference details from citation text"""
        reference = {'raw_text': citation_text}

        if citation_type == 'standard':
            # Extract standard number and year
            match = re.search(r'IS\s+(\d{2,5})\s*:?\s*(\d{4})', citation_text)
            if match:
                reference['standard_number'] = f"IS {match.group(1)}:{match.group(2)}"
                reference['part'] = match.group(1)
                reference['year'] = match.group(2)

        elif citation_type == 'web':
            # Extract URL
            match = re.search(r'https?://[^\s\)]+', citation_text)
            if match:
                reference['url'] = match.group(0)
                # Try to extract domain
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(match.group(0)).netloc
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    reference['domain'] = domain
                except:
                    pass

        elif citation_type == 'doi':
            # Extract DOI
            match = re.search(r'doi:\s*10\.\d{4,9}/[-._;()/:A-Z0-9]+', citation_text, re.IGNORECASE)
            if match:
                reference['doi'] = match.group(0).split(':')[1].strip()

        elif citation_type == 'reference':
            # Extract numeric references
            numbers = re.findall(r'\d+', citation_text)
            if numbers:
                reference['numbers'] = [int(n) for n in numbers]

        elif citation_type == 'author_year':
            # Extract author and year
            match = re.search(r'\(\s*([A-Z][a-z]+(?:\s+et\s+al\.)?),\s*(\d{4})\s*\)', citation_text)
            if match:
                reference['author'] = match.group(1)
                reference['year'] = match.group(2)

        return reference

    def _remove_citations_from_text(self, text: str) -> str:
        """Remove citation markers from text to get the claim"""
        cleaned = text
        # Remove web URLs
        cleaned = re.sub(r'https?://[^\s\)]+', '', cleaned)
        # Remove standard citations
        cleaned = re.sub(r'IS\s+\d{2,5}\s*:?\s*\d{4}', '', cleaned)
        # Remove DOI
        cleaned = re.sub(r'doi:\s*10\.\d{4,9}/[-._;()/:A-Z0-9]+', '', cleaned, flags=re.IGNORECASE)
        # Remove reference numbers
        cleaned = re.sub(r'\[\s*\d+(?:\s*,\s*\d+)*\s*\]', '', cleaned)
        # Remove author-year
        cleaned = re.sub(r'\(\s*[A-Z][a-z]+(?:\s+et\s+al\.)?,\s*\d{4}\s*\)', '', cleaned)
        # Clean up extra spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def _get_sentence_context(self, sentences: List[str], index: int) -> str:
        """Get context around a sentence (previous and next)"""
        context_parts = []
        if index > 0:
            context_parts.append(sentences[index-1])
        context_parts.append(sentences[index])
        if index < len(sentences) - 1:
            context_parts.append(sentences[index+1])
        return ' '.join(context_parts)

    def _generate_recommendations(
        self,
        claim: Claim,
        verification_details: List[Dict[str, Any]],
        is_verified: bool,
        confidence: float
    ) -> List[str]:
        """Generate recommendations based on verification results"""
        recommendations = []

        if not is_verified or confidence < 0.5:
            recommendations.append("Consider providing stronger evidence or more reliable sources for this claim")

        # Check for inaccessible citations
        inaccessible = [d for d in verification_details if not d['is_accessible']]
        if inaccessible:
            recommendations.append(f"{len(inaccessible)} citation(s) could not be accessed - verify URLs or document availability")

        # Check for citations that don't support the claim
        not_supporting = [d for d in verification_details if not d['supports_claim']]
        if not_supporting:
            recommendations.append(f"{len(not_supporting)} citation(s) do not appear to support the claim - review relevance")

        # Check for low confidence citations
        low_confidence = [d for d in verification_details if d['confidence'] < 0.4]
        if low_confidence:
            recommendations.append(f"{len(low_confidence)} citation(s) have low confidence - consider obtaining clearer sources")

        if not recommendations and is_verified and confidence > 0.7:
            recommendations.append("Claim is well-supported - no action needed")

        return recommendations[:4]  # Limit recommendations


# Global agent instance
_citation_verification_agent: Optional[CitationVerificationAgent] = None


def get_citation_verification_agent() -> CitationVerificationAgent:
    """Get or create the citation verification agent instance"""
    global _citation_verification_agent
    if _citation_verification_agent is None:
        _citation_verification_agent = CitationVerificationAgent()
    return _citation_verification_agent