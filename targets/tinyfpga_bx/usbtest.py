from migen import *

from litex.soc.cores import uart
from litex.soc.cores.uart import UARTWishboneBridge

from litescope import LiteScopeAnalyzer
from litescope import LiteScopeIO

from targets.utils import csr_map_update
from targets.tinyfpga_bx.base import BaseSoC

from third_party.valentyusb.valentyusb import usbcore


class USBTestSoC(BaseSoC):
    csr_peripherals = (
        "analyzer",
        "io",
    )
    csr_map_update(BaseSoC.csr_map, csr_peripherals)

    def __init__(self, platform, *args, **kwargs):

        kwargs['cpu_type'] = None
        kwargs['integrated_rom_size'] = 0
        kwargs['integrated_sram_size'] = 0
        BaseSoC.__init__(self, platform, *args, with_uart=False, **kwargs)

        self.add_cpu(UARTWishboneBridge(platform.request("serial"), self.clk_freq, baudrate=115200))
        self.add_wb_master(self.cpu.wishbone)

        # ValentyUSB
        usb_pads = platform.request("usb")
        usb_device = usbcore.UsbDevice(usb_pads.d_p, usb_pads.d_n, 0)
        self.submodules += ClockDomainsRenamer("usb_48")(usb_device)

        # Litescope for analyzing the BIST output
        # --------------------
        self.submodules.io = LiteScopeIO(8)
        self.comb += platform.request("user_led", 0).eq(self.io.output[0])
        # Give litescope control over the pullup.
        self.comb += usb_pads.pullup.eq(self.io.output[1])

        analyzer_signals = [
            usb_device.usb_tx_en,
            usb_device.usb_p_tx,
            usb_device.usb_n_tx,
            usb_device.usb_p_rx,
            usb_device.usb_n_rx,
        ]
        self.submodules.analyzer = LiteScopeAnalyzer(analyzer_signals, 256)

    def do_exit(self, vns, filename="test/analyzer.csv"):
        self.analyzer.export_csv(vns, filename)


SoC = USBTestSoC
