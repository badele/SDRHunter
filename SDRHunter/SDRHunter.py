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
HzUnities = {'M': 1e6, 'k': 1e3}
secUnities = {'s': 1, 'm': 60, 'h': 3600}


def loadJSON(filename):
    exists = os.path.isfile(filename)
    if exists:
        configlines = open(filename).read()
        config = json.loads(configlines)


        # Check global field if not exist in scans
        if 'scans' in config['global']:
            for field in config['global']['scans']:
                for scanlevel in config['scans']:
                    if field not in scanlevel:
                        scanlevel[field] = config['global']['scans'][field]

        if 'scans' in config:
            if 'nbsamples_freqs' in config['global'] or 'nbsamples_lines' in config['global']:
                for scanlevel in config['scans']:
                    if 'nbsamples_freqs' not in scanlevel:
                        scanlevel['nbsamples_freqs'] = config['global']['nbsamples_freqs']

                    if 'nbsamples_freqs' not in scanlevel:
                        scanlevel['nbsamples_lines'] = config['global']['nbsamples_lines']

        # Check required scan param
        for scanlevel in config['scans']:
            required = ['name', 'freq_start', 'freq_end', 'interval']
            for require in required:
                if require not in scanlevel:
                    raise Exception("key '%s' required in %s" % (require, scanlevel))


        # set windows var if not exist config exist
        for scanlevel in config['scans']:
            if 'windows' not in scanlevel:
                freqstart = Hz2Float(scanlevel['freq_start'])
                freqend = Hz2Float(scanlevel['freq_end'])
                scanlevel['windows'] = freqend - freqstart


        # Convert value to float
        for scanlevel in config['scans']:
            # Set vars
            scanlevel['freq_start'] = Hz2Float(scanlevel['freq_start'])
            scanlevel['freq_end'] = Hz2Float(scanlevel['freq_end'])
            scanlevel['delta'] = scanlevel['freq_end'] - scanlevel['freq_start']
            scanlevel['windows'] = Hz2Float(scanlevel['windows'])
            scanlevel['interval'] = sec2Float(scanlevel['interval'])
            scanlevel['quitafter'] = sec2Float(scanlevel['interval']) * scanlevel['nbsamples_lines']
            scanlevel['scandir'] = "%s/%s" % (config['global']['rootdir'], scanlevel['name'])
            scanlevel['binsize'] = np.ceil(scanlevel['windows'] / (scanlevel['nbsamples_freqs'] - 1))

            # Check multiple windows
            if (scanlevel['delta'] % scanlevel['windows']) != 0:
                step = int((scanlevel['delta'] / scanlevel['windows']))
                scanlevel['freq_end'] = scanlevel['freq_start'] + ((step + 1) * scanlevel['windows'])
                scanlevel['delta'] = scanlevel['freq_end'] - scanlevel['freq_start']

            scanlevel['nbstep'] = scanlevel['delta'] / scanlevel['windows']

            # Check if width if puissance of ^2
            if int(np.log2(scanlevel['nbsamples_freqs'])) != np.log2(scanlevel['nbsamples_freqs']):
                raise Exception("Please chose a dimension ^2 for %S" % scanlevel)


        return config

    return None


def saveJSON(filename,content):
    with open(filename, 'w') as f:
        jsontext = json.dumps(
            content, sort_keys=True,
            indent=4, separators=(',', ': ')
        )
        f.write(jsontext)
        f.close()


def unity2Float(stringvalue, unityobject):
    # If allready number, we consider is the Hz
    if isinstance(stringvalue, int) or isinstance(stringvalue, float):
        return stringvalue

    floatvalue = float(stringvalue[:-1])
    unity = stringvalue[-1]
    if not (unity.lower() in unityobject or unity.upper() in unityobject):
        raise Exception("Not unity found '%s' " % stringvalue)

    floatvalue = floatvalue * unityobject[unity]
    return floatvalue


def Hz2Float(stringvalue):
    return unity2Float(stringvalue, HzUnities)


def sec2Float(stringvalue):
    return unity2Float(stringvalue, secUnities)

