from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import re
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.standard import Standard, QCORecord

router = APIRouter(prefix="/consumer", tags=["Consumer Protection & Hallmarking"])

# Purity table under IS 1417 (Gold) and IS 2112 (Silver)
GOLD_PURITY_GRADES = {
    "999": {"karat": "24K", "fineness": "999", "pure_percentage": 99.9, "desc": "Fine Gold (99.9% pure)"},
    "958": {"karat": "23K", "fineness": "958", "pure_percentage": 95.8, "desc": "Standard Gold (95.8% pure)"},
    "916": {"karat": "22K", "fineness": "916", "pure_percentage": 91.6, "desc": "Most common for jewelry (91.6% pure)"},
    "833": {"karat": "20K", "fineness": "833", "pure_percentage": 83.3, "desc": "Vintage / Specialized jewelry (83.3% pure)"},
    "750": {"karat": "18K", "fineness": "750", "pure_percentage": 75.0, "desc": "Diamond / Studded jewelry (75.0% pure)"},
    "585": {"karat": "14K", "fineness": "585", "pure_percentage": 58.5, "desc": "Modern lightweight jewelry (58.5% pure)"},
    "375": {"karat": "9K", "fineness": "375", "pure_percentage": 37.5, "desc": "Budget gold jewelry (37.5% pure)"},
}

SILVER_PURITY_GRADES = {
    "9999": {"grade": "Fine Silver", "fineness": "999.9", "pure_percentage": 99.99},
    "999": {"grade": "Fine Silver", "fineness": "999.0", "pure_percentage": 99.9},
    "990": {"grade": "Silver 990", "fineness": "990.0", "pure_percentage": 99.0},
    "925": {"grade": "Sterling Silver", "fineness": "925.0", "pure_percentage": 92.5},
    "900": {"grade": "Coin Silver", "fineness": "900.0", "pure_percentage": 90.0},
    "800": {"grade": "Standard Silver", "fineness": "800.0", "pure_percentage": 80.0},
}

class HUIDVerifyRequest(BaseModel):
    huid: str = Field(..., description="6-character alphanumeric Hallmark Unique Identification code", example="AB12CD")
    metal_type: Optional[str] = Field("gold", description="gold or silver")
    declared_purity: Optional[str] = Field(None, description="Declared purity e.g. 22K, 916, 18K")

class CMLVerifyRequest(BaseModel):
    cml_number: str = Field(..., description="Certification Marks License Number (e.g. CM/L-1234567 or 1234567)")
    standard_number: Optional[str] = Field(None, description="Indian Standard e.g. IS 17802 or IS 694")

class GrievanceDraftRequest(BaseModel):
    consumer_name: str = Field(..., description="Full name of complainant")
    consumer_phone: str = Field(..., description="Phone number")
    consumer_email: Optional[str] = Field(None, description="Email address")
    complaint_category: str = Field(
        ...,
        description="fake_isi_mark | hallmarking_fraud | substandard_quality | qco_violation | overcharging"
    )
    product_name: str = Field(..., description="Name / description of product or jewelry")
    standard_number: Optional[str] = Field(None, description="Relevant IS number if known (e.g., IS 1417, IS 694)")
    seller_name: str = Field(..., description="Name of seller / jeweler / retailer")
    seller_location: str = Field(..., description="City and state of purchase")
    invoice_number: Optional[str] = Field(None, description="Tax invoice / bill number")
    invoice_date: Optional[str] = Field(None, description="Purchase date (YYYY-MM-DD)")
    incident_description: str = Field(..., description="Detailed explanation of the issue observed")

