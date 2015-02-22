#!/usr/bin/env python
# -*- coding: utf-8 -*-

__authors__ = 'Bruno Adelé <bruno@adele.im>'
__copyright__ = 'Copyright (C) 2014 Bruno Adelé'
__description__ = """Tools for searching the radio of signal"""
__license__ = 'GPL'
__version__ = '0.0.1'

import os
import json
from collections import OrderedDict

import numpy as np
import scipy.signal as signal

# Unit conversion
HzUnities = {'M': 1e6, 'k': 1e3}
secUnities = {'s': 1, 'm': 60, 'h': 3600}

def getJSONConfigFilename():
    if os.name == "nt":
        jsonfilename = "sdrhunter.json"
    else:
        jsonfilename = ".sdrhunter.json"

    return os.path.join(os.path.expanduser("~"), jsonfilename)


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


def unity2Float(stringvalue, unityobject):
    # If allready number, we consider is the Hz
    if isinstance(stringvalue, int) or isinstance(stringvalue, float):
        return stringvalue

    floatvalue = float(stringvalue[:-1])
    unity = stringvalue[-1]
    if (unity.lower() in unityobject or unity.upper() in unityobject):
        floatvalue = floatvalue * unityobject[unity]

    return floatvalue


def hz2Float(stringvalue):
    return unity2Float(stringvalue, HzUnities)


def sec2Float(stringvalue):
    return unity2Float(stringvalue, secUnities)

def float2Unity(value, unityobject, nbfloat=2, fillzero=False):
    unitysorted = sorted(unityobject, key=lambda x: unityobject[x], reverse=True)

    result = value
    for unity in unitysorted:
        if value >= unityobject[unity]:
            txtnbfloat = "%s" % nbfloat
            if fillzero:
                result = ("%08." + txtnbfloat + "f%s") % (value / unityobject[unity], unity)
            else:
                result = ("%." + txtnbfloat + "f%s") % (value / unityobject[unity], unity)
            break


    return str(result)


def float2Sec(value):
    return float2Unity(value, secUnities)


def float2Hz(value, nbfloat=2, fillzero=False):
    return float2Unity(value, HzUnities, nbfloat, fillzero)

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

def loadConfigFile(filename, location=""):
    config = loadJSON(filename)

    if config is None:
        raise Exception("No JSON SDRHunter configuration file find")


    # Check global section
    if 'rootdir' not in config['global'] or config['global']['rootdir'] == '':
        config['global']['rootdir'] = os.path.join(os.path.expanduser("~"), 'SDRHunter')

    if 'ppm' not in config['global']:
        config['global']['ppm'] = 0
    if 'gains' not in config['global']:
        config['global']['gains'] = [0, 25, 50]
    if 'verbose' not in config['global']:
        config['global']['verbose'] = True

    # Check in global scan section
    if 'scans' not in config['global']:
        config['global']['scans'] = {}
    if 'splitwindows' not in config['global']['scans']:
        config['global']['scans']['splitwindows'] = False
    if 'scanfromstations' not in config['global']['scans']:
        config['global']['scans']['scanfromstations'] = False

    # Replace Global variables


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
                freqstart = hz2Float(scanlevel['freq_start'])
                freqend = hz2Float(scanlevel['freq_end'])
                scanlevel['windows'] = freqend - freqstart


        # Convert value to float
        for scanlevel in config['scans']:
            # Set vars
            scanlevel['freq_start'] = hz2Float(scanlevel['freq_start'])
            scanlevel['freq_end'] = hz2Float(scanlevel['freq_end'])
            scanlevel['delta'] = scanlevel['freq_end'] - scanlevel['freq_start']
            scanlevel['windows'] = hz2Float(scanlevel['windows'])
            scanlevel['interval'] = sec2Float(scanlevel['interval'])
            scanlevel['quitafter'] = sec2Float(scanlevel['interval']) * scanlevel['nbsamples_lines']
            scanlevel['scandir'] = os.path.join(config['global']['rootdir'], location, scanlevel['name'])
            scanlevel['gains'] = config['global']['gains']
            scanlevel['binsize'] = np.ceil(scanlevel['windows'] / (scanlevel['nbsamples_freqs'] - 1))

            # Check multiple windows
            if (scanlevel['delta'] % scanlevel['windows']) != 0:
                #step = int((scanlevel['delta'] / (scanlevel['windows'] - (commons.hz2Float(scanlevel['windows']) / 2))))
                scanlevel['freq_end'] = scanlevel['freq_end'] + (scanlevel['windows'] - (scanlevel['delta'] % scanlevel['windows']))
                scanlevel['delta'] = scanlevel['freq_end'] - scanlevel['freq_start']

            if scanlevel['splitwindows']:
                scanlevel['nbstep'] = scanlevel['delta'] / (scanlevel['windows'] - (hz2Float(scanlevel['windows']) / 2))
            else:
                scanlevel['nbstep'] = scanlevel['delta'] / scanlevel['windows']

            # Check if width if puissance of ^2
            if int(np.log2(scanlevel['nbsamples_freqs'])) != np.log2(scanlevel['nbsamples_freqs']):
                raise Exception("Please chose a dimension ^2 for %S" % scanlevel)

        return config

    return None


