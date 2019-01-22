from litex.soc.cores import uart
from litex.soc.cores.uart import UARTWishboneBridge

from litedram.frontend.bist import LiteDRAMBISTGenerator, LiteDRAMBISTChecker

from litescope import LiteScopeAnalyzer
from litescope import LiteScopeIO

from gateware.memtest import LiteDRAMBISTCheckerScope

from targets.utils import csr_map_update
from targets.fomu_evt.base import BaseSoC

from third_party.valentyusb.valentyusb import usbcore
from third_party.valentyusb.valentyusb.usbcore import io as usbio
from third_party.valentyusb.valentyusb.usbcore.cpu import unififo
from third_party.valentyusb.valentyusb.usbcore.endpoint import EndpointType

class MemTestSoC(BaseSoC):
    csr_peripherals = (
        "analyzer",
        "io",
        "usb",
    )
    csr_map_update(BaseSoC.csr_map, csr_peripherals)

    def __init__(self, platform, *args, **kwargs):
        kwargs['cpu_type'] = None
        BaseSoC.__init__(self, platform, *args, with_uart=False, **kwargs)

        self.add_cpu_or_bridge(UARTWishboneBridge(platform.request("serial"), self.clk_freq, baudrate=115200))
        self.add_wb_master(self.cpu_or_bridge.wishbone)

        # Litescope for analyzing the BIST output
        # --------------------
        self.submodules.io = LiteScopeIO(8)
        self.comb += platform.request("user_ledg_n", 0).eq(self.io.output[0])
        self.comb += platform.request("user_led_n", 0).eq(self.io.output[1])
        self.comb += platform.request("user_ledr_n", 0).eq(self.io.output[2])
        print(hex(self.mem_map["rom"]))
        print(hex(self.cpu_reset_address))

        # ValentyUSB
        usb_pads = platform.request("usb")
        usb_iobuf = usbio.IoBuf(usb_pads.d_p, usb_pads.d_n, usb_pads.pullup)
        self.submodules.usb = unififo.UsbUniFifo(usb_iobuf)

        analyzer_signals = [
            self.usb.rx.bit_dat,
            self.usb.rx.bit_se0,
            # self.usb.rx.clock_data_recovery.line_state_valid,
            # self.usb.rx.clock_data_recovery.line_state_dj,
            # self.usb.rx.clock_data_recovery.line_state_dk,
            # self.usb.rx.clock_data_recovery.line_state_se0,
            # self.usb.rx.clock_data_recovery.line_state_se1,
        ]
        self.submodules.analyzer = LiteScopeAnalyzer(analyzer_signals, 1024, clock_domain="usb_12")


    def do_exit(self, vns, filename="test/analyzer.csv"):
        self.analyzer.export_csv(vns, filename)


SoC = MemTestSoC
