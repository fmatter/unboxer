import logging
import sys
import time
from pathlib import Path

import pandas as pd
import pybtex
from cldf_ldd import add_columns, add_keys
from cldf_ldd.components import tables as component_tables
from cldf_ldd.components import tables as ldd_tables
from cldfbench import CLDFSpec
from cldfbench.cldf import CLDFWriter
from humidifier import humidify
from pycldf.dataset import MD_SUFFIX
from pycldf.sources import Source
from pycldf.util import metadata2markdown, pkg_path
from tqdm import tqdm
from writio import load

from unboxer.helpers import _slugify

log = logging.getLogger(__name__)


def _splitcol(
    df, col, sep="; "
):  # split a column (like 'Gloss') by a separator (like ' ')
    df[col] = df[col].apply(lambda x: x.split(sep))


def create_dataset(
    tables, spec, conf, output_dir, cldf_name="cldf", languages=None, **kwargs
):
    with CLDFWriter(spec) as writer:
        # mapping e.g. "examples.csv" to e.g. "ExampleTable", to use add_component("ExampleTable") later
        cldf_names = {}
        for component_filename in pkg_path(
            "components"
        ).iterdir():  # .../.../pycldf/components/Example-Metadata.json
            component = load(component_filename)  # {"url": "examples.csv", ...}
            cldf_names[component["url"]] = str(component_filename.name).replace(
                MD_SUFFIX, ""
            )  # "examples.csv": Example

        # mapping columns to required table transformation workflows
        table_actions = {
            "Source": lambda x: _splitcol(x, "Source"),
            "Gloss": lambda x: _splitcol(x, "Gloss", sep=" "),
            "Analyzed_Word": lambda x: _splitcol(x, "Analyzed_Word", sep=" "),
            "Segments": lambda x: _splitcol(x, "Segments", sep=" "),
            "Alignment": lambda x: _splitcol(x, "Alignment", sep=" "),
        }

        additional_columns = {
            "Sense_IDs": {
                "target": "senses.csv",
                "metadata": {
                    "datatype": "string",
                    "separator": " ; ",
                    "name": "Sense_IDs",
                },
            },
        }

        for table in ldd_tables:  # morphs.csv
            if table["url"] in tables and len(tables[table["url"]]) > 0:
                writer.cldf.add_component(table)  # add json metadata for MorphTable
                for rec in tables.pop(table["url"]).to_dict(
                    "records"
                ):  # remove processed cldf-ldd files, iterate rows
                    writer.objects[table["url"]].append(rec)  # write row to CLDF

        # now only native CLDF components should be left over
        for key, df in tables.items():  # examples.csv
            if key not in cldf_names:
                continue
            if len(df) == 0:
                continue
            if (key, spec.module) not in [
                ("entries.csv", "Dictionary"),
                ("senses.csv", "Dictionary"),
                ("forms.csv", "Wordlist"),
            ]:
                writer.cldf.add_component(
                    cldf_names[key]
                )  # add json metadata for "ExampleTable"
            else:
                log.debug(f"Skipping table {key} for module {spec.module}")

            for colname in df.columns:
                if colname in additional_columns:
                    writer.cldf.add_columns(
                        key, additional_columns[colname]["metadata"]
                    )
                    writer.cldf.add_foreign_key(
                        key,
                        colname,
                        additional_columns[colname]["target"],
                        additional_columns[colname].get("target_id", "ID"),
                    )

            for col in df.columns:  # apply mapped methods to dataframe
                if col in table_actions:  # Gloss
                    table_actions[col](df)  # splitcol(df, "Gloss", sep=" ")
            if key == "examples.csv":
                writer.cldf.add_columns(
                    "ExampleTable",
                    {
                        "name": "Source",
                        "required": False,
                        "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#source",
                        "datatype": {"base": "string"},
                        "separator": ";",
                    },
                )
            for rec in df.to_dict("records"):
                writer.objects[key].append(rec)

        # add_columns(writer.cldf)  # add cldf-ldd columns to native tables
        add_keys(writer.cldf)  # write cldf-ldd specific keys

        if Path("sources.bib").is_file():  # add sources
            bib = pybtex.database.parse_file(
                "sources.bib",
            )
            writer.cldf.add_sources(
                *[Source.from_entry(k, e) for k, e in bib.entries.items()]
            )

        ds = writer.cldf
    return ds


