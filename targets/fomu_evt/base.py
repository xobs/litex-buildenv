import sys
import struct
import os.path
import argparse

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.build.generic_platform import Pins, Subsignal, IOStandard
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from gateware import up5kspram
from gateware import cas
from gateware import spi_flash

from targets.utils import csr_map_update
from platforms import fomu_evt

from litex.soc.interconnect import wishbone

class RandomFirmwareROM(wishbone.SRAM):
    def __init__(self, size):
        import random
        # Seed the random data with a fixed number, so different bitstreams
        # can all share firmware.
        random.seed(2373)
        data = []
        for d in range(int(size / 4)):
            data.append(random.getrandbits(32))
        data_size = len(data)*4
        assert data_size > 0
        assert data_size <= size, (
            "Firmware is too big! {} bytes > {} bytes".format(
                data_size, size))
        print("Firmware {} bytes of random data".format(
            data_size))
        wishbone.SRAM.__init__(self, size, read_only=True, init=data)

class _CRG(Module):
    def __init__(self, platform):
        clk48 = platform.request("clk48")

        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.cd_usb_48 = ClockDomain(reset_less=True)

        self.reset = Signal()
        self.clksys = Signal()

        # Use PLL to go from 48 MHz to 16 MHz
        self.specials += [
            Instance("SB_PLL40_CORE",        
                p_FEEDBACK_PATH="SIMPLE",
                p_PLLOUT_SELECT="GENCLK",
                p_DIVR=2,
                p_DIVF=63,
                p_DIVQ=6,
                p_FILTER_RANGE=1,

                i_BYPASS=0, i_RESETB=1,
                i_REFERENCECLK = clk48,
                o_PLLOUTCORE = self.cd_sys.clk,
                # o_LOCK=pll_locked_unbuffered
            ),
        ]
        #self.platform.add_period_constraint(self.usb_48.clk, 1e9/48e9)

        # FIXME: Use PLL, increase system clock to 32 MHz, pending nextpnr
        # fixes.
        self.comb += self.cd_usb_48.clk.eq(clk48)

        # POR reset logic- POR generated from sys clk, POR logic feeds sys clk
        # reset.
        self.clock_domains.cd_por = ClockDomain()
        reset_delay = Signal(12, reset=4095)
        self.comb += [
            self.cd_por.clk.eq(self.cd_sys.clk),
            self.cd_sys.rst.eq(reset_delay != 0),
        ]
        self.sync.por += \
            If(reset_delay != 0,
                reset_delay.eq(reset_delay - 1)
            )
        self.specials += AsyncResetSynchronizer(self.cd_por, self.reset)

class BaseSoC(SoCCore):
    csr_peripherals = (
        # "spiflash",
        "cas",
    )
    csr_map_update(SoCCore.csr_map, csr_peripherals)

    # mem_map = {
    #     "spiflash": 0x20000000,  # (default shadow @0xa0000000)
    # }
    # mem_map.update(SoCCore.mem_map)

    def __init__(self, platform, **kwargs):
        if 'integrated_rom_size' not in kwargs:
            kwargs['integrated_rom_size']=0
        if 'integrated_sram_size' not in kwargs:
            kwargs['integrated_sram_size']=0
        kwargs['cpu_reset_address'] = 0

        # self.flash_boot_address = self.mem_map["spiflash"]+platform.gateware_size+bios_size

        # FIXME: Force either lite or minimal variants of CPUs; full is too big.

        # Assume user still has LEDs/Buttons still attached to the PCB or as
        # a PMOD; pinout is identical either way.
        #platform.add_extension(fomu_evt.break_off_pmod)
        clk_freq = int(16e6)
        usb_clk_freq = int(48e6)

        print("ident: " + kwargs['ident'])
        kwargs['ident']=None
        # kwargs['cpu_reset_address']=self.mem_map["spiflash"]+platform.gateware_size
        SoCCore.__init__(self, platform, clk_freq,
                        with_ctrl=False,
                        **kwargs)

        bios_size = 0x2c00
        self.submodules.firmware_ram = RandomFirmwareROM(bios_size)
        self.add_constant("ROM_DISABLE", 1)
        # self.add_memory_region("rom", kwargs['cpu_reset_address'], bios_size)
        self.register_rom(self.firmware_ram.bus, bios_size)

        self.submodules.crg = _CRG(platform)
        self.platform.add_period_constraint(self.crg.cd_sys.clk, 1e9/clk_freq)

        # Control and Status
        # self.submodules.cas = cas.ControlAndStatus(platform, clk_freq)

        # SPI flash peripheral
        # TODO: Inferred tristate not currently supported by nextpnr; upgrade
        # to spiflash4x when possible.
        # self.submodules.spiflash = spi_flash.SpiFlashDualQuad(
        #     platform.request("spiflash4x"),
        # self.submodules.spiflash = spi_flash.SpiFlashSingle(
        #     platform.request("spiflash"),
        #     dummy=platform.spiflash_read_dummy_bits,
        #     div=platform.spiflash_clock_div,
        #     endianness=self.cpu.endianness)
        # self.add_constant("SPIFLASH_PAGE_SIZE", platform.spiflash_page_size)
        # self.add_constant("SPIFLASH_SECTOR_SIZE", platform.spiflash_sector_size)
        # self.register_mem("spiflash", self.mem_map["spiflash"],
        #     self.spiflash.bus, size=platform.spiflash_total_size)

        # bios_size = 0x8000
        # self.add_constant("ROM_DISABLE", 1)
        # self.add_memory_region("rom", kwargs['cpu_reset_address'], bios_size)
        # self.flash_boot_address = self.mem_map["spiflash"]+platform.gateware_size+bios_size

        # SPRAM- UP5K has single port RAM, might as well use it as SRAM to
        # free up scarce block RAM.
        self.submodules.spram = up5kspram.Up5kSPRAM(size=128*1024)
        # self.submodules.sprom = up5kspram.Up5kSPRAM(size=64*1024)
        self.register_mem("sram", 0x10000000, self.spram.bus, 128*1024)
        # self.register_mem("user_ram", 0x20000000, self.spram.bus, 64*1024)

        # # We don't have a DRAM, so use the remaining SPI flash for user
        # # program.
        # self.add_memory_region("user_flash",
        #     self.flash_boot_address,
        #     # Leave a grace area- possible one-by-off bug in add_memory_region?
        #     # Possible fix: addr < origin + length - 1
        #     platform.spiflash_total_size - (self.flash_boot_address - self.mem_map["spiflash"]) - 0x100)

        # Disable final deep-sleep power down so firmware words are loaded
        # onto softcore's address bus.
        platform.toolchain.build_template[3] = "icepack -s {build_name}.txt {build_name}.bin"
        platform.toolchain.nextpnr_build_template[2] = "icepack -s {build_name}.txt {build_name}.bin"

        # pad3 = platform.request("pmod_n", 3)
        # pad2 = platform.request("pmod_n", 2)
        # pad1 = platform.request("pmod_n", 1)
        # pad0 = platform.request("pmod_n", 0)
        # counter = Signal(4)
        # self.sync += [
        #     counter.eq(counter+1),
        #     pad3.eq(counter[0]),
        #     pad2.eq(counter[1]),
        #     pad1.eq(counter[2]),
        #     pad0.eq(counter[3]),
        # ]

SoC = BaseSoC
