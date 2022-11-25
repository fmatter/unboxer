"""Console script for box2csv."""
import logging
import sys
from pathlib import Path
import click
from box2csv import extract_corpus
from box2csv.helpers import load_config
from box2csv.helpers import load_default_config


log = logging.getLogger(__name__)


@click.group()
def main():
    pass  # pragma: no cover


@click.argument(
    "filename",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "-o",
    "--output",
    "output_dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Output directory",
)
@click.option(
    "-f",
    "--format",
    "data_format",
    type=click.Choice(["toolbox", "shoebox"], case_sensitive=False),
    default="toolbox",
    show_default=True,
    help="The format of the database you are processing",
)
@click.option(
    "-d", "--cldf", "cldf", default=False, is_flag=True, help="Create a CLDF dataset"
)
@click.option(
    "-c",
    "--conf",
    "config_file",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to a yaml configuration file",
)
@main.command()
def corpus(filename, data_format, config_file, cldf, output_dir):
    print(filename, config_file, cldf, output_dir)
    if config_file:
        conf = load_config(config_file, data_format)
    else:
        conf = load_default_config(data_format)
    if cldf and "Language_ID" not in conf:
        conf["Language_ID"] = click.prompt(
            "There is no Language_ID specified in the configuration, please enter manually",
            type=str,
        )
    extract_corpus(filename, output_dir=output_dir, conf=conf, cldf=cldf)


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