def create_cldf(tables, conf, module, output_dir, cldf_name="cldf", **kwargs):
    if "Language_ID" not in conf:
        raise TypeError("Please specify a Language_ID in your configuration")

    spec = CLDFSpec(
        dir=output_dir / cldf_name, module="Generic", metadata_fname="metadata.json"
    )
    if module == "Dictionary":
        spec = CLDFSpec(
            dir=output_dir / cldf_name,
            module="Dictionary",
            metadata_fname="metadata.json",
        )
    elif module == "Wordlist":
        spec = CLDFSpec(
            dir=output_dir / cldf_name,
            module="Wordlist",
            metadata_fname="metadata.json",
        )

    tick = time.perf_counter()
    log.info("Creating CLDF dataset")
    ds = create_dataset(
        tables=tables,
        conf=conf,
        spec=spec,
        output_dir=output_dir,
        cldf_name=cldf_name,
        **kwargs,
    )
    tock = time.perf_counter()
    log.info(
        f"Created dataset {ds.directory.resolve()}/{ds.filename} in {tock - tick:0.4f} seconds"
    )

    tick = time.perf_counter()
    log.info("Validating...")
    ds.validate(log=log)
    tock = time.perf_counter()
    log.info(f"Validated in {tock - tick:0.4f} seconds")

    readme = metadata2markdown(ds, ds.directory)
    with open(ds.directory / "README.md", "w", encoding="utf-8") as f:
        f.write(readme)


def _extract_meanings(meanings):
    for x in meanings:
        for y in x.split("; "):
            yield y


def _replace_meanings(label, meaning_dict):
    return [meaning_dict[x] for x in label.split("; ")]


def get_lg(lg_id, languages=None):
    try:
        import pyglottolog  # pylint: disable=import-outside-toplevel
        from cldfbench.catalogs import (
            Glottolog,
        )  # pylint: disable=import-outside-toplevel
    except ImportError:
        if languages is not None:
            lgs = load(languages, mode="csv2dict")
            if lg_id not in lgs:
                log.error(
                    f"The specified language ID [{lg_id}] was not found in the file {languages}"
                )
                sys.exit()
            return lgs[lg_id]
        else:
            log.error(
                "Install cldfbench and pyglottolog and run cldfbench catconfig to download the glottolog catalog. Alternatively, you can specify a languages.csv file."
            )
            sys.exit()
    glottolog = pyglottolog.Glottolog(Glottolog.from_config().repo.working_dir)
    languoid = glottolog.languoid(lg_id)
    return {
        "ID": languoid.id,
        "Name": languoid.name,
        "Latitude": languoid.latitude,
        "Longitude": languoid.longitude,
    }


def get_lexical_data(lexicon, drop_variants=False, sep="; "):
    lexicon["Form"] = lexicon["Headword"]
    # lexicon["Meaning"] = lexicon["Meaning"].apply(lambda x: x.split(sep))
    meanings = list(_extract_meanings(list(lexicon["Meaning"])))
    meaning_dict = {
        meaning: _slugify(meaning, "meanings", ids=False) for meaning in meanings
    }
    meanings = [{"ID": y, "Name": x} for x, y in meaning_dict.items()]
    meanings = pd.DataFrame.from_dict(meanings)
    meanings = meanings[meanings["Name"] != ""]
    lexicon["Parameter_ID"] = lexicon["Meaning"].apply(
        lambda x: _replace_meanings(x, meaning_dict)
    )
    lexicon = lexicon.explode("Parameter_ID", ignore_index=True)
    if drop_variants:
        lexicon = lexicon.drop_duplicates("Parameter_ID")
    lexicon["index"] = lexicon.index.map(str)
    lexicon["ID"] = lexicon["ID"] + "-" + lexicon["index"]
    return lexicon, meanings


def get_senses(lexicon):
    senses = lexicon.copy()
    senses["Entry_ID"] = senses["ID"]
    senses["ID"] = senses.apply(
        lambda x: humidify(x["Meaning"], key="senses", unique=True), axis=1
    )
    senses["Description"] = senses["Meaning"]
    return senses


def create_dictionary_cldf(
    lexicon, conf, output_dir, languages=None, examples=None, **kwargs
):
    tables = {}
    tables["entries.csv"] = lexicon
    tables["senses.csv"] = get_senses(lexicon)

    if isinstance(examples, pd.DataFrame):
        tables["examples.csv"] = examples
        if "Example_IDs" in tables["senses.csv"].columns:
            sense_ex_dict = dict(
                zip(tables["senses.csv"]["ID"], tables["senses.csv"]["Example_IDs"])
            )
            ex_sense_dict = {}
            for sense, exs in sense_ex_dict.items():
                if exs:
                    for exid in exs.split(" ; "):
                        ex_sense_dict.setdefault(exid, [])
                        ex_sense_dict[exid].append(sense)
            examples["Sense_IDs"] = examples.apply(
                lambda x: ex_sense_dict.get(x["ID"], []), axis=1
            )

    if languages:
        tables["languages.csv"] = load(languages)

    create_cldf(
        tables=tables, conf=conf, module="Dictionary", output_dir=output_dir, **kwargs
    )


def create_wordlist_cldf(
    lexicon, conf, output_dir, languages=None, audio=None, **kwargs
):
    lexicon, meanings = get_lexical_data(lexicon, **kwargs)
    tables = {"parameters.csv": meanings, "forms.csv": lexicon}
    if languages:
        tables["languages.csv"] = load(languages)
    create_cldf(tables=tables, conf=conf, module="Wordlist", output_dir=output_dir)
