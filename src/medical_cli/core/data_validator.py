"""Data validator module with Pydantic models for clinical data validation.

This module provides comprehensive validation for clinical trial subject data,
including subject identifiers, demographic information, and laboratory values.
"""

import math
import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
)

from medical_cli.utils.logger import setup_logger


# Configure logger for this module
logger = setup_logger("medical_cli.data_validator")


class LabValue(BaseModel):
    """Model for individual laboratory test values.
    
    Attributes:
        test_code: Laboratory test code (e.g., 'WBC', 'RBC', 'HGB').
        test_name: Full name of the laboratory test.
        value: Numeric value of the test result.
        unit: Unit of measurement (e.g., '10^9/L', 'g/L').
        reference_range_low: Lower bound of normal reference range.
        reference_range_high: Upper bound of normal reference range.
        is_abnormal: Flag indicating if value is outside reference range.
    """
    
    test_code: str = Field(..., min_length=1, max_length=20)
    test_name: str = Field(..., min_length=1, max_length=100)
    value: float
    unit: str = Field(..., min_length=1, max_length=20)
    reference_range_low: Optional[float] = None
    reference_range_high: Optional[float] = None
    is_abnormal: bool = False
    
    @field_validator("value")
    @classmethod
    def validate_value_not_nan(cls, v: float) -> float:
        """Ensure lab value is not NaN or infinite."""
        import math
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Laboratory value must be a finite number")
        return v
    
    @field_validator("test_code", mode="before")
    @classmethod
    def normalize_test_code(cls, v: str) -> str:
        """Normalize test code to uppercase."""
        if isinstance(v, str):
            return v.upper().strip()
        return v
    
    @model_validator(mode="after")
    def auto_populate_reference_ranges(self) -> "LabValue":
        """Auto-populate reference ranges from LAB_TEST_REFERENCE_RANGES if not provided."""
        # Only auto-populate if test_code exists and reference ranges are not set
        if self.test_code in LAB_TEST_REFERENCE_RANGES and self.reference_range_low is None:
            ref_low, ref_high, _ = LAB_TEST_REFERENCE_RANGES[self.test_code]
            self.reference_range_low = ref_low
            self.reference_range_high = ref_high
        return self
    
    @model_validator(mode="after")
    def check_abnormal_status(self) -> "LabValue":
        """Automatically determine abnormal status based on reference ranges.
        
        Defensive check: Only perform comparison if value is not None or NaN.
        """
        # Skip comparison if value is None, NaN, or cannot be compared
        if self.value is None:
            return self
        if isinstance(self.value, float) and not math.isfinite(self.value):
            return self
        
        if self.reference_range_low is not None and self.reference_range_low and self.value < self.reference_range_low:
            self.is_abnormal = True
        elif self.reference_range_high is not None and self.reference_range_high and self.value > self.reference_range_high:
            self.is_abnormal = True
        return self


# Valid laboratory test codes with their reference ranges
LAB_TEST_REFERENCE_RANGES: Dict[str, Tuple[float, float, str]] = {
    "WBC": (4.0, 11.0, "10^9/L"),      # White Blood Cell count
    "RBC": (4.0, 6.0, "10^12/L"),      # Red Blood Cell count
    "HGB": (120.0, 180.0, "g/L"),      # Hemoglobin
    "HCT": (0.36, 0.50, ""),            # Hematocrit
    "PLT": (100.0, 400.0, "10^9/L"),    # Platelet count
    "ALT": (5.0, 40.0, "U/L"),         # Alanine Aminotransferase
    "AST": (5.0, 40.0, "U/L"),         # Aspartate Aminotransferase
    "CRE": (44.0, 133.0, "umol/L"),    # Creatinine
    "BUN": (2.6, 7.5, "mmol/L"),       # Blood Urea Nitrogen
    "GLU": (3.9, 6.1, "mmol/L"),      # Fasting blood glucose
    "K": (3.5, 5.3, "mmol/L"),         # Potassium
    "NA": (135.0, 145.0, "mmol/L"),    # Sodium
    "CL": (96.0, 106.0, "mmol/L"),     # Chloride
}


class SubjectLabData(BaseModel):
    """Model for subject laboratory data.
    
    Attributes:
        subject_id: Unique subject identifier.
        lab_records: List of laboratory test records.
    """
    
    subject_id: str
    lab_records: List[LabValue] = Field(default_factory=list)
    
    @field_validator("subject_id")
    @classmethod
    def validate_subject_id_format(cls, v: str) -> str:
        """Validate subject ID follows SITE-XXX-XXXX format."""
        pattern = r"^[A-Z]{2,4}-\d{3}-\d{4}$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Subject ID must follow format SITE-XXX-XXXX (e.g., 'SITE-001-0001'), "
                f"got '{v}'"
            )
        return v.upper()


