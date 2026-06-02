# 🧬 CDM Data CLI (Clinical Data Management)

[![CI](https://github.com/AJDJFR/cdm-data-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/AJDJFR/cdm-data-cli/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An open-source, AI-ready foundational infrastructure designed for **Clinical Data Management (CDM)** in multi-center Randomized Controlled Trials (RCTs) and Investigator-Initiated Trials (IITs).

## 💡 The Ecosystem Problem

In multi-center clinical trials, integrating Local Lab results into Electronic Data Capture (EDC) systems poses massive challenges:
1. **Unstandardized Metrics:** Different sites use conflicting reference ranges and units (e.g., `mg/dL` vs. `mmol/L`).
2. **PHI Leakage Risks:** Raw lab exports often contain residual Protected Health Information (PHI) like patient names, IDs, or contact details, posing severe compliance risks (HIPAA/GCP).
3. **Manual Bottlenecks:** Data managers spend hundreds of hours manually verifying out-of-range clinical endpoints.

**CDM Data CLI** provides a fast, terminal-native pipeline to sanitize, validate, and normalize clinical datasets automatically.

## 🚀 Core Features

- 🛡️ **Automated PHI Sanitization:** Regex and pattern-matching engine to detect and mask Names, IDs, Emails, and Phone Numbers automatically.
- 🔬 **Clinical Validation Engine:** Built with strict `pydantic` schemas to validate Subject IDs, Demographics, and Visit Dates.
- 🩸 **Lab Value Normalization:** Pre-configured with reference ranges for vital labs (WBC, RBC, HGB, PLT, ALT, AST, K, NA, etc.) to flag abnormal deviations dynamically.
- 📊 **Audit-Ready Reporting:** Generates comprehensive JSON validation logs for compliance tracing.

## 🛠️ Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the lab data validation and PHI sanitization pipeline
medical-cli validate labs -i /path/to/local_lab_data.xlsx -o report.json --verbose
```

## 🏗️ Architecture

Built for scalability and integration into larger clinical data pipelines:

- **Click Framework:** For robust command-line interfacing.
- **Pydantic V2:** For high-performance, strict data validation.
- **Openpyxl/Pandas:** For native handling of hospital-level Excel exports.

## 🤝 Contributing

Contributions from Data Managers, CRAs, and clinical software engineers are highly encouraged. Please ensure all pull requests pass the CI pipeline (pytest & ruff linting) before requesting a review.

Built to accelerate clinical research and ensure data integrity.