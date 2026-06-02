"""Unit tests for ClinicalDataValidator and related models.

These tests cover:
- Age validation (0-120 range, pediatric/geriatric warnings)
- Laboratory value validation (reference ranges, abnormal detection)
- Subject ID format validation
- Gender validation
- Date parsing and validation
"""

import sys
from datetime import date, datetime
from pathlib import Path

import pytest

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from medical_cli.core.data_validator import (
    ClinicalSubjectBase,
    LabValue,
    ClinicalDataValidator,
    LAB_TEST_REFERENCE_RANGES,
)


# =============================================================================
# Test: Age Validation
# =============================================================================

class TestAgeValidation:
    """Tests for age field validation."""

    def test_valid_age_within_range(self):
        """Test that valid ages (0-120) are accepted."""
        valid_ages = [0, 1, 17, 18, 45, 65, 90, 119, 120]
        
        for age in valid_ages:
            subject = ClinicalSubjectBase(
                Subject_ID="SITE-001-0001",
                Age=age,
                Gender="M",
                Visit_Date=date(2024, 1, 15),
            )
            assert subject.Age == age

    def test_age_zero_is_valid(self):
        """Test that age 0 (newborn) is valid."""
        subject = ClinicalSubjectBase(
            Subject_ID="SITE-001-0001",
            Age=0,
            Gender="M",
            Visit_Date=date(2024, 1, 15),
        )
        assert subject.Age == 0

    def test_age_120_is_valid(self):
        """Test that maximum age 120 is valid."""
        subject = ClinicalSubjectBase(
            Subject_ID="SITE-001-0001",
            Age=120,
            Gender="F",
            Visit_Date=date(2024, 1, 15),
        )
        assert subject.Age == 120

    def test_age_below_zero_rejected(self):
        """Test that negative ages are rejected."""
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            ClinicalSubjectBase(
                Subject_ID="SITE-001-0001",
                Age=-1,
                Gender="M",
                Visit_Date=date(2024, 1, 15),
            )

    def test_age_above_120_rejected(self):
        """Test that ages above 120 are rejected."""
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            ClinicalSubjectBase(
                Subject_ID="SITE-001-0001",
                Age=121,
                Gender="M",
                Visit_Date=date(2024, 1, 15),
            )

    def test_age_string_converted(self):
        """Test that string age values are converted to int."""
        subject = ClinicalSubjectBase(
            Subject_ID="SITE-001-0001",
            Age="45",
            Gender="M",
            Visit_Date=date(2024, 1, 15),
        )
        assert subject.Age == 45
        assert isinstance(subject.Age, int)


# =============================================================================
# Test: Laboratory Value Abnormal Detection
# =============================================================================

class TestLabValueValidation:
    """Tests for laboratory value validation and abnormal detection."""

    def test_normal_lab_value_not_abnormal(self, sample_lab_values):
        """Test that normal lab values are not flagged as abnormal."""
        for lab_data in sample_lab_values:
            lab = LabValue(**lab_data)
            assert lab.is_abnormal is False

    def test_lab_value_above_range_is_abnormal(self):
        """Test that lab values above reference range are flagged as abnormal."""
        lab = LabValue(
            test_code="WBC",
            test_name="White Blood Cell Count",
            value=15.0,  # Above normal range (4.0-11.0)
            unit="10^9/L",
            reference_range_low=4.0,
            reference_range_high=11.0,
        )
        assert lab.is_abnormal is True

    def test_lab_value_below_range_is_abnormal(self):
        """Test that lab values below reference range are flagged as abnormal."""
        lab = LabValue(
            test_code="PLT",
            test_name="Platelet Count",
            value=80.0,  # Below normal range (100.0-400.0)
            unit="10^9/L",
            reference_range_low=100.0,
            reference_range_high=400.0,
        )
        assert lab.is_abnormal is True

    def test_lab_value_at_lower_boundary_not_abnormal(self):
        """Test that lab value at lower boundary is not abnormal."""
        lab = LabValue(
            test_code="WBC",
            test_name="White Blood Cell Count",
            value=4.0,  # Exactly at lower boundary
            unit="10^9/L",
            reference_range_low=4.0,
            reference_range_high=11.0,
        )
        assert lab.is_abnormal is False

    def test_lab_value_at_upper_boundary_not_abnormal(self):
        """Test that lab value at upper boundary is not abnormal."""
        lab = LabValue(
            test_code="WBC",
            test_name="White Blood Cell Count",
            value=11.0,  # Exactly at upper boundary
            unit="10^9/L",
            reference_range_low=4.0,
            reference_range_high=11.0,
        )
        assert lab.is_abnormal is False

    def test_lab_value_auto_detects_abnormal(self):
        """Test that abnormal status is auto-determined from reference range."""
        lab = LabValue(
            test_code="HGB",
            test_name="Hemoglobin",
            value=100.0,  # Below normal (120-180)
            unit="g/L",
            reference_range_low=120.0,
            reference_range_high=180.0,
        )
        assert lab.is_abnormal is True

    def test_lab_value_nan_rejected(self):
        """Test that NaN values are rejected."""
        with pytest.raises(ValueError, match="Laboratory value must be a finite number"):
            LabValue(
                test_code="WBC",
                test_name="White Blood Cell Count",
                value=float("nan"),
                unit="10^9/L",
            )

    def test_lab_value_infinity_rejected(self):
        """Test that infinite values are rejected."""
        with pytest.raises(ValueError, match="Laboratory value must be a finite number"):
            LabValue(
                test_code="WBC",
                test_name="White Blood Cell Count",
                value=float("inf"),
                unit="10^9/L",
            )


