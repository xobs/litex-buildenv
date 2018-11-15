from litex.soc.cores import uart
from litex.soc.cores.uart import UARTWishboneBridge

from litescope import LiteScopeAnalyzer
from litescope import LiteScopeIO

from targets.utils import csr_map_update
from targets.tinyfpga_bx.base import BaseSoC


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

        self.add_cpu(UARTWishboneBridge(platform.request("serial"), self.clk_freq, baudrate=19200))
        self.add_wb_master(self.cpu.wishbone)

        # Litescope for analyzing the BIST output
        # --------------------
        #self.submodules.io = LiteScopeIO(8)
        #self.comb += platform.request("user_led", 0).eq(self.io.output[0])

        analyzer_signals = [
            self.spiflash.bus,
        #    self.spiflash.cs_n,
        #    self.spiflash.clk,
        #    self.spiflash.dq_oe,
        #    self.spiflash.dqi,
        #    self.spiflash.sr,
        ]
        self.submodules.analyzer = LiteScopeAnalyzer(analyzer_signals, 256)

    def do_exit(self, vns, filename="test/analyzer.csv"):
        self.analyzer.export_csv(vns, filename)


SoC = USBTestSoC
