#!/bin/sh
#
#__authors__ = 'Bruno Adelé <bruno@adele.im>'
#__copyright__ = 'Copyright (C) 2014 Bruno Adelé'
#__description__ = """Tools for searching the radio of signal"""
#__license__ = 'GPL'
#__version__ = '0.0.1'

# Sample utilisation record_stations airport 80 "-f 118.5M -f 128.2M"
if [ "$#" -ne 4 ]; then
    echo "usage: $0 mode prefix squetch rtl_fm_options"
    echo "Global parameters in the script"
    echo ""
    echo "ex: $0 am airport 80 \"-f 118.5M -f 128.8M\""
    exit
fi

MODE=$1
PREFIX=$2
SQUETCH=$3
PARAMS="$4"

# Global SDR parameters
PPM=57
GAIN=49.2
ROOTDIR=~/tmp/sdr
PLAYFREQ=12000

# Set samplerate for mode
if [ "$MODE" == "am" ]; then
    SAMPLERATE="160k"
else
    SAMPLERATE=$PLAYFREQ
fi

# Record station
rtl_fm  -M $MODE $PARAMS -p $PPM  -s $SAMPLERATE -r $PLAYFREQ -g $GAIN -l $SQUETCH | play --buffer 128 -r $PLAYFREQ -t raw -e s -b 16 -c 1 -V1 -