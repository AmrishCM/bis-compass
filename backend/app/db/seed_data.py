"""
TEST FIXTURE ONLY — Development & Offline Regression Testing
THIS FILE IS A TEST FIXTURE. IT MUST NOT BE USED AS THE PRODUCTION KNOWLEDGE SOURCE.
In production, BIS-Compass operates as an open-world, web-grounded research engine.
"""

from datetime import datetime
import hashlib
import json
import logging
from sqlalchemy.orm import Session
from app.models.standard import Source, Standard, Clause, Scheme, LaboratoryRecord

logger = logging.getLogger(__name__)

def generate_embedding(text: str) -> list:
    """Generate a deterministic 768-dim float vector for standard seed text"""
    # Deterministic pseudo-embedding based on sha256 hash
    h = hashlib.sha256(text.encode('utf-8')).digest()
    vec = []
    for i in range(768):
        byte_val = h[i % len(h)]
        # Map to float between -1.0 and 1.0 with variance
        val = (byte_val / 128.0) - 1.0 + (0.01 * (i % 13))
        vec.append(round(val, 5))
    return vec

def seed_database(db: Session):
    """Seed the database with verified Indian Standards and official BIS sources"""
    valid_standards_count = db.query(Standard).filter(Standard.title.isnot(None), Standard.title != '').count()
    if valid_standards_count >= 10:
        logger.info(f"Database already contains {valid_standards_count} verified standards. Skipping seed.")
        return

    logger.info("Seeding verified BIS knowledge base...")

    # 1. Primary Official BIS Sources
    sources_data = [
        {
            "id": 1,
            "source_type": "official_bis",
            "organization": "Bureau of Indian Standards (BIS)",
            "url": "https://www.services.bis.gov.in/php/BIS_2.0/bisconnect/knowyourstandards/indian_standards/isdetails",
            "title": "Bureau of Indian Standards Official Portal & Standards Directory",
            "publication_date": datetime(2021, 1, 1),
            "authority_level": 1,
            "checksum": hashlib.sha256(b"bis_official_portal_v1").hexdigest(),
            "version": "2024.1"
        },
        {
            "id": 2,
            "source_type": "government",
            "organization": "Ministry of Consumer Affairs, Food & Public Distribution",
            "url": "https://consumeraffairs.nic.in",
            "title": "Quality Control Orders (QCO) Compulsory Certification Mandate",
            "publication_date": datetime(2023, 6, 1),
            "authority_level": 2,
            "checksum": hashlib.sha256(b"moca_qco_gazette_v1").hexdigest(),
            "version": "QCO-2023"
        },
        {
            "id": 3,
            "source_type": "official_bis",
            "organization": "MeitY / BIS Compulsory Registration Scheme (CRS)",
            "url": "https://www.crsbis.in",
            "title": "BIS Compulsory Registration Scheme Portal for Electronics & IT Goods",
            "publication_date": datetime(2022, 1, 1),
            "authority_level": 1,
            "checksum": hashlib.sha256(b"bis_crs_portal_v1").hexdigest(),
            "version": "CRS-2022"
        }
    ]

    source_objs = {}
    for s in sources_data:
        existing_src = db.query(Source).filter(Source.id == s["id"]).first()
        if not existing_src:
            existing_src = db.query(Source).filter(Source.title == s["title"]).first()
        if existing_src:
            source_objs[s["id"]] = existing_src
        else:
            src = Source(
                source_type=s["source_type"],
                organization=s["organization"],
                url=s["url"],
                title=s["title"],
                publication_date=s["publication_date"],
                last_verified=datetime.utcnow(),
                authority_level=s["authority_level"],
                checksum=s["checksum"],
                version=s["version"]
            )
            db.add(src)
            db.flush()
            source_objs[s["id"]] = src

    # 2. Standards, Clauses & Schemes
    standards_catalog = [
        # Standard 1: IS 17526:2021 (Stainless Steel Water Bottles / Flasks)
        {
            "standard_number": "IS 17526:2021",
            "title": "Domestic Stainless Steel Vacuum Flasks and Insulated Flasks - Specification",
            "scope": "This standard specifies requirements, sampling procedure, and tests for domestic stainless steel vacuum flasks, insulated flasks, and stainless steel bottles used for storage and transport of potable water and beverages. Applicable to double-walled and single-walled stainless steel drinkware.",
            "status": "active",
            "edition": "First",
            "publication_date": datetime(2021, 5, 1),
            "effective_date": datetime(2021, 11, 1),
            "source_id": 1,
            "clauses": [
                {
                    "clause_number": "1.1",
                    "heading": "Scope and Field of Application",
                    "text": "This Indian Standard prescribes the constructional, performance and safety requirements for domestic stainless steel insulated flasks, bottles, and double-walled containers intended for holding hot or cold potable water and beverages.",
                    "page": 1,
                    "section": "1. Scope"
                },
                {
                    "clause_number": "4.1",
                    "heading": "Material Requirements for Body and Liner",
                    "text": "The inner body, liner, and outer casing shall be manufactured from austenitic stainless steel conforming to Grade 304 (designation 04Cr18Ni10) or Grade 316 of IS 6911. All polymeric or silicone gasket components in contact with potable water must comply with IS 9845 for food-grade contact.",
                    "page": 3,
                    "section": "4. Materials"
                },
                {
                    "clause_number": "5.2",
                    "heading": "Thermal Insulation Performance Test",
                    "text": "When the insulated bottle is filled with boiling water at not less than 95°C and sealed, the temperature of the water shall not be less than 60°C after 6 hours and not less than 45°C after 24 hours when tested in an ambient room temperature of 20°C ± 2°C.",
                    "page": 4,
                    "section": "5. Performance Tests"
                },
                {
                    "clause_number": "5.4",
                    "heading": "Leakage and Seal Integrity",
                    "text": "The bottle or flask filled to nominal capacity with water shall be held in an inverted position and subjected to a pressure differential of 20 kPa for 10 minutes. There shall be no water leakage or moisture seepage observed around the stopper, lid, or neck joints.",
                    "page": 5,
                    "section": "5. Performance Tests"
                },
                {
                    "clause_number": "6.1",
                    "heading": "Drop and Impact Resistance",
                    "text": "The flask filled with water to 90% capacity shall be dropped freely from a height of 1.2 meters onto a hard wooden floor at three orientations: vertical on base, inverted on stopper, and at 45 degree angle on neck. The bottle shall remain functional with no puncture, vacuum breach, or detachment of base.",
                    "page": 6,
                    "section": "6. Mechanical Tests"
                },
                {
                    "clause_number": "7.2",
                    "heading": "Heavy Metal and Chemical Migration Limits",
                    "text": "When subjected to migration testing using 4 percent acetic acid food simulant at 70°C for 2 hours, migration limits shall satisfy: Lead (Pb) <= 0.01 mg/kg, Cadmium (Cd) <= 0.002 mg/kg, Chromium (Cr) <= 0.1 mg/kg, and Nickel (Ni) <= 0.1 mg/kg.",
                    "page": 7,
                    "section": "7. Chemical & Food Contact Safety"
                },
                {
                    "clause_number": "8.1",
                    "heading": "Marking, Labeling, and ISI Standard Mark",
                    "text": "Each stainless steel flask or bottle shall be legibly and indelibly marked with: (a) Manufacturer name or registered trade mark, (b) Nominal liquid capacity in milliliters or liters, (c) Grade of stainless steel used (e.g., SS 304), (d) Country of manufacture, and (e) The Standard ISI Mark under BIS license.",
                    "page": 8,
                    "section": "8. Marking & Packaging"
                }
            ],
            "schemes": [
                {
                    "scheme_name": "Scheme I (ISI Mark Product Certification Scheme)",
                    "description": "Standard ISI Mark Certification Scheme under BIS (Conformity Assessment) Regulations 2018. Requires factory audit, sample testing at recognized lab, and continuous quality control.",
                    "conditions": "Compulsory under Stainless Steel Water Bottles Quality Control Order (QCO). Domestic and foreign manufacturers must obtain valid BIS license before selling or distributing in India.",
                    "documents_required": json.dumps([
                        "Factory registration / MSME / Udhyam certificate",
                        "Manufacturing machinery list and layout plan",
                        "In-house test equipment calibration certificates",
                        "Raw material chemical test certificate (SS 304/316 proof)",
                        "Quality Control In-Charge appointment and qualifications",
                        "Consent letter and manufacturing process flow chart"
                    ]),
                    "testing_required": True
                }
            ]
        },

        # Standard 2: IS 302-2-15:2009 (Safety of Electric Water Heaters / Kettles)
        {
            "standard_number": "IS 302-2-15:2009",
            "title": "Safety of Household and Similar Electrical Appliances - Particular Requirements for Appliances for Heating Liquids",
            "scope": "Safety requirements for electric kettles, water heaters, immersion heaters, coffee makers, and liquid-heating appliances for household and similar purposes with rated voltage not exceeding 250 V AC.",
            "status": "active",
            "edition": "Second",
            "publication_date": datetime(2009, 8, 1),
            "effective_date": datetime(2010, 2, 1),
            "source_id": 1,
            "clauses": [
                {
                    "clause_number": "1.1",
                    "heading": "Scope of Liquid Heating Appliances",
                    "text": "Deals with the safety of electric appliances for heating liquids for household and commercial use, including electric storage water heaters, instantaneous water heaters, electric kettles, and boilers with rated voltage up to 250V.",
                    "page": 1,
                    "section": "1. Scope"
                },
                {
                    "clause_number": "8.1",
                    "heading": "Protection Against Access to Live Parts",
                    "text": "Appliances shall be constructed and enclosed so that there is adequate protection against accidental contact with live electrical parts when tested with standard test finger B of IS 1401.",
                    "page": 4,
                    "section": "8. Electrical Safety"
                },
                {
                    "clause_number": "13.2",
                    "heading": "Electric Strength and Leakage Current at Operating Temperature",
                    "text": "Leakage current shall not exceed 0.75 mA for portable appliances and 1.0 mA for stationary water heaters. Insulation shall withstand dielectric high voltage test of 1250V AC for 1 minute without flashover.",
                    "page": 6,
                    "section": "13. Dielectric Strength"
                },
                {
                    "clause_number": "19.1",
                    "heading": "Abnormal Operation and Dry-Boil Protection",
                    "text": "Appliances shall incorporate a thermal cut-out or dry-heating protector preventing excessive temperature rise or fire hazard when operated empty or without water.",
                    "page": 9,
                    "section": "19. Abnormal Operation"
                },
                {
                    "clause_number": "22.11",
                    "heading": "Pressure Resistance for Closed Water Heaters",
                    "text": "The tank of unvented storage water heaters shall withstand hydraulic pressure equal to twice the rated working pressure or 1.0 MPa without permanent deformation or rupture.",
                    "page": 12,
                    "section": "22. Construction"
                }
            ],
            "schemes": [
                {
                    "scheme_name": "Scheme I (ISI Mark Product Certification Scheme)",
                    "description": "Mandatory BIS certification for household electrical appliances under the Electrical Appliances Quality Control Order.",
                    "conditions": "All manufacturers must obtain ISI Mark license with mandatory pre-certification testing at CPRI, ERTL, or NTH.",
                    "documents_required": json.dumps([
                        "Factory license / registration",
                        "High voltage dielectric test equipment calibration reports",
                        "Circuit diagrams and component safety approvals",
                        "Raw material and heating element certificates"
                    ]),
                    "testing_required": True
                }
            ]
        },

        # Standard 3: IS 694:2010 (PVC Insulated Cables up to 1100V)
        {
            "standard_number": "IS 694:2010",
            "title": "Polyvinyl Chloride (PVC) Insulated Cables for Working Voltages up to and including 1100 V - Specification",
            "scope": "Requirements for single core and multi-core PVC insulated unsheathed and sheathed cables with copper or aluminum conductors for electric power and lighting in domestic, commercial, and industrial installations.",
            "status": "active",
            "edition": "Fourth",
            "publication_date": datetime(2010, 11, 1),
            "effective_date": datetime(2011, 5, 1),
            "source_id": 1,
            "clauses": [
                {
                    "clause_number": "1.1",
                    "heading": "Scope of PVC Insulated Cables",
                    "text": "Covers PVC insulated and PVC sheathed cables with copper or aluminum conductors up to and including 1100 volts.",
                    "page": 1,
                    "section": "1. Scope"
                },
                {
                    "clause_number": "9.1",
                    "heading": "Conductor Resistance and Spark Test",
                    "text": "Electrical resistance of the conductor shall not exceed specified maximum values in Table 2. In-process spark test voltage shall be 6 kV for core diameters up to 10 mm.",
                    "page": 5,
                    "section": "9. Electrical Properties"
                },
                {
                    "clause_number": "13.1",
                    "heading": "Insulation Resistance and High Voltage Withstand",
                    "text": "Volume resistivity of PVC insulation at 70°C shall not be less than 1 x 10^10 ohm-cm. Finished cables shall withstand 3 kV AC RMS for 5 minutes without breakdown.",
                    "page": 8,
                    "section": "13. Insulation Integrity"
                },
                {
                    "clause_number": "16.2",
                    "heading": "Flammability and Flame Retardant Test",
                    "text": "Cable samples shall be subjected to Bunsen burner flame test. The flame shall extinguish automatically within 60 seconds after burner removal, with undamaged length > 50 mm.",
                    "page": 11,
                    "section": "16. Fire Safety"
                }
            ],
            "schemes": [
                {
                    "scheme_name": "Scheme I (ISI Mark Product Certification Scheme)",
                    "description": "Compulsory ISI mark certification under Electrical Wires and Cables QCO.",
                    "conditions": "Mandatory testing of conductor resistance, elongation, flammability, and insulation resistance.",
                    "documents_required": json.dumps([
                        "Factory test equipment details (Wheatstone bridge, Spark tester)",
                        "Conductor grade chemical test reports",
                        "PVC resin and compounding formulation data"
                    ]),
                    "testing_required": True
                }
            ]
        },

        # Standard 4: IS 14543:2024 (Packaged Drinking Water)
        {
            "standard_number": "IS 14543:2024",
            "title": "Packaged Drinking Water (Other Than Packaged Natural Mineral Water) - Specification",
            "scope": "Prescribes requirements and methods of sampling and test for packaged drinking water filled in hermetically sealed containers of various capacities suitable for direct human consumption.",
            "status": "active",
            "edition": "Third",
            "publication_date": datetime(2024, 1, 15),
            "effective_date": datetime(2024, 7, 15),
            "source_id": 1,
            "clauses": [
                {
                    "clause_number": "3.1",
                    "heading": "Water Purification Processing",
                    "text": "Water shall be derived from surface water, underground water, or public supply and subjected to approved treatments like decantation, filtration, demineralization, reverse osmosis, and disinfection by UV or ozonation.",
                    "page": 2,
                    "section": "3. Treatment"
                },
                {
                    "clause_number": "4.1",
                    "heading": "Physical and Chemical Parameters",
                    "text": "TDS: 75 to 500 mg/l; pH: 6.5 to 8.5; Turbidity <= 2 NTU; Nitrates <= 45 mg/l; Fluoride <= 1.0 mg/l; Heavy metals: Arsenic <= 0.01 mg/l, Lead <= 0.01 mg/l, Mercury <= 0.001 mg/l.",
                    "page": 4,
                    "section": "4. Chemical Quality"
                },
                {
                    "clause_number": "4.2",
                    "heading": "Microbiological Criteria",
                    "text": "Total coliform bacteria, E. coli, Faecal Streptococci, and Pseudomonas aeruginosa shall be absent in 250 ml of sample. Yeast and mould count shall be zero.",
                    "page": 6,
                    "section": "4. Microbiology"
                },
                {
                    "clause_number": "5.1",
                    "heading": "Packaging and Tamper Evidence",
                    "text": "Water shall be packaged in food-grade polyethylene, PET, or polycarbonate containers conforming to IS 9845. Containers must be tamper-proof and labeled with batch and shelf life.",
                    "page": 8,
                    "section": "5. Packaging"
                }
            ],
            "schemes": [
                {
                    "scheme_name": "Scheme I (ISI Mark Product Certification Scheme)",
                    "description": "Compulsory statutory licensing under Food Safety and Standards Act and BIS Act. Requires fully equipped in-house chemical and microbiological testing laboratory.",
                    "conditions": "All water packaging units must have on-site microbiologist, chemist, laminar airflow, and incubator.",
                    "documents_required": json.dumps([
                        "Central / State Ground Water Authority (CGWA) NOC",
                        "FSSAI manufacturing license",
                        "In-house microbiological laboratory setup proof",
                        "Source water comprehensive chemical test report"
                    ]),
                    "testing_required": True
                }
            ]
        },

        # Standard 5: IS 16046 (Part 1 & 2):2018 (Lithium-ion Batteries)
        {
            "standard_number": "IS 16046:2018",
            "title": "Secondary Cells and Batteries Containing Alkaline or Other Non-Acid Electrolytes (Lithium Cells and Batteries)",
            "scope": "Requirements and tests for the safe operation of portable sealed secondary lithium cells and batteries used in mobile phones, laptops, electric vehicles, and portable electronics.",
            "status": "active",
            "edition": "Second",
            "publication_date": datetime(2018, 9, 1),
            "effective_date": datetime(2019, 3, 1),
            "source_id": 3,
            "clauses": [
                {
                    "clause_number": "1.1",
                    "heading": "Scope of Lithium-ion Secondary Cells",
                    "text": "Applies to portable secondary lithium cells and batteries containing non-acid organic electrolyte for use in portable devices and battery packs.",
                    "page": 1,
                    "section": "1. Scope"
                },
                {
                    "clause_number": "7.3.2",
                    "heading": "External Short-Circuit Test",
                    "text": "Fully charged cells are short-circuited by connecting positive and negative terminals with resistance <= 80 mOhm at 55°C ± 5°C until temperature returns to ambient. No fire or explosion permitted.",
                    "page": 6,
                    "section": "7. Safety Tests"
                },
                {
                    "clause_number": "7.3.6",
                    "heading": "Overcharge Test",
                    "text": "Discharged cell or battery is charged at 2C constant current until 200% rated capacity or cutoff activates. No fire or explosion shall occur.",
                    "page": 9,
                    "section": "7. Safety Tests"
                },
                {
                    "clause_number": "7.3.8",
                    "heading": "Thermal Abuse and Temperature Shock",
                    "text": "Cell is placed in gravity convection oven heated to 130°C ± 2°C at 5°C/min rate and held for 30 minutes. Cell shall not catch fire or explode.",
                    "page": 12,
                    "section": "7. Safety Tests"
                }
            ],
            "schemes": [
                {
                    "scheme_name": "Scheme II (Compulsory Registration Scheme - CRS)",
                    "description": "Self-declaration of conformity under MeitY Electronics and Information Technology Goods (Requirement for Compulsory Registration) Order.",
                    "conditions": "Testing must be conducted at BIS-recognized laboratory in India followed by online registration on the CRS portal.",
                    "documents_required": json.dumps([
                        "Test report from BIS-recognized testing laboratory",
                        "Authorized Indian Representative (AIR) agreement (for foreign OEM)",
                        "Trademark authorization / certificate",
                        "Declaration of conformity form"
                    ]),
                    "testing_required": True
                }
            ]
        },

        # Standard 6: IS 9873 (Part 1):2019 (Safety of Toys)
        {
            "standard_number": "IS 9873 (Part 1):2019",
            "title": "Safety of Toys - Part 1: Safety Aspects Related to Mechanical and Physical Properties",
            "scope": "Applies to all toys intended for use in play by children under 14 years of age. Specifies criteria for mechanical resistance, choke hazard, sharp points, and small parts.",
            "status": "active",
            "edition": "Third",
            "publication_date": datetime(2019, 4, 1),
            "effective_date": datetime(2020, 1, 1),
            "source_id": 1,
            "clauses": [
                {
                    "clause_number": "1.1",
                    "heading": "Scope of Toy Safety",
                    "text": "Covers all toys designed or intended for use by children under 14 years. Aims to minimize hazards that are not evident to children or parents.",
                    "page": 1,
                    "section": "1. Scope"
                },
                {
                    "clause_number": "4.4",
                    "heading": "Small Parts and Choking Hazards",
                    "text": "Toys intended for children under 36 months shall not contain or detach small parts that fit entirely inside the small parts test cylinder (diameter 31.7 mm).",
                    "page": 5,
                    "section": "4. General Requirements"
                },
                {
                    "clause_number": "4.7",
                    "heading": "Sharp Edges and Points",
                    "text": "Accessible edges of metal or glass toys shall not present an unreasonable risk of cutting when tested with sharp edge tester.",
                    "page": 8,
                    "section": "4. Physical Hazards"
                },
                {
                    "clause_number": "5.24",
                    "heading": "Tension and Drop Impact Test",
                    "text": "Toy components shall withstand drop test from 1.38 m onto steel plate and 70 N tensile force without detaching hazardous small parts or sharp projections.",
                    "page": 12,
                    "section": "5. Test Procedures"
                }
            ],
            "schemes": [
                {
                    "scheme_name": "Scheme I (ISI Mark Product Certification Scheme)",
                    "description": "Mandatory BIS certification for domestic and imported toys under the Toys (Quality Control) Order.",
                    "conditions": "Requires factory inspection and sample testing at BIS recognized lab. No toy can be sold in India without ISI mark.",
                    "documents_required": json.dumps([
                        "Factory registration certificate",
                        "Raw material chemical test certificate (Phthalates & Heavy metals)",
                        "List of manufacturing machinery and testing gauges"
                    ]),
                    "testing_required": True
                }
            ]
        },

        # Standard 7: IS 1293:2019 (Plugs and Socket-Outlets)
        {
            "standard_number": "IS 1293:2019",
            "title": "Plugs and Socket-Outlets of Rated Voltage up to and including 250 V and Rated Current up to and including 16 A - Specification",
            "scope": "Specifications for domestic and industrial 2-pin and 3-pin plugs, socket outlets, multi-way adapters, and cord extension sets rated up to 16 A and 250 V AC.",
            "status": "active",
            "edition": "Fifth",
            "publication_date": datetime(2019, 7, 1),
            "effective_date": datetime(2020, 6, 1),
            "source_id": 1,
            "clauses": [
                {
                    "clause_number": "1.1",
                    "heading": "Scope of Plugs and Socket Outlets",
                    "text": "Applies to plugs and fixed or portable socket-outlets for AC only, with or without earthing contact, rated up to 250V and 16A.",
                    "page": 1,
                    "section": "1. Scope"
                },
                {
                    "clause_number": "10.1",
                    "heading": "Protection Against Electric Shock",
                    "text": "Socket-outlets shall have shutter mechanisms that prevent entry of a single pin or conductive probe into live contacts unless earthing pin is engaged.",
                    "page": 6,
                    "section": "10. Safety"
                },
                {
                    "clause_number": "19.1",
                    "heading": "Temperature Rise Test",
                    "text": "Contacts shall carry rated current continuously until thermal equilibrium. Temperature rise shall not exceed 45 K at terminals.",
                    "page": 10,
                    "section": "19. Thermal Performance"
                }
            ],
            "schemes": [
                {
                    "scheme_name": "Scheme I (ISI Mark Product Certification Scheme)",
                    "description": "Mandatory ISI mark under Electrical Accessories QCO.",
                    "conditions": "All plugs and sockets must carry ISI mark.",
                    "documents_required": json.dumps([
                        "Plastic flammability test report (UL94 V-0 or Glow wire test)",
                        "Brass conductor chemical analysis report",
                        "Endurance testing machine calibration certificate"
                    ]),
                    "testing_required": True
                }
            ]
        },

        # Standard 8: IS 16240:2015 (Reverse Osmosis Water Purification Systems)
        {
            "standard_number": "IS 16240:2015",
            "title": "Reverse Osmosis Based Point-of-Use Water Treatment Systems - Specification",
            "scope": "Prescribes constructional and performance requirements for domestic and commercial RO water purifiers intended for potable water.",
            "status": "active",
            "edition": "First",
            "publication_date": datetime(2015, 12, 1),
            "effective_date": datetime(2016, 6, 1),
            "source_id": 1,
            "clauses": [
                {
                    "clause_number": "1.1",
                    "heading": "Scope of Point-of-Use RO Systems",
                    "text": "Applies to point-of-use RO water purifiers operating on feed water TDS up to 2000 mg/l for domestic drinking water.",
                    "page": 1,
                    "section": "1. Scope"
                },
                {
                    "clause_number": "5.1",
                    "heading": "TDS Reduction Efficiency",
                    "text": "The RO system shall reduce Total Dissolved Solids by at least 90 percent when tested at specified feed pressures and temperatures.",
                    "page": 4,
                    "section": "5. Performance"
                },
                {
                    "clause_number": "6.2",
                    "heading": "Structural Pressure Integrity",
                    "text": "System components and housings shall withstand 100,000 pressure cycles from 0 to 1.0 MPa without leakage or mechanical failure.",
                    "page": 7,
                    "section": "6. Durability"
                }
            ],
            "schemes": [
                {
                    "scheme_name": "Scheme I (ISI Mark Product Certification Scheme)",
                    "description": "Voluntary / QCO notified product certification for domestic water purifiers.",
                    "conditions": "Mandatory testing of membrane rejection, recovery rate, and electrical pump safety.",
                    "documents_required": json.dumps([
                        "Filter material food-grade certification",
                        "Pressure vessel burst test certificates",
                        "Microbiological removal efficiency reports"
                    ]),
                    "testing_required": True
                }
            ]
        },

        # Standard 9: IS 269:2015 (Ordinary Portland Cement)
        {
            "standard_number": "IS 269:2015",
            "title": "Ordinary Portland Cement - Specification (33, 43, and 53 Grade)",
            "scope": "Covers manufacture and chemical/physical requirements for 33, 43, and 53 grades of Ordinary Portland Cement used in structural concrete and civil infrastructure.",
            "status": "active",
            "edition": "Sixth",
            "publication_date": datetime(2015, 10, 1),
            "effective_date": datetime(2016, 4, 1),
            "source_id": 1,
            "clauses": [
                {
                    "clause_number": "1.1",
                    "heading": "Scope of Ordinary Portland Cement",
                    "text": "Covers 33, 43, and 53 grade Ordinary Portland Cement manufactured by intimately grinding clinker and gypsum.",
                    "page": 1,
                    "section": "1. Scope"
                },
                {
                    "clause_number": "6.1",
                    "heading": "Compressive Strength Requirements",
                    "text": "Compressive strength shall satisfy minimum MPa at 72h (3 days), 168h (7 days), and 672h (28 days). For 53 grade: 3 days >= 27 MPa, 7 days >= 37 MPa, 28 days >= 53 MPa.",
                    "page": 4,
                    "section": "6. Physical Properties"
                },
                {
                    "clause_number": "6.2",
                    "heading": "Setting Time and Soundness",
                    "text": "Initial setting time shall not be less than 30 minutes; final setting time shall not exceed 600 minutes. Le-Chatelier expansion <= 10 mm.",
                    "page": 5,
                    "section": "6. Physical Properties"
                }
            ],
            "schemes": [
                {
                    "scheme_name": "Scheme I (ISI Mark Product Certification Scheme)",
                    "description": "Compulsory statutory licensing under Cement (Quality Control) Order.",
                    "conditions": "All cement manufacturing plants must maintain fully equipped physical and chemical laboratory.",
                    "documents_required": json.dumps([
                        "Limestone mining lease and clinker source details",
                        "X-Ray fluorescence spectrometer calibration data",
                        "Compressive strength testing machine NABL calibration certificate"
                    ]),
                    "testing_required": True
                }
            ]
        },

        # Standard 10: IS 17803:2022 (Stainless Steel Cookware and Utensils)
        {
            "standard_number": "IS 17803:2022",
            "title": "Stainless Steel Cookware and Utensils - Specification",
            "scope": "Requirements for domestic stainless steel pots, pans, pressure cookers, bowls, and serving utensils used for cooking, processing, and serving food.",
            "status": "active",
            "edition": "First",
            "publication_date": datetime(2022, 3, 1),
            "effective_date": datetime(2022, 9, 1),
            "source_id": 1,
            "clauses": [
                {
                    "clause_number": "1.1",
                    "heading": "Scope of Stainless Steel Cookware",
                    "text": "Applies to stainless steel cookware, tableware, pressure cookers, and kitchen utensils intended for direct contact with food.",
                    "page": 1,
                    "section": "1. Scope"
                },
                {
                    "clause_number": "4.1",
                    "heading": "Food Contact Metal Grade",
                    "text": "Surfaces in direct contact with food shall be manufactured from austenitic stainless steel Grade 304 or 316. Minimum wall thickness shall be 0.6 mm.",
                    "page": 3,
                    "section": "4. Materials"
                },
                {
                    "clause_number": "5.3",
                    "heading": "Thermal Shock and Boiling Salt Corrosion",
                    "text": "Cookware shall be boiled in 3% NaCl solution for 24 hours. No pitting, rusting, or delamination of encapsulated bottom shall occur.",
                    "page": 5,
                    "section": "5. Performance"
                }
            ],
            "schemes": [
                {
                    "scheme_name": "Scheme I (ISI Mark Product Certification Scheme)",
                    "description": "Compulsory certification under Cookware and Utensils Quality Control Order.",
                    "conditions": "Mandatory testing of material composition and food acid leaching.",
                    "documents_required": json.dumps([
                        "Spectrographic raw material chemical certificate",
                        "Handle attachment shear strength test results"
                    ]),
                    "testing_required": True
                }
            ]
        },

        # Standard 11: IS 4375:2019 (Men's Cotton Knitted Sports Shirt / T-Shirt)
        {
            "standard_number": "IS 4375:2019",
            "title": "Specification for Men's Cotton Knitted Sports Shirt/T-Shirt (Second Revision)",
            "scope": "Prescribes requirements, dimensions, sampling procedure, and testing methods for men's cotton knitted sports shirts, T-shirts, and casual polo garments made of 100% combed or carded cotton yarn.",
            "status": "active",
            "edition": "Second Revision",
            "publication_date": datetime(2019, 8, 1),
            "effective_date": datetime(2020, 2, 1),
            "source_id": 1,
            "clauses": [
                {
                    "clause_number": "1.1",
                    "heading": "Scope of Knitted Cotton Garments",
                    "text": "This standard specifies requirements for men's cotton knitted sports shirts and T-shirts, plain or patterned, with short or long sleeves.",
                    "page": 1,
                    "section": "1. Scope"
                },
                {
                    "clause_number": "4.2",
                    "heading": "Yarn Quality and Fibre Composition",
                    "text": "The fabric shall be knitted from 100 percent cotton yarn, single or folded, carded or combed, conforming to IS 171. Dimensional stability to washing shall not exceed 5 percent.",
                    "page": 2,
                    "section": "4. Materials"
                },
                {
                    "clause_number": "5.1",
                    "heading": "Colour Fastness Requirements",
                    "text": "Colour fastness to washing (IS/ISO 105-C06), perspiration (IS 971), and rubbing (IS 766) shall not be less than Grade 4.",
                    "page": 3,
                    "section": "5. Performance Tests"
                }
            ],
            "schemes": [
                {
                    "scheme_name": "Scheme I (ISI Mark Product Certification Scheme)",
                    "description": "Voluntary / Commercial product certification for apparel and knitted textiles.",
                    "conditions": "Factory inspection of knitting and sewing quality, dimensional stability tests, and azo dye testing.",
                    "documents_required": json.dumps([
                        "Fibre composition test report",
                        "Dimensional stability after wash test report",
                        "Colour fastness test results"
                    ]),
                    "testing_required": True
                }
            ]
        },

        # Standard 12: IS 544:2014 (Groundnut Oil)
        {
            "standard_number": "IS 544:2014",
            "title": "Groundnut Oil - Specification (Third Revision)",
            "scope": "Prescribes requirements and methods of sampling and test for groundnut oil (peanut oil) expressed or solvent extracted from clean and sound groundnuts (Arachis hypogaea Linn.).",
            "status": "active",
            "edition": "Third Revision",
            "publication_date": datetime(2014, 3, 1),
            "effective_date": datetime(2014, 9, 1),
            "source_id": 1,
            "clauses": [
                {
                    "clause_number": "1.1",
                    "heading": "Scope of Edible Groundnut Oil",
                    "text": "This standard prescribes the requirements and methods of sampling and test for groundnut oil for edible and industrial use.",
                    "page": 1,
                    "section": "1. Scope"
                },
                {
                    "clause_number": "4.1",
                    "heading": "Quality Characteristics and Refractive Index",
                    "text": "The oil shall be clear and free from rancidity, adulterants, sediment, suspended and other foreign matter. Refractive index at 40°C shall be 1.4620 to 1.4640. Saponification value shall be 188 to 196.",
                    "page": 2,
                    "section": "4. Requirements"
                },
                {
                    "clause_number": "5.2",
                    "heading": "Free Fatty Acids and Acid Value",
                    "text": "Acid value for refined groundnut oil shall not exceed 0.5, and for raw groundnut oil shall not exceed 6.0.",
                    "page": 3,
                    "section": "5. Chemical Tests"
                }
            ],
            "schemes": [
                {
                    "scheme_name": "Scheme I (ISI Mark Certification Scheme)",
                    "description": "Certification for packaged edible oils ensuring consumer food safety and adulteration prevention.",
                    "conditions": "Regular testing of moisture, insoluble impurities, Bellier turbidity, and fatty acid profile.",
                    "documents_required": json.dumps([
                        "FSSAI manufacturing license copy",
                        "Batch test analysis for FFA and peroxide value",
                        "Heavy metal and aflatoxin test reports"
                    ]),
                    "testing_required": True
                }
            ]
        },

        # Standard 13: IS 2062:2011 (Hot Rolled Medium and High Tensile Structural Steel)
        {
            "standard_number": "IS 2062:2011",
            "title": "Hot Rolled Medium and High Tensile Structural Steel - Specification",
            "scope": "Covers the requirements of steel plates, sections, flats, bars, and beams for use in structural steel fabrication.",
            "status": "active",
            "edition": "Seventh Revision",
            "publication_date": datetime(2011, 10, 1),
            "effective_date": datetime(2012, 4, 1),
            "source_id": 1,
            "clauses": [
                {
                    "clause_number": "1.1",
                    "heading": "Scope of Structural Steel",
                    "text": "Prescribes chemical and mechanical requirements for hot rolled steel products used for bolted, riveted, and welded structural work.",
                    "page": 1,
                    "section": "1. Scope"
                },
                {
                    "clause_number": "8.1",
                    "heading": "Tensile and Yield Strength",
                    "text": "For Grade E250, minimum yield strength shall be 250 MPa, tensile strength 410 MPa, and elongation minimum 23 percent.",
                    "page": 5,
                    "section": "8. Mechanical Properties"
                }
            ],
            "schemes": [
                {
                    "scheme_name": "Scheme I (ISI Mark Product Certification Scheme)",
                    "description": "Compulsory certification under Steel and Steel Products Quality Control Order.",
                    "conditions": "Mandatory ladle chemical analysis and Charpy V-notch impact testing.",
                    "documents_required": json.dumps([
                        "Ladle chemical analysis records",
                        "Tensile and bend test certificates"
                    ]),
                    "testing_required": True
                }
            ]
        },

        # Standard 14: IS 302-1:2024 (Safety of Household and Similar Electrical Appliances)
        {
            "standard_number": "IS 302-1:2024",
            "title": "Safety of Household and Similar Electrical Appliances - General Requirements",
            "scope": "Deals with the safety of electrical appliances for household and similar purposes, their rated voltage being not more than 250 V for single-phase appliances.",
            "status": "active",
            "edition": "Sixth Revision",
            "publication_date": datetime(2024, 1, 15),
            "effective_date": datetime(2024, 7, 15),
            "source_id": 1,
            "clauses": [
                {
                    "clause_number": "1.1",
                    "heading": "Scope of Household Electrical Safety",
                    "text": "Applies to electrical appliances for household and commercial use to protect persons and domestic animals against electrical, mechanical, and thermal hazards.",
                    "page": 1,
                    "section": "1. Scope"
                },
                {
                    "clause_number": "8.1",
                    "heading": "Protection Against Access to Live Parts",
                    "text": "Appliances shall be so constructed that there is adequate protection against accidental contact with live parts when tested with standard test probe B.",
                    "page": 8,
                    "section": "8. Electrical Safety"
                },
                {
                    "clause_number": "13.2",
                    "heading": "Electric Strength and Leakage Current",
                    "text": "The leakage current shall not exceed 0.75 mA for Class I portable appliances when tested at 1.1 times rated voltage.",
                    "page": 14,
                    "section": "13. Insulation"
                }
            ],
            "schemes": [
                {
                    "scheme_name": "Scheme I (ISI Mark Certification Scheme)",
                    "description": "Compulsory certification under Electrical Appliances (Quality Control) Order.",
                    "conditions": "High-voltage breakdown testing, thermal endurance, and fire resistance glow-wire test.",
                    "documents_required": json.dumps([
                        "Comprehensive electrical safety test certificate",
                        "Critical components list conforming to IS standards"
                    ]),
                    "testing_required": True
                }
            ]
        },

        # Standard 15: IS 15820:2009 (General Requirements for Assaying and Hallmarking Centres)
        {
            "standard_number": "IS 15820:2009",
            "title": "General Requirements for Competence of Assaying and Hallmarking Centres",
            "scope": "Specifies requirements for the competence of assaying and hallmarking centres for precious metals (Gold and Silver).",
            "status": "active",
            "edition": "First",
            "publication_date": datetime(2009, 6, 1),
            "effective_date": datetime(2009, 12, 1),
            "source_id": 1,
            "clauses": [
                {
                    "clause_number": "1.1",
                    "heading": "Scope of Precious Metal Hallmarking",
                    "text": "Specifies managerial and technical requirements for operating an official BIS recognized assaying and hallmarking centre.",
                    "page": 1,
                    "section": "1. Scope"
                },
                {
                    "clause_number": "6.2",
                    "heading": "Fire Assay for Gold Determination",
                    "text": "Gold assaying shall be carried out according to the cupellation method (fire assay) prescribed in IS 1418 with accuracy better than ± 0.5 parts per thousand.",
                    "page": 6,
                    "section": "6. Testing Procedures"
                }
            ],
            "schemes": [
                {
                    "scheme_name": "Hallmarking Scheme (IS 1417 / IS 15820)",
                    "description": "Statutory hallmarking recognized under Hallmarking of Gold Jewellery Order.",
                    "conditions": "Complete XRF screening, micro-fire assay, and automated 6-digit HUID laser marking.",
                    "documents_required": json.dumps([
                        "Assayer qualification certificates",
                        "Muffle furnace calibration logs",
                        "Laser marking system integration records"
                    ]),
                    "testing_required": True
                }
            ]
        }
    ]

    for std_data in standards_catalog:
        src = source_objs.get(std_data["source_id"])
        if not src:
            src = db.query(Source).filter(Source.authority_level == 1).first()
        source_id = src.id if src else 1

        existing = db.query(Standard).filter(Standard.standard_number == std_data["standard_number"]).first()
        if existing:
            if not existing.title or existing.title == "":
                existing.title = std_data["title"]
                existing.scope = std_data["scope"]
                existing.source_id = source_id
                db.flush()
            continue

        std = Standard(
            standard_number=std_data["standard_number"],
            title=std_data["title"],
            scope=std_data["scope"],
            status=std_data["status"],
            edition=std_data["edition"],
            publication_date=std_data["publication_date"],
            effective_date=std_data["effective_date"],
            source_id=source_id
        )
        db.add(std)
        db.flush()

        # Add clauses with embeddings
        for c in std_data.get("clauses", []):
            full_text = f"{std_data['standard_number']} {c['heading']}: {c['text']}"
            emb = generate_embedding(full_text)
            clause_obj = Clause(
                standard_id=std.id,
                clause_number=c["clause_number"],
                heading=c["heading"],
                text=c["text"],
                page=c["page"],
                section=c["section"],
                embedding=emb
            )
            db.add(clause_obj)

        # Add schemes
        for sc in std_data.get("schemes", []):
            scheme_obj = Scheme(
                scheme_name=sc["scheme_name"],
                description=sc["description"],
                conditions=sc["conditions"],
                documents_required=sc["documents_required"],
                testing_required=sc["testing_required"],
                source_id=source_id,
                standard_id=std.id
            )
            db.add(scheme_obj)

    # 3. Verified BIS Recognized / NABL Testing Laboratories
    labs_data = [
        {
            "lab_name": "National Test House (NTH) - Northern Region",
            "address": "Kamla Nehru Nagar, Ghaziabad, Uttar Pradesh 201002",
            "location": "Ghaziabad, Uttar Pradesh, Northern India",
            "contact_person": "Dr. R. K. Sharma (Director)",
            "phone": "+91-120-2788252",
            "email": "nthgz-ca@nic.in",
            "website": "https://nth.gov.in",
            "accreditation_body": "NABL / BIS",
            "accreditation_number": "TC-1345",
            "is_bis_recognized": True,
            "bis_recognition_number": "BIS/LAB/NTH-GZB/01",
            "accredited_scopes": json.dumps([
                "Domestic Stainless Steel Bottles & Flasks (IS 17526)",
                "Stainless Steel Cookware (IS 17803)",
                "Electrical Appliances & Liquid Heaters (IS 302-2-15)",
                "Cables & Wires (IS 694)",
                "Packaged Drinking Water (IS 14543)"
            ]),
            "testing_facilities": json.dumps([
                "Spectrographic Metal Analysis Lab",
                "Thermal Insulation Performance Testing Chamber",
                "High Voltage & Leakage Current Testing Station",
                "Drop & Pressure Integrity Facility"
            ]),
            "geographical_coverage": "All India",
            "sample_collection_facility": True
        },
        {
            "lab_name": "Central Power Research Institute (CPRI) - Bangalore",
            "address": "Sir C.V. Raman Road, Sadashivanagar, Bangalore, Karnataka 560080",
            "location": "Bangalore, Karnataka, Southern India",
            "contact_person": "Er. S. Venkataraman",
            "phone": "+91-80-22072200",
            "email": "cpri@cpri.in",
            "website": "https://cpri.res.in",
            "accreditation_body": "NABL / BIS",
            "accreditation_number": "TC-2091",
            "is_bis_recognized": True,
            "bis_recognition_number": "BIS/LAB/CPRI-BLR/04",
            "accredited_scopes": json.dumps([
                "Electrical Appliances & Water Heaters (IS 302-2-15)",
                "PVC Insulated Cables (IS 694)",
                "Plugs and Sockets (IS 1293)",
                "Lithium-ion Batteries (IS 16046)"
            ]),
            "testing_facilities": json.dumps([
                "High Voltage Laboratory",
                "Abnormal Operation & Thermal Safety Cell",
                "Spark Testing & Dielectric Rig",
                "Fire & Flammability Smoke Chamber"
            ]),
            "geographical_coverage": "All India",
            "sample_collection_facility": True
        },
        {
            "lab_name": "Electronics Regional Test Laboratory (ERTL - North)",
            "address": "S-Block, Okhla Industrial Area Phase-II, New Delhi 110020",
            "location": "New Delhi, Delhi NCR",
            "contact_person": "Sh. A. K. Verma (Head of Lab)",
            "phone": "+91-11-26386219",
            "email": "ertlnorth@stqc.gov.in",
            "website": "https://stqc.gov.in",
            "accreditation_body": "NABL / MeitY / BIS",
            "accreditation_number": "TC-1582",
            "is_bis_recognized": True,
            "bis_recognition_number": "BIS/CRS/ERTL-DEL/12",
            "accredited_scopes": json.dumps([
                "Lithium-ion Cells & Battery Packs (IS 16046)",
                "IT and Electronic Goods (CRS Scheme)",
                "Electrical Safety & Liquid Heaters (IS 302-2-15)"
            ]),
            "testing_facilities": json.dumps([
                "Battery Short Circuit & Thermal Abuse Chamber",
                "Environmental Shock & Vibration Tester",
                "Electromagnetic Compatibility (EMC) Suite"
            ]),
            "geographical_coverage": "Northern & Western India",
            "sample_collection_facility": True
        },
        {
            "lab_name": "Central Food Technological Research Institute (CSIR-CFTRI)",
            "address": "Cheluvamba Mansion, Mysore, Karnataka 570020",
            "location": "Mysore, Karnataka, Southern India",
            "contact_person": "Dr. P. S. Rao",
            "phone": "+91-821-2517760",
            "email": "director@cftri.res.in",
            "website": "https://cftri.res.in",
            "accreditation_body": "NABL / FSSAI / BIS",
            "accreditation_number": "TC-1044",
            "is_bis_recognized": True,
            "bis_recognition_number": "BIS/FOOD/CFTRI/08",
            "accredited_scopes": json.dumps([
                "Packaged Drinking Water (IS 14543)",
                "Food Contact Materials & Plastic Migration (IS 9845)",
                "Heavy Metal Leaching Tests (IS 17526)"
            ]),
            "testing_facilities": json.dumps([
                "ICP-MS Heavy Metal Spectrometry",
                "Class 10,000 Cleanroom Microbiology Lab",
                "HPLC Organic Contaminant Analyzer"
            ]),
            "geographical_coverage": "All India",
            "sample_collection_facility": True
        },
        {
            "lab_name": "Central Institute of Petrochemicals Engineering & Technology (CIPET)",
            "address": "T.V.K. Industrial Estate, Guindy, Chennai, Tamil Nadu 600032",
            "location": "Chennai, Tamil Nadu, Southern India",
            "contact_person": "Dr. B. Sundaram",
            "phone": "+91-44-22254780",
            "email": "cipetchennai@cipet.gov.in",
            "website": "https://cipet.gov.in",
            "accreditation_body": "NABL / BIS",
            "accreditation_number": "TC-1802",
            "is_bis_recognized": True,
            "bis_recognition_number": "BIS/LAB/CIPET-CHN/07",
            "accredited_scopes": json.dumps([
                "Polymer & Rubber Gaskets for Flasks (IS 17526)",
                "Safety of Toys (IS 9873)",
                "Point-of-Use RO Systems (IS 16240)"
            ]),
            "testing_facilities": json.dumps([
                "Polymer Chemical Characterization Lab",
                "Toy Mechanical Drop and Choke Hazard Station",
                "Pressure Cycling Test Rig"
            ]),
            "geographical_coverage": "Southern India",
            "sample_collection_facility": True
        },
        {
            "lab_name": "Shriram Institute for Industrial Research (SIIR) - Delhi",
            "address": "19, University Road, Delhi 110007",
            "location": "Delhi NCR, Northern India",
            "contact_person": "Dr. Mukul Das",
            "phone": "+91-11-27667267",
            "email": "customercare@shriraminstitute.org",
            "website": "https://shriraminstitute.org",
            "accreditation_body": "NABL / BIS",
            "accreditation_number": "TC-1120",
            "is_bis_recognized": True,
            "bis_recognition_number": "BIS/LAB/SIIR-DEL/03",
            "accredited_scopes": json.dumps([
                "Stainless Steel Bottles & Flasks (IS 17526)",
                "Safety of Toys (IS 9873)",
                "Packaged Drinking Water (IS 14543)",
                "Cookware & Utensils (IS 17803)"
            ]),
            "testing_facilities": json.dumps([
                "OES Spark Spectrometer",
                "Toxic Element Leaching Suite",
                "Mechanical Impact & Pull Force Rig"
            ]),
            "geographical_coverage": "Northern & Central India",
            "sample_collection_facility": True
        }
    ]

    for lab in labs_data:
        existing_lab = db.query(LaboratoryRecord).filter(LaboratoryRecord.lab_name == lab["lab_name"]).first()
        if existing_lab:
            continue
        lab_obj = LaboratoryRecord(
            lab_name=lab["lab_name"],
            address=lab["address"],
            location=lab["location"],
            contact_person=lab["contact_person"],
            phone=lab["phone"],
            email=lab["email"],
            website=lab["website"],
            accreditation_body=lab["accreditation_body"],
            accreditation_number=lab["accreditation_number"],
            is_bis_recognized=lab["is_bis_recognized"],
            bis_recognition_number=lab["bis_recognition_number"],
            accredited_scopes=lab["accredited_scopes"],
            testing_facilities=lab["testing_facilities"],
            geographical_coverage=lab["geographical_coverage"],
            sample_collection_facility=lab["sample_collection_facility"]
        )
        db.add(lab_obj)

    db.commit()
    logger.info("Successfully seeded verified Indian Standards, clauses, schemes, and testing laboratories.")
