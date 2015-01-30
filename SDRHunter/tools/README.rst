About
=====

These tools help for recording the sound from rtl_fm


Configuration
=============

For some configuration, you must edit the variables from scripts files, ex :

.. code-block:: console

    PPM=57
    GAIN=49.2
    FORMAT="flac"
    ROOTDIR=~/tmp/sdr
    PLAYFREQ=12000

Howto use
=========

Listen and search good squelch parameter

.. code-block:: console

    $ ./listen_stations.sh am airport 280 "-f 130M -f 132M"

Record the stations

.. code-block:: console

    $ ./record_stations.sh am airport 280 "-f 130M -f 132M"
