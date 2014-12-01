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
from collections import OrderedDict

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


def loadCSVFile(filename):

    exists = os.path.isfile(filename)
    if not exists:
        return None

    # Load a file
    f = open(filename,"rb")

    scaninfo = OrderedDict()
    timelist = OrderedDict()
    for line in f:
        line = [s.strip() for s in line.strip().split(',')]
        line = [s for s in line if s]

        # Get freq for CSV line
        linefreq_start = float(line[2])
        linefreq_end = float(line[3])
        linefreq_step = float(line[4])
        freqkey = (linefreq_start, linefreq_end, linefreq_step)
        nbsamples4line = int((linefreq_end - linefreq_start) / linefreq_step)

        # Calc time key
        dtime = '%s %s' % (line[0], line[1])
        if dtime not in timelist:
            timelist[dtime] = np.array([])

        # Add a uniq freq key
        if freqkey not in scaninfo:
            scaninfo[freqkey] = None

        # Get power dB
        linepower = [float(value) for value in line[6:nbsamples4line + 6]]
        timelist[dtime] = np.append(timelist[dtime], linepower)

    nbsubrange = len(scaninfo)
    globalfreq_start = float(scaninfo.items()[0][0][0])
    globalfreq_end = float(scaninfo.items()[nbsubrange - 1][0][1])

    nblines = len(timelist)
    nbstep = int((globalfreq_end - globalfreq_start) / linefreq_step)

    if (nbsamples4line * nbsubrange) != nbstep:
        raise Exception('No same numbers samples')

    times = timelist.keys()
    powersignal = np.array([])
    for freqkey, content in timelist.items():
        powersignal = np.append(powersignal, content)

    powersignal = powersignal.reshape((nblines,nbstep))

    # print "freq_start     : %s" % globalfreq_start
    # print "freq_end       : %s" % globalfreq_end
    # print "freq_step      : %s" % linefreq_step
    # print "nbsamples4line : %s" % nbsamples4line
    # print "nbsubrange     : %s" % nbsubrange
    # print "nblines        : %s" % nblines
    # print "nb_step        : %s" % nbstep
    # print "time_start     : %s" % time_start
    # print "time_end       : %s" % time_end

    return {'freq_start': globalfreq_start, 'freq_end': globalfreq_end, 'freq_step': linefreq_step, 'times': times, 'powersignal': powersignal}


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
    print "Scan %s : %shz-%shz" % (scanlevel['name'], float2Hz(start), float2Hz(start + scanlevel['windows']))

    # Create directory if not exists
    if not os.path.isdir(scanlevel['scandir']):
        os.makedirs(scanlevel['scandir'])

    filename = calcFilename(scanlevel, start)

    # Ignore call rtl_power if file already exist
    csv_filename = "%s.csv" % filename
    running_filename = "%s.running" % filename
    exists = os.path.isfile(running_filename) or os.path.isfile(csv_filename)
    if exists:
        return

    cmd = "rtl_power -f %s:%s:%s -i %s -e %s %s" % (
        start,
        start + scanlevel['windows'],
        scanlevel['binsize'],
        scanlevel['interval'],
        scanlevel['quitafter'],
        running_filename
    )

    # Call rtl_power shell command
    executeShell(cmd)

    # Rename file
    os.rename(running_filename, csv_filename)

def executeSumarizeSignals(config, scanlevel, start):
    print "Summarize %s : %shz-%shz" % (scanlevel['name'], float2Hz(start), float2Hz(start + scanlevel['windows']))

    filename = calcFilename(scanlevel, start)

    # ignore if rtl_power file not exists
    csv_filename = "%s.csv" % filename
    exists = os.path.isfile(csv_filename)
    if not exists:
        return

    # Ignore call summary if file already exist
    summary_filename = "%s.summary" % filename
    exists = os.path.isfile(summary_filename)
    if exists:
        return

    datas = loadCSVFile(csv_filename)
    result = summarizeSignal(datas)
    saveJSON(summary_filename, result)

    return result

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

        header = ['Config name', 'Location','Antenna']
        print tabulate(result_scan, headers=header, stralign="right")

    print ""

    # Show the scan information table
    result_scan = []
    if 'scans' in config:
        for scanlevel in config['scans']:
            result_scan.append(
                [
                    "%sHz" % float2Hz(scanlevel['freq_start']),
                    "%sHz" % float2Hz(scanlevel['freq_end']),
                    "%sHz" % float2Hz(scanlevel['windows']),
                    float2Sec(scanlevel['interval']),
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


def summarizeSignal(datas):
    summaries = {}

    # Samples
    summaries['samples'] = {}
    summaries['samples']['nblines'] = datas['powersignal'].shape[0]
    summaries['samples']['nbsamplescolumn'] = datas['powersignal'].shape[1]

    # Date
    summaries['time'] = {}
    summaries['time']['start'] = datas['times'][0]
    summaries['time']['end'] = datas['times'][-1]

    # Frequencies
    summaries['freq'] = {}
    summaries['freq']['start'] = datas['freq_start']
    summaries['freq']['end'] = datas['freq_end']
    summaries['freq']['step'] = datas['freq_step']

    # Signals
    summaries['avg'] = {}
    summaries['avg']['min'] = np.min(datas['powersignal'])
    summaries['avg']['max'] = np.max(datas['powersignal'])
    summaries['avg']['mean'] = np.mean(datas['powersignal'])
    summaries['avg']['std'] = np.std(datas['powersignal'])

    # Signals
    summaries['signal'] = {}
    summaries['signal']['min'] = np.min(datas['powersignal'], axis=0).tolist()
    summaries['signal']['max'] = np.max(datas['powersignal'], axis=0).tolist()
    summaries['signal']['mean'] = np.mean(datas['powersignal'], axis=0).tolist()
    summaries['signal']['std'] = np.std(datas['powersignal'], axis=0).tolist()

    return summaries


def scan(config, args):
    if 'scans' in config:
        for scanlevel in config['scans']:
            range = np.linspace(scanlevel['freq_start'],scanlevel['freq_end'], num=scanlevel['nbstep'], endpoint=False)
            for left_freq in range:
                executeRTLPower(config, scanlevel, left_freq)


def generateSummaries(config, args):
    if 'scans' in config:
        for scanlevel in config['scans']:
            range = np.linspace(scanlevel['freq_start'],scanlevel['freq_end'], num=scanlevel['nbstep'], endpoint=False)
            for left_freq in range:
                executeSumarizeSignals(config, scanlevel, left_freq)


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
