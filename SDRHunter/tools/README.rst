About
=====

These tools help for recording the sound from rtl_fm


Howto use
=========

Listen and search good squelch parameter

.. code-block:: console

    $ ./listen_stations.sh am airport 280 "-f 130M -f 132M"

Record the stations

.. code-block:: console

    $ ./record_stations.sh am airport 280 "-f 130M -f 132M"
