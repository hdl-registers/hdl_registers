# --------------------------------------------------------------------------------------------------
# Copyright (c) Lukas Vik. All rights reserved.
#
# This file is part of the hdl-registers project, an HDL register generator fast enough to run
# in real time.
# https://hdl-registers.com
# https://github.com/hdl-registers/hdl-registers
# --------------------------------------------------------------------------------------------------

"""
Some limited unit tests.
Note that the generated VHDL code is also simulated in a functional test.
"""

# First party libraries
from hdl_registers.generator.vhdl.axi_lite.wrapper import VhdlAxiLiteWrapperGenerator
from hdl_registers.register_list import RegisterList
from hdl_registers.register_modes import REGISTER_MODES


def test_file_is_not_generated_without_registers(tmp_path):
    register_list = RegisterList(name="test", source_definition_file=None)

    assert not (VhdlAxiLiteWrapperGenerator(register_list, tmp_path).create()).exists()

    register_list.add_constant(name="apa", value=True, description="")
    assert not (VhdlAxiLiteWrapperGenerator(register_list, tmp_path).create()).exists()

    register_list.append_register(name="hest", mode=REGISTER_MODES["r_w"], description="")
    assert (VhdlAxiLiteWrapperGenerator(register_list, tmp_path).create()).exists()


def test_re_generating_file_without_registers_should_delete_old_file(tmp_path):
    register_list = RegisterList(name="test", source_definition_file=None)
    register_list.append_register(name="apa", mode=REGISTER_MODES["r_w"], description="")

    assert (VhdlAxiLiteWrapperGenerator(register_list, tmp_path).create()).exists()

    register_list.register_objects = []
    assert not (VhdlAxiLiteWrapperGenerator(register_list, tmp_path).create()).exists()
