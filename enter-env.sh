#!/bin/bash

exec bash --rcfile <(echo '. ~/.bashrc; echo "Platform: $PLATFORM"; export PLATFORM=fomu_evt CPU_VARIANT=minimal TARGET=usb FIRMWARE=tinyusb; source scripts/enter-env.sh || exit 1') -i
#exec bash --rcfile <(echo '. ~/.bashrc; echo "Platform: $PLATFORM"; export PLATFORM=fomu_evt CPU_VARIANT=min CPU=vexriscv TARGET=usb FIRMWARE=tinyusb; source scripts/enter-env.sh || exit 1') -i