@router.post("/verify-huid", summary="Verify Gold & Silver HUID (Hallmark Unique Identification)")
async def verify_huid(payload: HUIDVerifyRequest):
    huid_clean = payload.huid.strip().upper()

    # HUID is strictly 6 alphanumeric characters (letters and numbers)
    is_valid_syntax = bool(re.match(r"^[A-Z0-9]{6}$", huid_clean))

    if not is_valid_syntax:
        return {
            "success": False,
            "huid": huid_clean,
            "is_valid_format": False,
            "error_message": "Invalid HUID format. An authentic BIS HUID must contain exactly 6 alphanumeric characters (e.g., 'AB12CD').",
            "required_format": "6-character alphanumeric (A-Z, 0-9)"
        }

    # Match purity details if supplied
    purity_info = None
    if payload.declared_purity:
        purity_key = payload.declared_purity.upper().replace("K", "").strip()
        for k, v in GOLD_PURITY_GRADES.items():
            if k == purity_key or v["karat"] == payload.declared_purity.upper():
                purity_info = v
                break

    return {
        "success": True,
        "huid": huid_clean,
        "is_valid_format": True,
        "metal_type": payload.metal_type,
        "standard_reference": "IS 1417:2016 (Gold & Gold Alloys)" if payload.metal_type == "gold" else "IS 2112:2014 (Silver)",
        "hallmarking_signs": [
            {
                "name": "BIS Standard Mark",
                "description": "Triangle BIS logo indicating certified standard conformance",
                "is_mandatory": True
            },
            {
                "name": "Purity & Fineness Grade",
                "description": "Indicates karat and pure gold per thousand (e.g. 22K916, 18K750, 14K585)",
                "is_mandatory": True
            },
            {
                "name": "AHC Identification Mark",
                "description": "Logo or code of the BIS-recognized Assaying & Hallmarking Centre",
                "is_mandatory": True
            },
            {
                "name": "6-Digit Alphanumeric HUID",
                "description": f"Unique laser-engraved piece identifier ({huid_clean}) providing complete traceability to the hallmarking batch",
                "is_mandatory": True
            }
        ],
        "purity_table": GOLD_PURITY_GRADES if payload.metal_type == "gold" else SILVER_PURITY_GRADES,
        "matched_declared_purity": purity_info,
        "verification_routes": {
            "bis_care_app_deep_link": f"biscare://huid/verify?code={huid_clean}",
            "bis_manakonline_url": "https://www.manakonline.in/MANAK/huidVerification",
            "verification_instruction": "Open BIS Care App > Click 'Verify HUID' > Enter this 6-character code or scan the jewelry barcode to view Jeweler Name, Registration No., AHC, and Hallmarking Date."
        },
        "consumer_advisory": (
            "Under the BIS (Hallmarking) Regulations, selling un-hallmarked gold jewelry is illegal "
            "in all notified mandatory hallmarking districts across India. Always demand a cash memo with the HUID explicitly printed."
        )
    }

@router.post("/verify-cml", summary="Verify ISI Mark & Certification Marks License (CML) Number")
async def verify_cml(payload: CMLVerifyRequest, db: Session = Depends(get_db)):
    raw = payload.cml_number.strip().upper()
    digits_match = re.search(r"(\d{7,8})", raw)

    if not digits_match:
        return {
            "success": False,
            "cml_number": raw,
            "is_valid_format": False,
            "error_message": "Invalid CML Number format. A genuine BIS License number contains 7 or 8 digits (e.g., 'CM/L-1234567').",
            "format_guideline": "CM/L-XXXXXXX (7 or 8 numeric digits)"
        }

    cml_digits = digits_match.group(1)
    formatted_cml = f"CM/L-{cml_digits}"

    # Search for associated standard in DB if standard_number was provided
    matched_std = None
    if payload.standard_number:
        clean_std = payload.standard_number.replace(" ", "").upper()
        matched_std = db.query(Standard).filter(
            Standard.standard_number.ilike(f"%{clean_std}%")
        ).first()

    return {
        "success": True,
        "cml_number": formatted_cml,
        "raw_input": raw,
        "is_valid_format": True,
        "license_digits": cml_digits,
        "verification_portal_url": f"https://www.services.bis.gov.in/php/BIS_2.0/bisconnect/knowyourisi/",
        "bis_care_app_route": "Open BIS Care App > 'Verify License Details' > Enter 7 or 8 digit CM/L number",
        "standard_info": {
            "standard_number": matched_std.standard_number if matched_std else payload.standard_number,
            "title": matched_std.title if matched_std else "Indian Standard Conformance",
            "is_qco_mandatory": matched_std.is_qco_mandatory if matched_std else True
        } if (matched_std or payload.standard_number) else None,
        "authenticity_indicators": [
            "Must display the exact Indian Standard number above the ISI mark (e.g., IS 17802).",
            f"Must display the 7/8-digit CM/L number below the ISI mark ({formatted_cml}).",
            "Packaging must clearly show manufacturer name, factory address, and manufacturing batch/date."
        ],
        "warning_flag": (
            "If any product claiming ISI certification displays an incomplete license number or lacks "
            "the corresponding IS number above the mark, it constitutes a non-cognizable offence under Section 29 of the BIS Act, 2016."
        )
    }

