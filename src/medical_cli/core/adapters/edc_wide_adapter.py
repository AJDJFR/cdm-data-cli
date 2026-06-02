"""EDC Wide-Table Adapter for complex clinical data exports.

This module provides an intelligent adapter that can parse EDC (Electronic Data Capture)
system exports with complex multi-row headers and wide-table structure.

Key Features:
- Heuristic dynamic header detection (no hardcoded row indices)
- Fuzzy column name matching using semantic patterns
- Wide-to-long transformation for clinical data validation
"""

import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from medical_cli.utils.logger import get_logger


logger = get_logger("medical_cli.core.adapters.edc_wide_adapter")


# Clinical core keyword vocabulary for header detection
CLINICAL_CORE_VOCABULARY: Set[str] = {
    # Chinese keywords
    "中心", "编号", "受试者", "日期", "检查", "姓名", "性别", "年龄",
    "白细胞", "红细胞", "血红蛋白", "血小板", "中性粒", "淋巴",
    "谷丙", "谷草", "转氨酶", "胆红素", "白蛋白", "肌酐", "尿素",
    "尿酸", "血糖", "血脂", "胆固醇", "甘油三酯",
    "钾", "钠", "氯", "肝功能", "肾功能", "血常规",
    # English keywords
    "WBC", "RBC", "HGB", "PLT", "ALT", "AST", "K", "NA", "CRE", "BUN",
    "Subject", "Patient", "Date", "Visit", "Age", "Sex", "Gender",
    "ID", "Lab", "Test", "Result", "Value", "Unit", "Normal", "Range",
}

# Metadata keywords that indicate non-data rows (control rows)
METADATA_KEYWORDS: Set[str] = {
    # Chinese control metadata
    "变量", "Variable", "变量ID", "VariableID", "类型", "Type",
    "必答", "Required", "必填", "必选", "格式", "Format", "长度", "Length",
    "选项", "Options", "范围", "Range", "默认值", "Default",
    "DataType", "Label", "Section", "Form", "CRF",
    # Control row specific keywords (for filtering after header)
    "选项编码", "编码", "是否必答", "是否必填", "单选题", "多选题",
    "文本题", "填空题", "下拉框", "复选框", "矩阵题",
    "题号", "题目", "题目描述", "变量说明",
    "填写说明", "注释", "备注", "说明",
}

# Control row patterns - high repetition indicators
CONTROL_REPETITION_PATTERNS: Set[str] = {
    "Y", "N", "是", "否", "文本", "数值", "日期", "选项", "选项1", "选项2",
    "必填", "非必填", "必答", "非必答", "是", "否", "请选择", "请输入",
}

