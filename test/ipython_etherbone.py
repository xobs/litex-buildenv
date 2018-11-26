#!/usr/bin/env python3

from IPython import embed

from litescope.software.driver.analyzer import LiteScopeAnalyzerDriver

from common import *
from make import get_args, get_testdir


def main():
    args, wb = connect("LiteX Etherbone Interactive Console")
    print_memmap(wb)
    print()

    analyzer_csv = '{}/analyzer.csv'.format(get_testdir(args))
    if os.path.exists(analyzer_csv):
        analyzer = LiteScopeAnalyzerDriver(wb.regs, "analyzer", config_csv=analyzer_csv, debug=True)
    else:
        print("WARNING: No litescope csv found at {},\nAssuming litescope not included in design!".format(analyzer_csv))

    print("Packet Count:", wb.regs.usb_pkt_count.read())
    def setup():
        for v in [0x12, 0x01, 0x00 , 0x02 , 0x00, 0x00, 0x00, 0x40, 0x9A, 0x23, 0x21, 0x80, 0x00, 0x01, 0x02, 0x03, 0x01, 0x01]:
            wb.regs.usb_ep_0_in_head.write(v)

    try:
        embed()
    finally:
        wb.close()


if __name__ == "__main__":
    main()
