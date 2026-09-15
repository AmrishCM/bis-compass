from fastapi import APIRouter, Depends, Query
from typing import Optional, List
import json
import logging
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.standard import LaboratoryRecord
from app.agents.laboratory_agent import LaboratoryAgent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/laboratories", tags=["BIS-Recognized Laboratories"])

@router.get("", summary="Search BIS-Recognized & NABL Testing Laboratories")
def list_laboratories(
    location: Optional[str] = Query(None, description="Filter by city, state, or region (e.g., Delhi, Bangalore)"),
    scope: Optional[str] = Query(None, description="Filter by accredited scope or standard keyword"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(LaboratoryRecord)

    if location:
        query = query.filter(
            (LaboratoryRecord.location.ilike(f"%{location}%")) |
            (LaboratoryRecord.address.ilike(f"%{location}%"))
        )

    if scope:
        query = query.filter(
            (LaboratoryRecord.accredited_scopes.ilike(f"%{scope}%")) |
            (LaboratoryRecord.testing_facilities.ilike(f"%{scope}%"))
        )

    labs = query.limit(limit).all()

    # Fallback to LaboratoryAgent KNOWN_LABORATORIES if database empty
    results = []
    if labs:
        for l in labs:
            scopes = []
            try:
                scopes = json.loads(l.accredited_scopes) if l.accredited_scopes else []
            except Exception:
                scopes = [l.accredited_scopes] if l.accredited_scopes else []

            facilities = []
            try:
                facilities = json.loads(l.testing_facilities) if l.testing_facilities else []
            except Exception:
                facilities = [l.testing_facilities] if l.testing_facilities else []

            results.append({
                "id": l.id,
                "lab_name": l.lab_name,
                "address": l.address,
                "location": l.location,
                "contact_person": l.contact_person,
                "phone": l.phone,
                "email": l.email,
                "website": l.website,
                "accreditation_body": l.accreditation_body,
                "accreditation_number": l.accreditation_number,
                "is_bis_recognized": l.is_bis_recognized,
                "bis_recognition_number": l.bis_recognition_number,
                "accredited_scopes": scopes,
                "testing_facilities": facilities,
                "geographical_coverage": l.geographical_coverage,
                "sample_collection_facility": l.sample_collection_facility
            })
    else:
        # Reference test fixture fallback when database cache has not yet indexed live laboratories
        for idx, k in enumerate(LaboratoryAgent.TEST_FIXTURE_LABORATORIES):
            results.append({
                "id": idx + 1,
                "lab_name": k["lab_name"],
                "address": k["address"],
                "location": k["location"],
                "contact_person": "In-charge",
                "phone": k.get("phone"),
                "email": k.get("email"),
                "website": k.get("website"),
                "accreditation_body": k.get("accreditation_body", "NABL"),
                "accreditation_number": k.get("accreditation_number"),
                "is_bis_recognized": True,
                "bis_recognition_number": k.get("bis_recognition_number"),
                "accredited_scopes": k.get("accredited_scopes", []),
                "testing_facilities": k.get("testing_facilities", []),
                "geographical_coverage": k.get("geographical_coverage", "All India"),
                "sample_collection_facility": True,
                "is_test_fixture": True,
                "source": [{
                    "source_type": "TEST_FIXTURE",
                    "verified": False,
                    "note": "Reference test fixture; verify with live portal."
                }]
            })

    return {
        "success": True,
        "total": len(results),
        "laboratories": results
    }