# Test code keywords for column classification
TEST_CODE_KEYWORDS: Dict[str, List[str]] = {
    "WBC": ["白细胞", "WBC", " leukocyte", "white blood"],
    "RBC": ["红细胞", "RBC", " erythrocyte", "red blood"],
    "HGB": ["血红蛋白", "HGB", "HB", "hemoglobin"],
    "PLT": ["血小板", "PLT", "thrombocyte", "platelet"],
    "NEUT": ["中性粒", "NEUT", "neutrophil"],
    "LYMPH": ["淋巴", "LYMPH", "lymphocyte"],
    "MONO": ["单核", "MONO", "monocyte"],
    "EOS": ["嗜酸", "EOS", "eosinophil"],
    "BASO": ["嗜碱", "BASO", "basophil"],
    "ALT": ["谷丙", "ALT", "GPT", "alanine"],
    "AST": ["谷草", "AST", "GOT", "aspartate"],
    "TBIL": ["总胆红素", "TBIL", "bilirubin"],
    "DBIL": ["直接胆红素", "DBIL"],
    "ALB": ["白蛋白", "ALB", "albumin"],
    "TP": ["总蛋白", "TP", "total protein"],
    "ALP": ["碱性磷酸酶", "ALP", "phosphatase"],
    "GGT": ["谷氨酰", "GGT", "transpeptidase"],
    "K": ["血清钾", "血钾", "K", "potassium"],
    "NA": ["血清钠", "血钠", "NA", "sodium"],
    "CL": ["血清氯", "血氯", "CL", "chloride"],
    "CRE": ["肌酐", "CRE", "creatinine"],
    "BUN": ["尿素氮", "BUN", "urea"],
    "UA": ["尿酸", "UA", "uric acid"],
    "GLU": ["血糖", "GLU", "glucose"],
    "TC": ["总胆固醇", "TC", "cholesterol"],
    "TG": ["甘油三酯", "TG", "triglyceride"],
    "HDL": ["高密度脂蛋白", "HDL"],
    "LDL": ["低密度脂蛋白", "LDL"],
    "CK": ["肌酸激酶", "CK", "CPK", "creatine kinase"],
    "TNI": ["肌钙蛋白", "TNI", "troponin"],
    "BNP": ["B型钠尿肽", "BNP", "natriuretic"],
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
    """Intelligent adapter for parsing EDC system exports with dynamic structure detection.
    
    This adapter:
    1. Auto-detects header rows using heuristic keyword matching
    2. Uses fuzzy column name matching for flexible column identification
    3. Transforms wide-table format to standard lab_values for validation
    
    Attributes:
        file_path: Path to the input file.
        dataframe: Parsed pandas DataFrame (after processing).
        header_row: Detected header row index.
        data_start_row: Detected data start row index.
    """
    
    def __init__(self, file_path: str) -> None:
        """Initialize the EDC Wide Adapter.
        
        Args:
            file_path: Path to the input file.
        """
        self.file_path = Path(file_path)
        self.header_row: Optional[int] = None
        self.data_start_row: Optional[int] = None
        self.dataframe: Optional[pd.DataFrame] = None
        self._parsed_data: List[Dict[str, Any]] = []
        
        if not self.file_path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")
    
    def parse_lab_data(self) -> List[Dict[str, Any]]:
        """Parse EDC wide-table data and convert to standard format.
        
        Performs:
        1. Heuristic header detection
        2. Fuzzy column name matching
        3. Wide-to-long transformation
        
        Returns:
            List of dictionaries with Subject_ID, Visit_Date, and lab_values.
        """
        logger.info(f"Parsing EDC wide-table file: {self.file_path}")
        
        try:
            # Step 1: Detect table structure (header and data rows)
            self._detect_table_structure()
            
            # Step 2: Read file with detected structure
            self.dataframe = self._read_file_with_structure()
            
            # Step 3: Build column mapping with fuzzy matching
            column_mapping = self._build_fuzzy_column_mapping()
            
            # Step 4: Transform wide-table to long format
            self._parsed_data = self._transform_wide_to_long(column_mapping)
            
            logger.info(f"Successfully parsed {len(self._parsed_data)} records")
            return self._parsed_data
            
        except Exception as e:
            logger.error(f"Failed to parse EDC file: {e}")
            raise
    
    def _detect_table_structure(self) -> None:
        """Ultimate 4.0 dynamic header and data detection algorithm.
        
        Features:
        1. Heuristic header row detection using clinical vocabulary
        2. Control row intelligent filtering:
           - Keyword interception for system metadata
           - Repetition rate and null value statistics
        3. Primary key format dynamic anchoring:
           - Detect subject ID patterns (non-Chinese, hyphenated, fixed prefixes)
           - Find the first row that matches primary key format
        
        Sets:
        - header_row: Row with most clinical vocabulary matches
        - data_start_row: First real data row (not control metadata)
        """
        logger.info("4.0 Engine: Detecting table structure with metadata filtering...")
        
        # Read first 20 rows without header
        ext = self.file_path.suffix.lower()
        if ext in ('.xlsx', '.xls'):
            df_preview = pd.read_excel(self.file_path, header=None, nrows=20)
        elif ext == '.csv':
            df_preview = pd.read_csv(
                self.file_path, 
                header=None, 
                nrows=20, 
                encoding='utf-8',
                on_bad_lines='skip'
            )
        else:
            df_preview = pd.read_csv(
                self.file_path, 
                header=None, 
                nrows=20, 
                encoding='utf-8',
                on_bad_lines='skip'
            )
        
        # Step 1: Find header row (clinical vocabulary matching)
        best_header_row = 0
        best_header_score = 0
        
        for row_idx in range(min(20, len(df_preview))):
            row = df_preview.iloc[row_idx]
            row_text = " ".join([str(v) for v in row.values if pd.notna(v)])
            
            # Count matches with clinical vocabulary
            clinical_score = sum(1 for keyword in CLINICAL_CORE_VOCABULARY if keyword in row_text)
            
            # Bonus for rows with multiple non-null values (likely column headers)
            non_null_count = sum(1 for v in row.values if pd.notna(v))
            clinical_score += non_null_count * 0.1
            
            # Penalize rows with metadata keywords
            meta_penalty = sum(0.5 for keyword in METADATA_KEYWORDS if keyword in row_text)
            clinical_score -= meta_penalty
            
            if clinical_score > best_header_score:
                best_header_score = clinical_score
                best_header_row = row_idx
        
        self.header_row = best_header_row
        logger.info(f"[Step 1] Header detected at pandas row {best_header_row} (Excel row {best_header_row + 1})")
        
        # Step 2: Find first real data row after header (control row filtering)
        # Primary key patterns for detection
        subject_id_patterns = [
            r'^[A-Z]{2,4}-\d+',  # FDC-005, SITE-001
            r'^SITE-', r'^SUBJ', r'^PAT', r'^CID',
            r'^\d{3,}.*-?\d+',   # Numeric IDs like 10134-001
            r'^[A-Z]\d{5,}',     # Single letter prefix with digits
        ]
        import re
        subject_pattern_re = re.compile('|'.join(subject_id_patterns), re.IGNORECASE)
        
        data_start = None
        control_row_indices = []
        
        logger.info(f"[Step 2] Scanning rows after header for control row filtering...")
        
        for row_idx in range(best_header_row + 1, min(30, len(df_preview))):
            row = df_preview.iloc[row_idx]
            row_values = [str(v) for v in row.values if pd.notna(v)]
            row_text = " ".join(row_values)
            
            # Skip completely empty rows
            if not row_text.strip():
                logger.info(f"  Row {row_idx}: Empty, skipping")
                continue
            
            # Feature 2a: Keyword interception - check first few cells for control keywords
            first_cells = [str(row.iloc[i]) if i < len(row) else "" for i in range(min(3, len(row)))]
            first_cells_text = " ".join(first_cells)
            
            control_detected = False
            for keyword in METADATA_KEYWORDS:
                if keyword in first_cells_text:
                    control_detected = True
                    control_row_indices.append(row_idx)
                    logger.info(f"  Row {row_idx}: CONTROL (keyword '{keyword}' in first cells: {first_cells_text[:50]})")
                    break
            
            if control_detected:
                continue
            
            # Feature 2b: Repetition rate check
            # Count repeated values vs unique values
            non_empty_values = [v.strip() for v in row_values if v.strip()]
            if len(non_empty_values) >= 3:
                unique_values = set(non_empty_values)
                # If 60%+ values are the same, it's likely a control row
                max_repeat = max(non_empty_values.count(v) for v in unique_values) if unique_values else 0
                repeat_ratio = max_repeat / len(non_empty_values) if non_empty_values else 0
                
                if repeat_ratio >= 0.6:
                    control_detected = True
                    control_row_indices.append(row_idx)
                    logger.info(f"  Row {row_idx}: CONTROL (high repetition: {repeat_ratio:.1%}, values: {non_empty_values[:5]})")
                    continue
            
            # Feature 2c: Null value rate check
            null_count = sum(1 for v in row.values if pd.isna(v) or str(v).strip() == '')
            null_ratio = null_count / len(row.values) if len(row.values) > 0 else 1.0
            
            if null_ratio >= 0.8:  # 80%+ null
                control_detected = True
                control_row_indices.append(row_idx)
                logger.info(f"  Row {row_idx}: CONTROL (high null ratio: {null_ratio:.1%})")
                continue
            
            # Step 3: Primary key format dynamic anchoring
            # Check if first column matches subject ID pattern
            first_col_value = str(row.iloc[0]) if len(row) > 0 else ""
            
            if subject_pattern_re.match(first_col_value.strip()):
                data_start = row_idx
                logger.info(f"[Step 3] PRIMARY KEY DETECTED at row {row_idx}: '{first_col_value}' matches subject ID pattern")
                break
            else:
                # Not a subject ID row but also not control - might be another metadata row
                logger.info(f"  Row {row_idx}: Potential data row but first cell '{first_col_value}' doesn't match subject pattern, skipping")
                continue
        
        # Fallback: if no subject pattern found, use first non-control row
        if data_start is None:
            for row_idx in range(best_header_row + 1, min(30, len(df_preview))):
                if row_idx not in control_row_indices:
                    row = df_preview.iloc[row_idx]
                    row_values = [str(v) for v in row.values if pd.notna(v)]
                    if row_values:
                        data_start = row_idx
                        first_cell = str(row.iloc[0]) if len(row) > 0 else ""
                        logger.info(f"[Fallback] Using first non-control row {row_idx} (first cell: '{first_cell}')")
                        break
        
        self.data_start_row = data_start if data_start is not None else best_header_row + 1
        
        logger.info(f"[Final] Header at pandas row {self.header_row} (Excel row {self.header_row + 1})")
        logger.info(f"[Final] Data starts at pandas row {self.data_start_row} (Excel row {self.data_start_row + 1})")
        logger.info(f"[Final] Control rows filtered: {control_row_indices}")
    
    def _read_file_with_structure(self) -> pd.DataFrame:
        """Read file using detected structure.
        
        Returns:
            DataFrame with proper column names and data rows.
        """
        logger.info(f"Reading file with header_row={self.header_row}, data_start={self.data_start_row}")
        
        ext = self.file_path.suffix.lower()
        
        if ext in ('.xlsx', '.xls'):
            df = pd.read_excel(self.file_path, header=self.header_row)
        elif ext == '.csv':
            df = pd.read_csv(
                self.file_path, 
                header=self.header_row, 
                encoding='utf-8',
                on_bad_lines='skip'
            )
        else:
            df = pd.read_csv(
                self.file_path, 
                header=self.header_row, 
                encoding='utf-8',
                on_bad_lines='skip'
            )
        
        # Calculate rows to skip after header to reach data_start_row
        rows_to_skip = self.data_start_row - self.header_row
        
        # Skip to data rows
        if rows_to_skip > 0 and len(df) > rows_to_skip:
            df = df.iloc[rows_to_skip:]
        
        # Clean up column names
        df.columns = [str(col).strip() if pd.notna(col) else f"col_{i}" 
                      for i, col in enumerate(df.columns)]
        
        # Remove unnamed/empty columns
        df = df.loc[:, ~df.columns.str.match(r"^(col_\d+|Unnamed:\s*\d+|nan)$", flags=re.IGNORECASE)]
        
        # Drop all-NaN rows
        df = df.dropna(how='all')
        
        logger.info(f"Read {len(df)} data rows, columns: {list(df.columns)}")
        return df
    
    def _build_fuzzy_column_mapping(self) -> Dict[str, Dict[str, str]]:
        """Build fuzzy column mapping using semantic matching.
        
        Returns:
            Dictionary mapping standard column names to detected column names:
            {
                'subject_id': '患者研究编号',
                'visit_date': '检查日期',
                'lab_tests': {
                    'WBC': {'value': '白细胞结果', 'unit': '白细胞单位'},
                    ...
                }
            }
        """
        logger.info("Building fuzzy column mapping...")
        
        mapping: Dict[str, Any] = {
            'subject_id': {},
            'visit_date': {},
            'lab_tests': {},
        }
        
        # Core column matching with similarity
        core_columns = {
            'subject_id': ['患者研究编号', '受试者编号', '患者编号', 'Subject_ID', 'SubjectID', 'subject_id', 'SUBJID', '受试者ID'],
            'visit_date': ['检查日期', '访视日期', '检验日期', 'Visit_Date', 'visit_date', 'Date', '日期'],
        }
        
        for col_name, variants in core_columns.items():
            for col in self.dataframe.columns:
                col_lower = str(col).lower()
                for variant in variants:
                    # Check exact substring match first, then fuzzy match
                    if variant.lower() in col_lower or self._fuzzy_match(col_lower, variant.lower()) >= 0.8:
                        mapping[col_name][variant] = col
                        break
        
        # Lab test column matching with fuzzy logic
        for test_code, keywords in TEST_CODE_KEYWORDS.items():
            mapping['lab_tests'][test_code] = {'value': None, 'unit': None}
            
            for col in self.dataframe.columns:
                col_str = str(col)
                col_lower = col_str.lower()
                
                # Check if column matches test code keywords (fuzzy: contains keyword OR similar)
                matches_test = False
                for kw in keywords:
                    kw_lower = kw.lower()
                    # Substring match or fuzzy similarity >= 0.6
                    if kw_lower in col_lower or self._fuzzy_match(col_lower, kw_lower) >= 0.6:
                        matches_test = True
                        break
                
                if matches_test:
                    # Determine if this is a value column or unit column
                    is_unit = any(uw in col_lower for uw in ['单位', 'unit'])
                    is_significance = any(sw in col_lower for sw in ['意义', 'significance', '参考', 'range', 'normal'])
                    
                    if is_unit:
                        mapping['lab_tests'][test_code]['unit'] = col
                    elif not is_significance:
                        # This should be the value column
                        if mapping['lab_tests'][test_code]['value'] is None:
                            mapping['lab_tests'][test_code]['value'] = col
        
        logger.info(f"Column mapping built: {mapping}")
        return mapping
    
    def _fuzzy_match(self, text1: str, text2: str) -> float:
        """Calculate fuzzy match similarity score using SequenceMatcher.
        
        Args:
            text1: First text string.
            text2: Second text string.
            
        Returns:
            Similarity score between 0 and 1.
        """
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _transform_wide_to_long(self, column_mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform wide-table format to standard long format with lab_values.
        
        Args:
            column_mapping: Mapping of column names from fuzzy matching.
            
        Returns:
            List of records with Subject_ID, Visit_Date, and lab_values.
        """
        records: List[Dict[str, Any]] = []
        
        # Get subject and date columns
        subject_col = self._get_best_match(column_mapping.get('subject_id', {}))
        date_col = self._get_best_match(column_mapping.get('visit_date', {}))
        
        logger.info(f"Using subject column: {subject_col}, date column: {date_col}")
        
        for idx, row in self.dataframe.iterrows():
            try:
                # Extract subject and visit information
                subject_id = self._safe_get_value(row, subject_col) if subject_col else None
                
                if not subject_id or pd.isna(subject_id):
                    continue
                
                # Build lab values from mapped columns
                lab_values: List[Dict[str, Any]] = []
                
                for test_code, col_info in column_mapping.get('lab_tests', {}).items():
                    value_col = col_info.get('value')
                    unit_col = col_info.get('unit')
                    
                    if value_col and value_col in self.dataframe.columns:
                        value = self._safe_get_numeric_value(row, value_col)
                        if value is not None:
                            unit = self._safe_get_value(row, unit_col) if unit_col else self._get_unit_for_test(test_code)
                            if unit is None:
                                unit = self._get_unit_for_test(test_code)
                            
                            lab_entry = {
                                "test_code": test_code,
                                "test_name": test_code,
                                "value": value,
                                "unit": str(unit).strip() if unit else "",
                            }
                            lab_values.append(lab_entry)
                
                # Create record
                record: Dict[str, Any] = {
                    "Subject_ID": str(subject_id).strip(),
                }
                
                # Add visit date if found
                visit_date = self._safe_get_value(row, date_col) if date_col else None
                if visit_date and not pd.isna(visit_date):
                    record["Visit_Date"] = str(visit_date)
                
                if lab_values:
                    record["lab_values"] = lab_values
                
                records.append(record)
                
            except Exception as e:
                logger.warning(f"Error processing row {idx}: {e}")
                continue
        
        return records
    
    def _get_best_match(self, mapping_dict: Dict[str, str]) -> Optional[str]:
        """Get the best non-null match from a mapping dictionary.
        
        Args:
            mapping_dict: Dictionary of possible column matches.
            
        Returns:
            Best matching column name or None.
        """
        if not mapping_dict:
            return None
        for col in mapping_dict.values():
            if col:
                return col
        return None
    
    def _safe_get_value(self, row: pd.Series, column: Optional[str]) -> Any:
        """Safely get a value from a DataFrame row.
        
        Args:
            row: DataFrame row.
            column: Column name.
            
        Returns:
            Value or None if not available.
        """
        if not column or column not in row.index:
            return None
        val = row[column]
        return None if pd.isna(val) else val
    
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
    
    def add_lab_test_mapping(self, test_code: str, keywords: List[str], unit_keywords: Optional[List[str]] = None) -> None:
        """Add custom lab test mapping for fuzzy matching.
        
        Args:
            test_code: Standard test code (e.g., "WBC").
            keywords: Keywords to match column names (e.g., ["白细胞", "WBC"]).
            unit_keywords: Optional keywords for unit columns.
        """
        if test_code not in TEST_CODE_KEYWORDS:
            TEST_CODE_KEYWORDS[test_code] = keywords
        else:
            TEST_CODE_KEYWORDS[test_code].extend(keywords)
        
        logger.info(f"Added custom mapping for {test_code}: {keywords}")
    
    def get_parsed_data(self) -> List[Dict[str, Any]]:
        """Get the parsed data after calling parse_lab_data().
        
        Returns:
            List of parsed records or empty list if not yet parsed.
        """
        return self._parsed_data