"""Top-level package for unboxer."""
import logging
import re
import sys
from itertools import combinations
from pathlib import Path

import colorlog
import pandas as pd
from humidifier import Humidifier, get_values, humidify
from morphinder import Morphinder, identify_complex_stem_position
from tqdm import tqdm

from unboxer import helpers
from unboxer.cldf import (
    create_cldf,
    create_dictionary_cldf,
    create_wordlist_cldf,
    get_lexical_data,
)

handler = colorlog.StreamHandler(None)
handler.setFormatter(
    colorlog.ColoredFormatter("%(log_color)s%(levelname)-7s%(reset)s %(message)s")
)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.propagate = True
log.addHandler(handler)


__author__ = "Florian Matter"
__email__ = "fmatter@mailbox.org"
__version__ = "0.0.3.dev"


def _remove_spaces(text):
    for sep in ["- ", " -"]:
        while sep in text:
            text = text.replace(sep, sep.strip())
    return re.sub(r"\s+", "\t", text)


def id_glosses(gloss, sep=None):
    res = [humidify(g, key="glosses") for g in re.split(r"\.\b", gloss)]
    if sep:
        return sep.join(res)
    return res


def _get_fields(record, rec_marker, multiple, sep):
    out = {}
    marker = None
    for line in record.split("\n"):
        if line == "":
            continue
        if not line.startswith("\\"):
            out[marker] += " " + line
        elif " " in line:
            marker, content = line.split(" ", 1)
            content = content.strip(" ")
            if marker in out:
                if marker not in multiple:
                    out[marker] += " " + content
                else:
                    out[marker] += sep + content
            else:
                out[marker] = content
        else:
            out[line] = ""
    if "".join([v for k, v in out.items() if k != rec_marker]) == "":
        return None
    return out


def _fix_clitics(string):
    string = string.replace("=\t", "=").replace("\t=", "=")
    return string


def extract_morphs(lexicon, sep):
    morphs = []
    morphemes = []
    for rec in lexicon.to_dict("records"):
        m_id = rec["ID"]
        try:
            dic = {
                "Meaning": rec["Meaning"],
                "Part_Of_Speech": rec["Part_Of_Speech"],
                "Morpheme_ID": m_id,
            }
        except KeyError as e:
            log.error(f"Please define {e} in lexicon_mappings in your conf.")
            print(rec)
            sys.exit()
        morphs.append({**{"Form": rec["Headword"], "ID": rec["ID"]}, **dic})
        if "Variants" in rec and rec["Variants"] != "":
            for c, x in enumerate(rec["Variants"].split(sep)):
                morphs.append({**{"Form": x, "ID": f"{m_id}-{c}"}, **dic})
        morphemes.append(rec)
    return pd.DataFrame.from_dict(morphemes), pd.DataFrame.from_dict(morphs)


def tuplify(x):
    if isinstance(x, list):
        return tuple(x)
    if not isinstance(x, tuple):
        return tuple([x])
    return x


def listify(x):
    if isinstance(x, tuple):
        return list(x)
    if not isinstance(x, list):
        return [x]
    return x


