# --------------------------------------------------------------------------------------------------
# Copyright (c) Lukas Vik. All rights reserved.
#
# This file is part of the hdl_registers project, a HDL register generator fast enough to run
# in real time.
# https://hdl-registers.com
# https://gitlab.com/hdl_registers/hdl_registers
# --------------------------------------------------------------------------------------------------

# Standard libraries
import sys
from pathlib import Path

# Add path for default location of tsfpga to PYTHONPATH.
sys.path.append(
    str(
        (
            Path(__file__).parent.parent.parent.parent.parent.parent.parent / "tsfpga" / "tsfpga"
        ).resolve()
    ),
)

# Third party libraries
from tsfpga.examples.example_env import get_hdl_modules
from tsfpga.system_utils import create_directory
from vunit import VUnit

# First party libraries
from hdl_registers import HDL_REGISTERS_DOC, HDL_REGISTERS_GENERATED
from hdl_registers.field.register_field_type import (
    Signed,
    SignedFixedPoint,
    Unsigned,
    UnsignedFixedPoint,
)
from hdl_registers.parser import from_toml

THIS_FOLDER = Path(__file__).parent.resolve()


def test_running_simulation(tmp_path):
    """
    Run the testbench .vhd file that is next to this file. Contains assertions on the
    VHDL package generated from the example TOML file. Shows that the file can be compiled and
    that (some of) the information is correct.
    """
    regs_pkg_path = _generate_registers(output_path=tmp_path)

    def run(args, exit_code):
        argv = ["--minimal", "--num-threads", "4", "--output-path", str(tmp_path)] + args
        vunit_proj = VUnit.from_argv(argv=argv)
        vunit_proj.add_vhdl_builtins()

        library = vunit_proj.add_library(library_name="example")
        library.add_source_file(THIS_FOLDER / "tb_generated_vhdl_package.vhd")
        library.add_source_file(regs_pkg_path)

        for module in get_hdl_modules():
            vunit_library = vunit_proj.add_library(library_name=module.library_name)
            for hdl_file in module.get_simulation_files(include_tests=False):
                vunit_library.add_source_file(hdl_file.path)

        try:
            vunit_proj.main()
        except SystemExit as exception:
            assert exception.code == exit_code

    run(args=["--compile"], exit_code=0)
    # All these tests should pass.
    run(args=["--without-attribute", ".expected_failure"], exit_code=0)
    # All these should fail.
    # The only error checking here is that the return code is non-zero.
    # That will trigger as long as at least one test case fails, but others could technically pass.
    # A more robust method would be to parse the VUnit test report and check that each test case
    # has failed.
    run(args=["--with-attribute", ".expected_failure"], exit_code=1)


def _generate_registers(output_path):
    register_list = from_toml(
        module_name="example",
        toml_file=HDL_REGISTERS_DOC / "sphinx" / "files" / "regs_example.toml",
    )

    # Add some bit vector fields with types.
    # This is not supported by the TOML parser at this point, so we do it manually.
    register = register_list.append_register(name="field_test", mode="r_w", description="")
    register.append_bit_vector(
        name="u0", description="", width=2, default_value="11", field_type=Unsigned()
    )

    register.append_bit_vector(
        name="s0", description="", width=2, default_value="11", field_type=Signed()
    )
    register.append_bit_vector(
        name="ufixed0",
        description="",
        width=2,
        default_value="11",
        field_type=UnsignedFixedPoint(5, -2),
    )
    register.append_bit_vector(
        name="sfixed0",
        description="",
        width=2,
        default_value="11",
        field_type=SignedFixedPoint(2, -3),
    )

    register_list.create_vhdl_package(output_path=output_path)

    return output_path / "example_regs_pkg.vhd"


if __name__ == "__main__":
    vunit_output_path = create_directory(HDL_REGISTERS_GENERATED / "vunit_out", empty=True)
    test_running_simulation(tmp_path=vunit_output_path)
