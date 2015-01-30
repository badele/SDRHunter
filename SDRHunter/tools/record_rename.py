#!/usr/bin/env python
# -*- coding: utf-8 -*-

#__authors__ = 'Bruno Adelé <bruno@adele.im>'
#__copyright__ = 'Copyright (C) 2014 Bruno Adelé'
#__description__ = """Tools for searching the radio of signal"""
#__license__ = 'GPL'
#__version__ = '0.0.1'

__authors__ = 'Bruno Adelé <bruno@adele.im>'
__copyright__ = 'Copyright (C) 2015 Bruno Adelé'
__description__ = """Tools for searching the radio of signal"""
__license__ = 'GPL'
__version__ = '0.0.1'

import os
import re
import sys
import time


def rename_files(rootdir):
    unclassified = "%s/_unclassified_" % rootdir
    for filename in os.listdir(unclassified):
        m = re.match("^(.*?)_.*\.(.*)$", filename)
        if m:
            # Get file information
            prefix = m.group(1)
            ext = m.group(2)
            fullname = '%s/%s' % (unclassified, filename)
            filestat = time.gmtime(os.path.getmtime(fullname))

            # Create dir if not exist
            destdir = "%s/%s/%s" % (rootdir, prefix, time.strftime('%Y/%m/%d', filestat))
            if not os.path.exists(destdir):
                os.makedirs(destdir)

            # Rename files
            renamed = '%s/%s_%s.%s' % (destdir, prefix, time.strftime('%Y-%m-%d_%H:%M:%S', filestat), ext)
            os.rename(fullname, renamed)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "Usage: %s record_directory" % sys.argv[0]
        sys.exit(1)

    directory = sys.argv[1].rstrip('/')
    rename_files(directory)
