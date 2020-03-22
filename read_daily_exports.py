import gzip
from pathlib import Path
import json
import sqlite3
import logging
import re
import argparse

logging.basicConfig(level=logging.INFO)
FILENAME_RE = re.compile(r"tv_series_ids_(\d{2})_(\d{2})_(\d{4})\.json")

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group()
group.add_argument("-f", "--file", help="指定读取的文件名")
group.add_argument("-p", "--path", help="指定读取目录下所有文件", default="data")


def file2db(fpath: Path, conn)->None:
    """把文件名为fpath的文件写入数据库tv.db

    fpath是Path对象
    """
    logging.info(f"reading {fpath}...")
    month, day, year = map(int, FILENAME_RE.match(fpath.name).groups())
    date = f"{year}-{month}-{day}"
    with gzip.open(fpath, "rb") as f:
        for line in f:
            d = json.loads(line.decode("utf8"))
            conn.execute(
                sql, (d["id"], d["original_name"], d["popularity"], date))
    conn.commit()


if __name__ == "__main__":
    conn = sqlite3.connect("tv.db")
    sql = "INSERT INTO popularity (id,original_name,popularity,create_at) VALUES(?,?,?,?)"
    arg = parser.parse_args()
    if arg.file:
        file2db(Path(arg.file), conn)
    else:
        for fpath in Path(arg.path).glob("*.gz"):
            file2db(fpath, conn)
    conn.close()
