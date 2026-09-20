from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import logging
import re
import asyncio
import json
from app.services.retrieval.hybrid_retriever import get_hybrid_retriever
from app.services.products.product_understanding import ProductUnderstanding
from app.db.session import get_db

logger = logging.getLogger(__name__)


@dataclass
class LabSearchCriteria:
    """Criteria for searching BIS-recognized laboratories"""
    standard_number: Optional[str] = None
    test_types: Optional[List[str]] = None
    location: Optional[str] = None  # City, state or region (e.g., "Delhi", "Northern India")
    accreditation_body: Optional[str] = None  # e.g., "NABL"
    product_category: Optional[str] = None
    require_sample_collection: bool = False
    max_results: int = 10
    user_lat: Optional[float] = None
    user_lon: Optional[float] = None


@dataclass
class LabTestScope:
    """A test that a laboratory is accredited to perform"""
    test_type: str
    test_standard: Optional[str] = None  # e.g., "IS 302-2-15"
    match_confidence: float = 0.0  # How well the lab's scope matches the requested test
    remarks: Optional[str] = None


@dataclass
class Laboratory:
    """A BIS-recognized laboratory"""
    lab_id: int
    lab_name: str
    address: str
    location: str  # City/region for geo-filtering
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    accreditation_body: str = "NABL"
    accreditation_number: Optional[str] = None
    is_bis_recognized: bool = True
    bis_recognition_number: Optional[str] = None
    accredited_scopes: List[str] = field(default_factory=list)
    test_capabilities: List[LabTestScope] = field(default_factory=list)
    testing_facilities: List[str] = field(default_factory=list)
    geographical_coverage: str = "All India"
    sample_collection_facility: bool = False
    report_turnaround_time: Optional[str] = None
    match_score: float = 0.0  # Relevance against search criteria
    match_reasons: List[str] = field(default_factory=list)
    source: List[Dict[str, Any]] = field(default_factory=list)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_km: Optional[float] = None
    distance_str: str = "Distance not verified"
    empty_state_guidance: Optional[str] = None


