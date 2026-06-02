"""Transform command module."""

from typing import Any

from medical_cli.core import data_transformer


def add_parser(subparsers: Any) -> None:
    """Add transform command parser."""
    parser = subparsers.add_parser(
        "transform",
        help="Transform clinical data",
        description="Apply transformations to clinical data records",
    )
    parser.add_argument(
        "input",
        type=str,
        help="Input file path",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="transformed_data.json",
        help="Output file path (default: transformed_data.json)",
    )
    parser.add_argument(
        "--rules",
        "-r",
        type=str,
        help="Path to transformation rules file",
    )
    parser.add_argument(
        "--normalize",
        action="store_true",
        help="Normalize data values",
    )


def execute(args: Any) -> int:
    """Execute the transform command."""
    print(f"Transforming data from: {args.input}")
    print(f"Output: {args.output}")
    
    if args.rules:
        print(f"Using rules: {args.rules}")
    if args.normalize:
        print("Normalizing data values")
    
    # Placeholder for actual implementation
    return data_transformer.transform(
        args.input,
        args.output,
        rules_path=args.rules,
        normalize=args.normalize,
    )