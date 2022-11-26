"""Tests for the box2csv module.
"""
from click.testing import CliRunner
from box2csv.cli import corpus
from pycldf import Dataset


def test_toolbox(data, tmp_path):
    runner = CliRunner()
    runner.invoke(
        corpus,
        [
            str(data / "yekwana.txt"),
            "--conf",
            str(data / "yekwana.yaml"),
            "--output",
            tmp_path,
            "--cldf",
        ],
        catch_exceptions=False,
    )
    assert (tmp_path / "yekwana.csv").is_file()
    assert (tmp_path / "cldf" / "examples.csv").is_file()
    ds = Dataset.from_metadata(tmp_path / "cldf" / "metadata.json")
    assert ds.validate()



def test_shoebox(data, tmp_path):
    runner = CliRunner()
    runner.invoke(
        corpus,
        [
            str(data / "pemontexts.db"),
            "--format",
            "shoebox",
            "--conf",
            str(data / "pemon.yaml"),
            "--output",
            tmp_path,
            "--cldf",
        ],
        catch_exceptions=False,
    )
    assert (tmp_path / "pemontexts.csv").is_file()
    assert (tmp_path / "cldf" / "examples.csv").is_file()
    ds = Dataset.from_metadata(tmp_path / "cldf" / "metadata.json")
    assert ds.validate()
