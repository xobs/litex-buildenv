from migen import *

from litex.soc.cores import uart
from litex.soc.cores.uart import UARTWishboneBridge
from litex.soc.integration.soc_core import *

from targets.utils import csr_map_update
from targets.tinyfpga_bx.base import serial, _CRG

from third_party.valentyusb.valentyusb import usbcore

from gateware import spi_flash
from gateware import firmware


class USBSoC(SoCCore):
    csr_peripherals = (
        "spiflash",
#        "cas",
#        "info",
        "usb",
    )
    csr_map_update(SoCCore.csr_map, csr_peripherals)

    mem_map = {
        "spiflash": 0x20000000,  # (default shadow @0xa0000000)
    }
    mem_map.update(SoCCore.mem_map)

    interrupt_map = {
        "usb": 3,
    }
    interrupt_map.update(SoCCore.interrupt_map)

    def __init__(self, platform, **kwargs):

        # The TinyFPGA BX has 128kbit of blockram == 16kbytes
        # Each BRAM is 512bytes == 32 BRAM blocks
        # Need 4 BRAM blocks for USB, leaving 28.
        #  - 8kbytes ROM - 16 x BRAMs
        #  - 4kbytes RAM -  8 x BRAMs

        if 'integrated_rom_size' not in kwargs:
            kwargs['integrated_rom_size']=0
        if 'integrated_sram_size' not in kwargs:
            kwargs['integrated_sram_size']=1*1024
        if 'integrated_main_ram_size' not in kwargs:
            kwargs['integrated_main_ram_size']=0 #4*1024

        kwargs['integrated_rom_init'] = [0]

        if 'cpu_variant' not in kwargs:
            kwargs['cpu_variant']='minimal'

        #kwargs['uart_baudrate']=19200

        platform.add_extension(serial)

        clk_freq = int(16e6)

        SoCCore.__init__(self, platform, clk_freq, **kwargs)

        # Map the firmware directly into ROM
        firmware_rom_size = 11*1024
        firmware_filename = "build/tinyfpga_bx_usb_{}.minimal/software/stub/firmware.bin".format(
                kwargs.get('cpu_type', 'lm32'))
        self.submodules.firmware_rom = firmware.FirmwareROM(firmware_rom_size, firmware_filename)
        self.register_mem("rom", self.mem_map["rom"], self.firmware_rom.bus, firmware_rom_size)
        self._memory_regions.append(("user_flash", self.mem_map['rom'], firmware_rom_size))

        # Make sram and main_ram into the same region
        #self._memory_regions.append(("sram", self.mem_map['main_ram'], 4*1024))

        self.submodules.crg = _CRG(platform)
        self.platform.add_period_constraint(self.crg.cd_sys.clk, 1e9/clk_freq)

#        self.submodules.info = info.Info(platform, self.__class__.__name__)

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

        # ValentyUSB
        usb_pads = platform.request("usb")
        usb_iobuf = usbcore.UsbIoBuf(usb_pads.d_p, usb_pads.d_n)
        self.submodules.usb = usbcore.UsbDeviceCpuInterface(usb_iobuf)

        # Disable USB activity until we switch to a USB UART.
        #self.comb += [platform.request("usb").pullup.eq(0)]

        # Arachne-pnr is unsupported- it has trouble routing this design
        # on this particular board reliably. That said, annotate the build
        # template anyway just in case.
        # Disable final deep-sleep power down so firmware words are loaded
        # onto softcore's address bus.
        platform.toolchain.build_template[3] = "icepack -s {build_name}.txt {build_name}.bin"
        platform.toolchain.nextpnr_build_template[2] = "icepack -s {build_name}.txt {build_name}.bin"


SoC = USBSoC
