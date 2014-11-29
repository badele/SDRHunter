#!/usr/bin/env python
# -*- coding: utf-8 -*-

__authors__ = 'Bruno Adelé <bruno@adele.im>'
__copyright__ = 'Copyright (C) 2014 Bruno Adelé'
__description__ = """Tools for searching the radio of signal"""
__license__ = 'GPL'
__version__ = '0.0.1'

import os
import sys
import json
import shlex
import pprint
import argparse
import subprocess

import numpy as np
from tabulate import tabulate

# Unit conversion
HzUnities = {'M': 1e6, 'K': 1e3}
secUnities = {'S': 1, 'M': 60, 'H': 3600}


def loadJSON(filename):
    exists = os.path.isfile(filename)
    if exists:
        configlines = open(filename).read()
        infos = json.loads(configlines)

        if int(np.log2(infos['global']['nbsamples_freqs'])) != np.log2(infos['global']['nbsamples_freqs']):
            raise Exception("Please chose a dimension ^2")

        return infos


    return None


def saveJSON(filename,content):
    with open(filename, 'w') as f:
        jsontext = json.dumps(
            content, sort_keys=True,
            indent=4, separators=(',', ': ')
        )
        f.write(jsontext)
        f.close()


def Hz2String(floatvalue, unityvalue, addunity=True):

    unity = unityvalue.upper()
    if unity in HzUnities:
        stringvalue = floatvalue / HzUnities[unity]

        if addunity:
            stringvalue = '%f%s' % (stringvalue, unity)

    return stringvalue


def unity2Float(stringvalue, unityvalues):
    # If allready number, we consider is the Hz
    if isinstance(stringvalue, int) or isinstance(stringvalue, float):
        return stringvalue

    stringvalue = stringvalue.upper()
    floatvalue = float(stringvalue[:-1])
    unity = stringvalue[-1].upper()
    if unity not in unityvalues:
        raise Exception("Not unity found '%s' " % stringvalue)

    floatvalue = floatvalue * unityvalues[unity]
    return floatvalue


def Hz2Float(stringvalue):
    return unity2Float(stringvalue, HzUnities)


def sec2Float(stringvalue):
    return unity2Float(stringvalue, secUnities)


def executeShell(cmd):
    cmdargs = shlex.split(cmd)
    p = subprocess.Popen(cmdargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, errors = p.communicate()
    if p.returncode:
        print 'Failed running %s' % cmd
        raise Exception(errors)
    else:
        pass

    return output


def executeRTLPower(dirname, start, end, binsize, interval, quitafter):
    # Create directory if not exists
    if not os.path.isdir(dirname):
        os.makedirs(dirname)

    filename = "%s/%sMhz-%sMhz-%s-%si-%sq" % (
        dirname,
        start,
        end,
        binsize,
        interval,
        quitafter
    )

    # Ignore call rtl_power if file already exist
    csv_filename = "%s.csv" % filename
    exists = os.path.isfile(csv_filename)
    if exists:
        return

    cmd = "rtl_power -f %s:%s:%s -i %s -e %s %s" % (
        start,
        end,
        binsize,
        interval,
        quitafter,
        csv_filename
    )

    # Call rtl_power shell command
    executeShell(cmd)


def showInfo(args):
    infos = loadJSON(args.filename)
    if not infos:
        print "No infos found in %s" % args.filename

    # Show config
    result_scan = []
    if 'configs' in infos:
        for configname in infos['configs']:
            result_scan.append(
                [
                    configname,
                    infos['configs'][configname]['location'],
                    infos['configs'][configname]['antenna'],
                ]
            )

        header = [ 'Config name', 'Location','Antenna' ]
        print tabulate(result_scan, headers=header, stralign="right")

    print ""

    # Show the scan information table
    result_scan = []
    if 'scans' in infos:
        for scanlevel in infos['scans']:
            result_scan.append(
                [
                    scanlevel['freq_start'],
                    scanlevel['freq_end'],
                    scanlevel['windows'],
                    scanlevel['binsize'],
                    scanlevel['interval'],
                    scanlevel['quitafter'],
                    scanlevel['maxlevel_legend'],
                ]
            )

        header = [
            'Freq. Start', 'Freq. End', 'Windows', 'Binsize', 'Interval', 'Quit After', 'Max legend level'
        ]
        print tabulate(result_scan, headers=header, stralign="right")

    # Show global config
    if 'global' in infos:
        pprint.pprint(infos['global'],indent=2)


def scan(args):
    infos = loadJSON(args.filename)

    if 'scans' in infos:
        for scan in infos['scans']:
            scandir = "%s/%s" % (infos['global']['rootdir'], scan['name'])
            freqstart = Hz2Float(scan['freq_start'])
            freqend = Hz2Float(scan['freq_end'])
            scanbw = Hz2Float(scan['windows'])
            interval = scan['interval']
            delta = freqend - freqstart

            nbsamples_lines = infos['global']['nbsamples_lines']
            if 'nbsamples_lines' in scan:
                nbsamples_lines = scan['nbsamples_lines']
            nbsamples_freqs = infos['global']['nbsamples_freqs']
            if 'nbsamples_freqs' in scan:
                nbsamples_lines = scan['nbsamples_freqs']

            binsize = np.ceil(scanbw / (nbsamples_freqs - 1))
            quit_after = sec2Float(interval) * nbsamples_lines

            if (delta % scanbw) != 0:
                step = int((delta / scanbw))
                freqend = freqstart + ((step+1)*scanbw)
                delta = freqend - freqstart

            nbstep = delta / scanbw
            range = np.linspace(freqstart,freqend, num=nbstep, endpoint=False)

            for left_freq in range:
                print "Scan %sMhz-%sMhz" % (int(Hz2String(left_freq,'M', False)),int(Hz2String(left_freq+scanbw,'M', False)))
                executeRTLPower(scandir, Hz2String(left_freq,'M'), Hz2String(left_freq+scanbw,'M'), binsize, interval, quit_after)


def parse_arguments(cmdline=""):
    """Parse the arguments"""

    parser = argparse.ArgumentParser(
        description=__description__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        '-a', '--action',
        action='store',
        dest='action',
        default='infos',
        choices=[
            'infos',
            'scan',
        ],
        help='Action'
    )

    parser.add_argument(
        '-f', '--filename',
        action='store',
        dest='filename',
        default='sdrhunter.json',
        help='JSON config filename'
    )

    parser.add_argument(
        '-c', '--configname',
        action='store',
        dest='configname',
        default=None,
        help='Config name'
    )


    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s {version}'.format(version=__version__)
    )



    a = parser.parse_args(cmdline)
    return a


def main():
    # Parse arguments
    args = parse_arguments(sys.argv[1:])  # pragma: no cover

    if args.action:
        if 'infos' in args.action:
            showInfo(args)

        if 'scan' in args.action:
            scan(args)

if __name__ == '__main__':
    main()  # pragma: no cover
