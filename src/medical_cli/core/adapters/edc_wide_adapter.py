"""EDC Wide-Table Adapter for complex clinical data exports.

This module provides an adapter that can parse EDC (Electronic Data Capture)
system exports with complex multi-row headers and wide-table structure.

The adapter handles:
- Multi-row metadata headers (rows 1-7 contain system info)
- Chinese column names for clinical variables
- Wide-table format with multiple lab values per subject row
- Conversion to standard lab_values format for validation
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from medical_cli.utils.logger import get_logger


logger = get_logger("medical_cli.core.adapters.edc_wide_adapter")


# Mapping from Chinese clinical variable names to standard Test_Codes
CHINESE_TO_TEST_CODE_MAPPING: Dict[str, str] = {
    # Blood routine tests
    "血常规_白细胞": "WBC",
    "血常规_红细胞": "RBC",
    "血常规_血红蛋白": "HGB",
    "血常规_血小板": "PLT",
    "血常规_中性粒细胞": "NEUT",
    "血常规_淋巴细胞": "LYMPH",
    "血常规_单核细胞": "MONO",
    "血常规_嗜酸性粒细胞": "EOS",
    "血常规_嗜碱性粒细胞": "BASO",
    
    # Liver function tests
    "肝功能_谷丙转氨酶": "ALT",
    "肝功能_谷草转氨酶": "AST",
    "肝功能_总胆红素": "TBIL",
    "肝功能_直接胆红素": "DBIL",
    "肝功能_白蛋白": "ALB",
    "肝功能_总蛋白": "TP",
    "肝功能_碱性磷酸酶": "ALP",
    "肝功能_谷氨酰转肽酶": "GGT",
    
    # Renal function tests
    "肾功能_血清钾": "K",
    "肾功能_血清钠": "NA",
    "肾功能_血清氯": "CL",
    "肾功能_血清肌酐": "CRE",
    "肾功能_尿素氮": "BUN",
    "肾功能_尿酸": "UA",
    
    # Blood glucose tests
    "血糖_空腹血糖": "GLU",
    "血糖_餐后2h血糖": "GLU_2H",
    
    # Lipid tests
    "血脂_总胆固醇": "TC",
    "血脂_甘油三酯": "TG",
    "血脂_高密度脂蛋白": "HDL",
    "血脂_低密度脂蛋白": "LDL",
    
    # Cardiac markers
    "心肌标志物_肌酸激酶": "CK",
    "心肌标志物_肌钙蛋白": "TNI",
    "心肌标志物_B型钠尿肽": "BNP",
    
    # Coagulation tests
    "凝血功能_凝血酶原时间": "PT",
    "凝血功能_活化部分凝血活酶时间": "APTT",
    "凝血功能_凝血酶时间": "TT",
    "凝血功能_纤维蛋白原": "FIB",
}

# Standard reference ranges for common lab tests (test_code -> (low, high, unit))
LAB_REFERENCE_RANGES: Dict[str, Tuple[float, float, str]] = {
    "WBC": (4.0, 11.0, "10^9/L"),
    "RBC": (4.0, 6.0, "10^12/L"),
    "HGB": (120.0, 180.0, "g/L"),
    "PLT": (100.0, 400.0, "10^9/L"),
    "NEUT": (1.8, 7.7, "10^9/L"),
    "LYMPH": (1.1, 3.2, "10^9/L"),
    "MONO": (0.2, 1.0, "10^9/L"),
    "EOS": (0.02, 0.5, "10^9/L"),
    "BASO": (0.0, 0.1, "10^9/L"),
    "ALT": (5.0, 40.0, "U/L"),
    "AST": (5.0, 40.0, "U/L"),
    "TBIL": (3.4, 20.5, "umol/L"),
    "DBIL": (0.0, 6.8, "umol/L"),
    "ALB": (35.0, 52.0, "g/L"),
    "TP": (60.0, 82.0, "g/L"),
    "ALP": (44.0, 147.0, "U/L"),
    "GGT": (7.0, 45.0, "U/L"),
    "K": (3.5, 5.3, "mmol/L"),
    "NA": (135.0, 145.0, "mmol/L"),
    "CL": (96.0, 106.0, "mmol/L"),
    "CRE": (44.0, 133.0, "umol/L"),
    "BUN": (2.6, 7.5, "mmol/L"),
    "UA": (150.0, 420.0, "umol/L"),
    "GLU": (3.9, 6.1, "mmol/L"),
    "TC": (3.1, 5.7, "mmol/L"),
    "TG": (0.4, 1.8, "mmol/L"),
    "HDL": (1.0, 1.9, "mmol/L"),
    "LDL": (0.0, 3.4, "mmol/L"),
    "CK": (25.0, 200.0, "U/L"),
    "TNI": (0.0, 0.04, "ng/mL"),
    "BNP": (0.0, 100.0, "pg/mL"),
    "PT": (11.0, 13.5, "sec"),
    "APTT": (25.0, 35.0, "sec"),
    "TT": (14.0, 21.0, "sec"),
    "FIB": (2.0, 4.0, "g/L"),
}


class EDCWideAdapter:
    """Adapter for parsing EDC system exports with wide-table structure.
    
    This adapter handles Excel files exported from EDC systems that have:
    - Complex multi-row headers (rows 1-7 contain metadata)
    - Chinese variable names as column headers
    - Wide-table format with multiple lab values per row
    
    It converts the complex structure to standard lab_values format
    for downstream validation.
    
    Attributes:
        file_path: Path to the input Excel/CSV file.
        dataframe: Parsed pandas DataFrame (after processing).
        mapping: Dictionary mapping Chinese names to Test_Codes.
    """
    
    def __init__(
        self,
        file_path: str,
        header_row_index: int = 3,  # Row 4 in Excel (1-based) = pandas index 3
        data_start_row: int = 7,     # Row 8 in Excel (1-based) = pandas index 7
    ) -> None:
        """Initialize the EDC Wide Adapter.
        
        Args:
            file_path: Path to the input file.
            header_row_index: Row index (0-based in pandas) containing business column names.
                              Default: 3 (Row 4 in Excel 1-based numbering).
            data_start_row: Row index (0-based in pandas) where actual data begins.
                           Default: 7 (Row 8 in Excel 1-based numbering).
        """
        self.file_path = Path(file_path)
        self._header_row_index = header_row_index
        self.data_start_row = data_start_row
        self.mapping = CHINESE_TO_TEST_CODE_MAPPING.copy()
        self.dataframe: Optional[pd.DataFrame] = None
        self._parsed_data: List[Dict[str, Any]] = []
        
        if not self.file_path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")
    
    def parse_lab_data(self) -> List[Dict[str, Any]]:
        """Parse EDC wide-table data and convert to standard format.
        
        Reads the file, extracts business column names from the specified header row,
        and converts wide-table structure to standard lab_values format.
        
        Returns:
            List of dictionaries containing parsed clinical data with:
            - Subject_ID
            - Visit_Date
            - lab_values: list of standardized lab test entries
            
        Raises:
            Exception: If file parsing fails.
        """
        logger.info(f"Parsing EDC wide-table file: {self.file_path}")
        
        try:
            # Determine file type and read accordingly
            ext = self.file_path.suffix.lower()
            
            if ext in (".xlsx", ".xls"):
                self.dataframe = self._read_excel()
            elif ext == ".csv":
                self.dataframe = self._read_csv()
            else:
                raise ValueError(f"Unsupported file format: {ext}")
            
            # Convert wide-table to long format with lab values
            self._parsed_data = self._melt_wide_to_long()
            
            logger.info(f"Successfully parsed {len(self._parsed_data)} records")
            return self._parsed_data
            
        except Exception as e:
            logger.error(f"Failed to parse EDC file: {e}")
            raise
    
    def _read_excel(self) -> pd.DataFrame:
        """Read Excel file with fixed header row (Row 4 = index 3).
        
        Returns:
            DataFrame with business column names as headers.
        """
        logger.info(f"Reading Excel file with header at row index {self._header_row_index}")
        
        # Read Excel with fixed header row index (3 = Row 4 in Excel 1-based)
        df = pd.read_excel(self.file_path, header=self._header_row_index)
        
        # Skip header row to get to data rows
        df = df.iloc[self._header_row_index + 1:]
        
        # Clean up column names
        df.columns = [str(col).strip() if pd.notna(col) else f"col_{i}" 
                      for i, col in enumerate(df.columns)]
        
        # Drop columns that are entirely empty or unnamed metadata columns
        df = df.loc[:, ~df.columns.str.match(r"^(col_\d+|Unnamed:\s*\d+)$")]
        
        # Drop rows that are all NaN
        df = df.dropna(how='all')
        
        logger.info(f"Read {len(df)} data rows, columns: {list(df.columns)}")
        return df
    
    def _read_csv(self) -> pd.DataFrame:
        """Read CSV file with fixed header row (Row 4 = index 3).
        
        Returns:
            DataFrame with business column names as headers.
        """
        logger.info(f"Reading CSV file with header at row index {self._header_row_index}")
        
        # Read CSV with fixed header row index (3 = Row 4 in 1-based numbering)
        df = pd.read_csv(self.file_path, header=self._header_row_index, encoding='utf-8')
        
        # Skip header row to get to data rows
        df = df.iloc[self._header_row_index + 1:]
        
        # Clean up column names
        df.columns = [str(col).strip() if pd.notna(col) else f"col_{i}" 
                      for i, col in enumerate(df.columns)]
        
        df = df.loc[:, ~df.columns.str.match(r"^(col_\d+|Unnamed:\s*\d+)$")]
        df = df.dropna(how='all')
        
        logger.info(f"Read {len(df)} data rows, columns: {list(df.columns)}")
        return df
    
    def _melt_wide_to_long(self) -> List[Dict[str, Any]]:
        """Convert wide-table format to standard long format with lab_values.
        
        Extracts subject information and maps Chinese column names to
        standardized lab test entries.
        
        Returns:
            List of records with Subject_ID, Visit_Date, and lab_values.
        """
        records: List[Dict[str, Any]] = []
        
        # Identify subject ID and visit date columns
        subject_col = self._find_column(["患者研究编号", "Subject_ID", "subject_id", "受试者编号"])
        date_col = self._find_column(["检查日期", "Visit_Date", "visit_date", "访视日期", "检验日期"])
        
        logger.info(f"Identified subject column: {subject_col}, date column: {date_col}")
        
        for idx, row in self.dataframe.iterrows():
            try:
                # Extract subject and visit information
                subject_id = self._safe_get_value(row, subject_col) if subject_col else None
                visit_date = self._safe_get_value(row, date_col) if date_col else None
                
                # Skip rows without subject ID
                if not subject_id or pd.isna(subject_id):
                    continue
                
                # Build lab values list from mapped columns
                lab_values: List[Dict[str, Any]] = []
                
                for chinese_name, test_code in self.mapping.items():
                    if chinese_name in self.dataframe.columns:
                        value = self._safe_get_numeric_value(row, chinese_name)
                        if value is not None:
                            # Get unit from adjacent column or use default
                            unit = self._get_unit_for_test(test_code)
                            
                            lab_entry = {
                                "test_code": test_code,
                                "test_name": test_code,
                                "value": value,
                                "unit": unit,
                            }
                            lab_values.append(lab_entry)
                
                # Create record
                record: Dict[str, Any] = {
                    "Subject_ID": str(subject_id).strip(),
                }
                
                if visit_date:
                    if isinstance(visit_date, str):
                        record["Visit_Date"] = visit_date
                    else:
                        record["Visit_Date"] = str(visit_date)
                
                if lab_values:
                    record["lab_values"] = lab_values
                
                records.append(record)
                
            except Exception as e:
                logger.warning(f"Error processing row {idx}: {e}")
                continue
        
        return records
    
    def _find_column(self, possible_names: List[str]) -> Optional[str]:
        """Find a column that matches one of the possible names.
        
        Args:
            possible_names: List of column name variants to search for.
            
        Returns:
            Matching column name or None if not found.
        """
        for name in possible_names:
            if name in self.dataframe.columns:
                return name
        
        # Try case-insensitive match
        cols_lower = {c.lower(): c for c in self.dataframe.columns}
        for name in possible_names:
            if name.lower() in cols_lower:
                return cols_lower[name.lower()]
        
        return None
    
    def _safe_get_value(self, row: pd.Series, column: str) -> Any:
        """Safely get a value from a DataFrame row.
        
        Args:
            row: DataFrame row.
            column: Column name.
            
        Returns:
            Value or None if not available.
        """
        if column and column in row.index:
            val = row[column]
            if pd.isna(val):
                return None
            return val
        return None
    
    def _safe_get_numeric_value(self, row: pd.Series, column: str) -> Optional[float]:
        """Safely get a numeric value from a DataFrame row.
        
        Args:
            row: DataFrame row.
            column: Column name.
            
        Returns:
            Float value or None if not available or not numeric.
        """
        val = self._safe_get_value(row, column)
        if val is None:
            return None
        
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    
    def _get_unit_for_test(self, test_code: str) -> str:
        """Get the standard unit for a test code.
        
        Args:
            test_code: Standard test code (e.g., "WBC", "K").
            
        Returns:
            Standard unit string or empty string if unknown.
        """
        if test_code in LAB_REFERENCE_RANGES:
            _, _, unit = LAB_REFERENCE_RANGES[test_code]
            return unit
        return ""
    
    def add_mapping(self, chinese_name: str, test_code: str) -> None:
        """Add a custom mapping from Chinese name to test code.
        
        Args:
            chinese_name: Chinese column name in the Excel file.
            test_code: Standard test code (e.g., "WBC").
        """
        self.mapping[chinese_name] = test_code
        logger.info(f"Added custom mapping: {chinese_name} -> {test_code}")
    
    def get_parsed_data(self) -> List[Dict[str, Any]]:
        """Get the parsed data after calling parse_lab_data().
        
        Returns:
            List of parsed records or empty list if not yet parsed.
        """
        return self._parsed_data