def calculate_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on the Earth (Haversine formula in km)."""
    import math
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)


class LaboratoryAgent:
    """Agent responsible for finding BIS-recognized laboratories that can test a product
    against a given standard, with filtering by location, accreditation, and test scope."""

    @staticmethod
    def calculate_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        return calculate_haversine(lat1, lon1, lat2, lon2)

    # TEST FIXTURE ONLY: Curated reference laboratory directory for unit tests and offline fallback.
    # NOT used as primary operational data in open-world live research mode.
    TEST_FIXTURE_LABORATORIES: List[Dict[str, Any]] = [
        {
            "lab_name": "National Test House (NTH) - Ghaziabad",
            "address": "Kamla Nehru Nagar, Ghaziabad, Uttar Pradesh 201002",
            "location": "Ghaziabad, Northern India",
            "phone": "0120-2788252",
            "email": "nthgz@nth.gov.in",
            "accreditation_body": "NABL",
            "accreditation_number": "TC-1345",
            "bis_recognition_number": "NTH/2023/014",
            "accredited_scopes": ["Electrical Testing", "Electronics Testing",
                                  "Mechanical Testing", "Building Materials"],
            "testing_facilities": ["Electrical Safety Lab", "HV Test Lab",
                                   "Environmental Test Lab", "Mechanical Test Lab"],
            "geographical_coverage": "All India",
            "sample_collection_facility": True,
            "report_turnaround_time": "10-15 days",
        },
        {
            "lab_name": "Central Power Research Institute (CPRI) - Bengaluru",
            "address": "Prof. Sir C V Raman Road, Sadashivanagar Post, Bengaluru, Karnataka 560080",
            "location": "Bengaluru, Southern India",
            "phone": "080-23606935",
            "email": "info@cpri.in",
            "website": "https://www.cpri.in",
            "accreditation_body": "NABL",
            "accreditation_number": "TC-2044",
            "bis_recognition_number": "CPRI/2023/007",
            "accredited_scopes": ["Electrical Testing", "High Voltage Testing",
                                  "Transformer Testing", "Switchgear Testing", "Cable Testing"],
            "testing_facilities": ["Short Circuit Test Lab", "HV Laboratory",
                                   "Transformer Test Lab", "Cable Test Lab"],
            "geographical_coverage": "All India",
            "sample_collection_facility": True,
            "report_turnaround_time": "15-20 days",
        },
        {
            "lab_name": "ERDA (Electrical Research and Development Association) - Vadodara",
            "address": "ERDA Road, GIDC Makarpura, Vadodara, Gujarat 390010",
            "location": "Vadodara, Western India",
            "phone": "0265-2638041",
            "email": "erda@erda.org",
            "website": "https://www.erda.org",
            "accreditation_body": "NABL",
            "accreditation_number": "TC-3122",
            "bis_recognition_number": "ERDA/2023/011",
            "accredited_scopes": ["Electrical Testing", "Electronics Testing",
                                  "Energy Efficiency Testing", "Safety Testing"],
            "testing_facilities": ["Electrical Safety Lab", "Energy Efficiency Lab",
                                   "Photometric Lab"],
            "geographical_coverage": "All India",
            "sample_collection_facility": True,
            "report_turnaround_time": "12-18 days",
        },
        {
            "lab_name": "Sri Ram Institute for Industrial Research - Delhi",
            "address": "19 University Road, Delhi 110007",
            "location": "Delhi, Northern India",
            "phone": "011-27667906",
            "email": "info@sribidi.com",
            "accreditation_body": "NABL",
            "accreditation_number": "TC-5567",
            "accredited_scopes": ["Chemical Testing", "Food Testing",
                                  "Water Testing", "Material Testing"],
            "testing_facilities": ["Chemical Analysis Lab", "Food Testing Lab",
                                   "Environmental Lab"],
            "geographical_coverage": "All India",
            "sample_collection_facility": True,
            "report_turnaround_time": "7-14 days",
        },
        {
            "lab_name": "Indian Institute of Technology (IIT) Testing Facilities - Mumbai",
            "address": "Powai, Mumbai, Maharashtra 400076",
            "location": "Mumbai, Western India",
            "phone": "022-25722545",
            "accreditation_body": "NABL",
            "accreditation_number": "TC-8801",
            "accredited_scopes": ["Material Testing", "Mechanical Testing",
                                  "Civil Testing", "Chemical Testing"],
            "testing_facilities": ["Materials Testing Lab", "Concrete Lab", "Structures Lab"],
            "geographical_coverage": "All India",
            "sample_collection_facility": False,
            "report_turnaround_time": "14-21 days",
        },
        {
            "lab_name": "Textile Committee Laboratory - Mumbai",
            "address": "P. Balu Road, Prabhadevi, Mumbai, Maharashtra 400025",
            "location": "Mumbai, Western India",
            "phone": "022-24222201",
            "email": "tc@textilecommittee.org.in",
            "accreditation_body": "NABL",
            "accreditation_number": "TC-1102",
            "bis_recognition_number": "TC/2023/021",
            "accredited_scopes": ["Textile Testing", "Fabric Testing", "Colour Fastness Testing"],
            "testing_facilities": ["Fabric Testing Lab", "Colour Fastness Lab", "Dyeing Lab"],
            "geographical_coverage": "All India",
            "sample_collection_facility": True,
            "report_turnaround_time": "8-12 days",
        },
        {
            "lab_name": "National Metallurgical Laboratory (NML) - Jamshedpur",
            "address": "Burmamines, Jamshedpur, Jharkhand 831007",
            "location": "Jamshedpur, Eastern India",
            "phone": "0657-2345001",
            "email": "director@nmlindia.org",
            "accreditation_body": "NABL",
            "accreditation_number": "TC-4908",
            "accredited_scopes": ["Metallurgical Testing", "Material Testing",
                                  "Corrosion Testing", "Mechanical Testing"],
            "testing_facilities": ["Metallography Lab", "Corrosion Lab", "Mechanical Testing Lab"],
            "geographical_coverage": "All India",
            "sample_collection_facility": True,
            "report_turnaround_time": "12-18 days",
        },
        {
            "lab_name": "Regional Toxicology Centre Laboratory - Chennai",
            "address": "Kilpauk, Chennai, Tamil Nadu 600010",
            "location": "Chennai, Southern India",
            "phone": "044-26411071",
            "accreditation_body": "NABL",
            "accreditation_number": "TC-2301",
            "accredited_scopes": ["Toxicology Testing", "Chemical Testing", "Water Testing"],
            "testing_facilities": ["Toxicology Lab", "Chemical Analysis Lab"],
            "geographical_coverage": "Southern India",
            "sample_collection_facility": False,
            "report_turnaround_time": "10-16 days",
        },
    ]

    # Backward compatibility alias for test suites
    KNOWN_LABORATORIES = TEST_FIXTURE_LABORATORIES

    # Quick lookup for country-wide regions
    REGION_KEYWORDS = {
        "north": ["delhi", "ghaziabad", "gurgaon", "gurugram", "jaipur", "lucknow", "chandigarh"],
        "south": ["bengaluru", "bangalore", "chennai", "hyderabad", "kochi", "coimbatore"],
        "east": ["kolkata", "jamshedpur", "bhubaneswar", "patna", "guwahati"],
        "west": ["mumbai", "pune", "vadodara", "ahmedabad", "nagpur", "surat"],
        "central": ["bhopal", "indore", "raipur", "nagpur"],
    }

    CITY_COORDINATES = {
        "delhi": (28.6139, 77.2090),
        "new delhi": (28.6139, 77.2090),
        "ghaziabad": (28.6692, 77.4538),
        "gurgaon": (28.4595, 77.0266),
        "gurugram": (28.4595, 77.0266),
        "noida": (28.5355, 77.3910),
        "mumbai": (19.0760, 72.8777),
        "pune": (18.5204, 73.8567),
        "bengaluru": (12.9716, 77.5946),
        "bangalore": (12.9716, 77.5946),
        "chennai": (13.0827, 80.2707),
        "hyderabad": (17.3850, 78.4867),
        "kolkata": (22.5726, 88.3639),
        "ahmedabad": (23.0225, 72.5714),
        "jaipur": (26.9124, 75.7873),
        "lucknow": (26.8467, 80.9462),
        "jamshedpur": (22.8046, 86.2029),
        "chandigarh": (30.7333, 76.7794),
        "nagpur": (21.1458, 79.0882),
        "coimbatore": (11.0168, 76.9558),
        "surat": (21.1702, 72.8311),
        "bhopal": (23.2599, 77.4126),
    }

    @staticmethod
    def calculate_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        from math import radians, cos, sin, asin, sqrt
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * asin(sqrt(a))
        return round(c * 6371.0, 1)

    def __init__(self):
        self.hybrid_retriever_factory = get_hybrid_retriever

    def _retrieve_labs_from_db(self, criteria: LabSearchCriteria) -> List[Laboratory]:
        """Retrieve verified laboratories from local database LaboratoryRecord table"""
        labs: List[Laboratory] = []
        try:
            from app.db.session import SessionLocal
            from app.models.standard import LaboratoryRecord

            with SessionLocal() as db:
                records = db.query(LaboratoryRecord).all()
                for idx, r in enumerate(records):
                    scopes = []
                    if r.accredited_scopes:
                        try:
                            scopes = json.loads(r.accredited_scopes) if isinstance(r.accredited_scopes, str) else r.accredited_scopes
                        except Exception:
                            scopes = [s.strip() for s in r.accredited_scopes.split(",") if s.strip()]

                    facilities = []
                    if r.testing_facilities:
                        try:
                            facilities = json.loads(r.testing_facilities) if isinstance(r.testing_facilities, str) else r.testing_facilities
                        except Exception:
                            facilities = [f.strip() for f in r.testing_facilities.split(",") if f.strip()]

                    lab = Laboratory(
                        lab_id=r.id or (idx + 1),
                        lab_name=r.lab_name,
                        address=r.address,
                        location=r.location,
                        contact_person=r.contact_person,
                        phone=r.phone,
                        email=r.email,
                        website=r.website,
                        accreditation_body=r.accreditation_body or "NABL",
                        accreditation_number=r.accreditation_number,
                        is_bis_recognized=bool(r.is_bis_recognized),
                        bis_recognition_number=r.bis_recognition_number,
                        accredited_scopes=scopes,
                        testing_facilities=facilities,
                        geographical_coverage=r.geographical_coverage or "All India",
                        sample_collection_facility=bool(r.sample_collection_facility),
                        latitude=getattr(r, "latitude", None),
                        longitude=getattr(r, "longitude", None),
                        source=[{
                            "type": "BIS_LIMS",
                            "title": "BIS LIMS Recognized Laboratory Directory",
                            "url": "https://lims.bis.gov.in"
                        }]
                    )
                    labs.append(lab)
        except Exception as e:
            logger.warning(f"Error reading laboratories from database: {e}")
        return labs

    async def search_laboratories(
        self,
        criteria: LabSearchCriteria,
        product_understanding: Optional[ProductUnderstanding] = None
    ) -> List[Laboratory]:
        """
        Search for BIS-recognized laboratories matching the given criteria.

        Queries the maintained local database and curated directory first,
        supplements with live LIMS/document retrieval, then scores, geocodes,
        and ranks results by standard testing scope and geographical proximity.

        Args:
            criteria: Search criteria (standard, test types, location, etc.)
            product_understanding: Optional product context to refine test scope matching

        Returns:
            List of Laboratory objects sorted by distance ascending and match score
        """
        try:
            logger.info(
                f"Searching laboratories for standard={criteria.standard_number}, "
                f"location={criteria.location}, category={criteria.product_category}"
            )

            # Step 1: Query maintained database records first
            db_candidates = self._retrieve_labs_from_db(criteria)
            if not db_candidates:
                db_candidates = self._build_seed_candidates(criteria)

            # Step 2: Retrieve from ingested documents & live LIMS web discovery
            retrieved_candidates = await self._retrieve_labs_from_documents(criteria)
            try:
                web_candidates = await asyncio.wait_for(self._discover_labs_via_web(criteria), timeout=4.0)
            except Exception:
                web_candidates = []

            # Step 3: Merge candidates prioritizing authoritative records
            merged: Dict[str, Laboratory] = {}
            for lab in db_candidates + web_candidates + retrieved_candidates:
                key = self._normalise_name(lab.lab_name)
                existing = merged.get(key)
                if existing is None:
                    merged[key] = lab
                else:
                    self._merge_lab(existing, lab)

            candidates = list(merged.values())

            # Detect user coordinates if location/coords provided
            user_coords = None
            if criteria.user_lat is not None and criteria.user_lon is not None:
                user_coords = (criteria.user_lat, criteria.user_lon)
            elif criteria.location:
                loc_lower = criteria.location.lower().strip()
                for city, coords in self.CITY_COORDINATES.items():
                    if city in loc_lower:
                        user_coords = coords
                        break

            # Score and compute distance for each candidate
            for lab in candidates:
                self._score_lab_against_criteria(lab, criteria, product_understanding)

                # Assign lab coordinates from address / location if known
                lab_coords = None
                if lab.latitude is not None and lab.longitude is not None:
                    lab_coords = (lab.latitude, lab.longitude)
                else:
                    lab_text = f"{lab.location} {lab.address} {lab.lab_name}".lower()
                    for city, coords in self.CITY_COORDINATES.items():
                        if city in lab_text:
                            lab_coords = coords
                            lab.latitude, lab.longitude = coords
                            break

                # Compute distance strictly if both coordinates exist
                if user_coords and lab_coords:
                    dist = self.calculate_haversine(user_coords[0], user_coords[1], lab_coords[0], lab_coords[1])
                    lab.distance_km = dist
                    lab.distance_str = f"{dist} km away"
                else:
                    lab.distance_km = None
                    lab.distance_str = f"Located in {lab.location}"

            # Keep only relevant labs (standard or category or test match)
            scored = [lab for lab in candidates if lab.match_score > 0]

            # Sort: Verified nearest distance first, then match score descending
            scored.sort(key=lambda x: (
                0 if x.distance_km is not None else 1,
                x.distance_km if x.distance_km is not None else 999999,
                -x.match_score
            ))

            results = scored[:criteria.max_results]

            if not results:
                if criteria.location and user_coords is None:
                    logger.info(f"Empty lab result reason: geocoding_failed for '{criteria.location}'")
                elif candidates:
                    logger.info(f"Empty lab result reason: no_labs_in_radius for '{criteria.location}'")
                else:
                    logger.info(f"Empty lab result reason: no_directory_coverage for '{criteria.standard_number}'")

            logger.info(f"Laboratory search returned {len(results)} labs (db={len(db_candidates)}, web={len(web_candidates)}, doc={len(retrieved_candidates)})")
            return results

        except Exception as e:
            logger.error(f"Error searching laboratories: {str(e)}")
            return []

    async def find_labs_for_product(
        self,
        product_understanding: ProductUnderstanding,
        standard_id: int,
        location: Optional[str] = None,
        max_results: int = 5,
        standard_number: Optional[str] = None
    ) -> List[Laboratory]:
        """
        Convenience wrapper: find labs that can test a product against a specific standard.

        Args:
            product_understanding: Structured product information
            standard_id: ID of the standard the product must be tested against
            location: Optional location filter
            max_results: Maximum number of labs to return
            standard_number: Optional standard number (e.g. 'IS 17526:2021')

        Returns:
            List of matching Laboratory objects
        """
        try:
            # Resolve the standard number if not explicitly passed
            if not standard_number and standard_id > 0:
                db = next(get_db())
                try:
                    from app.models.standard import Standard
                    standard = db.query(Standard).filter(Standard.id == standard_id).first()
                    if standard:
                        standard_number = standard.standard_number
                finally:
                    db.close()

            criteria = LabSearchCriteria(
                standard_number=standard_number,
                product_category=product_understanding.category,
                test_types=self._infer_test_types_from_product(product_understanding),
                location=location,
                max_results=max_results
            )

            return await self.search_laboratories(criteria, product_understanding)

        except Exception as e:
            logger.error(f"Error finding labs for product: {str(e)}")
            return []

    # ------------------------------------------------------------------
    # Candidate collection
    # ------------------------------------------------------------------

    async def _retrieve_labs_from_documents(
        self,
        criteria: LabSearchCriteria
    ) -> List[Laboratory]:
        """Search ingested BIS documents for laboratory information"""
        labs: List[Laboratory] = []
        try:
            query_parts = ["BIS recognized laboratory test house accredited"]
            if criteria.standard_number:
                query_parts.append(criteria.standard_number)
            if criteria.product_category:
                query_parts.append(criteria.product_category)
            if criteria.test_types:
                query_parts.extend(criteria.test_types[:3])
            if criteria.accreditation_body:
                query_parts.append(criteria.accreditation_body)

            query = " ".join(query_parts)

            db = next(get_db())
            try:
                retriever = self.hybrid_retriever_factory(db)
                results = await retriever.hybrid_search(
                    query=query,
                    limit=10,
                    min_confidence=0.3
                )
            finally:
                db.close()

            for result in results:
                lab = self._parse_lab_from_search_result(result, criteria)
                if lab:
                    labs.append(lab)

        except Exception as e:
            logger.warning(f"Could not retrieve labs from documents: {str(e)}")

        return labs

    def _build_seed_candidates(self, criteria: LabSearchCriteria) -> List[Laboratory]:
        """Build Laboratory objects from the curated known-lab directory"""
        labs: List[Laboratory] = []
        for entry in self.KNOWN_LABORATORIES:
            labs.append(self._lab_from_directory_entry(entry, criteria))
        return labs

    async def _discover_labs_via_web(
        self,
        criteria: LabSearchCriteria
    ) -> List[Laboratory]:
        """Dynamically search authoritative official sources for BIS-recognized laboratories"""
        if not criteria.standard_number:
            return []
        labs: List[Laboratory] = []
        try:
            # First try official BIS discovery service for LIMS recognized labs
            from app.services.research.bis_discovery import get_bis_discovery_service
            bis_svc = get_bis_discovery_service()
            clean_is = criteria.standard_number.replace("IS", "").strip()
            hits = await bis_svc.search_by_is_number(clean_is)
            if hits and hits[0].get("pk_is_id"):
                pk_id = hits[0]["pk_is_id"]
                details = await bis_svc.get_standard_details(pk_id)
                official_labs = details.get("recognized_laboratories", [])
                for o_lab in official_labs:
                    # aaData typically contains lab details from BIS LIMS
                    if isinstance(o_lab, dict) and o_lab.get("lab_name"):
                        l_name = o_lab.get("lab_name")
                        labs.append(Laboratory(
                            lab_id=abs(hash(l_name)) % 100000,
                            lab_name=l_name,
                            address=o_lab.get("address") or "Accredited Testing Laboratory",
                            location=o_lab.get("city") or o_lab.get("state") or criteria.location or "India",
                            contact_person=None,
                            website=None,
                            accreditation_body="BIS Recognized / NABL",
                            accreditation_number=o_lab.get("accreditation_no"),
                            is_bis_recognized=True,
                            bis_recognition_number=o_lab.get("recognition_no"),
                            accredited_scopes=[f"Testing as per {criteria.standard_number}"],
                            testing_facilities=[f"Testing as per {criteria.standard_number}"],
                            geographical_coverage="All India",
                            sample_collection_facility=False,
                            report_turnaround_time=None,
                            match_score=95.0,
                            match_reasons=[f"Officially listed in BIS LIMS directory for {criteria.standard_number}"],
                            source=[{
                                "source_type": "OFFICIAL_BIS_LIMS",
                                "source_url": "https://services.bis.gov.in/php/BIS_2.0/bis_core/Is_labs/getlabs",
                                "domain": "services.bis.gov.in",
                                "verified": True
                            }]
                        ))

            if not labs:
                from app.services.research.search_providers import get_search_provider
                search_provider = get_search_provider()
                query = f"site:services.bis.gov.in OR site:bis.gov.in recognized testing laboratory {criteria.standard_number}"
                try:
                    hits = await asyncio.wait_for(
                        search_provider.search(
                            query=query,
                            domains=["bis.gov.in", "services.bis.gov.in"],
                            max_results=3
                        ),
                        timeout=4.0
                    )
                except Exception:
                    hits = []

                for hit in hits:
                    title = hit.title
                    combined_snippet = f"{title} {hit.snippet}".lower()
                    if any(kw in combined_snippet for kw in ["laboratory", "test house", "institute", "testing"]):
                        # Rule 8.8 & Rule I.3 Integrity Check:
                        if criteria.standard_number:
                            std_clean = criteria.standard_number.lower().replace(" ", "")
                            snippet_clean = combined_snippet.replace(" ", "")
                            base_num = std_clean.split(":")[0]
                            if std_clean not in snippet_clean and base_num not in snippet_clean:
                                continue  # Cannot claim verified scope without standard citation in authoritative result
                        lab_name = re.sub(r'(\s*[-|–].*)$', '', title).strip()
                        if len(lab_name) > 6:
                            lab = Laboratory(
                                lab_id=abs(hash(lab_name)) % 100000,
                                lab_name=lab_name,
                                address="Accredited Facility, India",
                                location=criteria.location or "India",
                                contact_person=None,
                                website=hit.url,
                                accreditation_body="BIS / NABL",
                                accreditation_number=None,
                                is_bis_recognized=True,
                                bis_recognition_number=None,
                                accredited_scopes=[f"Testing as per {criteria.standard_number}"],
                                testing_facilities=[f"Testing as per {criteria.standard_number}"],
                                geographical_coverage="All India",
                                sample_collection_facility=False,
                                report_turnaround_time=None,
                                match_score=85.0,
                                match_reasons=[f"Discovered via official BIS portal for {criteria.standard_number}"],
                                source=[{
                                    "source_type": "OFFICIAL_BIS_PORTAL",
                                    "source_url": hit.url,
                                    "domain": hit.domain,
                                    "verified": True
                                }]
                            )
                            labs.append(lab)
        except Exception as e:
            logger.debug(f"Dynamic laboratory web discovery error: {e}")
        return labs

    def _lab_from_directory_entry(
        self,
        entry: Dict[str, Any],
        criteria: LabSearchCriteria
    ) -> Laboratory:
        """Create a Laboratory object from a directory entry, with test-capability matching"""
        lab = Laboratory(
            lab_id=abs(hash(entry["lab_name"])) % 100000,
            lab_name=entry["lab_name"],
            address=entry.get("address", ""),
            location=entry.get("location", ""),
            contact_person="Laboratory Incharge",
            phone=entry.get("phone"),
            email=entry.get("email"),
            website=entry.get("website"),
            accreditation_body=entry.get("accreditation_body", "NABL"),
            accreditation_number=entry.get("accreditation_number"),
            is_bis_recognized=bool(entry.get("bis_recognition_number")),
            bis_recognition_number=entry.get("bis_recognition_number"),
            accredited_scopes=entry.get("accredited_scopes", []),
            testing_facilities=entry.get("testing_facilities", []),
            geographical_coverage=entry.get("geographical_coverage", "All India"),
            sample_collection_facility=entry.get("sample_collection_facility", False),
            report_turnaround_time=entry.get("report_turnaround_time"),
            source=[{
                "source_type": "TEST_FIXTURE",
                "verified": False,
                "note": "Reference test fixture; verify with live portal."
            }]
        )

        # Build test capabilities from accredited scopes
        for scope in lab.accredited_scopes:
            lab.test_capabilities.append(LabTestScope(test_type=scope))

        return lab

    def _parse_lab_from_search_result(
        self,
        result: Dict[str, Any],
        criteria: LabSearchCriteria
    ) -> Optional[Laboratory]:
        """Parse laboratory information from a hybrid search result"""
        try:
            text = result.get("text", "")
            heading = result.get("heading", "")
            combined = f"{heading}\n{text}"

            lab_keywords = ["laboratory", "lab", "test house", "testing facility",
                            "nabl", "recognized", "accredited"]
            if not any(k in combined.lower() for k in lab_keywords):
                return None

            # Name: prefer heading, else first sentence-ish fragment
            lab_name = heading if heading and len(heading) > 4 else combined.split(".")[0][:120]

            # Address
            address = ""
            m = re.search(r'address\s*:?\s*([^\n]+)', combined, re.IGNORECASE)
            if m:
                address = m.group(1).strip()

            # Contact details
            phone = None
            m = re.search(r'(\+91[\-\s]?\d[\d\s\-]{7,}|\b0\d{2,4}[\-\s]?\d{6,8})', combined)
            if m:
                phone = m.group(1).strip()

            email = None
            m = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', combined)
            if m:
                email = m.group(0)

            website = None
            m = re.search(r'https?://[^\s,\)]+', combined)
            if m:
                website = m.group(0)

            # Accreditation
            accreditation_body = "NABL"
            accreditation_number = None
            m = re.search(r'(NABL|ILAC|BIS)\s*(?:accredited|accreditation)?\s*(?:no\.?|number)?\s*:?\s*([A-Z0-9\-\/]+)?',
                          combined, re.IGNORECASE)
            if m:
                accreditation_body = m.group(1).upper()
                if m.group(2):
                    accreditation_number = m.group(2)

            scopes: List[LabTestScope] = []
            std_in_combined = False
            if criteria.standard_number:
                std_clean = criteria.standard_number.lower().replace(" ", "")
                base_num = std_clean.split(":")[0]
                comb_clean = combined.lower().replace(" ", "")
                std_in_combined = (std_clean in comb_clean or base_num in comb_clean)

            for scope_kw in ["electrical", "mechanical", "chemical", "textile",
                             "electronic", "food", "material", "metallurgical",
                             "high voltage", "safety"]:
                if scope_kw in combined.lower():
                    scopes.append(LabTestScope(
                        test_type=f"{scope_kw.title()} Testing",
                        test_standard=criteria.standard_number if std_in_combined else None
                    ))

            location = ""
            for kw_region, cities in self.REGION_KEYWORDS.items():
                for city in cities:
                    if city in combined.lower():
                        location = f"{city.title()}, {kw_region.title()}ern India".replace("Northestern", "Northern").replace("easterneast", "east")
                        break
                if location:
                    break

            return Laboratory(
                lab_id=result.get("clause_id") or abs(hash(lab_name)) % 100000,
                lab_name=lab_name,
                address=address or "Address not specified",
                location=location or "Unknown",
                phone=phone,
                email=email,
                website=website,
                accreditation_body=accreditation_body,
                accreditation_number=accreditation_number,
                is_bis_recognized="bis" in combined.lower() or "recognized" in combined.lower(),
                accredited_scopes=[s.test_type for s in scopes] if scopes else ["General Testing"],
                test_capabilities=scopes if scopes else [LabTestScope(test_type="General Testing")],
                geographical_coverage="All India",
                sample_collection_facility="sample" in combined.lower(),
                report_turnaround_time=None,
                source=[{
                    "type": "search_result",
                    "standard_id": result.get("standard_id"),
                    "clause_id": result.get("clause_id"),
                    "clause_number": result.get("clause_number"),
                    "text_preview": text[:100] + "..." if len(text) > 100 else text,
                    "relevance_score": result.get("combined_score", 0.0),
                    "organization": result.get("organization"),
                }]
            )

        except Exception as e:
            logger.warning(f"Error parsing lab from search result: {str(e)}")
            return None

    # ------------------------------------------------------------------
    # Scoring and matching
    # ------------------------------------------------------------------

    def _score_lab_against_criteria(
        self,
        lab: Laboratory,
        criteria: LabSearchCriteria,
        product_understanding: Optional[ProductUnderstanding] = None
    ) -> None:
        """Score a laboratory against search criteria; sets lab.match_score and match_reasons"""
        score = 0.0
        reasons: List[str] = []

        # 1. Standard match: does any capability reference the requested standard?
        if criteria.standard_number:
            std_num = criteria.standard_number.lower().replace(" ", "")
            base_num = std_num.split(":")[0]
            has_standard = any(
                (cap.test_standard and (std_num in cap.test_standard.lower().replace(" ", "") or base_num in cap.test_standard.lower().replace(" ", ""))) or
                (std_num in (cap.remarks or "").lower().replace(" ", "") or base_num in (cap.remarks or "").lower().replace(" ", ""))
                for cap in lab.test_capabilities
            ) or any(
                std_num in scope.lower().replace(" ", "") or base_num in scope.lower().replace(" ", "")
                for scope in lab.accredited_scopes
            )
            std_in_name = base_num in lab.lab_name.lower().replace(" ", "")
            if has_standard or std_in_name:
                score += 0.5
                reasons.append(f"Accredited scope references {criteria.standard_number}")
            else:
                # Standard not found in lab's scopes, but don't disqualify entirely
                # Allow other factors (location, test type, etc.) to contribute to score
                reasons.append(f"Scope does not specifically reference {criteria.standard_number}")
        else:
            score += 0.1  # No standard constraint: neutral positive

        # 2. Test type scope match
        if criteria.test_types:
            matched_types = set()
            lab_text = " ".join(
                lab.accredited_scopes + [c.test_type for c in lab.test_capabilities] +
                lab.testing_facilities
            ).lower()

            for tt in criteria.test_types:
                tt_lower = tt.lower()
                # direct match
                if tt_lower in lab_text:
                    matched_types.add(tt)
                    continue
                # keyword-based match (e.g. "Temperature Rise Test" -> "electrical")
                for scope_kw in lab_text.split(","):
                    kw = scope_kw.strip()
                    if kw and kw.split()[0] in tt_lower:
                        matched_types.add(tt)
                        break

            if matched_types:
                ratio = len(matched_types) / len(criteria.test_types)
                score += 0.25 * ratio
                reasons.append(f"Scope covers {len(matched_types)}/{len(criteria.test_types)} requested test types")
            else:
                score -= 0.1
        else:
            score += 0.1

        # 3. Product category match
        category = criteria.product_category or (
            product_understanding.category if product_understanding else None
        )
        if category:
            cat_lower = category.lower()
            lab_text = " ".join(lab.accredited_scopes).lower()
            if cat_lower in lab_text:
                score += 0.15
                reasons.append(f"Accredited for {category} testing")
            else:
                # fuzzy: category keyword overlaps scope
                for scope in lab.accredited_scopes:
                    if any(word in scope.lower() for word in cat_lower.split() if len(word) > 3):
                        score += 0.08
                        reasons.append(f"Scope partially overlaps {category}")
                        break

        # 4. Location match
        if criteria.location:
            loc_lower = criteria.location.lower()
            lab_loc_lower = lab.location.lower()
            lab_geo_lower = lab.geographical_coverage.lower()
            if loc_lower in lab_loc_lower:
                score += 0.2
                reasons.append(f"Located in/near requested location ({criteria.location})")
            elif "all india" in lab_geo_lower:
                score += 0.12
                reasons.append("Covers all India (serves requested region)")
            else:
                # region keyword overlap
                matched_region = False
                for region, cities in self.REGION_KEYWORDS.items():
                    if region in loc_lower or any(c in loc_lower for c in cities):
                        if any(c in lab_loc_lower for c in cities) or region in lab_geo_lower:
                            score += 0.1
                            reasons.append(f"Located in same region ({region.title()} India)")
                            matched_region = True
                            break
                if not matched_region:
                    score -= 0.15  # Penalize clear geographical mismatch

        # 5. Accreditation body match
        if criteria.accreditation_body:
            if criteria.accreditation_body.lower() == lab.accreditation_body.lower():
                score += 0.1
                reasons.append(f"Accredited by {criteria.accreditation_body}")
            else:
                score -= 0.2
                reasons.append(f"Not accredited by requested body ({criteria.accreditation_body})")

        # 6. BIS recognition
        if lab.is_bis_recognized:
            score += 0.1
            reasons.append("BIS-recognized laboratory")

        # 7. Sample collection requirement
        if criteria.require_sample_collection:
            if lab.sample_collection_facility:
                score += 0.08
                reasons.append("Offers sample collection facility")
            else:
                score -= 0.15
                reasons.append("No sample collection facility")

        # 8. Turnaround time (small bonus for faster labs)
        if lab.report_turnaround_time:
            m = re.search(r'(\d+)', lab.report_turnaround_time)
            if m:
                days = int(m.group(1))
                if days <= 10:
                    score += 0.05
                    reasons.append(f"Fast reporting ({lab.report_turnaround_time})")

        lab.match_score = max(min(score, 1.0), 0.0)
        lab.match_reasons = reasons

    def _infer_test_types_from_product(
        self,
        product_understanding: ProductUnderstanding
    ) -> List[str]:
        """Infer relevant test types from the product understanding"""
        inferred: List[str] = []
        category = (product_understanding.category or "").lower()

        if any(k in category for k in ["electrical", "electronic", "appliance", "switch", "cable"]):
            inferred += ["Electrical Testing", "Safety Testing"]
        if any(k in category for k in ["mechanical", "machinery", "tool", "steel", "metal"]):
            inferred += ["Mechanical Testing", "Material Testing"]
        if any(k in category for k in ["chemical", "plastic", "polymer", "paint"]):
            inferred += ["Chemical Testing"]
        if any(k in category for k in ["textile", "fabric", "cloth"]):
            inferred += ["Textile Testing"]
        if any(k in category for k in ["food", "beverage"]):
            inferred += ["Food Testing"]
        if any(k in category for k in ["cement", "concrete", "building", "construction"]):
            inferred += ["Building Materials Testing"]

        # From technical attributes (e.g. voltage implies electrical testing)
        for attr_key in (product_understanding.technical_attributes or {}).keys():
            attr_lower = str(attr_key).lower()
            if any(k in attr_lower for k in ["voltage", "current", "power", "watt"]):
                if "Electrical Testing" not in inferred:
                    inferred.append("Electrical Testing")
                if "Safety Testing" not in inferred:
                    inferred.append("Safety Testing")

        return inferred[:5]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_name(name: str) -> str:
        """Normalise a lab name for deduplication"""
        return re.sub(r'[^a-z0-9]', '', name.lower())

    def _merge_lab(self, target: Laboratory, other: Laboratory) -> None:
        """Merge information from another Laboratory into target (target wins on core identity)"""
        if other.source:
            target.source.extend(other.source)
        # Fill in missing contact details
        for attr in ("phone", "email", "website", "accreditation_number",
                     "bis_recognition_number", "report_turnaround_time"):
            if getattr(target, attr) is None and getattr(other, attr) is not None:
                setattr(target, attr, getattr(other, attr))
        # Extend scopes/capabilities without duplicates
        existing_scopes = set(s.lower() for s in target.accredited_scopes)
        for scope in other.accredited_scopes:
            if scope.lower() not in existing_scopes:
                target.accredited_scopes.append(scope)
        existing_caps = set(c.test_type.lower() for c in target.test_capabilities)
        for cap in other.test_capabilities:
            if cap.test_type.lower() not in existing_caps:
                target.test_capabilities.append(cap)
        if other.is_bis_recognized:
            target.is_bis_recognized = True
        target.sample_collection_facility = (
            target.sample_collection_facility or other.sample_collection_facility
        )


# Global agent instance
_laboratory_agent: Optional[LaboratoryAgent] = None


def get_laboratory_agent() -> LaboratoryAgent:
    """Get or create the laboratory agent instance"""
    global _laboratory_agent
    if _laboratory_agent is None:
        _laboratory_agent = LaboratoryAgent()
    return _laboratory_agent