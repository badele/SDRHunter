.. image:: https://travis-ci.org/badele/SDRHunter.png?branch=master
   :target: https://travis-ci.org/badele/SDRHunter

.. image:: https://coveralls.io/repos/badele/SDRHunter/badge.png
   :target: https://coveralls.io/r/badele/SDRHunter

.. disableimage:: https://pypip.in/v/SDRHunter/badge.png
   :target: https://crate.io/packages/SDRHunter/

.. disableimage:: https://pypip.in/d/SDRHunter/badge.png
   :target: https://crate.io/packages/SDRHunter/



About
=====

``SDRHunter`` Tools for searching the radio of signal


Installing
==========

To install the latest release from `PyPI <http://pypi.python.org/pypi/SDRHunter>`_

.. code-block:: console

    $ pip install SDRHunter

To install the latest development version from `GitHub <https://github.com/badele/SDRHunter>`_

.. code-block:: console

    $ pip install git+git://github.com/badele/SDRHunter.git


Windows Installation
====================
 - Download and install (select add python.exe to Path in installation option) https://www.python.org/ftp/python/2.7.9/python-2.7.9.msi
 - Download https://raw.githubusercontent.com/badele/SDRHunter/master/SDRHunter/tools/installation\install_for_windows.py and extract to c:\temp\

.. code-block:: console
    cd c:\temp\
    python installation\install_for_windows.py
    cd C:\SDRHunter\SDRHunter-master
    python setup.py install

 - Modify path in the <PYTHON DIR INSTALL>\LIB\site-packages\SDRHUNTER-x.x.x-py2.7.egg\sdrhunter.json file

Using
=====

Exemple for using the scanner :

.. code-block:: console

    $ ./SDRHunter.py -l Montpellier -a scan
    $ ./SDRHunter.py -l Montpellier -a gensummaries
    $ ./SDRHunter.py -l Montpellier -a genheatmapparameters
    $ ./HeapAnalyzer.py




