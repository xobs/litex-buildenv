#!/bin/bash

if [ "x$1" = "xlm32" ]
then
    exec bash --rcfile <(echo '. ~/.bashrc; echo "Platform: $PLATFORM"; export PLATFORM=fomu_evt CPU_VARIANT=minimal TARGET=usb FIRMWARE=tinyusb; source scripts/enter-env.sh || exit 1') -i
elif [ "x$1" = "xvexriscv" ]
then
    exec bash --rcfile <(echo '. ~/.bashrc; echo "Platform: $PLATFORM"; export PLATFORM=fomu_evt CPU_VARIANT=min CPU=vexriscv TARGET=usb FIRMWARE=tinyusb; source scripts/enter-env.sh || exit 1') -i
else
    echo "No CPU specified"
    echo "Usage: $0 [lm32|vexriscv]"
    exit 1
fi