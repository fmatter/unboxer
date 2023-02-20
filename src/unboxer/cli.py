"""Console script for unboxer."""
import logging
import sys
from pathlib import Path
import click
from unboxer import extract_corpus
from unboxer import extract_lexicon
from unboxer.helpers import load_config
from unboxer.helpers import load_default_config


log = logging.getLogger(__name__)


@click.group()
def main():
    pass  # pragma: no cover


class ConvertCommand(click.Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.params.extend(
            [
                click.core.Option(
                    ("-o", "--output", "output_dir"),
                    type=click.Path(exists=True, path_type=Path),
                    default=Path("."),
                    show_default=True,
                    help="Output directory",
                ),
                click.core.Option(
                    ("-c", "--conf", "config_file"),
                    type=click.Path(exists=True, path_type=Path),
                    default=None,
                    help="Path to a yaml configuration file",
                ),
                click.core.Option(
                    ("-d", "--cldf", "cldf"),
                    default=False,
                    is_flag=True,
                    help="Create a CLDF dataset",
                ),
                click.core.Option(
                    ("-f", "--format", "data_format"),
                    type=click.Choice(["toolbox", "shoebox"], case_sensitive=False),
                    default="toolbox",
                    show_default=True,
                    help="The format of the database you are processing",
                ),
            ]
        )


@click.argument(
    "filename",
    type=click.Path(exists=True, path_type=Path),
)
@main.command(cls=ConvertCommand)
def lexicon(filename, data_format, config_file, cldf, output_dir):
    if config_file:
        conf = load_config(config_file, data_format)
    else:
        conf = load_default_config(data_format)
    if cldf and "Language_ID" not in conf:
        conf["Language_ID"] = click.prompt(
            "There is no Language_ID specified in the configuration, please enter manually",
            type=str,
        )
    extract_lexicon(filename, output_dir=output_dir, conf=conf, cldf=cldf)


@click.argument(
    "filename",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "-l",
    "--lexicon",
    "lexicon",
    default=None,
    help="Connect corpus to a lexicon",
    type=click.Path(exists=True, path_type=Path),
)
@main.command(cls=ConvertCommand)
def corpus(filename, data_format, config_file, cldf, output_dir, lexicon):
    if config_file:
        conf = load_config(config_file, data_format)
    else:
        conf = load_default_config(data_format)
    if cldf and "Language_ID" not in conf:
        conf["Language_ID"] = click.prompt(
            "There is no Language_ID specified in the configuration, please enter manually",
            type=str,
        )
    extract_corpus(
        filename, output_dir=output_dir, conf=conf, cldf=cldf, lexicon=lexicon
    )


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover