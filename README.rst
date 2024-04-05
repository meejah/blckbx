Black Box (``blckbx``)
======================

`FTC-Dashboard <https://acmerobotics.github.io/ftc-dashboard/>`_ allows you to see realtime data from your FIRST FTC / REV Robotics controller.

``blckbx`` records that data to a file; it is a small Python tool that uses WebSockets to connect to the Web server that `FTC-Dashboard <https://acmerobotics.github.io/ftc-dashboard/>`_ runs on your robot and record all Telemetry messages.


Installation
------------

Python comes with a "virtual environment" tool that allows you to install ``blckbx`` in an isolated environment on Windows, MacOS or Linux.

First, create a new environment for this tool.
Here we simply use ``--user`` to use a shared, per-user location (if you already have conflicting things installed this way, please consult the `Python venv documentation <https://docs.python.org/3/library/venv.html>`_ for a way to install in isolation).


For Linux and MacOS::

    pip install --user blckbx
    blckbx --help
    # or if the above doesn't work:
    python -m blckbx --help

For Windows::

    py -m pip install --user blckbx
    py -m blckbx --help


Usage Overview
--------------

The defaults should work for most users if you've already got FTC-Dashboard working.

There are two subcommands: ``record`` and ``csv``.

blckbx record
`````````````

What happens is that we connect to ``ws://192.168.43.1:8000/`` with a WebSocket connection -- which is the very same thing the JavaScript running in your Web browser is doing when you visit `http://192.168.43.1:8080/dash <192.168.43.1:8080/dash>`_ to see the Dashboard.

All the "telemetry" data is then written to a file like ``XXX.js``.
A new filename is created every time the robot is "stopped".

So, if you had some on-robot Java code doing telemetry like the following:

.. code-block:: Java

    TelemetryPacket pack = new TelemetryPacket();
    pack.put("pos_y", drive.odo.position_y());
    pack.put("pos_x", drive.odo.position_x());
    pack.put("battery", battery.getVoltage());
    pack.put("heading", drive.getHeading());
    pack.put("target_heading", drive.headingControl.getSetPoint());
    FtcDashboard.getInstance().sendTelemetryPacket(pack);

...then you would see lines in the collected ``blackbox-`` files that look like this (notice that a ``seconds`` key is added, which is seconds from the start)::

.. code-block:: javascript

    {"battery": "13.739", "pos_x": "-0.07539822368615504", "pos_y": "0.07539822368615504", "heading": "-0.038568612188100815", "target_heading": "0.0", "seconds": 1.0}
    {"battery": "13.739", "pos_x": "-0.07539822368615504", "pos_y": "0.07539822368615504", "heading": "-0.038568612188100815", "target_heading": "0.0", "seconds": 2.0}

Each line is a complete, valid JSON message.
Note that JSON doesn't preserve order of things inside objects like this (so things won't necessarily be in the same order as in your Java code).

Use ``ctrl-C`` to exit the program and record no more data.


blckbx csv
``````````

This subcommand takes a previously recorded file (by default "the newest one in the current directory") and produces CSV data from it.
This can be loaded by most spreadsheet software.

You can pass arguments to specify particular columns to include; only telemetry packets that have ALL columns that are specificed will be included.

For example::

    blckbx csv --column pos_x --column pos_y

Used on the above example data, this will produce something like::

    "seconds", "pos_x", "pos_y"
    -0.07539822368615504, 0.07539822368615504, 1.0
    -0.07539822368615504, 0.07539822368615504, 2.0


...
---

This has been produced for use by FIRST FTC team 10015.