# =============================================================================
# Test: ClinicalSubjectBase with Lab Values
# =============================================================================

class TestClinicalSubjectWithLabs:
    """Tests for ClinicalSubjectBase with laboratory values."""

    def test_subject_with_normal_lab_values(self, sample_lab_values):
        """Test subject creation with normal lab values."""
        subject = ClinicalSubjectBase(
            Subject_ID="SITE-001-0001",
            Age=45,
            Gender="M",
            Visit_Date=date(2024, 1, 15),
            lab_values=[LabValue(**lab) for lab in sample_lab_values],
        )
        assert len(subject.lab_values) == 3
        assert all(not lab.is_abnormal for lab in subject.lab_values)

    def test_subject_with_abnormal_lab_values(self, abnormal_lab_values):
        """Test subject creation with abnormal lab values."""
        subject = ClinicalSubjectBase(
            Subject_ID="SITE-001-0001",
            Age=45,
            Gender="M",
            Visit_Date=date(2024, 1, 15),
            lab_values=[LabValue(**lab) for lab in abnormal_lab_values],
        )
        assert len(subject.lab_values) == 2
        assert all(lab.is_abnormal for lab in subject.lab_values)

    def test_subject_with_empty_lab_values(self):
        """Test subject creation with no lab values."""
        subject = ClinicalSubjectBase(
            Subject_ID="SITE-001-0001",
            Age=45,
            Gender="M",
            Visit_Date=date(2024, 1, 15),
            lab_values=[],
        )
        assert subject.lab_values == []


# =============================================================================
# Test: Subject ID Format Validation
# =============================================================================

class TestSubjectIDValidation:
    """Tests for Subject_ID format validation."""

    @pytest.mark.parametrize("subject_id", [
        "SITE-001-0001",
        "SJ-123-4567",
        "ABCD-789-0123",
        "XX-000-0000",
        "SH-123-4567",
    ])
    def test_valid_subject_id_formats(self, subject_id):
        """Test that valid Subject_ID formats are accepted."""
        subject = ClinicalSubjectBase(
            Subject_ID=subject_id,
            Age=45,
            Gender="M",
            Visit_Date=date(2024, 1, 15),
        )
        assert subject.Subject_ID == subject_id.upper()

    @pytest.mark.parametrize("invalid_id", [
        "SITE0010001",      # Missing hyphens
        "SITE-01-001",      # Wrong digit count
        "SITE-001-001",     # Last part too short
        "SITE_001_0001",    # Underscores instead of hyphens
        "SITE-001-00010",   # Last part too long
        "1SITE-001-0001",   # Starts with number
        "S-001-0001",       # Site code too short (1 char)
        "SITEE-001-0001",   # Site code too long (5 chars)
    ])
    def test_invalid_subject_id_formats(self, invalid_id):
        """Test that invalid Subject_ID formats are rejected."""
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            ClinicalSubjectBase(
                Subject_ID=invalid_id,
                Age=45,
                Gender="M",
                Visit_Date=date(2024, 1, 15),
            )


# =============================================================================
# Test: Gender Validation
# =============================================================================

class TestGenderValidation:
    """Tests for Gender field validation."""

    @pytest.mark.parametrize("gender,expected", [
        ("M", "M"),
        ("F", "F"),
        ("O", "O"),
        ("  M  ", "M"),
    ])
    def test_valid_genders(self, gender, expected):
        """Test that valid gender values are accepted and normalized."""
        subject = ClinicalSubjectBase(
            Subject_ID="SITE-001-0001",
            Age=45,
            Gender=gender,
            Visit_Date=date(2024, 1, 15),
        )
        assert subject.Gender == expected

    @pytest.mark.parametrize("invalid_gender", [
        "X",
        "U",
        "male",
        "female",
        "unknown",
        "MALE",
        "FEMALE",
        "OTHER",
    ])
    def test_invalid_genders(self, invalid_gender):
        """Test that invalid gender values are rejected."""
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            ClinicalSubjectBase(
                Subject_ID="SITE-001-0001",
                Age=45,
                Gender=invalid_gender,
                Visit_Date=date(2024, 1, 15),
            )


# =============================================================================
# Test: Visit Date Validation
# =============================================================================