@router.post("/grievance/draft", summary="Generate Structured Legal Grievance for BIS / Consumer Forum")
async def draft_grievance(payload: GrievanceDraftRequest):
    timestamp_str = datetime.now().strftime("%d-%B-%Y")
    
    category_labels = {
        "fake_isi_mark": "Counterfeit / Unauthorized Use of ISI Mark (Section 14/15 BIS Act 2016)",
        "hallmarking_fraud": "Non-Hallmarked Jewelry / Fake HUID / Purity Deficit (IS 1417 / IS 2112)",
        "substandard_quality": "Failure to Meet Indian Standard Quality & Safety Norms",
        "qco_violation": "Manufacture or Sale of Product in Violation of Mandatory Quality Control Order",
        "overcharging": "Overcharging on Hallmarking Fees or Misrepresentation of Conformance"
    }

    category_title = category_labels.get(payload.complaint_category, "Violation of Bureau of Indian Standards Norms")

    # Construct formal complaint letter
    formal_letter = f"""FORMAL COMPLAINT NOTICE UNDER THE BUREAU OF INDIAN STANDARDS ACT, 2016
Date: {timestamp_str}

TO:
The Grievance Redressal Officer / Chief Vigilance Officer
Bureau of Indian Standards (BIS), Manak Bhavan, 9 Bahadur Shah Zafar Marg, New Delhi 110002
Copy to: National Consumer Helpline (NCH), Ministry of Consumer Affairs, Food & Public Distribution

FROM:
Complainant Name: {payload.consumer_name}
Contact Phone: {payload.consumer_phone}
Email: {payload.consumer_email or 'N/A'}
Location: {payload.seller_location}

SUBJECT: Formal complaint regarding {category_title} by {payload.seller_name}

RESPECTED AUTHORITY,

I am writing to lodge an official complaint against the undermentioned seller/manufacturer for serious non-compliance with the Bureau of Indian Standards Act, 2016 and applicable Consumer Protection rules.

1. DETAILS OF OPPOSING PARTY:
   - Name of Seller/Jeweler/Manufacturer: {payload.seller_name}
   - Address / Location: {payload.seller_location}

2. PRODUCT & PURCHASE PARTICULARS:
   - Product / Article Description: {payload.product_name}
   - Indian Standard Applicable: {payload.standard_number or 'Applicable BIS Standard'}
   - Invoice / Cash Memo Number: {payload.invoice_number or 'Provided upon inspection'}
   - Date of Purchase: {payload.invoice_date or timestamp_str}

3. GROUNDS OF COMPLAINT & FACTUAL NARRATIVE:
{payload.incident_description}

4. STATUTORY VIOLATIONS:
   - Section 14 & Section 15 of the BIS Act, 2016 prohibits the unauthorized use of the Standard Mark and false representation of standard conformity.
   - Section 29 prescribes stringent criminal liability, including imprisonment up to two years and substantial financial penalties not less than two lakh rupees for counterfeit standard marking.
   - Section 2(47) of the Consumer Protection Act, 2019 classifies such practices as Unfair Trade Practices.

5. RELIEF SOUGHT:
   a. Initiation of an immediate regulatory inspection/enforcement raid on the seller's premises.
   b. Seizure and laboratory testing of counterfeit or sub-standard stock.
   c. Full refund/compensation for the defective and substandard product.
   d. Strict penal action under Section 29 of the BIS Act, 2016.

I declare that the information stated above is true to the best of my knowledge and belief. I have preserved the purchase invoice and photographic evidence for physical inspection.

Yours sincerely,
{payload.consumer_name}
Contact: {payload.consumer_phone}
"""

    return {
        "success": True,
        "complaint_id": f"GRV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "subject": f"Formal Complaint: {category_title} - {payload.seller_name}",
        "category": payload.complaint_category,
        "formal_complaint_letter": formal_letter,
        "submission_channels": [
            {
                "channel_name": "BIS e-Grievance Portal",
                "portal_url": "https://www.services.bis.gov.in/php/BIS_2.0/bisconnect/grievance/",
                "method": "Online Submission",
                "note": "Attach the generated letter above along with invoice and product photos."
            },
            {
                "channel_name": "National Consumer Helpline (NCH)",
                "portal_url": "https://consumerhelpline.gov.in/",
                "phone_helpline": "1915 (Toll Free) or SMS to 8800001915",
                "note": "Register grievance online for fast-track dispute redressal with merchant."
            },
            {
                "channel_name": "BIS Care Mobile App",
                "portal_url": "https://play.google.com/store/apps/details?id=com.bis.mobileapp",
                "method": "App-based Complaints",
                "note": "Click 'Complaints' tab > Select 'Quality Issue' or 'Misuse of ISI Mark' > Upload photo."
            }
        ],
        "evidence_checklist": [
            "Original or copy of Tax Invoice / Cash Memo clearly showing seller GSTIN and date",
            "Clear, high-resolution photographs of the product, packaging, and the alleged fake mark/HUID",
            "Any laboratory test report or purity discrepancy slip from a recognized AHC (for jewelry)",
            "Copy of written correspondence or refund rejection from the merchant (if any)"
        ]
    }
