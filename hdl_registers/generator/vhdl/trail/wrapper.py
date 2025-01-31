# --------------------------------------------------------------------------------------------------
# Copyright (c) Lukas Vik. All rights reserved.
#
# This file is part of the hdl-registers project, an HDL register generator fast enough to run
# in real time.
# https://hdl-registers.com
# https://github.com/hdl-registers/hdl-registers
# --------------------------------------------------------------------------------------------------

# Standard libraries
from pathlib import Path
from typing import Any

# First party libraries
from hdl_registers.generator.vhdl.vhdl_generator_common import VhdlGeneratorCommon
from hdl_registers.register_mode import HardwareAccessDirection, SoftwareAccessDirection


class VhdlTrailWrapperGenerator(VhdlGeneratorCommon):
    """
    Generate a VHDL wrapper around a generic TRAIL register file with correct generics and ports.
    """

    __version__ = "1.0.5"

    SHORT_DESCRIPTION = "VHDL TRAIL register file"

    @property
    def output_file(self) -> Path:
        """
        Result will be placed in this file.
        """
        return self.output_folder / f"{self.name}_register_file_trail.vhd"

    def create(self, **kwargs: Any) -> Path:
        """
        See super class for API details.

        Overloaded here because this file shall only be created if the register list
        actually has any registers.
        """
        return self._create_if_there_are_registers_otherwise_delete_file(**kwargs)

    def get_code(self, **kwargs: Any) -> str:
        """
        Get VHDL code for a wrapper around the generic AXi_lite register file from hdl-modules:
        """
        entity_name = self.output_file.stem

        up_port = f"    regs_up : in {self.name}_regs_up_t := {self.name}_regs_up_init;\n"
        has_any_up = self.has_any_hardware_accessible_register(HardwareAccessDirection.UP)

        down_port = (
            f"    regs_down : out {self.name}_regs_down_t " f":= {self.name}_regs_down_init;\n"
        )
        has_any_down = self.has_any_hardware_accessible_register(HardwareAccessDirection.DOWN)

        was_read_port, was_written_port = self._get_was_accessed_ports()

        # Note that either of 'reg_was_read' or 'reg_was_written' is always present, otherwise
        # there would be no registers and we would not create this wrapper.
        # Hence it is safe to always end the 'regs_up'/'regs_down' ports with a semicolon.
        entity = f"""\
entity {entity_name} is
  port (
    clk : in std_ulogic;
    --# {{}}
    --# Register control bus.
    trail_operation : in trail_operation_t;
    trail_response : out trail_response_t := trail_response_init;
    --# {{}}
    -- Register values.
{up_port if has_any_up else ""}\
{down_port if has_any_down else ""}\
    --# {{}}
    -- Each bit is pulsed for one cycle when the corresponding register is read/written.
{was_read_port}\
{was_written_port}\
  );
end entity;
"""

        up_conversion = """

  ------------------------------------------------------------------------------
  -- Combinatorially convert the register record to a list of SLV values that can be handled
  -- by the generic register file implementation.
  assign_regs_up : process(regs_up)
  begin
    regs_up_slv <= to_slv(regs_up);
  end process;
"""
        down_conversion = f"""

  ------------------------------------------------------------------------------
  -- Combinatorially convert the list of SLV values from the generic register file into the record
  -- we want to use in our application.
  assign_regs_down : process(regs_down_slv)
  begin
    regs_down <= to_{self.name}_regs_down(regs_down_slv);
  end process;
"""

        was_read_conversion = f"""

  ------------------------------------------------------------------------------
  -- Combinatorially convert status mask to a record where only the applicable registers \
are present.
  assign_reg_was_read : process(reg_was_read_slv)
  begin
    reg_was_read <= to_{self.name}_reg_was_read(reg_was_read_slv);
  end process;
"""

        was_written_conversion = f"""

  ------------------------------------------------------------------------------
  -- Combinatorially convert status mask to a record where only the applicable registers \
are present.
  assign_reg_was_written : process(reg_was_written_slv)
  begin
    reg_was_written <= to_{self.name}_reg_was_written(reg_was_written_slv);
  end process;
"""

        vhdl = f"""\
-- -----------------------------------------------------------------------------
-- AXI-Lite register file for the '{self.name}' module registers.
--
-- Is a wrapper around the generic AXI-Lite register file from hdl-modules:
-- * https://hdl-modules.com/modules/register_file/register_file.html#axi-lite-reg-file-vhd
-- * https://github.com/hdl-modules/hdl-modules/blob/main/modules/register_file/\
src/axi_lite_register_file.vhd
--
-- Sets correct generics, and performs conversion to the easy-to-use register record types.
-- -----------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;

library trail;
use trail.trail_pkg.all;

library register_file;
use register_file.register_file_pkg.all;

use work.{self.name}_regs_pkg.all;
use work.{self.name}_register_record_pkg.all;


{entity}
architecture a of {entity_name} is

  signal regs_up_slv, regs_down_slv : {self.name}_regs_t := {self.name}_regs_init;

  signal reg_was_read_slv, reg_was_written_slv : {self.name}_reg_was_accessed_t := (
    others => '0'
  );

begin

  ------------------------------------------------------------------------------
  -- Instantiate the generic AXI-Lite register file from
  -- * https://hdl-modules.com/modules/register_file/register_file.html#axi-lite-reg-file-vhd
  -- * https://github.com/hdl-modules/hdl-modules/blob/main/modules/register_file/src/\
axi_lite_register_file.vhd
  trail_register_file_inst : entity register_file.trail_register_file
    generic map (
      registers => {self.name}_register_map,
      default_values => {self.name}_regs_init
    )
    port map(
      clk => clk,
      --
      trail_operation => trail_operation,
      trail_response => trail_response,
      --
      regs_up => regs_up_slv,
      regs_down => regs_down_slv,
      --
      reg_was_read => reg_was_read_slv,
      reg_was_written => reg_was_written_slv
    );
{up_conversion if has_any_up else ""}\
{down_conversion if has_any_down else ""}\
{was_read_conversion if was_read_port else ""}\
{was_written_conversion if was_written_port else ""}\

end architecture;
"""

        return vhdl

    def _get_was_accessed_ports(self) -> tuple[str, str]:
        has_any_read = self.has_any_software_accessible_register(
            direction=SoftwareAccessDirection.READ
        )
        has_any_write = self.has_any_software_accessible_register(
            direction=SoftwareAccessDirection.WRITE
        )

        # If present, is always the last port so no trailing semicolon needed.
        was_written = (
            (
                f"    reg_was_written : out {self.name}_reg_was_written_t := "
                f"{self.name}_reg_was_written_init\n"
            )
            if has_any_write
            else ""
        )

        was_read = (
            (
                f"    reg_was_read : out {self.name}_reg_was_read_t := "
                f"{self.name}_reg_was_read_init"
            )
            if has_any_read
            else ""
        )

        if has_any_read:
            was_read += ";\n" if was_written else "\n"

        return was_read, was_written