class TestVisitDateValidation:
    """Tests for Visit_Date field validation."""

    @pytest.mark.parametrize("date_str,expected_date", [
        ("2024-01-15", date(2024, 1, 15)),
        ("2024/01/15", date(2024, 1, 15)),
        ("15-01-2024", date(2024, 1, 15)),
        ("01/15/2024", date(2024, 1, 15)),
        ("20240115", date(2024, 1, 15)),
    ])
    def test_valid_date_formats(self, date_str, expected_date):
        """Test that various date formats are accepted."""
        subject = ClinicalSubjectBase(
            Subject_ID="SITE-001-0001",
            Age=45,
            Gender="M",
            Visit_Date=date_str,
        )
        assert subject.Visit_Date == expected_date

    def test_date_object_accepted(self):
        """Test that date objects are accepted directly."""
        visit_date = date(2024, 1, 15)
        subject = ClinicalSubjectBase(
            Subject_ID="SITE-001-0001",
            Age=45,
            Gender="M",
            Visit_Date=visit_date,
        )
        assert subject.Visit_Date == visit_date

    def test_datetime_midnight_accepted(self):
        """Test that datetime objects at midnight are accepted (date portion used)."""
        visit_datetime = datetime(2024, 1, 15, 0, 0, 0)
        subject = ClinicalSubjectBase(
            Subject_ID="SITE-001-0001",
            Age=45,
            Gender="M",
            Visit_Date=visit_datetime,
        )
        assert subject.Visit_Date == date(2024, 1, 15)


# =============================================================================
# Test: ClinicalDataValidator Class
# =============================================================================

class TestClinicalDataValidator:
    """Tests for the ClinicalDataValidator class."""

    def test_validator_initialization(self):
        """Test validator can be initialized with default settings."""
        validator = ClinicalDataValidator()
        assert validator.strict_mode is False

    def test_validator_strict_mode(self):
        """Test validator can be initialized with strict mode."""
        validator = ClinicalDataValidator(strict_mode=True)
        assert validator.strict_mode is True

    def test_validate_record_success(self, sample_subject_data):
        """Test successful validation of a valid record."""
        validator = ClinicalDataValidator()
        is_valid, errors = validator.validate_record(sample_subject_data)
        assert is_valid is True
        assert errors == []

    def test_validate_record_failure(self):
        """Test validation failure for invalid record."""
        validator = ClinicalDataValidator()
        invalid_record = {
            "Subject_ID": "INVALID",  # Wrong format
            "Age": 45,
            "Gender": "M",
            "Visit_Date": "2024-01-15",
        }
        is_valid, errors = validator.validate_record(invalid_record)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_schema_valid(self):
        """Test schema validation with valid schema."""
        validator = ClinicalDataValidator()
        schema = {"fields": ["Subject_ID", "Age"]}
        assert validator.validate_schema(schema) is True

    def test_validate_schema_missing_fields(self):
        """Test schema validation with missing required field."""
        validator = ClinicalDataValidator()
        schema = {"name": "test"}  # Missing "fields"
        assert validator.validate_schema(schema) is False


# =============================================================================
# Test: Reference Ranges Constants
# =============================================================================

class TestLabReferenceRanges:
    """Tests for LAB_TEST_REFERENCE_RANGES constant."""

    def test_reference_ranges_exist(self):
        """Test that reference ranges dictionary is defined."""
        assert len(LAB_TEST_REFERENCE_RANGES) > 0

    def test_common_lab_tests_defined(self):
        """Test that common lab tests are in reference ranges."""
        common_tests = ["WBC", "RBC", "HGB", "PLT", "ALT", "AST", "CRE", "GLU"]
        for test in common_tests:
            assert test in LAB_TEST_REFERENCE_RANGES

    def test_reference_range_format(self):
        """Test that reference ranges have correct format (low, high, unit)."""
        for test_code, (low, high, unit) in LAB_TEST_REFERENCE_RANGES.items():
            assert low < high, f"{test_code}: low must be less than high"
            assert isinstance(unit, str), f"{test_code}: unit must be string"


# =============================================================================
# Test: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_subject_id_converted_to_uppercase(self):
        """Test that lowercase subject IDs are converted to uppercase."""
        subject = ClinicalSubjectBase(
            Subject_ID="site-001-0001",
            Age=45,
            Gender="m",
            Visit_Date="2024-01-15",
        )
        assert subject.Subject_ID == "SITE-001-0001"
        assert subject.Gender == "M"

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed (extra='allow')."""
        # Creating subject with extra fields should not raise
        ClinicalSubjectBase(
            Subject_ID="SITE-001-0001",
            Age=45,
            Gender="M",
            Visit_Date=date(2024, 1, 15),
            Custom_Field="value",
            Another_Field=123,
        )
        # If we reach here without exception, test passes

    def test_whitespace_trimmed(self):
        """Test that whitespace is trimmed from string fields."""
        subject = ClinicalSubjectBase(
            Subject_ID="  SITE-001-0001  ",
            Age=45,
            Gender="  M  ",
            Visit_Date="2024-01-15",
        )
        assert subject.Subject_ID == "SITE-001-0001"
        assert subject.Gender == "M"