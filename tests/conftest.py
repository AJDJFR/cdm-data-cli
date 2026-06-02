"""Pytest configuration and shared fixtures for medical-cli tests."""

import sys
from pathlib import Path

import pytest

# Add src directory to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_subject_data():
    """Provide sample valid subject data for testing."""
    return {
        "Subject_ID": "SITE-001-0001",
        "Age": 45,
        "Gender": "M",
        "Visit_Date": "2024-01-15",
    }


@pytest.fixture
def sample_lab_values():
    """Provide sample lab values for testing."""
    return [
        {
            "test_code": "WBC",
            "test_name": "White Blood Cell Count",
            "value": 7.5,
            "unit": "10^9/L",
            "reference_range_low": 4.0,
            "reference_range_high": 11.0,
        },
        {
            "test_code": "RBC",
            "test_name": "Red Blood Cell Count",
            "value": 5.2,
            "unit": "10^12/L",
            "reference_range_low": 4.0,
            "reference_range_high": 6.0,
        },
        {
            "test_code": "HGB",
            "test_name": "Hemoglobin",
            "value": 150.0,
            "unit": "g/L",
            "reference_range_low": 120.0,
            "reference_range_high": 180.0,
        },
    ]


@pytest.fixture
def abnormal_lab_values():
    """Provide sample abnormal lab values for testing."""
    return [
        {
            "test_code": "WBC",
            "test_name": "White Blood Cell Count",
            "value": 15.0,  # Above normal range
            "unit": "10^9/L",
            "reference_range_low": 4.0,
            "reference_range_high": 11.0,
        },
        {
            "test_code": "PLT",
            "test_name": "Platelet Count",
            "value": 80.0,  # Below normal range
            "unit": "10^9/L",
            "reference_range_low": 100.0,
            "reference_range_high": 400.0,
        },
    ]