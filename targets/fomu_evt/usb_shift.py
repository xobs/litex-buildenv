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
import platforms.fomu_evt as fomu_evt
from targets.fomu_evt.base import BaseSoC
from third_party.valentyusb.valentyusb import usbcore
from third_party.valentyusb.valentyusb.usbcore import io as usbio
from third_party.valentyusb.valentyusb.usbcore.cpu import unififo
from third_party.valentyusb.valentyusb.usbcore.endpoint import EndpointType

from litex.soc.interconnect import wishbone

class RandomFirmwareROM(wishbone.SRAM):
    def __init__(self, size, seed=2373):
        import random
        # Seed the random data with a fixed number, so different bitstreams
        # can all share firmware.
        random.seed(seed)
        data = []
        for d in range(int(size / 4)):
            data.append(random.getrandbits(32))
        print("Firmware {} bytes of random data".format(size))
        wishbone.SRAM.__init__(self, size, read_only=True, init=data)


class USBNoBios(SoCCore):
    csr_peripherals = (
        "spiflash",
        "usb",
        #"cas",
    )
    csr_map_update(SoCCore.csr_map, csr_peripherals)

    mem_map = {
        "spiflash": 0x20000000,  # (default shadow @0xa0000000)
    }
    mem_map.update(SoCCore.mem_map)

    interrupt_map = {
        "usb": 3,
    }
    interrupt_map.update(BaseSoC.interrupt_map)

    def __init__(self, platform, **kwargs):
        kwargs['integrated_rom_size']=0
        kwargs['integrated_sram_size']=0

        clk_freq = int(12e6)

        kwargs['cpu_reset_address']=0
        kwargs['with_ctrl']=False
        BaseSoC.__init__(self, platform, skip_spi_boot=True, **kwargs)

        bios_size = 0x1000
        self.submodules.random_rom = RandomFirmwareROM(bios_size)
        self.add_constant("ROM_DISABLE", 1)
        self.register_rom(self.random_rom.bus, bios_size)

        # ValentyUSB

        usb_pads = platform.request("usb")
        usb_iobuf = usbio.IoBuf(usb_pads.d_p, usb_pads.d_n, usb_pads.pullup)
        self.submodules.usb = unififo.UsbUniFifo(usb_iobuf)

        # Disable final deep-sleep power down so firmware words are loaded
        # onto softcore's address bus.
        platform.toolchain.build_template[3] = "icepack -s {build_name}.txt {build_name}.bin"
        platform.toolchain.nextpnr_build_template[2] = "icepack -s {build_name}.txt {build_name}.bin"

SoC = USBNoBios
