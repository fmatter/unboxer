"""Tests for the unboxer module.
"""
from click.testing import CliRunner
from unboxer.cli import corpus
from pycldf import Dataset


# def test_toolbox(data, tmp_path):
#     runner = CliRunner()
#     runner.invoke(
#         corpus,
#         [
#             str(data / "yekwana.txt"),
#             "--conf",
#             str(data / "yekwana.yaml"),
#             "--output",
#             tmp_path,
#             "--cldf",
#         ],
#         catch_exceptions=False,
#     )
#     assert (tmp_path / "yekwana.csv").is_file()
#     assert (tmp_path / "cldf" / "examples.csv").is_file()
#     ds = Dataset.from_metadata(tmp_path / "cldf" / "metadata.json")
#     assert ds.validate()


def test_shoebox(data, tmp_path):
    runner = CliRunner()
    runner.invoke(
        corpus,
        [
            str(data / "pem_txt_sb.db"),
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
    assert (tmp_path / "pem_txt_sb.csv").is_file()
    assert (tmp_path / "cldf" / "examples.csv").is_file()
    ds = Dataset.from_metadata(tmp_path / "cldf" / "metadata.json")
    assert ds.validate()

def test_toolbox(data, tmp_path):
    runner = CliRunner()
    runner.invoke(
        corpus,
        [
            str(data / "pem_txt_tb.txt"),
            "--conf",
            str(data / "pemon.yaml"),
            "--output",
            tmp_path,
            "--cldf",
        ],
        catch_exceptions=False,
    )
    assert (tmp_path / "pem_txt_tb.csv").is_file()
    assert (tmp_path / "cldf" / "examples.csv").is_file()
    ds = Dataset.from_metadata(tmp_path / "cldf" / "metadata.json")
    assert ds.validate()