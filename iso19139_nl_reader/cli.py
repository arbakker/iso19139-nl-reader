import json
import sys
from .metadata_record import MetadataRecord
import click


@click.group()
def cli():
    pass


@cli.command(name="read")
@click.argument(
    'md-file', 
    type=click.File('r'),
    default=sys.stdin
    )
def read_metadata_command(md_file):
    service_record = MetadataRecord(md_file)
    result = service_record.convert_to_dictionary()
    print(json.dumps(result, indent=4))


@cli.command(name="validate")
@click.argument(
    'md-file', 
    type=click.File('r'),
    default=sys.stdin
    )
def validate_metadata_command(md_file):
    service_record = MetadataRecord(md_file)
    result = service_record.schema_validation_errors()
    if result:
        print(result)
        exit(1)
    else:
        print("metadata record is valid")


if __name__ == "__main__":
    cli()
