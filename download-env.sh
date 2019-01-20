#!/bin/bash

if [ "x$1" = "xlm32" ]
then
    PLATFORM=fomu_evt CPU_VARIANT=minimal TARGET=usb FIRMWARE=tinyusb ./scripts/download-env.sh
    echo "Run this once you enter the env:"
    echo "conda install gcc-riscv32-elf-newlib"
elif [ "x$1" = "xvexriscv" ]
then
    PLATFORM=fomu_evt CPU_VARIANT=min CPU=vexriscv TARGET=usb FIRMWARE=tinyusb ./scripts/download-env.sh
    echo "Run this once you enter the env:"
    echo "conda install gcc-lm32-elf-newlib"
else
    echo "No CPU specified"
    echo "Usage: $0 [lm32|vexriscv]"
    exit 1
fi
