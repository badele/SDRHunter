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
from collections import OrderedDict
import matplotlib.pyplot as plt

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

def loadConfigFile(args):
    config = loadJSON(args.filename)

    # Check global section
    if 'ppm' not in config['global']:
        config['global']['ppm'] = 0
    if 'gain' not in config['global']:
        config['global']['gain'] = "automatic"
    if 'verbose' not in config['global']:
        config['global']['verbose'] = True

    # Check in global scan section
    if 'scans' not in config['global']:
        config['global']['scans'] = {}
    if 'splitwindows' not in config['global']['scans']:
        config['global']['scans']['splitwindows'] = False
    if 'scanfromstations' not in config['global']['scans']:
        config['global']['scans']['scanfromstations'] = False


    if config:
        # Check global field if not exist in scanlevel
        if 'scans' in config['global']:
            for field in config['global']['scans']:
                for scanlevel in config['scans']:
                    if field not in scanlevel:
                        scanlevel[field] = config['global']['scans'][field]

        # Check required scan param
        for scanlevel in config['scans']:
            required = ['name', 'freq_start', 'freq_end', 'interval', 'splitwindows']
            for require in required:
                if require not in scanlevel:
                    raise Exception("key '%s' required in %s" % (require, scanlevel))


        # set windows var if not exist config exist
        for scanlevel in config['scans']:
            if 'windows' not in scanlevel:
                freqstart = commons.hz2Float(scanlevel['freq_start'])
                freqend = commons.hz2Float(scanlevel['freq_end'])
                scanlevel['windows'] = freqend - freqstart


        # Convert value to float
        for scanlevel in config['scans']:
            # Set vars
            scanlevel['freq_start'] = commons.hz2Float(scanlevel['freq_start'])
            scanlevel['freq_end'] = commons.hz2Float(scanlevel['freq_end'])
            scanlevel['delta'] = scanlevel['freq_end'] - scanlevel['freq_start']
            scanlevel['windows'] = commons.hz2Float(scanlevel['windows'])
            scanlevel['interval'] = commons.sec2Float(scanlevel['interval'])
            scanlevel['quitafter'] = commons.sec2Float(scanlevel['interval']) * scanlevel['nbsamples_lines']
            scanlevel['scandir'] = "%s/%s/%s" % (config['global']['rootdir'], args.location, scanlevel['name'])
            scanlevel['gain'] = config['global']['gain']
            scanlevel['binsize'] = np.ceil(scanlevel['windows'] / (scanlevel['nbsamples_freqs'] - 1))

            # Check multiple windows
            if (scanlevel['delta'] % scanlevel['windows']) != 0:
                #step = int((scanlevel['delta'] / (scanlevel['windows'] - (commons.hz2Float(scanlevel['windows']) / 2))))
                scanlevel['freq_end'] = scanlevel['freq_end'] + (scanlevel['windows'] - (scanlevel['delta'] % scanlevel['windows']))
                scanlevel['delta'] = scanlevel['freq_end'] - scanlevel['freq_start']

            if scanlevel['splitwindows']:
                scanlevel['nbstep'] = scanlevel['delta'] / (scanlevel['windows'] - (commons.hz2Float(scanlevel['windows']) / 2))
            else:
                scanlevel['nbstep'] = scanlevel['delta'] / scanlevel['windows']

            # Check if width if puissance of ^2
            if int(np.log2(scanlevel['nbsamples_freqs'])) != np.log2(scanlevel['nbsamples_freqs']):
                raise Exception("Please chose a dimension ^2 for %S" % scanlevel)

        return config

    return None


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

        nbsamples4line = int(np.round((linefreq_end - linefreq_start) / linefreq_step))

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
    nbstep = int(np.round((globalfreq_end - globalfreq_start) / linefreq_step))

    if (nbsamples4line * nbsubrange) != nbstep:
        raise Exception('No same numbers samples')

    times = timelist.keys()
    powersignal = np.array([])
    for freqkey, content in timelist.items():
        powersignal = np.append(powersignal, content)

    powersignal = powersignal.reshape((nblines,nbstep))

    return {'freq_start': globalfreq_start, 'freq_end': globalfreq_end, 'freq_step': linefreq_step, 'times': times, 'powersignal': powersignal}


def smooth(x,window_len=11,window='hanning'):
    # http://wiki.scipy.org/Cookbook/SignalSmooth
    if x.ndim != 1:
        raise ValueError, "smooth only accepts 1 dimension arrays."

    if x.size < window_len:
        raise ValueError, "Input vector needs to be bigger than window size."


    if window_len<3:
        return x


    if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
        raise ValueError, "Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'"


    s=np.r_[x[window_len-1:0:-1],x,x[-1:-window_len:-1]]
    if window == 'flat': #moving average
        w=np.ones(window_len,'d')
    else:
        w=eval('numpy.'+window+'(window_len)')

    y=np.convolve(w/w.sum(),s,mode='valid')
    return y

def calcFilename(scanlevel, start):
    filename = "%s/%sHz-%sHz-%07.2fdB-%sHz-%s-%s" % (
        scanlevel['scandir'],
        commons.float2Hz(start, True),
        commons.float2Hz(start + scanlevel['windows'], True),
        scanlevel['gain'],
        commons.float2Hz(scanlevel['binsize'], True),
        commons.commons.float2Sec(scanlevel['interval']),
        commons.commons.float2Sec(scanlevel['quitafter'])
    )

    return filename


