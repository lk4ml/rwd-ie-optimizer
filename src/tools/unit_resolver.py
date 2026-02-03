"""
Unit Resolver Tool

Handles unit conversions for lab tests and measurements.
"""

from typing import Dict, Optional, List


# Known unit conversions for common lab tests
UNIT_CONVERSIONS = {
    "egfr": {
        "standard_unit": "mL/min/1.73m²",
        "alternative_units": [],
        "range": {"normal": [90, 120], "ckd_stage_3": [30, 59], "ckd_stage_4": [15, 29]},
    },
    "hba1c": {
        "standard_unit": "%",
        "alternative_units": [
            {"unit": "mmol/mol", "conversion": "mmol/mol = (% - 2.15) * 10.929"}
        ],
        "range": {"normal": [4.0, 5.6], "prediabetes": [5.7, 6.4], "diabetes": [6.5, 15.0]},
    },
    "glucose": {
        "standard_unit": "mg/dL",
        "alternative_units": [{"unit": "mmol/L", "conversion": "mg/dL = mmol/L * 18.0"}],
        "range": {"normal_fasting": [70, 99], "diabetes_fasting": [126, 400]},
    },
    "creatinine": {
        "standard_unit": "mg/dL",
        "alternative_units": [{"unit": "μmol/L", "conversion": "mg/dL = μmol/L / 88.4"}],
        "range": {"normal_male": [0.7, 1.3], "normal_female": [0.6, 1.1]},
    },
    "uacr": {
        "standard_unit": "mg/g",
        "alternative_units": [{"unit": "mg/mmol", "conversion": "mg/g = mg/mmol * 0.113"}],
        "range": {
            "normal": [0, 30],
            "microalbuminuria": [30, 300],
            "macroalbuminuria": [300, 10000],
        },
    },
    "ldl": {
        "standard_unit": "mg/dL",
        "alternative_units": [{"unit": "mmol/L", "conversion": "mg/dL = mmol/L * 38.67"}],
        "range": {"optimal": [0, 100], "near_optimal": [100, 129], "high": [160, 500]},
    },
    "hdl": {
        "standard_unit": "mg/dL",
        "alternative_units": [{"unit": "mmol/L", "conversion": "mg/dL = mmol/L * 38.67"}],
        "range": {"low_risk_male": [40, 100], "low_risk_female": [50, 100]},
    },
}


def resolve_units(test_name: str) -> Dict:
    """
    Get unit information and conversion rules for a lab test.

    Args:
        test_name: Lab test name (e.g., "eGFR", "HbA1c", "glucose")

    Returns:
        Dictionary with:
        - standard_unit: The standard unit for this test
        - alternative_units: List of alternative units with conversion formulas
        - range: Normal/abnormal ranges
        - available: Whether we have information for this test

    Example:
        >>> resolve_units("hba1c")
        {
            "test_name": "hba1c",
            "available": True,
            "standard_unit": "%",
            "alternative_units": [
                {"unit": "mmol/mol", "conversion": "mmol/mol = (% - 2.15) * 10.929"}
            ],
            "range": {
                "normal": [4.0, 5.6],
                "prediabetes": [5.7, 6.4],
                "diabetes": [6.5, 15.0]
            }
        }
    """

    test_key = test_name.lower().replace(" ", "").replace("_", "")

    if test_key in UNIT_CONVERSIONS:
        info = UNIT_CONVERSIONS[test_key]
        return {
            "test_name": test_name,
            "available": True,
            "standard_unit": info["standard_unit"],
            "alternative_units": info.get("alternative_units", []),
            "range": info.get("range", {}),
            "notes": f"Standard unit: {info['standard_unit']}",
        }
    else:
        return {
            "test_name": test_name,
            "available": False,
            "message": f"No unit information available for '{test_name}'",
            "suggestion": "Use standard clinical units or consult data dictionary",
        }


def get_all_supported_tests() -> List[str]:
    """
    Get list of all tests with unit conversion support.

    Returns:
        List of supported test names
    """
    return list(UNIT_CONVERSIONS.keys())


# For testing
if __name__ == "__main__":
    import json

    print("Supported tests:")
    print(json.dumps(get_all_supported_tests(), indent=2))

    print("\n\nResolving units for HbA1c:")
    result = resolve_units("hba1c")
    print(json.dumps(result, indent=2))

    print("\n\nResolving units for eGFR:")
    result = resolve_units("egfr")
    print(json.dumps(result, indent=2))
