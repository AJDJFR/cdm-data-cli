"""Main CLI entry point for medical-cli.

This CLI uses click for command handling, providing commands for extracting,
transforming, validating, and exporting clinical data.
"""

import sys
from typing import Optional

import click

from medical_cli.commands import extract, transform, export
from medical_cli.commands.validate import validate_group


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(version="0.1.0", prog_name="medical-cli")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose output with detailed logging",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Medical CLI - A tool for processing medical clinical data.
    
    This CLI provides commands for extracting, transforming, validating,
    and exporting clinical trial data with built-in PHI sanitization.
    
    \b
    Quick Start:
        medical-cli extract -i data.csv -o extracted.json
        medical-cli validate labs -i lab_results.xlsx
        medical-cli transform -i data.json -o transformed.json
    
    \b
    For more information on any command, run:
        medical-cli <command> --help
    """
    ctx.obj = {"verbose": verbose}


# Register command groups
# Only register commands that have been implemented with click
if hasattr(extract, "extract_group") and extract.extract_group is not None:
    cli.add_command(extract.extract_group)

if hasattr(transform, "transform_group") and transform.transform_group is not None:
    cli.add_command(transform.transform_group)

# Register validate command (fully implemented with click)
cli.add_command(validate_group)

if hasattr(export, "export_group") and export.export_group is not None:
    cli.add_command(export.export_group)


def main(argv: Optional[list] = None) -> int:
    """Main entry point.
    
    Args:
        argv: Optional list of command-line arguments.
              If None, uses sys.argv.
              
    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    try:
        cli(argv)
        return 0
    except click.Abort:
        return 1
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())