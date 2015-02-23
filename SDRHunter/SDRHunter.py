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
import time
import pprint
import argparse
import subprocess
#from collections import OrderedDict
#import matplotlib.pyplot as plt

import numpy as np
import scipy.signal as signal
from tabulate import tabulate

import commons

# Todo: In searchstations, save after Nb Loop
# TODO: rename range into freqs_range
# TODO: search best bandwith for windows and 1s
# TODO: Optimise call function, ex: scan,zoomedscan, gensummaries, etc ...as
# TODO: Analyse if zoomedscan must merge with scan function

# Unit conversion
HzUnities = {'M': 1e6, 'k': 1e3}
secUnities = {'s': 1, 'm': 60, 'h': 3600}

# Class for terminal Color
class tcolor:
    DEFAULT = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[0;1;31;40m"
    GREEN = "\033[0;1;32;40m"
    BLUE = "\033[0;1;36;40m"
    ORANGE = "\033[0;1;33;40m"
    MAGENTA = "\033[0;1;36;40m"
    RESET = "\033[2J\033[H"
    BELL = "\a"

def showVerbose(config, mess):
    if config['global']['verbose']:
        print mess

def loadJSON(filename):
    exists = os.path.isfile(filename)
    if exists:
        configlines = open(filename).read()
        content = json.loads(configlines)
        return content

    return None


def saveJSON(filename,content):
    with open(filename, 'w') as f:
        jsontext = json.dumps(
            content, sort_keys=True,
            indent=4, separators=(',', ': ')
        )
        f.write(jsontext)
        f.close()


def loadStations(filename):
    stations = loadJSON(filename)
    if not stations:
        stations = {'stations': []}

    return stations



def calcFilename(scanlevel, start, gain):
    filename = "%s/%sHz-%sHz-%07.2fdB-%sHz-%s-%s" % (
        scanlevel['scandir'],
        commons.float2Hz(start, 3, True),
        commons.float2Hz(start + scanlevel['windows'], 3, True),
        gain,
        commons.float2Hz(scanlevel['binsize'], 3, True),
        commons.float2Sec(scanlevel['interval']),
        commons.float2Sec(scanlevel['quitafter'])
    )

    return filename


def executeShell(cmd, directory=None):
    p = subprocess.Popen(cmd, shell=True, cwd=directory, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, errors = p.communicate()
    if p.returncode:
        print 'Failed running %s' % cmd
        raise Exception(output)
    else:
        pass

    return output


def executeRTLPower(config, scanlevel, start):
    # Create directory if not exists
    if not os.path.isdir(scanlevel['scandir']):
        os.makedirs(scanlevel['scandir'])

    for gain in scanlevel['gains']:
        filename = calcFilename(scanlevel, start, gain)

        # Ignore call rtl_power if file already exist
        csv_filename = "%s.csv" % filename
        exists = os.path.isfile(csv_filename)
        if exists:
            showVerbose(
                config,
                "%sScan '%s' : %shz-%shz already exists%s" % (
                    tcolor.GREEN,
                    scanlevel['name'],
                    commons.float2Hz(start), commons.float2Hz(start + scanlevel['windows']),
                    tcolor.DEFAULT
                )
            )
            return
        else:
            running_filename = "%s.running" % filename
            exists = os.path.isfile(running_filename)
            if exists:
                print "%sScan '%s' : delete old running file %shz-%shz" % (
                    tcolor.DEFAULT,
                    scanlevel['name'],
                    commons.float2Hz(start), commons.float2Hz(start + scanlevel['windows']),
                )
                os.remove(running_filename)

            print "%sScan '%s' : %shz-%shz with %s gain / Begin: %s / Finish in: ~%s" % (
                tcolor.DEFAULT,
                scanlevel['name'],
                commons.float2Hz(start), commons.float2Hz(start + scanlevel['windows']),
                gain,
                time.strftime("%H:%M:%S", time.localtime()),
                commons.float2Sec(scanlevel['quitafter']),
            )

            cmddir = None
            if os.name == "nt":
                cmddir = "C:\\SDRHunter\\rtl-sdr-release\\x32"

            cmd = "rtl_power -p %s -g %s -f %s:%s:%s -i %s -e %s %s" % (
                config['global']['ppm'],
                gain,
                start,
                start + scanlevel['windows'],
                scanlevel['binsize'],
                scanlevel['interval'],
                scanlevel['quitafter'],
                running_filename
            )

            # Call rtl_power shell command
            executeShell(cmd, cmddir)

            # Rename file
            os.rename(running_filename, csv_filename)

def executeSumarizeSignals(config, scanlevel, start):
    for gain in scanlevel['gains']:
        filename = calcFilename(scanlevel, start, gain)

        # ignore if rtl_power file not exists
        csv_filename = "%s.csv" % filename
        exists = os.path.isfile(csv_filename)
        if not exists:
            showVerbose(
                config,
                "%s %s not exist%s" % (
                    tcolor.RED,
                    csv_filename,
                    tcolor.DEFAULT,
                )
            )
            continue

        # Ignore call summary if file already exist
        summary_filename = "%s.summary" % filename
        exists = os.path.isfile(summary_filename)
        if exists:
            showVerbose(
                config,
                "%sSummarize '%s' : %shz-%shz%s for %s gain" % (
                    tcolor.GREEN,
                    scanlevel['name'], commons.float2Hz(start), commons.float2Hz(start + scanlevel['windows']),
                    gain,
                    tcolor.DEFAULT,
                )
            )
            continue

        print "%sSummarize '%s' : %shz-%shz for %s gain" % (
            tcolor.DEFAULT,
            scanlevel['name'], commons.float2Hz(start), commons.float2Hz(start + scanlevel['windows']),
            gain
        )


        sdrdatas = commons.SDRDatas(csv_filename)
        saveJSON(summary_filename, sdrdatas.summaries)


def executeSearchStations(config, stations, scanlevel, start):


    filename = calcFilename(scanlevel, start)

    # ignore if rtl_power file not exists
    csv_filename = "%s.csv" % filename
    exists = os.path.isfile(csv_filename)
    if not exists:
        showVerbose(
            config,
            "%s %s not exist%s" % (
                tcolor.RED,
                csv_filename,
                tcolor.DEFAULT,
            )
        )
        return

    # Ignore if call summary not exist
    summary_filename = "%s.summary" % filename
    exists = os.path.isfile(summary_filename)
    if not exists:
        showVerbose(
            config,
            "%s %s not exist%s" % (
                tcolor.RED,
                summary_filename,
                tcolor.DEFAULT,
            )
        )
        return
    summaries = loadJSON(summary_filename)

    print "%sFind stations '%s' : %shz-%shz" % (
        tcolor.DEFAULT,
        scanlevel['name'], commons.float2Hz(start), commons.float2Hz(start + scanlevel['windows']),
    )

    smooth_max = commons.smooth(np.array(summaries['max']['signal']),10, 'flat')

    limitmin = summaries['min']['peak']['min']['mean'] - summaries['min']['peak']['min']['std']
    limitmax = summaries['max']['mean'] + summaries['max']['std']
    searchStation(scanlevel, stations, summaries, smooth_max, limitmin, limitmax)




def executeHeatmapParameters(config, scanlevel, start):
    for gain in scanlevel['gains']:
        filename = calcFilename(scanlevel, start, gain)

        # Ignore if summary file not exists
        summary_filename = "%s.summary" % filename
        exists = os.path.isfile(summary_filename)
        if not exists:
            showVerbose(
                config,
                "%s %s not exist%s" % (
                    tcolor.RED,
                    summary_filename,
                    tcolor.DEFAULT,
                )
            )
            continue

        summaries = loadJSON(summary_filename)
        params_filename = "%s.hparam" % filename
        exists = os.path.isfile(params_filename)
        if exists:
            showVerbose(
                config,
                "%sHeatmap Parameter '%s' : %shz-%shz%s" % (
                tcolor.GREEN,
                scanlevel['name'], commons.float2Hz(start), commons.float2Hz(start + scanlevel['windows']),
                tcolor.DEFAULT,
                )
            )
            continue

        print "%sHeatmap Parameter '%s' : %shz-%shz for % gain" % (
            tcolor.DEFAULT,
            scanlevel['name'], commons.float2Hz(start), commons.float2Hz(start + scanlevel['windows']),
            gain,
        )

        parameters = {}
        parameters['reversetextorder'] = True

        # Db
        #parameters['db'] = {}
        ##parameters['db']['mean'] = summaries['avg']['mean']
        #parameters['db']['min'] = summaries['avg']['min']
        #parameters['db']['max'] = summaries['avg']['max']

        # Text
        parameters['texts'] = []
        parameters['texts'].append({'text': "Min signal: %.2f" % summaries['avg']['min']})
        parameters['texts'].append({'text': "Max signal: %.2f" % summaries['avg']['max']})
        parameters['texts'].append({'text': "Mean signal: %.2f" % summaries['avg']['mean']})
        parameters['texts'].append({'text': "Std signal: %.2f" % summaries['avg']['std']})

        parameters['texts'].append({'text': ""})
        parameters['texts'].append({'text': "avg min %.2f" % summaries['avg']['min']})
        parameters['texts'].append({'text': "std min %.2f" % summaries['avg']['std']})

        # Add sscanlevel stations name in legends
        if 'stationsfilename' in scanlevel or 'heatmap' in config['global']:
            parameters['legends'] = []

        if 'stationsfilename' in scanlevel:
            parameters['legends'].append(scanlevel['stationsfilename'])

        if 'heatmap' in config['global']:
            # Add global stations name in legends
            if 'heatmap' in config['global'] and "stationsfilenames" in config['global']['heatmap']:
                for stationsfilename in config['global']['heatmap']['stationsfilenames']:
                    parameters['legends'].append(stationsfilename)

        saveJSON(params_filename, parameters)


def executeHeatmap(config, scanlevel, start):
    for gain in scanlevel['gains']:
        filename = calcFilename(scanlevel, start, gain)

        csv_filename = "%s.csv" % filename
        exists = os.path.isfile(csv_filename)
        if not exists:
            showVerbose(
                config,
                "%s %s not exist%s" % (
                    tcolor.RED,
                    csv_filename,
                    tcolor.DEFAULT,
                )
            )
            continue

        params_filename = "%s.hparam" % filename
        exists = os.path.isfile(params_filename)
        if not exists:
            showVerbose(
                config,
                "%s %s not exist%s" % (
                    tcolor.RED,
                    params_filename,
                    tcolor.DEFAULT,
                )
            )
            continue

        # Check if scan exist
        img_filename = "%s_heatmap.png" % filename
        exists = os.path.isfile(img_filename)
        if exists:
            showVerbose(
                config,
                 "%sHeatmap '%s' : %shz-%shz%s" % (
                            tcolor.GREEN,
                            scanlevel['name'], commons.float2Hz(start), commons.float2Hz(start + scanlevel['windows']),
                            tcolor.DEFAULT
                )
            )
            continue

        print "%sHeatmap '%s' : %shz-%shz for %s gain" % (
            tcolor.DEFAULT,
            scanlevel['name'], commons.float2Hz(start), commons.float2Hz(start + scanlevel['windows']),
            gain,
        )

        print "CSV: %s" % csv_filename
        datas = commons.SDRDatas(csv_filename)
        for line in datas.samples:
            print len(line)

        print ""


        # # Check calc or check if Heatmap paramters exists
        # cmd = "python heatmap.py --parameters %s %s %s" % (
        #     params_filename,
        #     csv_filename,
        #     img_filename
        # )
        # print cmd
        #
        # # Call heatmap.py shell command
        # executeShell(cmd, config['global']['heatmap']['dirname'])

def executeSpectre(config, scanlevel, start):
    for gain in scanlevel['gains']:
        filename = calcFilename(scanlevel, start, gain)

        csv_filename = "%s.csv" % filename
        exists = os.path.isfile(csv_filename)
        if not exists:
            showVerbose(
                config,
                "%s %s not exist%s" % (
                    tcolor.RED,
                    csv_filename,
                    tcolor.DEFAULT,
                )
            )
            return

        # Ignore if summary file not exists
        summary_filename = "%s.summary" % filename
        exists = os.path.isfile(summary_filename)
        if not exists:
            showVerbose(
                config,
                "%s %s not exist%s" % (
                    tcolor.RED,
                    summary_filename,
                    tcolor.DEFAULT,
                )
            )
            return
        summaries = loadJSON(summary_filename)

        # Check if scan exist
        img_filename = "%s_spectre.png" % filename
        exists = os.path.isfile(img_filename)
        if exists:
            showVerbose(
                config,
                "%sSpectre '%s' : %shz-%shz%s" % (
                    tcolor.GREEN,
                    scanlevel['name'], commons.float2Hz(start), commons.float2Hz(start + scanlevel['windows']),
                    tcolor.DEFAULT
                )
            )
            return

        print "%sSpectre '%s' : %shz-%shz" % (
            tcolor.DEFAULT,
            scanlevel['name'], commons.float2Hz(start), commons.float2Hz(start + scanlevel['windows']),
        )

        plt.figure(figsize=(15,10))
        plt.grid()

        freqs = np.linspace(summaries['freq']['start'], summaries['freq']['end'], num=summaries['samples']['nbsamplescolumn'])



        limitmin = summaries['min']['peak']['min']['mean'] - summaries['min']['peak']['min']['std']
        limitmax = summaries['max']['mean'] + summaries['max']['std']
        limits = np.linspace(limitmin, limitmax, 5)
        # Max
        for limit in limits:
            plt.axhline(limit, color='blue')

        smooth_max = commons.smooth(np.array(summaries['max']['signal']),10, 'flat')
        plt.plot(freqs, smooth_max[:len(freqs)],color='red')

        # Set X Limit
        locs, labels = plt.xticks()
        for idx in range(len(labels)):
            labels[idx] = commons.float2Hz(locs[idx])
        plt.xticks(locs, labels)
        plt.xlabel('Freq in Hz')

        # Set Y Limit
        # plt.ylim(summary['groundsignal'], summary['maxsignal'])
        plt.ylabel('Power density in dB')


        plt.savefig(img_filename)
        plt.close()


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
                    "%sHz" % commons.float2Hz(scanlevel['freq_start']),
                    "%sHz" % commons.float2Hz(scanlevel['freq_end']),
                    "%sHz" % commons.float2Hz(scanlevel['windows']),
                    commons.float2Sec(scanlevel['interval']),
                    scanlevel['nbsamples_lines'],
                    commons.float2Sec(commons.sec2Float(scanlevel['interval']) * scanlevel['nbsamples_lines']),
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


def searchStation(scanlevel, stations, summaries, samples, limitmin, limitmax):

    #search_limit = sorted(limit_list)
    freqstep = summaries['freq']['step']
    stations['stations'] = sorted(stations['stations'], key=lambda x: commons.hz2Float(x['freq_center']) - commons.hz2Float((x['bw'])))

    bwmin = commons.hz2Float(scanlevel['minscanbw'])
    bwmax = commons.hz2Float(scanlevel['maxscanbw'])

    limits = np.linspace(limitmin, limitmax, 5)
    for limit in limits:
        # Search peak upper than limit
        startup = -1
        foundlower = False
        for idx in np.arange(len(samples)):
            powerdb = samples[idx]
            isup = powerdb > limit

            # Search first lower limit signal
            if not foundlower:
                if not isup:
                    foundlower = True
                else:
                    continue


            # Find first upper
            if startup == -1:
                if isup:
                    startup = idx
                    maxidx = startup
                    maxdb = powerdb
            else:
                # If upper, check if db is upper
                if isup:
                    if powerdb > maxdb:
                        maxdb = powerdb
                        maxidx = idx
                # If lower, calc bandwidth and max db
                else:
                    endup = idx - 1

                    bw_nbstep = endup - startup
                    bw = bw_nbstep * freqstep
                    freqidx = startup + int(bw_nbstep / 2)
                    # TODO: compare with freqidx, set % error ?
                    freq_center = summaries['freq']['start'] + (maxidx * freqstep)
                    freq_center = summaries['freq']['start'] + (freqidx * freqstep)
                    freq_left = freq_center - bw

                    deltadb = (maxdb - limit)
                    if bwmin <= bw <= bwmax and deltadb > scanlevel['minrelativedb']:

                        print "Freq:%s / Bw:%s / Abs: %s dB / From ground:%.2f dB" % (commons.float2Hz(freq_center), commons.float2Hz(bw), maxdb, maxdb - limitmax)

                        found = False
                        for station in stations['stations']:
                            if freq_center >= commons.hz2Float(station['freq_center']) - bw and freq_center <= commons.hz2Float(station['freq_center']) + bw:
                                found = True
                                break

                        if not found:

                            stations['stations'].append(
                                {'freq_center': commons.float2Hz(freq_center),
                                  'bw': commons.float2Hz(bw),
                                  'powerdb': float("%.2f" % maxdb),
                                  'relativedb': float("%.2f" % (maxdb - limitmin))
                                }
                            )
                            stations['stations'] = sorted(stations['stations'], key=lambda x: commons.hz2Float(x['freq_center']) - commons.hz2Float(x['bw']))


                    startup = -1


def scan(config, args):
    if 'scans' in config:
        for scanlevel in config['scans']:
            if not scanlevel['scanfromstations']:
                range = np.linspace(scanlevel['freq_start'],scanlevel['freq_end'], num=scanlevel['nbstep'], endpoint=False)
                for left_freq in range:
                    executeRTLPower(config, scanlevel, left_freq)


def zoomedscan(config, args):
    if 'scans' in config:
        for scanlevel in config['scans']:
            if scanlevel['scanfromstations']:
                stations = loadJSON(scanlevel['stationsfilename'])
                confirmed_station = []
                for station in stations['stations']:
                    if 'name' in station:
                        confirmed_station.append(station)
                for station in confirmed_station:
                    freq_left = commons.hz2Float(station['freq_center']) - commons.hz2Float(scanlevel['windows'] / 2)
                    executeRTLPower(config, scanlevel, freq_left)


def generateSummaries(config, args):
    if 'scans' in config:
        for scanlevel in config['scans']:
            range = np.linspace(scanlevel['freq_start'],scanlevel['freq_end'], num=scanlevel['nbstep'], endpoint=False)
            for left_freq in range:
                executeSumarizeSignals(config, scanlevel, left_freq)

            # For scanlevel with stationsfilename
            if 'stationsfilename' in scanlevel:
                stations = loadJSON(scanlevel['stationsfilename'])
                confirmed_station = []
                for station in stations['stations']:
                    if 'name' in station:
                        confirmed_station.append(station)
                for station in confirmed_station:
                    freq_left = commons.hz2Float(station['freq_center']) - commons.hz2Float(scanlevel['windows'] / 2)
                    executeSumarizeSignals(config, scanlevel, freq_left)

def searchStations(config, args):
    if 'scans' in config:
        for scanlevel in config['scans']:
            stations_filename = "%s/%s/scanresult.json" % (config['global']['rootdir'], args.location)
            stations = loadStations(stations_filename)
            range = np.linspace(scanlevel['freq_start'],scanlevel['freq_end'], num=scanlevel['nbstep'], endpoint=False)
            for left_freq in range:
                executeSearchStations(config, stations, scanlevel, left_freq)

            saveJSON(stations_filename, stations)

def generateHeatmapParameters(config, args):
    if 'scans' in config:
        for scanlevel in config['scans']:
            range = np.linspace(scanlevel['freq_start'],scanlevel['freq_end'], num=scanlevel['nbstep'], endpoint=False)
            for left_freq in range:
                executeHeatmapParameters(config, scanlevel, left_freq)

            # For scanlevel with stationsfilename
            if 'stationsfilename' in scanlevel:
                stations = loadJSON(scanlevel['stationsfilename'])
                confirmed_station = []
                for station in stations['stations']:
                    if 'name' in station:
                        confirmed_station.append(station)
                for station in confirmed_station:
                    freq_left = commons.hz2Float(station['freq_center']) - commons.hz2Float(scanlevel['windows'] / 2)
                    executeHeatmapParameters(config, scanlevel, freq_left)


def generateHeatmaps(config, args):
    if 'scans' in config:
        for scanlevel in config['scans']:
            range = np.linspace(scanlevel['freq_start'],scanlevel['freq_end'], num=scanlevel['nbstep'], endpoint=False)
            for left_freq in range:
                executeHeatmap(config, scanlevel, left_freq)

            # For scanlevel with stationsfilename
            if 'stationsfilename' in scanlevel:
                stations = loadJSON(scanlevel['stationsfilename'])
                confirmed_station = []
                for station in stations['stations']:
                    if 'name' in station:
                        confirmed_station.append(station)
                for station in confirmed_station:
                    freq_left = commons.hz2Float(station['freq_center']) - commons.hz2Float(scanlevel['windows'] / 2)
                    executeHeatmap(config, scanlevel, freq_left)

def generateSpectres(config, args):
    if 'scans' in config:
        for scanlevel in config['scans']:
            range = np.linspace(scanlevel['freq_start'],scanlevel['freq_end'], num=scanlevel['nbstep'], endpoint=False)
            for left_freq in range:
                executeSpectre(config, scanlevel, left_freq)

            # For scanlevel with stationsfilename
            if 'stationsfilename' in scanlevel:
                stations = loadJSON(scanlevel['stationsfilename'])
                confirmed_station = []
                for station in stations['stations']:
                    if 'name' in station:
                        confirmed_station.append(station)
                for station in confirmed_station:
                    freq_left = commons.hz2Float(station['freq_center']) - commons.hz2Float(scanlevel['windows'] / 2)
                    executeSpectre(config, scanlevel, freq_left)


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
            'zoomedscan',
            'gensummaries',
            'searchstations',
            'genheatmapparameters',
            'genheatmaps',
            'genspectres'
        ],
        help='Action'
    )

    parser.add_argument(
        '-l', '--location',
        action='store',
        dest='location',
        required=True,
        help='Scan location'
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
    config = commons.loadConfigFile(commons.getJSONConfigFilename())
    if not config:
        raise Exception("No infos found in %s" % args.filename)

    # Execute successive action
    if args.action:
        if 'infos' == args.action:
            showInfo(config, args)

        if 'scan' == args.action:
            scan(config, args)

        if 'zoomedscan' == args.action:
            zoomedscan(config, args)

        if 'gensummaries' == args.action:
            generateSummaries(config, args)

        if 'searchstations' == args.action:
            searchStations(config, args)

        if 'genheatmapparameters' == args.action:
            generateHeatmapParameters(config, args)

        if 'genheatmaps' == args.action:
            generateHeatmaps(config, args)

        if 'genspectres' == args.action:
            generateSpectres(config, args)


if __name__ == '__main__':
    main()  # pragma: no cover

