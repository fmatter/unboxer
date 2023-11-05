"""Console script for unboxer."""
import logging
import sys
from pathlib import Path

import click
from writio import load

from unboxer import extract_corpus, extract_lexicon
from unboxer.helpers import load_config, load_default_config

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
                    type=click.Path(path_type=Path),
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
                click.core.Option(
                    ("-a", "--audio", "audio"),
                    type=click.Path(exists=True, path_type=Path),
                    default=None,
                    show_default=True,
                    help="A directory containing your audio files.",
                ),
                click.core.Option(
                    ("-L", "--languages", "languages"),
                    type=click.Path(exists=True, path_type=Path),
                    default=None,
                    show_default=True,
                    help="A CSV file containing language data.",
                ),
            ]
        )


@click.argument(
    "filename",
    type=click.Path(exists=True, path_type=Path),
)
@main.command(cls=ConvertCommand)
def wordlist(filename, data_format, config_file, cldf, output_dir, audio, languages):
    if not output_dir.is_dir():
        output_dir.mkdir(exist_ok=True, parents=True)
    if config_file:
        conf = load_config(config_file, data_format)
    else:
        conf = load_default_config(data_format)
    if cldf and "Language_ID" not in conf:
        conf["Language_ID"] = click.prompt(
            "There is no Language_ID specified in the configuration, please enter manually",
            type=str,
        )
    extract_lexicon(
        filename,
        output_dir=output_dir,
        conf=conf,
        cldf="wordlist" if cldf else None,
        audio=audio,
        languages=languages,
    )


@click.argument(
    "filename",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "-e",
    "--examples",
    "examples",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    show_default=True,
    help="An examples (corpus) database file",
)
@main.command(cls=ConvertCommand)
def dictionary(
    filename, data_format, config_file, cldf, output_dir, audio, languages, examples
):
    if not output_dir.is_dir():
        output_dir.mkdir(exist_ok=True, parents=True)
    if config_file:
        conf = load_config(config_file, data_format)
    else:
        conf = load_default_config(data_format)
    if cldf and "Language_ID" not in conf:
        conf["Language_ID"] = click.prompt(
            "There is no Language_ID specified in the configuration, please enter manually",
            type=str,
        )
    extract_lexicon(
        filename,
        output_dir=output_dir,
        conf=conf,
        cldf="dictionary" if cldf else None,
        audio=audio,
        languages=languages,
        examples=examples,
    )


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
@click.option(
    "-i",
    "--inflection",
    "inflection",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    show_default=True,
    nargs=3,
    help="1. A CSV table of inflection categories.\n2. A CSV table of inflection values.\n3. A .yaml file with a dict mapping morph IDs to inflectional values",
)
@main.command(cls=ConvertCommand)
def corpus(
    filename,
    data_format,
    config_file,
    cldf,
    output_dir,
    inflection,
    languages,
    **kwargs
):
    if not output_dir.is_dir():
        output_dir.mkdir(exist_ok=True, parents=True)
    if config_file:
        conf = load_config(config_file, data_format)
    else:
        conf = load_default_config(data_format)
    if cldf and "Language_ID" not in conf:
        conf["Language_ID"] = click.prompt(
            "There is no Language_ID specified in the configuration, please enter manually",
            type=str,
        )
    infl_dict = {}
    if inflection:
        for k, x in zip(["infl_cats", "infl_vals", "infl_morphemes"], inflection):
            infl_dict[k] = load(x, index_col="ID")
    extract_corpus(
        filename,
        conf=conf,
        cldf=cldf,
        output_dir=output_dir,
        inflection=infl_dict,
        languages=languages,
        **kwargs
    )


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
