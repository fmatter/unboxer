import pandas as pd
from clld.cliutil import slug
from clldutils.loglib import Logging, get_colorlog
import sys
from pathlib import Path
log = get_colorlog(__name__, sys.stdout)

# for creating IDs from strings
def slugify(s):
    out = slug(s)
    if out == "":
        out = "X"
    return out


def decode_parse_lines(lines, merge=" ", tag_dic={}):
    out = {}
    for line in lines:
        if line.startswith("\\"):
            tag = line.split(" ")[0]
            line = line.strip(tag).strip()
            if tag in tag_dic:
                tag = tag_dic[tag]
            if tag in out:
                out[tag] += merge + line
            else:
                out[tag] = line
    return out

def ipaify_lex(tokenizer, str):
    out = []
    strings = str.split("; ")
    rem = ["[", "]", "="]
    rem = []
    for string in strings:
        for i in rem:
            string = string.replace(i, "")
        if ("�" in tokenizer(string, "IPA", segment_separator="", separator=" ") and len(string) > 1):
            string = string.lower()
        conv = tokenizer(string, "IPA", segment_separator="", separator=" ")
        if "�" in conv:
            log.warning(f"Can't convert {string}: {conv}")
            return str
        out.append(conv)
    return "; ".join(out)

def segmentify(tokenizer, str):
    str = str.replace("-", "").replace("=", "").replace("0", "")
    res = tokenizer(str, column="IPA")
    if "�" in res:
        return ""
    else:
        return res

def split_parse_file(input):
    entries = input.split("\n\n")
    entries = [decode_parse_lines(entry.split("\n"), tag_dic={"\\wd": "Form", "\\mb": "Morphemes"}) for entry in entries]
    # for entry in entries[1::]:
    #     if entry["Form"] == "eh":
    #         print(entry)
    return entries[1::]

# gather allomorphs of a given morpheme by using the parsing database
def extract_allomorphs(filename):

    def prune_words(l):
        return [x for x in l if " " not in x]

    parse_entries = open(filename, "r", encoding="cp1252").read()
    parse_entries = split_parse_file(parse_entries)
    # for e in parse_entries:
    #     if list(e.keys()) != ["Form", "Morphemes"]:
    #         print(e)
    df = pd.DataFrame.from_dict(parse_entries)
    # print(df[df["Form"] == "eh"])
    df = df[(df["Morphemes"].str.contains("; ") | ~(df["Form"].str.contains(" ")))]
    # print(df[df["Form"] == "eh"])
    df["Morphemes"] = df["Morphemes"].apply(lambda x: x.split("; "))
    # print(df[df["Form"] == "eh"])
    df["Morphemes"] = df["Morphemes"].apply(lambda x: prune_words(x))
    # print(df[df["Form"] == "eh"])
    # df = df[df["check"]]
    # df.drop(columns="check", inplace=True)
    # print(df[df["Form"] == "eh"])
    morphemes = []
    for i, row in df.iterrows():
        for morpheme in row["Morphemes"]:
            morphemes.append({"Morpheme": morpheme, "Allomorph": row["Form"]})
    return morphemes


# main function
def convert_shoebox(filename, lg, parsing_db=None, tokenizer=None, col_dic={}, encoding="cp1252"):
    log.info(f"Parsing lexical database {filename} ({lg}), using parsing database {parsing_db}")
    ids = []
    full_text = open(filename, "r", encoding=encoding).read()
    entries = full_text.split("\n\n")
    conv_entries = []
    for entry in entries[1::]:
        out = {}
        for line in entry.split("\n"):
            col = line.split(" ")[0]
            if col in col_dic:
                current_col = col_dic[col]
                out[current_col] = line.replace(col, "").strip(" ")
            else:
                out[current_col] += " " + line
        if "Form" in out:
            id = slugify(out["Form"])
            final_id = id
            if id in ids:
                c = 0
                while final_id in ids:
                    c += 1
                    final_id = f"{id}-{c}"
            else:
                final_id = id
            ids.append(final_id)
            out["ID"] = final_id
            conv_entries.append(out)
    df = pd.DataFrame.from_dict(conv_entries)
    df["Language_ID"] = lg
    df["Parameter_ID"].replace("", "?", inplace=True)

    # get allomorphs, if parsing database present
    if parsing_db:
        allomorphs = extract_allomorphs(parsing_db)
        allomorphs = pd.DataFrame.from_dict(allomorphs)
        # print(allomorphs[allomorphs["Allomorph"] == "-thïrï"])
        allomorphs = (
            allomorphs.groupby("Morpheme").agg({"Allomorph": "; ".join}).reset_index()
        )
        allomorphs.rename(columns={"Allomorph": "Allomorphs"}, inplace=True)
        allomorphs = allomorphs[allomorphs["Morpheme"] != ""]
        allomorphs = allomorphs[allomorphs["Morpheme"] != "***"]
        # print(df[df["Parameter_ID"].str.contains("Cop")])
        df = pd.merge(df, allomorphs, left_on="Form", right_on="Morpheme", how="left")
        # print(df[df["Parameter_ID"].str.contains("Cop")])
        df["Morpheme"] = df["Morpheme"].fillna("")
        df.drop(columns="Morpheme", inplace=True)
        # print(df[["Allomorphs", "Form"]])
        df["Allomorphs"] = df["Allomorphs"].apply(lambda x: x.split("; ") if not pd.isnull(x) else [])
        df["Allomorphs"] = df.apply(lambda x: x["Allomorphs"] if x["Form"] in x["Allomorphs"] else x["Allomorphs"] + [x["Form"]], axis=1)

        forms = []
        for i, row in df.iterrows():
            for a_count, a in enumerate(row["Allomorphs"]):
                forms.append(
                    {
                        "ID": f"{row['ID']}-{a_count}",
                        "Form": a,
                        "Morpheme_ID": row["ID"],
                        "Language_ID": row["Language_ID"],
                        "Parameter_ID": row["Parameter_ID"],
                    }
                )
                if tokenizer:
                    forms[-1]["Segments"] = segmentify(tokenizer, a)
        forms = pd.DataFrame.from_dict(forms)

        df.drop(columns=["Allomorphs"], inplace=True)
    if tokenizer:
        df["Form"] = df["Form"].apply(lambda x: ipaify_lex(tokenizer, x))
        forms["Form"] = forms["Form"].apply(lambda x: ipaify_lex(tokenizer, x))
    return df, forms