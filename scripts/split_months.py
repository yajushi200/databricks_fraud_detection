"""Split the full transactions CSV into one CSV per month.

Simulates monthly file arrival for Auto Loader #10.
Reads row by row, so memory use stays small regardless of file size,
and fails loudly if the output row count does not match the source.
"""
import csv
from pathlib import Path

INPUT = Path("data/transactions_data.csv")       
OUTPUT_DIR = Path("data/transactions_monthly")
EXPECTED_ROWS = 13_305_915


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    writers = {}          # month ("2010-01") -> (open file, csv writer)
    rows_written = 0

    with open(INPUT, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        date_idx = header.index("date")

        for row in reader:
            month = row[date_idx][:7]            # "2010-01-01 00:01:00" -> "2010-01"
            if month not in writers:
                out_path = OUTPUT_DIR / f"transactions_{month.replace('-', '_')}.csv"
                out_file = open(out_path, "w", newline="")
                out_writer = csv.writer(out_file)
                out_writer.writerow(header)
                writers[month] = (out_file, out_writer)
            writers[month][1].writerow(row)
            rows_written += 1

    for out_file, _ in writers.values():
        out_file.close()

    print(f"{len(writers)} files, {rows_written:,} rows written to {OUTPUT_DIR}")
    if rows_written != EXPECTED_ROWS:
        raise ValueError(f"Expected {EXPECTED_ROWS:,} rows, wrote {rows_written:,}")


if __name__ == "__main__":
    main()