import sys
import struct
import os.path
import argparse

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.build.generic_platform import Pins, Subsignal, IOStandard
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from gateware import info
#from gateware import cas
from gateware import spi_flash

from targets.utils import csr_map_update


serial =  [
    ("serial", 0,
        Subsignal("rx", Pins("GPIO:0")), # Pin 1 - A2 - Silkscreen 1
        Subsignal("tx", Pins("GPIO:1")), # Pin 2 - A1 - Silkscreen 2
        IOStandard("LVCMOS33")
    )
]


class _CRG(Module):
    def __init__(self, platform):
        clk16 = platform.request("clk16")

        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.usb_48 = ClockDomain(reset_less=True)
        self.reset = Signal()

        # FIXME: Use PLL, increase system clock to 32 MHz, pending nextpnr
        # fixes.
        self.comb += self.cd_sys.clk.eq(clk16)

        # POR reset logic- POR generated from sys clk, POR logic feeds sys clk
        # reset.
        self.clock_domains.cd_por = ClockDomain()
        reset_delay = Signal(12, reset=4095)
        self.comb += [
            self.cd_por.clk.eq(self.cd_sys.clk),
            self.cd_sys.rst.eq(reset_delay != 0)
        ]
        self.sync.por += \
            If(reset_delay != 0,
                reset_delay.eq(reset_delay - 1)
            )
        self.specials += AsyncResetSynchronizer(self.cd_por, self.reset)

        self.specials += [
            Instance(
                "SB_PLL40_CORE",
                # Parameters
                p_DIVR = 0,
                p_DIVF = 0b0101111,
                p_DIVQ = 0b100,
                p_FILTER_RANGE = 1,
                p_FEEDBACK_PATH = "SIMPLE",
                p_DELAY_ADJUSTMENT_MODE_FEEDBACK = "FIXED",
                p_FDA_FEEDBACK = 0,
                p_DELAY_ADJUSTMENT_MODE_RELATIVE = "FIXED",
                p_FDA_RELATIVE = 0,
                p_SHIFTREG_DIV_MODE = 0,
                p_PLLOUT_SELECT = "GENCLK",
                p_ENABLE_ICEGATE = 0,
                # IO
                i_REFERENCECLK = clk16,
                o_PLLOUTCORE = self.usb_48.clk,
                #o_PLLOUTGLOBAL,
                #i_EXTFEEDBACK,
                #i_DYNAMICDELAY,
                #o_LOCK,
                i_BYPASS = 0,
                i_RESETB = 1,
                #i_LATCHINPUTVALUE,
                #o_SDO,
                #i_SDI,
            ),
        ]


class BaseSoC(SoCCore):
    csr_peripherals = (
        "spiflash",
#        "cas",
        "info",
    )
    csr_map_update(SoCCore.csr_map, csr_peripherals)

    mem_map = {
        "spiflash": 0x20000000,  # (default shadow @0xa0000000)
    }
    mem_map.update(SoCCore.mem_map)

    def __init__(self, platform, **kwargs):
        if 'integrated_rom_size' not in kwargs:
            kwargs['integrated_rom_size']=0
        if 'integrated_sram_size' not in kwargs:
            kwargs['integrated_sram_size']=0x2800

        # FIXME: Force either lite or minimal variants of CPUs; full is too big.

        platform.add_extension(serial)
        clk_freq = int(16e6)

        # Extra 0x28000 is due to bootloader bitstream.
        kwargs['cpu_reset_address']=self.mem_map["spiflash"]+platform.gateware_size+platform.bootloader_size
        SoCCore.__init__(self, platform, clk_freq, **kwargs)

        self.submodules.crg = _CRG(platform)
        self.platform.add_period_constraint(self.crg.cd_sys.clk, 1e9/clk_freq)

        self.submodules.info = info.Info(platform, self.__class__.__name__)

        # Control and Status
#        self.submodules.cas = cas.ControlAndStatus(platform, clk_freq)

        # SPI flash peripheral
        self.submodules.spiflash = spi_flash.SpiFlashSingle(
            platform.request("spiflash"),
            dummy=platform.spiflash_read_dummy_bits,
            div=platform.spiflash_clock_div)
        self.add_constant("SPIFLASH_PAGE_SIZE", platform.spiflash_page_size)
        self.add_constant("SPIFLASH_SECTOR_SIZE", platform.spiflash_sector_size)
        self.register_mem("spiflash", self.mem_map["spiflash"],
            self.spiflash.bus, size=platform.spiflash_total_size)

        bios_size = 0x8000
        self.add_constant("ROM_DISABLE", 1)
        self.add_memory_region("rom", kwargs['cpu_reset_address'], bios_size)
        self.flash_boot_address = self.mem_map["spiflash"]+platform.gateware_size+bios_size+platform.bootloader_size

        # We don't have a DRAM, so use the remaining SPI flash for user
        # program.
        self.add_memory_region("user_flash",
            self.flash_boot_address,
            # Leave a grace area- possible one-by-off bug in add_memory_region?
            # Possible fix: addr < origin + length - 1
            platform.spiflash_total_size - (self.flash_boot_address - self.mem_map["spiflash"]) - 0x100)

        # Disable USB activity until we switch to a USB UART.
        #self.comb += [platform.request("usb").pullup.eq(0)]

        # Arachne-pnr is unsupported- it has trouble routing this design
        # on this particular board reliably. That said, annotate the build
        # template anyway just in case.
        # Disable final deep-sleep power down so firmware words are loaded
        # onto softcore's address bus.
        platform.toolchain.build_template[3] = "icepack -s {build_name}.txt {build_name}.bin"
        platform.toolchain.nextpnr_build_template[2] = "icepack -s {build_name}.txt {build_name}.bin"

SoC = BaseSoC