def build_slices(
    df,
    morphinder=None,
    obj_key="Analyzed_Word",
    gloss_key="Gloss",
    infl_cats=None,
    infl_vals=None,
    infl_morphemes=None,
):  # pylint:ignore=too-many-arguments,too-many-locals
    df = df.copy()
    for c in [obj_key, gloss_key]:
        df[c] = df[c].apply(lambda x: re.sub(r"-\s+", "-INTERN", x))
        df[c] = df[c].apply(lambda x: re.sub(r"\s+-", "INTERN-", x))
        df[c] = df[c].apply(lambda x: re.split(r"\s+", x))
    wfs = {}
    w_slices = []
    s_slices = []
    inflections = []
    infl_tuples = {}
    wordformstems = []
    infl_morphemes = infl_morphemes or {}
    for k, v in infl_morphemes.items():
        new_k = tuplify(k)
        new_v = listify(v)
        infl_tuples[new_k] = new_v
        infl_morphemes[k] = new_v
    w_meanings = {}
    found_stems = {}
    stem_parts = []
    for sentence in tqdm(df.to_dict("records"), desc="Building slices"):
        for s_idx, (obj, gloss) in enumerate(
            zip(sentence[obj_key], sentence[gloss_key])
        ):
            w_obj = obj.replace("INTERN", "")
            w_gloss = gloss.replace("INTERN", "")
            w_id = humidify(f"{w_obj}-{w_gloss}", "wordforms")
            meaning_id = humidify(w_gloss, "meanings")
            if meaning_id not in w_meanings:
                w_meanings[meaning_id] = {"ID": meaning_id, "Name": w_gloss}
            if w_obj == "":
                continue
            if w_id not in wfs:
                if w_gloss != "":
                    wfs[w_id] = {
                        "ID": w_id,
                        "Form": w_obj.replace("-", ""),
                        "Gloss": w_gloss,
                        "Description": w_gloss,
                        "Parameter_ID": [humidify(w_gloss, "meanings")],
                        "Morpho_Segments": w_obj.strip("-").split("-"),
                    }
                if morphinder:
                    infl_hits = {}
                    stem_mids = []
                    for m_idx, (morph_obj, morph_gloss) in enumerate(
                        zip(obj.split("INTERN"), gloss.split("INTERN"))
                    ):
                        if (
                            morph_obj is None
                            or morph_gloss is None
                            or morph_gloss == "***"
                        ):
                            continue
                        morph_gloss = morph_gloss.strip("-").strip("=")
                        m_id, sense = morphinder.retrieve_morph_id(
                            morph_obj,
                            morph_gloss,
                            "",
                            gloss_key="Meaning",
                            type_key="Part_Of_Speech",
                        )
                        del sense
                        if morph_gloss == "":
                            log.warning(
                                f"Missing gloss for {morph_obj} in {sentence['ID']}"
                            )
                            continue
                        if m_id:
                            slice_id = f"{w_id}-{m_id}-{m_idx}"
                            w_slices.append(
                                {
                                    "ID": slice_id,
                                    "Wordform_ID": w_id,
                                    "Morph_ID": m_id,
                                    "Form_Meaning": meaning_id,
                                    "Gloss": morph_gloss,
                                    "Morpheme_Meaning": humidify(
                                        morph_gloss, "gloss_meanings"
                                    ),
                                    "Form": morph_obj,
                                    "Index": m_idx,
                                }
                            )
                        if m_id in infl_morphemes:
                            infl_hits[m_id] = (morph_obj, slice_id)
                        else:
                            stem_mids.append(m_id)
                    if len(infl_hits) > 1:
                        wf_inflections = []
                        stem_objs = obj.split("INTERN")
                        stem_glosses = gloss.split("INTERN")
                        i = len(infl_hits)
                        while i > 0:
                            cands = list(combinations(infl_hits.keys(), i))
                            for cand in cands:
                                if cand in infl_tuples:
                                    cand = tuple(cand)
                                    for m_id in cand:
                                        m_form, slice_id = infl_hits[m_id]
                                        for val in infl_tuples[cand]:
                                            # print(
                                            #     "adding value",
                                            #     val,
                                            #     "for morph",
                                            #     m_id,
                                            #     "in wordform",
                                            #     w_id,
                                            #     "for part",
                                            #     slice_id,
                                            #     "(index",
                                            #     m_idx,
                                            #     ")",
                                            # )
                                            wf_inflections.append(
                                                {
                                                    "ID": humidify(
                                                        f"{w_id}-{m_id}-{val}"
                                                    ),
                                                    "Wordformpart_ID": [slice_id],
                                                    "Value_ID": val,
                                                }
                                            )
                                    if m_form in stem_objs:
                                        del stem_glosses[stem_objs.index(m_form)]
                                        stem_objs.remove(m_form)
                                    else:
                                        print(m_form)
                                        print(stem_objs)
                                        exit()
                            i -= 1
                        stem_form = "".join(stem_objs)
                        stem_gloss = "".join(stem_glosses)
                        stem_id = humidify(f"{stem_form}-{stem_gloss}")
                        wordformstems.append(
                            {
                                "ID": f"{stem_id}{w_id}",
                                "Wordform_ID": w_id,
                                "Stem_ID": stem_id,
                                "Index": identify_complex_stem_position(
                                    obj.replace("INTERN", ""), stem_form
                                ),
                            }
                        )
                        if stem_id not in found_stems:
                            found_stems[stem_id] = {
                                "ID": stem_id,
                                "Name": stem_form,
                                "Meaning": stem_gloss,
                                "Morpho_Segments": [x.strip("-") for x in stem_objs],
                            }
                            # exit()
                            # print(stem_form)
                            # print(stem_objs)
                            # print(stem_glosses)
                            # print(infl_hits)
                            for smid_idx, (part, partgloss) in enumerate(
                                zip(stem_mids, stem_glosses)
                            ):
                                if not part:
                                    continue
                                stem_parts.append(
                                    {
                                        "ID": f"{stem_id}-{smid_idx}",
                                        "Stem_ID": stem_id,
                                        "Morph_ID": part,
                                        "Gloss_ID": id_glosses(partgloss),
                                        "Index": smid_idx,
                                    }
                                )
                        for infl in wf_inflections:
                            infl["Stem_ID"] = stem_id
                            inflections.append(infl)
            s_slices.append(
                {
                    "ID": f"{sentence['ID']}-{s_idx}",
                    "Example_ID": sentence["ID"],
                    "Wordform_ID": w_id,
                    "Form": w_obj.replace("-", ""),
                    "Segmentation": w_obj,
                    "Gloss": w_gloss,
                    "Parameter_ID": meaning_id,
                    "Index": s_idx,
                }
            )
    if not morphinder:
        w_slices = None
    else:
        if morphinder.failed_cache:
            log.warning("Could not find lexicon entries for the following morphs:")
            for a, b in morphinder.failed_cache:
                log.warning(f"{a} ‘{b}’")
        w_slices = pd.DataFrame.from_dict(w_slices)
    return (
        pd.DataFrame.from_dict(wfs.values()),
        pd.DataFrame.from_dict(w_meanings.values()),
        pd.DataFrame.from_dict(s_slices),
        w_slices,
        pd.DataFrame.from_dict(inflections),
        pd.DataFrame.from_dict(found_stems.values()),
        pd.DataFrame.from_dict(wordformstems),
        pd.DataFrame.from_dict(stem_parts),
    )