def executeShell(cmd, directory=None):
    cmdargs = shlex.split(cmd)
    p = subprocess.Popen(cmdargs, cwd=directory, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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

    filename = calcFilename(scanlevel, start)

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

        print "%sScan '%s' : %shz-%shz Begin: %s / Finish in: ~%s" % (
            tcolor.DEFAULT,
            scanlevel['name'],
            commons.float2Hz(start), commons.float2Hz(start + scanlevel['windows']),
            time.strftime("%H:%M:%S", time.localtime()),
            commons.float2Sec(scanlevel['quitafter']),
        )

        cmd = "rtl_power -p %s -g %s -f %s:%s:%s -i %s -e %s %s" % (
            config['global']['ppm'],
            config['global']['gain'],
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

    # Ignore call summary if file already exist
    summary_filename = "%s.summary" % filename
    exists = os.path.isfile(summary_filename)
    if exists:
        showVerbose(
            config,
            "%sSummarize '%s' : %shz-%shz%s" % (
                tcolor.GREEN,
                scanlevel['name'], commons.float2Hz(start), commons.float2Hz(start + scanlevel['windows']),
                tcolor.DEFAULT,
            )
        )
        return

    print "%sSummarize '%s' : %shz-%shz" % (
        tcolor.DEFAULT,
        scanlevel['name'], commons.float2Hz(start), commons.float2Hz(start + scanlevel['windows']),
    )


    datas = loadCSVFile(csv_filename)
    result = summarizeSignal(datas)
    saveJSON(summary_filename, result)

    return result


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

    smooth_max = smooth(np.array(summaries['max']['signal']),10, 'flat')

    limitmin = summaries['min']['peak']['min']['mean'] - summaries['min']['peak']['min']['std']
    limitmax = summaries['max']['mean'] + summaries['max']['std']
    searchStation(scanlevel, stations, summaries, smooth_max, limitmin, limitmax)




def executeHeatmapParameters(config, scanlevel, start):
    filename = calcFilename(scanlevel, start)

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
        return

    print "%sHeatmap Parameter '%s' : %shz-%shz" % (
        tcolor.DEFAULT,
        scanlevel['name'], commons.float2Hz(start), commons.float2Hz(start + scanlevel['windows']),
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

    return parameters


def executeHeatmap(config, scanlevel, start):
    filename = calcFilename(scanlevel, start)

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
        return

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
        return

    print "%sHeatmap '%s' : %shz-%shz" % (
        tcolor.DEFAULT,
        scanlevel['name'], commons.float2Hz(start), commons.float2Hz(start + scanlevel['windows']),
    )

    # Check calc or check if Heatmap paramters exists
    cmd = "python heatmap.py --parameters %s %s %s" % (
        params_filename,
        csv_filename,
        img_filename
    )
    print cmd

    # Call heatmap.py shell command
    executeShell(cmd, config['global']['heatmap']['dirname'])

def executeSpectre(config, scanlevel, start):
    filename = calcFilename(scanlevel, start)

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

    smooth_max = smooth(np.array(summaries['max']['signal']),10, 'flat')
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


def computeAvgSignal(summaries, summaryname, spectre):
    summaries[summaryname] = {}
    summaries[summaryname]['signal'] = spectre.tolist()

    # AVG signal
    summaries[summaryname]['min'] = np.min(spectre)
    summaries[summaryname]['max'] = np.max(spectre)
    summaries[summaryname]['mean'] = np.mean(spectre)
    summaries[summaryname]['std'] = np.std(spectre)

    # Compute Ground Noise of signal
    lensignal = len(spectre)
    smooth_signal = smooth(spectre,10, 'flat')
    peakmin = signal.argrelextrema(smooth_signal[:lensignal], np.less)
    peakmax = signal.argrelextrema(smooth_signal[:lensignal], np.greater)

    peakminidx = []
    for idx in peakmin[0]:
        if smooth_signal[:lensignal][idx] < summaries[summaryname]['mean']:
            peakminidx.append(idx)
    summaries[summaryname]['peak'] = {}
    summaries[summaryname]['peak']['min'] = {}
    summaries[summaryname]['peak']['min']['idx'] = peakminidx
    summaries[summaryname]['peak']['min']['mean'] = np.mean(spectre[peakminidx])
    summaries[summaryname]['peak']['min']['std'] = np.std(spectre[peakminidx])

    peakmaxidx = []
    for idx in peakmax[0]:
        if smooth_signal[:lensignal][idx] > summaries[summaryname]['mean']:
            peakmaxidx.append(idx)
    summaries[summaryname]['peak']['max'] = {}
    summaries[summaryname]['peak']['max']['idx'] = peakmaxidx
    summaries[summaryname]['peak']['max']['mean'] = np.mean(spectre[peakmaxidx])
    summaries[summaryname]['peak']['max']['std'] = np.std(spectre[peakmaxidx])

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

    # Avg signal
    avgsignal = np.mean(datas['powersignal'], axis=0)
    computeAvgSignal(summaries, 'avg', avgsignal)

    # Min signal
    minsignal = np.min(datas['powersignal'], axis=0)
    computeAvgSignal(summaries, 'min', minsignal)

    # Max signal
    maxsignal = np.max(datas['powersignal'], axis=0)
    computeAvgSignal(summaries, 'max', maxsignal)

    # Delta signal
    deltasignal = maxsignal - minsignal
    computeAvgSignal(summaries, 'delta', deltasignal)

    return summaries


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
    config = loadConfigFile(args)
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

