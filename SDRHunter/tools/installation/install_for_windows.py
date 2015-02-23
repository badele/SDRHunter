#!/usr/bin/env python
# -*- coding: utf-8 -*-

__authors__ = 'Bruno Adelé <bruno@adele.im>'
__copyright__ = 'Copyright (C) 2014 Bruno Adelé'
__description__ = """Tools for searching the radio of signal"""
__license__ = 'GPL'
__version__ = '0.0.1'

import os
import shlex
import urllib2
import zipfile
import platform
import subprocess
import shutil

DOWNLOADDIR = "c:\SDRHunter\Download"
INSTALLDIR = "c:\SDRHunter"

def main():
    # Download files
    downloadFile('http://sourceforge.net/projects/numpy/files/NumPy/1.9.1/numpy-1.9.1-win32-superpack-python2.7.exe/download','numpy-1.9.1-win32-superpack-python2.7.exe')
    downloadFile('http://sourceforge.net/projects/scipy/files/scipy/0.15.1/scipy-0.15.1-win32-superpack-python2.7.exe/download','scipy-0.15.1-win32-superpack-python2.7.exe')
    downloadFile('https://github.com/badele/SDRHunter/archive/master.zip','master.zip')
    downloadFile('http://sdr.osmocom.org/trac/raw-attachment/wiki/rtl-sdr/RelWithDebInfo.zip','RelWithDebInfo.zip')
    downloadFile('http://sdrsharp.com/downloads/sdr-nightly-rtlsdr.zip', 'sdr-nightly-rtlsdr.zip')
    if platform.release() == "XP":
        downloadFile('http://zadig.akeo.ie/downloads/zadig_xp.exe', 'zadig.exe')
    else:
        downloadFile('http://zadig.akeo.ie/downloads/zadig.exe', 'zadig.exe')

    # Install the packages
    executeShell('"%s\%s" /s' % (DOWNLOADDIR, 'numpy-1.9.1-win32-superpack-python2.7.exe'))
    executeShell('"%s\%s" /s' % (DOWNLOADDIR, 'scipy-0.15.1-win32-superpack-python2.7.exe'))
    executeShell('"%s\%s" /s' % (DOWNLOADDIR, 'zadig.exe'))
    unzipFiles('master.zip', INSTALLDIR)
    unzipFiles('RelWithDebInfo.zip', INSTALLDIR)
    unzipFiles('sdr-nightly-rtlsdr.zip', "%s\\sdr-nightly-rtlsdr" % INSTALLDIR)
    shutil.copyfile("C:\\SDRHunter\\sdr-nightly-rtlsdr\\msvcr100.dll", "C:\\SDRHunter\\rtl-sdr-release\\x32\\msvcr100.dll")


def downloadFile(url, filename):
    if not os.path.isdir(DOWNLOADDIR):
        os.makedirs(DOWNLOADDIR)

    fullname = "%s\%s" % (DOWNLOADDIR, filename)
    if not os.path.exists(fullname):
        print "Download %s" % url
        req = urllib2.urlopen(url)
        buffersize = 16 * 1024
        with open(fullname, 'wb') as fp:
          while True:
            buffer = req.read(buffersize)
            if not buffer:
                break
            fp.write(buffer)

def unzipFiles(zipname,destination):
    print "Unzip %s" % zipname
    zfile = zipfile.ZipFile("%s\%s" % (DOWNLOADDIR, zipname))
    zfile.extractall(destination)



def executeShell(cmd, directory=None):
    print "Execute %s" % cmd
    cmdargs = shlex.split(cmd)
    p = subprocess.Popen(cmdargs, cwd=directory, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, errors = p.communicate()
    if p.returncode:
        print 'Failed running %s' % cmd
        raise Exception(output)
    else:
        pass

    return output


if __name__ == '__main__':
    main()  # pragma: no cover
