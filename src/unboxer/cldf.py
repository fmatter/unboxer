import logging
import sys
import pandas as pd
from cldf_ldd import add_keys
from cldf_ldd import components
from cldfbench import CLDFSpec
from cldfbench.cldf import CLDFWriter
from pycldf.util import metadata2markdown
from unboxer.helpers import _slugify


log = logging.getLogger(__name__)


def create_dataset(tables, conf, output_dir):

    table_map = {
        default: default for default in ["ExampleTable", "ParameterTable", "FormTable"]
    }

    for component in components:
        table_map[component["url"].replace(".csv", "")] = component

    def get_table_url(tablename):
        if tablename.lower() != tablename:
            return table_map[tablename]
        else:
            return table_map[tablename]["url"]

    spec = CLDFSpec(
        dir=output_dir / "cldf", module="Generic", metadata_fname="metadata.json"
    )
    with CLDFWriter(spec) as writer:
        writer.cldf.add_component("LanguageTable")
        writer.objects["LanguageTable"].append(get_lg(conf["Language_ID"]))
        for table, df in tables.items():
            writer.cldf.add_component(table_map[table])
            if table in ["ExampleTable"]:
                writer.cldf.remove_columns(
                    table, "Language_ID"
                )  # turn Language_ID into virtual columns
                writer.cldf.add_columns(
                    table,
                    {
                        "name": "Language_ID",
                        "virtual": True,
                        "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#glottocode",
                        "valueUrl": conf["Language_ID"],
                    },
                )
            if table == "ExampleTable":
                for col in conf["aligned_fields"]:
                    df[col] = df[col].apply(lambda x: x.split("\t"))
            for rec in df.to_dict("records"):
                writer.objects[get_table_url(table)].append(rec)
        writer.write()
        add_keys(writer.cldf)
        return writer.cldf


def create_cldf(tables, conf, output_dir):
    if "Language_ID" not in conf:
        raise TypeError("Please specify a Language_ID in your configuration")
    ds = create_dataset(tables, conf, output_dir)
    ds.validate(log=log)
    readme = metadata2markdown(ds, ds.directory)
    with open(ds.directory / "README.md", "w", encoding="utf-8") as f:
        f.write(readme)
    log.info(f"Created cldf dataset at {ds.directory.resolve()}/{ds.filename}")


def _extract_meanings(meanings):
    for x in meanings:
        for y in x:
            yield y


def _replace_meanings(label, meaning_dict):
    return [meaning_dict[x] for x in label]


def get_lg(lg_id):
    try:
        import pyglottolog  # pylint: disable=import-outside-toplevel
        from cldfbench.catalogs import Glottolog  # pylint: disable=import-outside-toplevel
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
    lexicon["Meaning"] = lexicon["Meaning"].apply(lambda x: x.split(sep))
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
    ds = _create_wordlist_cldf(lexicon, conf, output_dir, sep="; ")
    ds.validate(log=log)