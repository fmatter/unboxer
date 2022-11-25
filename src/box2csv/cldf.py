import logging
from cldfbench import CLDFSpec
from cldfbench.cldf import CLDFWriter
from pycldf.util import metadata2markdown


log = logging.getLogger(__name__)

table_map = {"ExampleTable": "ExampleTable"}


def create_dataset(tables, conf, output_dir):
    spec = CLDFSpec(
        dir=output_dir / "cldf", module="Generic", metadata_fname="metadata.json"
    )
    with CLDFWriter(spec) as writer:
        for table, df in tables.items():
            if table in ["ExampleTable"]:
                writer.cldf.add_component(table_map[table])
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
                for col in conf["tabbed_fields"]:
                    df[col] = df[col].apply(lambda x: x.split("\t"))
            for rec in df.to_dict("records"):
                writer.objects[table].append(rec)
        writer.write()
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
