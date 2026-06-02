# Medical CLI

A command-line tool for processing and managing medical clinical data.

## Overview

Medical CLI provides a set of commands for extracting, transforming, validating, and exporting clinical data. It is designed for healthcare professionals, data analysts, and developers who need to work with medical datasets.

## Features

- **Extract**: Import clinical data from various source formats (JSON, CSV, XML)
- **Transform**: Apply transformations and normalizations to data records
- **Validate**: Verify data against schemas and business rules
- **Export**: Export processed data to multiple output formats

## Requirements

- Python 3.9+
- pip (package installer)

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/example/medical-cli.git
cd medical-cli

# Install in development mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

### Using pip

```bash
pip install medical-cli
```

## Quick Start

```bash
# Extract data from a file
medical-cli extract ./data/clinical_records.json -o extracted.json

# Transform data with normalization
medical-cli transform ./extracted.json --normalize -o transformed.json

# Validate against a schema
medical-cli validate ./transformed.json --schema ./schemas/clinical.json

# Export to different formats
medical-cli export ./transformed.json -f csv -o output.csv
```

## Command Reference

### extract

Extract clinical data from source files.

```bash
medical-cli extract <INPUT> [OPTIONS]

Options:
  -o, --output PATH    Output file path (default: extracted_data.json)
  -f, --format FORMAT  Output format: json, csv, xml (default: json)
  --dry-run            Preview extraction without writing output
```

**Examples:**

```bash
# Basic extraction
medical-cli extract ./records.json -o data.json

# Extract to CSV
medical-cli extract ./records.json -f csv -o data.csv

# Preview without writing
medical-cli extract ./records.json --dry-run
```

### transform

Apply transformations to clinical data records.

```bash
medical-cli transform <INPUT> [OPTIONS]

Options:
  -o, --output PATH     Output file path (default: transformed_data.json)
  -r, --rules PATH      Path to transformation rules file
  --normalize           Normalize data values
```

**Examples:**

```bash
# Basic transformation
medical-cli transform ./input.json -o output.json

# Transform with custom rules
medical-cli transform ./input.json -r ./rules.json -o output.json

# Transform with normalization
medical-cli transform ./input.json --normalize -o output.json
```

### validate

Validate clinical data against defined schemas and rules.

```bash
medical-cli validate <INPUT> [OPTIONS]

Options:
  -s, --schema PATH     Path to validation schema file
  --strict              Enable strict validation mode
  --report PATH         Path to save validation report
```

**Examples:**

```bash
# Basic validation
medical-cli validate ./data.json

# Validate with schema
medical-cli validate ./data.json -s ./schema.json

# Strict validation with report
medical-cli validate ./data.json --strict --report validation_report.json
```

### export

Export clinical data to various formats.

```bash
medical-cli export <INPUT> [OPTIONS]

Options:
  -o, --output PATH     Output file path
  -f, --format FORMAT   Export format: json, csv, xml, xlsx (default: json)
  --compress            Compress output file
```

**Examples:**

```bash
# Export to JSON
medical-cli export ./data.json -f json -o output.json

# Export to CSV
medical-cli export ./data.json -f csv -o output.csv

# Export to Excel
medical-cli export ./data.json -f xlsx -o output.xlsx

# Compressed export
medical-cli export ./data.json --compress -o output.json.gz
```

## Configuration

Medical CLI can be configured using a configuration file:

```yaml
# .medical-cli.yaml
output_dir: ./output
log_level: INFO
default_format: json
strict_validation: false
```

### Global Options

| Option | Description |
|--------|-------------|
| `--version` | Show version information |
| `-v, --verbose` | Enable verbose output |
| `--config PATH` | Path to configuration file |

## Project Structure

```
medical-cli/
├── src/
│   └── medical_cli/
│       ├── __init__.py
│       ├── cli.py              # Main CLI entry point
│       ├── commands/            # Command implementations
│       │   ├── extract.py
│       │   ├── transform.py
│       │   ├── validate.py
│       │   └── export.py
│       ├── core/               # Core processing modules
│       │   ├── data_extractor.py
│       │   ├── data_transformer.py
│       │   ├── data_validator.py
│       │   └── data_exporter.py
│       └── utils/              # Utility modules
│           ├── logger.py
│           └── file_helpers.py
├── tests/                      # Test suite
├── docs/                       # Documentation
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Development

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements-dev.txt

# Install package in development mode
pip install -e .
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=medical_cli --cov-report=term-missing

# Run specific test file
pytest tests/test_extractor.py
```

### Code Quality

```bash
# Format code
black src/

# Sort imports
isort src/

# Lint code
ruff check src/

# Type checking
mypy src/
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and feature requests, please use the [GitHub Issue Tracker](https://github.com/example/medical-cli/issues).

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

**Note**: This tool processes sensitive medical data. Ensure compliance with applicable healthcare regulations (HIPAA, GDPR, etc.) and implement appropriate security measures when handling patient information.