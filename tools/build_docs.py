# --------------------------------------------------------------------------------------------------
# Copyright (c) Lukas Vik. All rights reserved.
#
# This file is part of the hdl_registers project.
# https://hdl-registers.com
# https://gitlab.com/tsfpga/hdl_registers
# --------------------------------------------------------------------------------------------------

import argparse
from pathlib import Path
import shutil
from subprocess import check_call
import sys
from xml.etree import ElementTree

from pybadges import badge

# Do PYTHONPATH insert() instead of append() to prefer any local repo checkout over any pip install
REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))
PATH_TO_TSFPGA = REPO_ROOT.parent.resolve() / "tsfpga"
sys.path.insert(0, str(PATH_TO_TSFPGA))

from tsfpga.system_utils import create_directory, create_file, delete, read_file
from tsfpga.tools.sphinx_doc import build_sphinx, generate_release_notes

import hdl_registers
from hdl_registers.about import get_readme_rst
from hdl_registers.parser import from_toml

GENERATED_SPHINX = hdl_registers.HDL_REGISTERS_GENERATED / "sphinx_rst"
GENERATED_SPHINX_HTML = hdl_registers.HDL_REGISTERS_GENERATED / "sphinx_html"
SPHINX_DOC = hdl_registers.HDL_REGISTERS_DOC / "sphinx"


def main():
    args = arguments()

    rst = generate_release_notes(
        repo_root=hdl_registers.REPO_ROOT,
        release_notes_directory=hdl_registers.HDL_REGISTERS_DOC / "release_notes",
        project_name="hdl_registers",
    )
    create_file(GENERATED_SPHINX / "release_notes.rst", rst)

    generate_apidoc()

    generate_register_code()

    generate_sphinx_index()

    build_sphinx(build_path=SPHINX_DOC, output_path=GENERATED_SPHINX_HTML)

    badges_path = create_directory(GENERATED_SPHINX_HTML / "badges")
    build_information_badges(badges_path)

    if args.skip_coverage:
        return

    build_python_coverage_badge(badges_path)
    copy_python_coverage_to_html_output()


def arguments():
    parser = argparse.ArgumentParser(
        "Build sphinx documentation", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--skip-coverage",
        action="store_true",
        help="skip handling of all coverage reports",
    )
    return parser.parse_args()


def generate_apidoc():
    output_path = delete(GENERATED_SPHINX / "apidoc")

    cmd = [
        sys.executable,
        "-m",
        "sphinx.ext.apidoc",
        # Place module documentation before submodule documentation
        "--module-first",
        "--output-dir",
        str(output_path),
        # module path
        "hdl_registers",
        # exclude pattern
        "**/test/**",
    ]
    check_call(cmd, cwd=hdl_registers.REPO_ROOT)


def generate_register_code():
    toml_file = SPHINX_DOC / "files" / "example.toml"
    register_list = from_toml(module_name="example", toml_file=toml_file, default_registers=None)

    output_path = GENERATED_SPHINX / "register_code"

    create_directory(output_path / "vhdl")
    register_list.create_vhdl_package(output_path=output_path / "vhdl")

    register_list.create_html_page(output_path=output_path / "html")
    register_list.create_html_register_table(output_path=output_path / "html")
    register_list.create_html_constant_table(output_path=output_path / "html")

    register_list.create_c_header(output_path=output_path / "c")

    register_list.create_cpp_interface(output_path=output_path / "cpp")
    register_list.create_cpp_header(output_path=output_path / "cpp")
    register_list.create_cpp_implementation(output_path=output_path / "cpp")


def generate_sphinx_index():
    """
    Generate index.rst for sphinx. Also verify that readme.rst in the project is identical.

    Rst file inclusion in readme.rst does not work on gitlab unfortunately, hence this
    cumbersome handling of syncing documentation.
    """
    rst_to_verify = get_readme_rst(include_website_link=True)
    if read_file(hdl_registers.REPO_ROOT / "readme.rst") != rst_to_verify:
        file_path = create_file(
            hdl_registers.HDL_REGISTERS_GENERATED / "sphinx" / "readme.rst", rst_to_verify
        )
        raise ValueError(
            f"readme.rst in repo root not correct. Compare to reference in python: {file_path}"
        )

    result = get_readme_rst(include_website_link=False)
    create_file(GENERATED_SPHINX / "index.rst", result)


def build_information_badges(output_path):
    badge_svg = badge(left_text="pip install", right_text="hdl-registers", right_color="blue")
    create_file(output_path / "pip_install.svg", badge_svg)

    badge_svg = badge(left_text="license", right_text="BSD 3-Clause", right_color="blue")
    create_file(output_path / "license.svg", badge_svg)

    badge_svg = badge(
        left_text="",
        right_text="tsfpga/hdl_registers",
        left_color="grey",
        right_color="grey",
        logo="https://about.gitlab.com/images/press/press-kit-icon.svg",
        embed_logo=True,
    )
    create_file(output_path / "gitlab.svg", badge_svg)

    badge_svg = badge(
        left_text="",
        right_text="hdl-registers.com",
        left_color="grey",
        right_color="grey",
        logo="https://design.firefox.com/product-identity/firefox/firefox/firefox-logo.svg",
        embed_logo=True,
    )
    create_file(output_path / "website.svg", badge_svg)


def build_python_coverage_badge(output_path):
    coverage_xml = hdl_registers.HDL_REGISTERS_GENERATED / "python_coverage.xml"
    assert coverage_xml.exists(), "Run pytest with coverage before building documentation"

    xml_root = ElementTree.parse(coverage_xml).getroot()
    line_coverage = int(round(float(xml_root.attrib["line-rate"]) * 100))
    assert line_coverage > 50, f"Coverage is way low: {line_coverage}. Something is wrong."
    color = "green" if line_coverage > 80 else "red"

    badge_svg = badge(
        left_text="line coverage",
        right_text=f"{line_coverage}%",
        right_color=color,
        logo=str(SPHINX_DOC / "Python-logo-notext.svg"),
        embed_logo=True,
        left_link="https://hdl-registers.com/python_coverage_html",
        right_link="https://hdl-registers.com/python_coverage_html",
    )
    create_file(output_path / "python_coverage.svg", badge_svg)


def copy_python_coverage_to_html_output():
    html_output_path = GENERATED_SPHINX_HTML / "python_coverage_html"
    delete(html_output_path)

    coverage_html = hdl_registers.HDL_REGISTERS_GENERATED / "python_coverage_html"
    assert (
        coverage_html / "index.html"
    ).exists(), "Run pytest with coverage before building documentation"

    shutil.copytree(coverage_html, html_output_path)


if __name__ == "__main__":
    main()
