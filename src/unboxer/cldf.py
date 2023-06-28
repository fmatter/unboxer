import logging
import sys
import time
import pandas as pd
from cldf_ldd import add_keys
from cldf_ldd.components import tables as component_tables
from cldfbench import CLDFSpec
from cldfbench.cldf import CLDFWriter
from pycldf.util import metadata2markdown
from tqdm import tqdm
from unboxer.helpers import _slugify


log = logging.getLogger(__name__)


def create_dataset(tables, conf, output_dir, cldf_name="cldf"):
    table_map = {
        default: default
        for default in ["ExampleTable", "ParameterTable", "FormTable", "MediaTable"]
    }

    for component in component_tables:
        table_map[component["url"].replace(".csv", "")] = component

    def get_table_url(tablename):
        if tablename.lower() != tablename:
            return table_map[tablename]
        return table_map[tablename]["url"]

    spec = CLDFSpec(
        dir=output_dir / cldf_name, module="Generic", metadata_fname="metadata.json"
    )
    with CLDFWriter(spec) as writer:
        writer.cldf.add_component("LanguageTable")
        if "language" in conf:
            writer.objects["LanguageTable"].append(conf["language"])
        else:
            log.info(f"Retrieving data for language {conf['Language_ID']}")
            writer.objects["LanguageTable"].append(get_lg(conf["Language_ID"]))
        for table, df in tqdm(tables.items(), desc="CLDF tables"):
            if len(df) == 0:
                log.warning(f"{table} is empty")
                continue
            writer.cldf.add_component(table_map[table])
            if table in ["morphs", "morphemes"]:
                writer.cldf.remove_columns(table_map[table]["url"], "Parameter_ID")
                writer.cldf.add_columns(
                    table_map[table]["url"],
                    {
                        "name": "Parameter_ID",
                        "required": True,
                        "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#parameterReference",
                        "dc:description": f"A reference to the meaning denoted by the {table[0:-1]}.",
                        "datatype": "string",
                        "separator": "; ",
                        "dc:extent": "multivalued",
                    },
                )
            if table == "ExampleTable":
                for col in conf["aligned_fields"]:
                    df[col] = df[col].apply(lambda x: x.split("\t"))
            for rec in df.to_dict("records"):
                writer.objects[get_table_url(table)].append(rec)
        if "sources" in conf:
            writer.cldf.add_sources(*conf["sources"])

        log.info("Creating dataset")
        writer.write()
        add_keys(writer.cldf)
        return writer.cldf


def create_cldf(tables, conf, output_dir, cldf_name="cldf"):
    if "Language_ID" not in conf:
        raise TypeError("Please specify a Language_ID in your configuration")

    tick = time.perf_counter()
    log.info("Creating CLDF dataset")
    ds = create_dataset(tables, conf, output_dir, cldf_name=cldf_name)
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


def get_lg(lg_id):
    try:
        import pyglottolog  # pylint: disable=import-outside-toplevel
        from cldfbench.catalogs import (
            Glottolog,
        )  # pylint: disable=import-outside-toplevel
    except ImportError:
        log.error(
            "Install cldfbench and pyglottolog and run cldfbench catconfig to download the glottolog catalog. Alternatively, you can add a languages.csv file."
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


def get_data(lexicon, drop_variants=False, sep="; "):
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


def _create_wordlist_cldf(lexicon, conf, output_dir, sep="; "):
    lexicon, meanings = get_data(lexicon, sep=sep)
    spec = CLDFSpec(dir=output_dir / "cldf", module="Wordlist")
    with CLDFWriter(spec) as writer:
        writer.cldf.add_component("ParameterTable")
        for entry in lexicon.to_dict("records"):
            writer.objects["FormTable"].append(entry)
        for meaning in meanings.to_dict("records"):
            writer.objects["ParameterTable"].append(meaning)
        writer.cldf.add_component("LanguageTable")
        writer.objects["LanguageTable"].append(get_lg(conf["Language_ID"]))
        writer.cldf.remove_columns(
            "FormTable", "Language_ID"
        )  # turn Language_ID into virtual columns
        writer.cldf.add_columns(
            "FormTable",
            {
                "name": "Language_ID",
                "virtual": True,
                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#languageReference",
                "valueUrl": conf["Language_ID"],
            },
        )

        writer.write()

        return writer.cldf


def create_wordlist_cldf(lexicon, conf, output_dir, sep="; "):
    ds = _create_wordlist_cldf(lexicon, conf, output_dir, sep)
    ds.validate(log=log)