def extract_corpus(
    filenames=None,
    conf=None,
    lexicon=None,
    output_dir=".",
    cldf=False,
    audio=None,
    skip_empty_obj=False,
    complain=False,
    tokenize=None,
    exclude=None,
    inflection=None,
    include="all",
    cldf_name="cldf",
    parsing_db=None,
    languages=None,
):
    """Extract text records from a corpus.

    Args:
        database_file (str): The path to the corpus database file.
        conf (dict): Configuration (see) todo: insert link
        cldf (bool, optional): Should a CLDF dataset be created? Defaults to `False`.
    """
    if not isinstance(filenames, list):
        filenames = [filenames]
    conf = helpers.markerize(conf)
    out = []
    inflection = inflection or {}
    for filename in filenames:
        database_file = Path(filename)
        record_marker = "\\" + conf["record_marker"]
        sep = conf["cell_separator"]

        try:
            with open(database_file, "r", encoding=conf["encoding"]) as f:
                content = f.read()
        except UnicodeDecodeError:
            log.error(
                f"""Could not open the file with the encoding [{conf["encoding"]}].
    Make sure that you are not parsing a shoebox project as toolbox or vice versa.
    You can also explicitly set the correct file encoding in your config."""
            )
            sys.exit()
        records = content.split(record_marker + " ")
        for record in records[1::]:
            res = _get_fields(
                record_marker + " " + record, record_marker, multiple=[], sep=sep
            )
            if res:
                out.append(res)
            else:
                pass
                # log.warning("Empty record:")
                # log.warning(record)
    df = pd.DataFrame.from_dict(out)
    if not df[record_marker].is_unique:
        if complain:
            log.warning("Found duplicate IDs, will only keep first of each:")
            dupes = df[df.duplicated(record_marker)]
            print(dupes)
        df.drop_duplicates(record_marker, inplace=True)
    df.rename(columns=conf["interlinear_mappings"], inplace=True)
    if "Analyzed_Word" not in df.columns:
        raise ValueError("Did not find Analyzed_Word:", conf["interlinear_mappings"])
    if skip_empty_obj:
        old = len(df)
        df = df[df["Gloss"] != ""]
        log.info(f"Dropped {old-len(df)} unparsed records.")
    df.fillna("", inplace=True)
    df = df[df["Primary_Text"] != ""]
    if "ID" in df:
        if conf.get("slugify", True):
            tqdm.pandas(desc="Creating record IDs")
            df["ID"] = df["ID"].progress_apply(
                lambda x: humidify(x, "sentence_id", unique=True)
            )
    else:
        df["ID"] = df.index

    if lexicon:
        lex_df = extract_lexicon(
            lexicon, parsing_db=parsing_db, conf=conf, output_dir=output_dir
        )
        morphemes, morphs = extract_morphs(lex_df, sep)
        morphinder = Morphinder(morphs, complain=complain)
    else:
        tdf = df.copy()
        morphs = {}
        for c in ["Analyzed_Word", "Gloss"]:
            tdf[c] = df[c].apply(lambda x: re.sub(r"-\s+", "-INTERN", x))
            tdf[c] = df[c].apply(lambda x: re.sub(r"\s+-", "INTERN-", x))
            tdf[c] = df[c].apply(lambda x: re.split(r"\s+", x))
        for rec in tdf.to_dict("records"):
            for obj, gloss in zip(rec["Analyzed_Word"], rec["Gloss"]):
                if obj == "":
                    continue
                morph_id = humidify(obj + "-" + gloss, key="pairs")
                if morph_id not in morphs:
                    morphs[morph_id] = {
                        "ID": morph_id,
                        "Form": obj,
                        "Meaning": gloss.strip("-").strip("="),
                    }
        morphs = pd.DataFrame.from_dict(morphs.values())
        morphinder = Morphinder(morphs, complain=complain)
    (
        wordforms,
        form_meanings,
        sentence_slices,
        morph_slices,
        inflections,
        stems,
        wordformstems,
        stemparts,
    ) = build_slices(df, morphinder, **inflection)
    morph_meanings = {}
    stem_meanings = {}
    for meanings in tqdm(morphs["Meaning"], desc="Morphs"):
        for meaning in meanings.split("; "):
            morph_meanings.setdefault(
                meaning, {"ID": humidify(meaning, key="meanings"), "Name": meaning}
            )

    if len(stems) > 0:
        for stem_gloss in tqdm(stems["Meaning"], desc="Stems"):
            stem_meanings.setdefault(
                stem_gloss,
                {
                    "ID": humidify(stem_gloss, key="meanings"),
                    "Name": stem_gloss,
                },
            )
    if include != "all":
        rec_list = include
    elif exclude:
        rec_list = list(df["ID"]) - exclude
    else:
        rec_list = list(df["ID"])
    df = df[df["ID"].isin(rec_list)]
    sentence_slices = sentence_slices[sentence_slices["Example_ID"].isin(rec_list)]
    for col in tqdm(df.columns, desc="Columns"):
        if col in conf["aligned_fields"]:
            df[col] = df[col].apply(_remove_spaces)
    df = df[df["ID"].isin(rec_list)]
    df = df.apply(helpers.fix_glosses, axis=1)
    sentence_slices = sentence_slices[sentence_slices["Example_ID"].isin(rec_list)]
    if conf["fix_clitics"]:
        log.info("Fixing clitics")
        for col in conf["aligned_fields"]:
            df[col] = df[col].apply(_fix_clitics)
    if "Primary_Text" in df.columns:
        df["Primary_Text"] = df["Primary_Text"].apply(lambda x: re.sub(r"\s+", " ", x))

    if len(wordforms) > 0:
        wordforms["Language_ID"] = conf.get("Language_ID", "undefined")
        wordforms = wordforms[wordforms["Form"] != ""]
    df["Language_ID"] = conf.get("Language_ID", "undefined")

    if lexicon:
        morphemes["Language_ID"] = conf.get("Language_ID", "undefined")
    morphs["Language_ID"] = conf.get("Language_ID", "undefined")
    if not morphs["ID"].is_unique:
        log.warning("Duplicate IDs in morph table, only keeping first instances:")
        log.warning(morphs[morphs.duplicated(subset="ID", keep=False)])
        morphs.drop_duplicates(subset="ID", inplace=True)
    if output_dir:
        df.to_csv(
            (Path(output_dir) / database_file.name).with_suffix(".csv"), index=False
        )
        morphs.to_csv((Path(output_dir) / "morphs.csv"), index=False)
        if lexicon:
            morphemes.to_csv((Path(output_dir) / "morphemes.csv"), index=False)
    if cldf:
        tables = {"examples.csv": df}
        tables["exampleparts.csv"] = sentence_slices
        if lexicon:
            morphemes["Name"] = morphemes["Headword"]
            morphemes["Description"] = morphemes["Meaning"]
            morphemes["Parameter_ID"] = morphemes["Meaning"].apply(
                lambda x: [morph_meanings[y]["ID"] for y in x.split("; ")]
            )
        if inflection:
            stems["Parameter_ID"] = stems["Meaning"].apply(
                lambda x: [stem_meanings[x]["ID"]]
            )

        if audio:
            tables["media.to_csv"] = pd.DataFrame.from_dict(
                [
                    {
                        "ID": f.stem,
                        "Media_Type": "audio/" + f.suffix.strip("."),
                        "Download_URL": str(f),
                    }
                    for f in audio.iterdir()
                ]
            )

        morphs["Name"] = morphs["Form"]
        if tokenize:
            log.info("Tokenizing...")
            for df in [wordforms, morphs]:
                if len(df) > 0:
                    for orig, repl in conf.get("replace", {}).items():
                        df["Form"] = df["Form"].replace(orig, repl, regex=True)
                    df["Segments"] = df["Form"].apply(lambda x: tokenize(x).split(" "))
                    bad = df[df["Segments"].apply(lambda x: "�" in x)]
                    if len(bad) > 1:
                        log.warning("Unsegmentable")
                        print(bad)
                        df["Segments"] = df["Segments"].apply(
                            lambda x: "" if "�" in x else x
                        )
        if len(morph_slices) > 0:
            morph_slices["Gloss_ID"] = morph_slices["Gloss"].apply(id_glosses)
            tables["glosses.csv"] = pd.DataFrame.from_dict(
                [{"ID": v, "Name": k} for k, v in get_values("glosses").items()]
            )
        morphs["Description"] = morphs["Meaning"]
        morphs["Parameter_ID"] = morphs["Description"].apply(
            lambda x: [morph_meanings[y]["ID"] for y in x.split("; ")]
        )
        if len(form_meanings) > 0:
            morph_meanings = pd.DataFrame.from_dict(
                [
                    x
                    for x in morph_meanings.values()
                    if x["ID"] not in list(form_meanings["ID"])
                ]
            )
            stem_meanings = pd.DataFrame.from_dict(
                [
                    x
                    for x in stem_meanings.values()
                    if x["ID"] not in list(form_meanings["ID"])
                ]
            )
            tables["parameters.csv"] = pd.concat(
                [form_meanings, morph_meanings, stem_meanings]
            )
        else:
            morph_meanings = pd.DataFrame.from_dict(morph_meanings.values())
            tables["parameters.csv"] = morph_meanings
        if len(wordforms) > 0:
            tables["wordforms.csv"] = wordforms
        tables["morphs.csv"] = morphs
        tables["wordformparts.csv"] = morph_slices
        if len(stems) > 0:
            stems["Language_ID"] = conf.get("Language_ID", "undefined")
            stems["Lexeme_ID"] = stems["ID"]
            tables["stems.csv"] = stems
            tables["lexemes.csv"] = stems
            tables["stemparts.csv"] = stemparts
            tables["wordformstems.csv"] = wordformstems
            tables["inflections.csv"] = inflections
            tables["inflectionalcategories.csv"] = inflection["infl_cats"]
            tables["inflectionalvalues.csv"] = inflection["infl_vals"]
        if lexicon:
            lexicon, meanings = get_lexical_data(lex_df)
            tables["morphemes.csv"] = morphemes
            tables["parameters.csv"] = pd.concat([meanings, tables["parameters.csv"]])
            tables["parameters.csv"].drop_duplicates(subset="ID", inplace=True)
        create_cldf(
            tables=tables,
            conf=conf,
            output_dir=output_dir,
            cldf_name=cldf_name,
            languages=languages,
            module="corpus",
        )
    return df


