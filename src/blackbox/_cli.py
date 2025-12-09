import click
import math
import json
import re
from datetime import datetime
from pathlib import Path

from twisted.internet.task import react
from twisted.internet.defer import ensureDeferred

from ._monitor import _monitor_dashboard
from ._dump import _process_file


@click.group()
def blckbx():
    """
    Record and process data from FTC-Dashboard on the command-line.
    """


@blckbx.command()
def record():
    """
    Record one or more telemetry sessions.
    """

    def main(reactor):
        return ensureDeferred(_monitor_dashboard(reactor))
    react(main)


def fname_to_date(fn):
    m = re.match("^blackbox-(.*)\\.js", str(fn))
    assert m is not None
    return datetime.strptime(m.group(1), '%a-%b-%d-%H:%M:%S-%Y')


def find_newest_data():
    d = Path(".")
    potential = []
    for f in d.iterdir():
        if str(f).startswith("blackbox-") and str(f).endswith(".js"):
            potential.append(d.joinpath(f))

    # return newest non-empty file
    for f in reversed(sorted(potential, key=fname_to_date)):
        if f.stat().st_size > 0:
            return f
    return None


@blckbx.command()
def clean():
    """
    Delete all empty telemetry files
    """
    d = Path(".")
    potential = []
    for f in d.iterdir():
        if str(f).startswith("blackbox-") and str(f).endswith(".js"):
            potential.append(d.joinpath(f))

    for f in potential:
        if f.stat().st_size == 0:
            print(f"Deleting: {f}")
            f.unlink()


@blckbx.command()
@click.option(
    "--column", "-c",
    multiple=True,
    help="Column to analyze",
)
@click.argument("file", type=click.File("r"), required=False, default=None)
def analyze(file, column):
    """
    """
    if file is None:
        fname = find_newest_data()
        print(f"opening: {fname}")
        file = open(fname, "r")
    last_time = None
    intervals = []
    positions = []
    targets = []
    times = []
    col_mins = [10000] * len(column)
    col_maxs = [0] * len(column)
    for line in file.readlines():
        js = json.loads(line)
        positions.append((float(js["position-x"]), float(js["position-y"])))
#        targets.append((float(js["target-x"]), float(js["target-y"])))
        times.append(float(js["seconds"]))
        coldata = []
        for i, c in enumerate(column):
            v = js.get(c, "<no-data>")
            try:
                x = float(v)
                if x > col_maxs[i]:
                    col_maxs[i] = x
                if x < col_mins[i]:
                    col_mins[i] = x
                v = "{}={:2.2f}".format(c, x)
            except ValueError:
                pass
            coldata.append(v)
        print(" ".join(coldata))
        # print(js)
        if last_time is not None:
            interval = float(js["seconds"]) - float(last_time)
            intervals.append(interval)
        last_time = float(js["seconds"])


    def point_distance(a, b):
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        return math.sqrt(dx*dx + dy*dy)

    velocities = []
    velocities.append((0, 0))
    last_position = positions[0]
    last_time = times[0]
    max_vel = 0.0
    vel = 0.0
    for (position, t) in zip(positions[1:], times[1:]):
        vel = point_distance(last_position, position) / (t - last_time)
        if vel > max_vel:
            max_vel = vel
        last_position = position
        last_time = t

    print()
    for i, c in enumerate(column):
        print("{}: min={:2.2f} max={:2.2f}".format(c, col_mins[i], col_maxs[i]))

    average_interval = sum(intervals) / len(intervals)
    print(f"average loop: {average_interval}s")
    lps = 1.0 / average_interval
    print(f"loops per second: {lps}")
    print(f"max velocity: {vel}m/s")



@blckbx.command()
@click.option(
    "--column", "-c",
    multiple=True,
    help="A value to include as a column in the output",
)
@click.argument("files", type=click.File("r"), nargs=-1)
def csv(files, column):
    """
    Process data from a prior telemetry session.
    """
    if len(files) == 0:
        fname = find_newest_data()
        print(f"opening: {fname}")
        files = [open(fname, "r")]

    for f in files:
        _process_file(f, column or [])