def float2Unity(value, unityobject):
    unitysorted = sorted(unityobject, key=lambda x: unityobject[x], reverse=True)

    result = value
    for unity in unitysorted:
        if value >= unityobject[unity]:
            convertresult = value / unityobject[unity]
            if int(convertresult) == convertresult:
                result = "%s%s" % (int(value / unityobject[unity]), unity)
            else:
                result = "%.2f%s" % (value / unityobject[unity], unity)
            break


    return result


def float2Sec(value):
    return float2Unity(value, secUnities)


def float2Hz(value):
    return float2Unity(value, HzUnities)


def calcFilename(scanlevel, start):
    filename = "%s/%sHz-%sHz-%sHz-%s-%s" % (
        scanlevel['scandir'],
        float2Hz(start),
        float2Hz(start + scanlevel['windows']),
        float2Hz(scanlevel['binsize']),
        float2Sec(scanlevel['interval']),
        float2Sec(scanlevel['quitafter'])
    )

    return filename


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


def executeRTLPower(config, scanlevel, start):
    # Create directory if not exists
    if not os.path.isdir(scanlevel['scandir']):
        os.makedirs(scanlevel['scandir'])

    filename = calcFilename(scanlevel, start)

    # Ignore call rtl_power if file already exist
    csv_filename = "%s.csv" % filename
    exists = os.path.isfile(csv_filename)
    if exists:
        return

    cmd = "rtl_power -f %s:%s:%s -i %s -e %s %s" % (
        start,
        start + scanlevel['windows'],
        scanlevel['binsize'],
        scanlevel['interval'],
        scanlevel['quitafter'],
        csv_filename
    )

    # Call rtl_power shell command
    executeShell(cmd)


def showInfo(config, args):
    # Show config
    result_scan = []
    if 'configs' in config:
        for configname in config['configs']:
            result_scan.append(
                [
                    configname,
                    config['configs'][configname]['location'],
                    config['configs'][configname]['antenna'],
                ]
            )

        header = [ 'Config name', 'Location','Antenna' ]
        print tabulate(result_scan, headers=header, stralign="right")

    print ""

    # Show the scan information table
    result_scan = []
    if 'scans' in config:
        for scanlevel in config['scans']:
            result_scan.append(
                [
                    scanlevel['freq_start'],
                    scanlevel['freq_end'],
                    scanlevel['windows'],
                    scanlevel['interval'],
                    scanlevel['nbsamples_lines'],
                    float2Sec(sec2Float(scanlevel['interval']) * scanlevel['nbsamples_lines']),
                    # scanlevel['quitafter'],
                    scanlevel['maxlevel_legend'],
                ]
            )

        header = [
            'Freq. Start', 'Freq. End', 'Windows', 'Interval', 'Nb lines', 'Total time', 'Max legend level'
        ]
        print tabulate(result_scan, headers=header, stralign="right")

    # Show global config
    if 'global' in config:
        pprint.pprint(config['global'],indent=2)


def scan(config, args):
    if 'scans' in config:
        for scanlevel in config['scans']:
            range = np.linspace(scanlevel['freq_start'],scanlevel['freq_end'], num=scanlevel['nbstep'], endpoint=False)
            for left_freq in range:
                print "Scan %shz-%shz" % (float2Hz(left_freq), float2Hz(left_freq + scanlevel['windows']))
                executeRTLPower(config, scanlevel, left_freq)


def generateSummaries(config, args):
    if 'scans' in config:
        for scan in config['scans']:
            scandir = "%s/%s" % (config['global']['rootdir'], scan['name'])


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
            'generatesummaries',
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

    # Load JSON config
    config = loadJSON(args.filename)
    if not config:
        raise Exception("No infos found in %s" % args.filename)

    # Execute successive action
    if args.action:
        if 'infos' in args.action:
            showInfo(config, args)

        if 'scan' in args.action:
            scan(config, args)

        if 'generatesummaries' in args.action:
            generateSummaries(config, args)

if __name__ == '__main__':
    main()  # pragma: no cover