def extract_lexicon(
    database_file,
    conf,
    parsing_db=None,
    output_dir=None,
    cldf=None,
    audio=None,
    languages=None,
    examples=None,
):
    hum = Humidifier()

    def humidify(*args, **kwargs):
        return hum.humidify(*args, **kwargs)

    database_file = Path(database_file)
    conf["lexicon_mappings"]["\\" + conf["entry_marker"]] = "Headword"
    entry_marker = "\\" + conf["entry_marker"]
    with open(database_file, "r", encoding=conf["encoding"]) as f:
        content = f.read()
    sep = conf["cell_separator"]
    lookup_dict = {}
    if parsing_db:
        with open(parsing_db, "r", encoding=conf["encoding"]) as f:
            parsing = f.read()
        parses = parsing.split("\n\n")
        for parse in parses[1::]:
            res = _get_fields(parse, None, multiple=[], sep=sep)
            if res:
                val = res[conf["parsing_underlying"]]
                if " " not in val:
                    lookup_dict.setdefault(val, [])
                    lookup_dict[val].append(res[conf["parsing_surface"]])

    if entry_marker not in content:
        raise ValueError(
            f"entry_marker is defined as '{entry_marker}', which is not found in the database."
        )
    records = content.split(entry_marker)
    out = []
    for record in records[1::]:
        res = _get_fields(
            entry_marker + record, entry_marker, multiple=["\a", "\\glo"], sep=sep
        )
        if res:
            out.append(res)
        else:
            log.warning("Empty record:")
            log.warning(record)
    df = pd.DataFrame.from_dict(out)
    df.rename(columns=conf["lexicon_mappings"], inplace=True)
    df.fillna("", inplace=True)
    if "Variants" not in df.columns:
        df["Variants"] = ""
    df["Variants"] = df["Variants"].apply(lambda x: x.split(sep))

    def insert_variants(rec):
        if rec["Headword"] in lookup_dict:
            for var in lookup_dict[rec["Headword"]]:
                rec["Variants"].append(var)
        return rec

    df = df.apply(insert_variants, axis=1)
    df["Variants"] = df["Variants"].apply(lambda x: sep.join([y for y in x if y]))
    try:
        df["ID"] = df.apply(
            lambda x: humidify(
                f"{x['Headword']}-{x['Meaning'].split(sep)[0]}", "form", unique=True
            ),
            axis=1,
        )
    except KeyError as e:
        log.error(f"Please define marker for {e} in lexicon_mappings in your conf.")
        print(df)
        sys.exit()

    if conf["Language_ID"]:
        df["Language_ID"] = conf["Language_ID"]

    if examples:
        example_df = extract_corpus(examples, conf=conf)
    else:
        example_df = None

    if output_dir:
        df.to_csv(
            (Path(output_dir) / database_file.name).with_suffix(".csv"), index=False
        )

    if cldf == "wordlist":
        create_wordlist_cldf(
            df, conf=conf, output_dir=output_dir, audio=audio, languages=languages
        )
    if cldf == "dictionary":
        create_dictionary_cldf(
            df,
            conf=conf,
            output_dir=output_dir,
            audio=audio,
            languages=languages,
            examples=example_df,
        )
    return df
