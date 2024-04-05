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

    if not lines:
        print(f"Error: {f.name} is empty")
        return

    if not columns:
        first_data = json.loads(lines[0])
        columns = tuple(sorted(first_data.keys()))
    columns = ("seconds", ) + columns

    stats = {
        c: 0
        for c in columns
    }

    with open(path.with_suffix(".csv"), "w") as csvfile:
        print("Writing: {}".format(csvfile.name))
        writer = csv.writer(csvfile)
        writer.writerow(columns)
        for line in lines:
            data = json.loads(line)
            try:
                row = [
                    data[c]
                    for c in columns
                ]
                found_any = True
            except KeyError as e:
                stats[e.args[0]] += 1
                continue
            writer.writerow(row)
    for c in columns:
        if stats[c]:
            print('Error: "{}": {} rows lacking "{}".'.format(f.name, stats[c], c))
