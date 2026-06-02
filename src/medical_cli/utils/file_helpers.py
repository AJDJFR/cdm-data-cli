"""File handling utilities."""

import json
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List


def read_json(file_path: str) -> Any:
    """
    Read JSON file.
    
    Args:
        file_path: Path to JSON file
    
    Returns:
        Parsed JSON data
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(data: Any, file_path: str, indent: int = 2) -> None:
    """
    Write data to JSON file.
    
    Args:
        data: Data to write
        file_path: Output file path
        indent: JSON indentation level
    """
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def read_csv(file_path: str) -> List[Dict[str, str]]:
    """
    Read CSV file.
    
    Args:
        file_path: Path to CSV file
    
    Returns:
        List of row dictionaries
    """
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_csv(data: List[Dict[str, Any]], file_path: str) -> None:
    """
    Write data to CSV file.
    
    Args:
        data: List of row dictionaries
        file_path: Output file path
    """
    if not data:
        return
    
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)


def read_xml(file_path: str) -> ET.Element:
    """
    Read XML file.
    
    Args:
        file_path: Path to XML file
    
    Returns:
        Root XML element
    """
    return ET.parse(file_path).getroot()


def write_xml(data: Any, file_path: str, root_tag: str = "root") -> None:
    """
    Write data to XML file.
    
    Args:
        data: Data to write
        file_path: Output file path
        root_tag: Root element tag name
    """
    root = ET.Element(root_tag)
    # TODO: Implement proper XML serialization
    tree = ET.ElementTree(root)
    tree.write(file_path, encoding="utf-8", xml_declaration=True)


def ensure_dir(path: str) -> None:
    """
    Ensure directory exists.
    
    Args:
        path: Directory path
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def get_file_extension(path: str) -> str:
    """
    Get file extension.
    
    Args:
        path: File path
    
    Returns:
        File extension (lowercase, without dot)
    """
    return Path(path).suffix.lstrip(".").lower()