import json
import pathlib
import csv


def _process_file(f, columns):
    """
    Read every JSON line from "f" and output its csv equivalent.

    If "columns" is specified, only write these values as columns and
    only if found in the data.
    """
    path = pathlib.Path(f.name)
    lines = f.readlines()

    if not columns:
        first_data = json.loads(lines[0])
        columns = tuple(sorted(first_data.keys()))
    columns = ("seconds", ) + columns

    with open(path.with_suffix(".csv"), "w") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(columns)
        for line in lines:
            data = json.loads(line)
            row = [
                data[c]
                for c in columns
            ]
            writer.writerow(row)
