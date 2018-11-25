from migen import *

from litex.soc.cores import uart
from litex.soc.cores.uart import UARTWishboneBridge
from litex.soc.integration.soc_core import mem_decoder

from litescope import LiteScopeAnalyzer
from litescope import LiteScopeIO

from targets.utils import csr_map_update
from targets.tinyfpga_bx.base import BaseSoC

from third_party.valentyusb.valentyusb import usbcore


class USBTestSoC(BaseSoC):
    csr_peripherals = (
        "analyzer",
        "io",
        "usb",
    )
    csr_map_update(BaseSoC.csr_map, csr_peripherals)

    interrupt_map = {
        "usb": 3,
    }
    interrupt_map.update(BaseSoC.interrupt_map)

    mem_map = {
        "usb": 0x40000000,  # (default shadow @0xa0000000)
    }
    mem_map.update(BaseSoC.mem_map)

    def __init__(self, platform, *args, **kwargs):

        kwargs['cpu_type'] = None
        kwargs['integrated_rom_size'] = 0
        kwargs['integrated_sram_size'] = 0
        BaseSoC.__init__(self, platform, *args, with_uart=False, **kwargs)

        self.add_cpu(UARTWishboneBridge(platform.request("serial"), self.clk_freq, baudrate=115200))
        self.add_wb_master(self.cpu.wishbone)

        # ValentyUSB
        usb_pads = platform.request("usb")
        usb_iobuf = usbcore.UsbIoBuf(usb_pads.d_p, usb_pads.d_n)
        self.submodules.usb = usbcore.UsbDeviceCpuInterface(usb_iobuf)

        self.add_wb_slave(mem_decoder(self.mem_map["usb"]), self.usb.bus)
        self.add_memory_region(
            "usb", self.mem_map["usb"] | self.shadow_base, 512)

        # Litescope for analyzing the BIST output
        # --------------------
        led = Signal()
        self.submodules.io = LiteScopeIO(8)
        self.comb += [
            led.eq(self.io.output[0]),
            platform.request("user_led", 0).eq(led),
        ]
        # Give litescope control over the pullup.
        self.comb += usb_pads.pullup.eq(self.io.output[1])

        analyzer_signals = [
            led,
            #usb_pads.pullup,
            #usb_device.usb_tx_en,
            #usb_device.usb_p_tx,
            #usb_device.usb_n_tx,
            #usb_device.usb_p_rx,
            #usb_device.usb_n_rx,
        ]
        self.submodules.analyzer = LiteScopeAnalyzer(analyzer_signals, 1024) #, clock_domain="usb_48")

    def do_exit(self, vns, filename="test/analyzer.csv"):
        self.analyzer.export_csv(vns, filename)


SoC = USBTestSoC