class SDRDatas(object):
    def __init__(self, filename):
        self.csv = self.loadCSVFile(filename)
        self.summarizeSignal()

    def loadCSVFile(self, filename):

        exists = os.path.isfile(filename)
        if not exists:
            return None

        # Load a file
        f = open(filename, "rb")

        scaninfo = OrderedDict()
        timelist = OrderedDict()
        for line in f:
            line = [s.strip() for s in line.strip().split(',')]
            line = [s for s in line if s]

            # Get freq for CSV line
            linefreq_start = float(line[2])
            linefreq_end = float(line[3])
            freq_step = float(line[4])
            freqkey = (linefreq_start, linefreq_end, freq_step)
            nbsamples4line = int(np.round((linefreq_end - linefreq_start) / freq_step))

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
        self.freq_start = float(scaninfo.items()[0][0][0])
        self.freq_end = float(scaninfo.items()[nbsubrange - 1][0][1])
        nblines = len(timelist)
        nbstep = int(np.round((self.freq_end - self.freq_start) / freq_step))

        allrangestep = nbsamples4line * nbsubrange
        if allrangestep != nbstep:
            raise Exception('No same numbers samples')

        globalfreq_step = (self.freq_end - self.freq_start) / allrangestep

        self.times = timelist.keys()
        self.samples = np.array([])
        for freqkey, content in timelist.items():
            self.samples = np.append(self.samples, content)

        self.samples = self.samples.reshape((nblines,nbstep))

        return {'freq_start': self.freq_start, 'freq_end': self.freq_end, 'freq_step': globalfreq_step, 'times': self.times, 'samples': self.samples}


    def summarizeSignal(self):
        self.summaries = {}

        # Samples
        self.summaries['samples'] = {}
        self.summaries['samples']['nblines'] = self.csv['samples'].shape[0]
        self.summaries['samples']['nbsamplescolumn'] = self.csv['samples'].shape[1]

        # Date
        self.summaries['time'] = {}
        self.summaries['time']['start'] = self.csv['times'][0]
        self.summaries['time']['end'] = self.csv['times'][-1]

        # Frequencies
        self.summaries['freq'] = {}
        self.summaries['freq']['start'] = self.csv['freq_start']
        self.summaries['freq']['end'] = self.csv['freq_end']
        self.summaries['freq']['step'] = self.csv['freq_step']

        # Avg signal
        avgsignal = np.mean(self.csv['samples'], axis=0)
        self.computeAvgSignal('avg', avgsignal)

        # Min signal
        minsignal = np.min(self.csv['samples'], axis=0)
        self.computeAvgSignal('min', minsignal)

        # Max signal
        maxsignal = np.max(self.csv['samples'], axis=0)
        self.computeAvgSignal('max', maxsignal)

        # Delta signal
        deltasignal = maxsignal - minsignal
        self.computeAvgSignal('delta', deltasignal)


    def computeAvgSignal(self, summaryname, spectre):
        self.summaries[summaryname] = {}
        self.summaries[summaryname]['signal'] = spectre.tolist()

        # AVG signal
        self.summaries[summaryname]['min'] = np.min(spectre)
        self.summaries[summaryname]['max'] = np.max(spectre)
        self.summaries[summaryname]['mean'] = np.mean(spectre)
        self.summaries[summaryname]['std'] = np.std(spectre)

        # Compute Ground Noise of signal
        lensignal = len(spectre)
        smooth_signal = smooth(spectre,10, 'flat')
        peakmin = signal.argrelextrema(smooth_signal[:lensignal], np.less)
        peakmax = signal.argrelextrema(smooth_signal[:lensignal], np.greater)

        peakminidx = []
        for idx in peakmin[0]:
            if smooth_signal[:lensignal][idx] < self.summaries[summaryname]['mean']:
                peakminidx.append(idx)
        self.summaries[summaryname]['peak'] = {}
        self.summaries[summaryname]['peak']['min'] = {}
        self.summaries[summaryname]['peak']['min']['idx'] = peakminidx
        self.summaries[summaryname]['peak']['min']['mean'] = np.mean(spectre[peakminidx])
        self.summaries[summaryname]['peak']['min']['std'] = np.std(spectre[peakminidx])

        peakmaxidx = []
        for idx in peakmax[0]:
            if smooth_signal[:lensignal][idx] > self.summaries[summaryname]['mean']:
                peakmaxidx.append(idx)
        self.summaries[summaryname]['peak']['max'] = {}
        self.summaries[summaryname]['peak']['max']['idx'] = peakmaxidx
        self.summaries[summaryname]['peak']['max']['mean'] = np.mean(spectre[peakmaxidx])
        self.summaries[summaryname]['peak']['max']['std'] = np.std(spectre[peakmaxidx])

    def power2RGB(self, power):
        g = (power - self.summaries['min']['min']) / (self.summaries['max']['max'] - self.summaries['min']['min'])
        return g

