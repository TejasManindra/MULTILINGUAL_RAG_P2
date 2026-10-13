import json
from pathlib import Path

OUTPUT_FILE = Path("data/metadata/central_eligibility_rules.json")

with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

for scheme in data["schemes"]:
    if scheme["scheme_id"] == "PMAY_G":

        scheme["eligibility_rules"] = []

        scheme["exclusion_rules"] = [
            {
                "field": "has_pucca_house_or_availed_other_housing_scheme",
                "operator": "equals",
                "value": True,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c21",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "beneficiary_deceased_without_nominee",
                "operator": "equals",
                "value": True,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c21",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "permanently_migrated",
                "operator": "equals",
                "value": True,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c21",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "owns_motorised_vehicle_or_fishing_boat",
                "operator": "equals",
                "value": True,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c21",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "owns_mechanised_agricultural_equipment",
                "operator": "equals",
                "value": True,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c21",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "kcc_credit_limit",
                "operator": "greater_than_or_equal",
                "value": 50000,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c21",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "household_has_government_employee",
                "operator": "equals",
                "value": True,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c21",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "non_agricultural_enterprise_registered_with_government",
                "operator": "equals",
                "value": True,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c21",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "highest_monthly_family_income",
                "operator": "greater_than",
                "value": 10000,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c21",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "pays_income_tax",
                "operator": "equals",
                "value": True,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c21",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "pays_professional_tax",
                "operator": "equals",
                "value": True,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c21",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "owns_refrigerator",
                "operator": "equals",
                "value": True,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c21",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "owns_landline_phone",
                "operator": "equals",
                "value": True,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c21",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "irrigated_land_acres",
                "operator": "greater_than_or_equal",
                "value": 2.5,
                "additional_condition": "with_at_least_one_irrigation_equipment",
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c21",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "irrigated_land_acres",
                "operator": "greater_than_or_equal",
                "value": 5,
                "additional_condition": "irrigated_for_two_or_more_crop_seasons",
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c21",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "land_acres",
                "operator": "greater_than_or_equal",
                "value": 7.5,
                "additional_condition": "with_at_least_one_irrigation_equipment",
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c21",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "unwilling_to_construct_house",
                "operator": "equals",
                "value": True,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c22",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "beneficiary_not_traceable",
                "operator": "equals",
                "value": True,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c22",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "living_in_sensitive_or_forest_area_and_unable_to_construct",
                "operator": "equals",
                "value": True,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c22",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "duplicate_registration",
                "operator": "equals",
                "value": True,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c22",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "moved_from_rural_to_urban_area",
                "operator": "equals",
                "value": True,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c22",
                    "source_date": "2020-12-03"
                }
            },
            {
                "field": "site_dispute_or_joint_property_or_court_case",
                "operator": "equals",
                "value": True,
                "rule_type": "exclusion",
                "evidence": {
                    "source_file": "PMAY-G for Rural Housing.pdf",
                    "page_number": 9,
                    "chunk_id": "PMAY-G for Rural Housing_p9_c22",
                    "source_date": "2020-12-03"
                }
            }
        ]

        scheme["evidence"].append({
            "source_file": "PMAY-G for Rural Housing.pdf",
            "source_type": "government_guideline",
            "source_date": "2020-12-03",
            "pages": [9],
            "note": "Exclusion/rejection reasons from AwaasSoft remand SOP. Verify against the latest PMAY-G rules before using for current eligibility decisions."
        })

        break

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("PMAY-G rules added successfully.")