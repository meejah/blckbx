import click
import json
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


@blckbx.command()
@click.argument("file", type=click.File("r"))
def analyze(file):
    """
    """
    last_time = None
    intervals = []
    for line in file.readlines():
        js = json.loads(line)
        # print(js)
        if last_time is not None:
            interval = float(js["time"]) - float(last_time)
            intervals.append(interval)
        last_time = float(js["time"])

    average_interval = sum(intervals) / len(intervals)
    print(f"average loop: {average_interval}s")
    lps = 1.0 / average_interval
    print(f"loops per second: {lps}")



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
    for f in files:
        _process_file(f, column or [])