class ClinicalSubjectBase(BaseModel):
    """Base model for clinical subject data with core validation.
    
    This is the foundational Pydantic model for validating clinical trial data.
    It enforces strict validation rules for subject identifiers, demographics,
    and provides extensible laboratory value validation.
    
    Attributes:
        Subject_ID: Unique subject identifier following SITE-XXX-XXXX format.
        Age: Subject age in years, must be between 0 and 120.
        Gender: Subject gender, must be one of 'M', 'F', or 'O' (Other).
        Visit_Date: Date of the clinical visit.
        Visit_Type: Type of visit (e.g., 'Screening', 'Baseline', 'Follow-up').
        Enrollment_Site: Site code where subject was enrolled.
        lab_values: Optional list of laboratory test values for validation.
        extra_data: Additional fields not explicitly defined.
        
    Example:
        >>> data = ClinicalSubjectBase(
        ...     Subject_ID="SITE-001-0001",
        ...     Age=45,
        ...     Gender="M",
        ...     Visit_Date=date(2024, 1, 15)
        ... )
    """
    
    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
    )
    
    Subject_ID: str = Field(
        ...,
        description="Unique subject identifier following SITE-XXX-XXXX format",
    )
    Age: int = Field(
        ...,
        ge=0,
        le=120,
        description="Subject age in years (0-120)",
    )
    Gender: str = Field(
        ...,
        description="Subject gender: M (Male), F (Female), O (Other)",
    )
    Visit_Date: date = Field(
        ...,
        description="Date of the clinical visit",
    )
    Visit_Type: Optional[str] = Field(
        default="Baseline",
        description="Type of clinical visit",
    )
    Enrollment_Site: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Site code where subject was enrolled",
    )
    lab_values: Optional[List[LabValue]] = Field(
        default=None,
        description="Laboratory test values for this visit",
    )
    extra_data: Optional[Dict[str, Any]] = Field(
        default=None,
        exclude=True,
    )
    
    @field_validator("Subject_ID")
    @classmethod
    def validate_subject_id(cls, v: str) -> str:
        """Validate subject ID matches required format SITE-XXX-XXXX.
        
        The format consists of:
        - 2-4 uppercase letters for site code
        - A hyphen
        - 3 digits
        - A hyphen
        - 4 digits
        
        Args:
            v: The subject ID string to validate.
            
        Returns:
            The validated and uppercased subject ID.
            
        Raises:
            ValueError: If the format does not match requirements.
        """
        # Normalize to uppercase for consistency
        v = v.upper()
        
        # Pattern: 2-4 letters, hyphen, 3 digits, hyphen, 4 digits
        pattern = r"^[A-Z]{2,4}-\d{3}-\d{4}$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Subject_ID must follow format SITE-XXX-XXXX "
                f"(e.g., 'SITE-001-0001', 'SJ-123-4567'), got '{v}'"
            )
        
        logger.info(f"Validated subject ID: {v}")
        return v
    
    @field_validator("Age")
    @classmethod
    def validate_age_range(cls, v: int) -> int:
        """Validate age is within acceptable range for clinical studies.
        
        Args:
            v: Age value to validate.
            
        Returns:
            The validated age.
            
        Raises:
            ValueError: If age is outside 0-120 range.
        """
        if v < 0 or v > 120:
            raise ValueError(f"Age must be between 0 and 120, got {v}")
        
        # Log warning for unusual but valid ages
        if v < 18:
            logger.warning(f"Subject age {v} is under 18 (pediatric)")
        elif v > 90:
            logger.warning(f"Subject age {v} is over 90 (geriatric)")
        
        return v
    
    @field_validator("Gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        """Validate gender is one of the allowed values.
        
        Args:
            v: Gender string to validate.
            
        Returns:
            Normalized gender value.
            
        Raises:
            ValueError: If gender is not one of 'M', 'F', or 'O'.
        """
        v = v.upper().strip()
        
        valid_genders = {"M", "F", "O"}
        if v not in valid_genders:
            raise ValueError(
                f"Gender must be one of 'M' (Male), 'F' (Female), 'O' (Other), got '{v}'"
            )
        
        gender_map = {"MALE": "M", "FEMALE": "F", "OTHER": "O"}
        if v in gender_map:
            v = gender_map[v]
        
        return v
    
    @field_validator("Visit_Date", mode="before")
    @classmethod
    def validate_visit_date(cls, v: Any) -> date:
        """Parse and validate visit date from various formats.
        
        Args:
            v: Date value in various formats (string, datetime, date).
            
        Returns:
            Validated date object.
            
        Raises:
            ValueError: If date cannot be parsed or is invalid.
        """
        from datetime import datetime
        
        if isinstance(v, date):
            return v
        
        if isinstance(v, datetime):
            return v.date()
        
        if isinstance(v, str):
            # Try common date formats
            formats = [
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%d-%m-%Y",
                "%d/%m/%Y",
                "%m-%d-%Y",
                "%m/%d/%Y",
                "%Y%m%d",
            ]
            
            for fmt in formats:
                try:
                    parsed = datetime.strptime(v, fmt).date()
                    # Validate date is not in the future
                    if parsed > date.today():
                        raise ValueError(
                            f"Visit_Date cannot be in the future: {v}"
                        )
                    return parsed
                except ValueError:
                    continue
            
            raise ValueError(
                f"Visit_Date must be in format YYYY-MM-DD or similar, got '{v}'"
            )
        
        raise ValueError(f"Visit_Date must be a date object or string, got {type(v)}")
    
    @model_validator(mode="after")
    def validate_lab_values(self) -> "ClinicalSubjectBase":
        """Validate laboratory values if present.
        
        This validator ensures that if laboratory values are provided,
        they follow expected patterns and ranges for clinical data.
        
        Returns:
            Self with validated lab values.
            
        Raises:
            ValueError: If lab values have invalid structure or values.
        """
        if self.lab_values is None or len(self.lab_values) == 0:
            return self
        
        logger.debug(f"Validating {len(self.lab_values)} laboratory values for {self.Subject_ID}")
        
        # Track which tests we've seen
        seen_tests: Dict[str, int] = {}
        
        for idx, lab in enumerate(self.lab_values):
            # Check for duplicate test codes
            if lab.test_code in seen_tests:
                logger.warning(
                    f"Duplicate lab test '{lab.test_code}' found for {self.Subject_ID} "
                    f"(occurrences: {seen_tests[lab.test_code] + 1})"
                )
            seen_tests[lab.test_code] = idx
            
            # Validate against known reference ranges
            if lab.test_code in LAB_TEST_REFERENCE_RANGES:
                expected_low, expected_high, expected_unit = LAB_TEST_REFERENCE_RANGES[lab.test_code]
                
                # Update reference ranges if not provided
                if lab.reference_range_low is None:
                    lab.reference_range_low = expected_low
                if lab.reference_range_high is None:
                    lab.reference_range_high = expected_high
                
                # Check if unit matches expected
                if lab.unit and lab.unit != expected_unit:
                    logger.warning(
                        f"Unit mismatch for {lab.test_code}: expected '{expected_unit}', "
                        f"got '{lab.unit}'"
                    )
                
                # Log abnormal values
                if lab.is_abnormal:
                    logger.warning(
                        f"Abnormal lab value for {self.Subject_ID}: "
                        f"{lab.test_code}={lab.value} "
                        f"(ref: {expected_low}-{expected_high})"
                    )
        
        return self


class ClinicalDataValidator:
    """High-level validator for clinical trial data files.
    
    This class provides batch validation capabilities for clinical data
    files, supporting both single records and file-based validation with
    detailed reporting.
    
    Attributes:
        strict_mode: If True, validation errors will raise exceptions.
        schema: Optional custom validation schema.
        
    Example:
        >>> validator = ClinicalDataValidator(strict_mode=True)
        >>> result = validator.validate_file("./data/clinical_records.csv")
    """
    
    def __init__(
        self,
        strict_mode: bool = False,
        schema: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the clinical data validator.
        
        Args:
            strict_mode: If True, raise exceptions on validation errors.
            schema: Optional custom schema for extended validation.
        """
        self.strict_mode = strict_mode
        self.schema = schema
        self._validation_errors: List[Dict[str, Any]] = []
        self._warnings: List[str] = []
        
        logger.info(f"Initialized ClinicalDataValidator (strict={strict_mode})")
    
    def validate(
        self,
        input_path: str,
        schema_path: Optional[str] = None,
        strict: bool = False,
    ) -> Dict[str, Any]:
        """Validate clinical data against defined schemas and rules.
        
        Args:
            input_path: Path to input file to validate.
            schema_path: Optional path to validation schema file.
            strict: Enable strict validation mode.
            
        Returns:
            Validation result dictionary containing:
                - valid (bool): Overall validation status
                - errors (list): List of validation errors
                - warnings (list): List of warning messages
                - record_count (int): Number of records validated
                - error_count (int): Number of errors found
        """
        logger.info(f"Starting validation for: {input_path}")
        
        self._validation_errors = []
        self._warnings = []
        use_strict = strict or self.strict_mode
        
        try:
            from medical_cli.utils.file_helpers import read_json, read_csv
            
            ext = input_path.lower().split(".")[-1]
            
            if ext in ("json",):
                data = read_json(input_path)
            elif ext in ("csv",):
                data = read_csv(input_path)
            else:
                raise ValueError(f"Unsupported file format: {ext}")
            
            # Handle both single record and list of records
            if isinstance(data, dict):
                records = [data]
            elif isinstance(data, list):
                records = data
            else:
                raise ValueError(f"Unexpected data type: {type(data)}")
            
            validated_count = 0
            for idx, record in enumerate(records):
                try:
                    if isinstance(record, dict):
                        # Convert to ClinicalSubjectBase for validation
                        subject = ClinicalSubjectBase(**record)
                        validated_count += 1
                        
                        # Check for lab value anomalies
                        if subject.lab_values:
                            self._check_lab_anomalies(subject)
                            
                except Exception as e:
                    error_msg = f"Record {idx + 1}: {str(e)}"
                    self._validation_errors.append(error_msg)
                    if use_strict:
                        raise
                    logger.warning(error_msg)
            
            result = {
                "valid": len(self._validation_errors) == 0,
                "errors": self._validation_errors,
                "warnings": self._warnings,
                "record_count": validated_count,
                "error_count": len(self._validation_errors),
            }
            
            logger.info(
                f"Validation complete: {validated_count} records, "
                f"{len(self._validation_errors)} errors"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": self._warnings,
                "record_count": 0,
                "error_count": 1,
            }
    
    def _check_lab_anomalies(self, subject: ClinicalSubjectBase) -> None:
        """Check for anomalies in laboratory values.
        
        Args:
            subject: Validated subject record.
        """
        if not subject.lab_values:
            return
        
        # Check for multiple critical abnormalities
        critical_abnormalities = [
            lab for lab in subject.lab_values
            if lab.is_abnormal and lab.test_code in ("WBC", "PLT", "HGB")
        ]
        
        if len(critical_abnormalities) >= 2:
            self._warnings.append(
                f"{subject.Subject_ID}: Multiple critical lab abnormalities detected"
            )
        
        # Check for extremely abnormal values
        for lab in subject.lab_values:
            if lab.reference_range_low and lab.reference_range_high:
                range_mid = (lab.reference_range_low + lab.reference_range_high) / 2
                deviation = abs(lab.value - range_mid) / range_mid if range_mid > 0 else 0
                
                if deviation > 0.5:  # More than 50% deviation from normal
                    self._warnings.append(
                        f"{subject.Subject_ID}: {lab.test_code} value significantly "
                        f"deviates from normal range ({lab.value} vs expected "
                        f"{lab.reference_range_low}-{lab.reference_range_high})"
                    )
    
    def validate_record(
        self,
        record: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, List[str]]:
        """Validate a single record against a schema.
        
        Args:
            record: Data record to validate.
            schema: Optional validation schema.
            
        Returns:
            Tuple of (is_valid, list_of_errors).
        """
        errors: List[str] = []
        
        try:
            ClinicalSubjectBase(**record)
            return True, []
        except Exception as e:
            errors.append(str(e))
            return False, errors if self.strict_mode else errors[:1]
    
    def validate_schema(self, schema: Dict[str, Any]) -> bool:
        """Validate a schema definition itself.
        
        Args:
            schema: Schema to validate.
            
        Returns:
            True if valid schema, False otherwise.
        """
        required_fields = ["fields"]
        
        for field in required_fields:
            if field not in schema:
                logger.error(f"Schema missing required field: {field}")
                return False
        
        return True


# Backwards compatibility function wrappers
def validate(
    input_path: str,
    schema_path: Optional[str] = None,
    strict: bool = False,
) -> Dict[str, Any]:
    """Validate clinical data against defined schemas and rules.
    
    Args:
        input_path: Path to input file to validate.
        schema_path: Optional path to validation schema file.
        strict: Enable strict validation mode.
        
    Returns:
        Validation result dictionary with 'valid' boolean and 'errors' list.
    """
    validator = ClinicalDataValidator(strict_mode=strict)
    return validator.validate(input_path, schema_path, strict)


def validate_record(record: Dict[str, Any], schema: Optional[Dict[str, Any]] = None) -> bool:
    """Validate a single record against a schema.
    
    Args:
        record: Data record to validate.
        schema: Validation schema.
        
    Returns:
        True if valid, False otherwise.
    """
    try:
        ClinicalSubjectBase(**record)
        return True
    except Exception:
        return False


def validate_schema(schema: Dict[str, Any]) -> bool:
    """Validate a schema definition itself.
    
    Args:
        schema: Schema to validate.
        
    Returns:
        True if valid schema, False otherwise.
    """
    return ClinicalDataValidator().validate_schema(schema)