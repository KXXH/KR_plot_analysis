import requests
from lxml import etree
import argparse
from datetime import date, timedelta
import logging
import sqlite3
from collections import defaultdict
import time
import pandas as pd
import re
from functools import partial
from concurrent import futures

parser = argparse.ArgumentParser()
parser.add_argument("start", help="爬虫开始日期", default=str(
    date.today()), type=date.fromisoformat)
parser.add_argument("end", help="爬虫结束日期", default=str(
    date.today()), type=date.fromisoformat)
parser.add_argument("area", help="地区编码，01表示大都市区，00表示全国",
                    choices=("00", "01"), default="00")
parser.add_argument("-d", "--db", help="数据库位置", default="tv.db")
parser.add_argument("-v", "--verbose", help="显示日志输出", action="store_true")
parser.add_argument("-t", "--thread", help="并行线程数", default=8, type=int)

DOWNLOAD_URL = "http://www.nielsenkorea.co.kr/tv_terrestrial_day.asp"

REMOVE_COMMA_RE = re.compile(",")
remove_comma = partial(REMOVE_COMMA_RE.sub, "")

SCHEMA = """
    CREATE TABLE IF NOT EXISTS "kr_top20"(
        "show_name" TEXT,
        "rating" REAL,
        "viewnum" INTEGER,
        "record_date" TEXT,
        PRIMARY KEY("show_name","record_date")
    )
    """


def download(url, cur_date: date, area)->str:
    logging.debug(f"正在下载URL: {url}...")
    r = requests.get(url, params={
        "menu": "Tit_1",
        "sub_menu": "1_1",
        "area": area,
        "begin_date": cur_date.strftime("%Y%m%d")
    })
    r.encoding = "utf8"
    return r.text


def parse_table(table):
    rows = table.xpath("./tr[count(./td)>1 and not(@class)]")
    logging.debug(f"从表格中解析了{len(rows)}条记录")
    res = defaultdict(lambda x: None)
    for row in rows:
        rank, channel, name, rate = map(
            lambda item: item.xpath("normalize-space()"), row.xpath("td"))
        res[name] = remove_comma(rate)
    return res


def parse_html(s_html):
    html = etree.HTML(s_html)
    top20_rating, top20_viewnum = html.xpath("//table[@class='ranking_tb']")
    d_rating = parse_table(top20_rating)
    d_viewnum = parse_table(top20_viewnum)
    df_rating = pd.DataFrame(list(d_rating.items()),
                             columns=("name", "rating"))
    df_viewnum = pd.DataFrame(list(d_viewnum.items()),
                              columns=("name", "viewnum"))
    df_res = df_rating.merge(df_viewnum, how="outer")
    df_res["rating"] = df_res["rating"].apply(pd.to_numeric, errors='ignore')
    df_res["viewnum"] = df_res["viewnum"].apply(pd.to_numeric, errors='ignore')
    return df_res


class Scheduler:
    def __init__(self, start, end, area, db_fname, thread):
        self.start = start
        self.end = end
        self.area = area
        self.conn = sqlite3.connect(db_fname)
        self.thread = thread

    def download_date(self, cur_date):
        df = parse_html(download(DOWNLOAD_URL, cur_date, self.area))
        df["record_date"] = cur_date
        time.sleep(.1)
        return df

    def crawler(self):
        dt = timedelta(days=1)
        days = (self.end-self.start).days+1
        todo = (self.start+n*dt for n in range(days))
        with futures.ThreadPoolExecutor(self.thread) as executor:
            result = executor.map(self.download_date, todo)
        for df in result:
            df.to_sql("kr_top20", self.conn, SCHEMA,
                      if_exists="append", index=False)


if __name__ == "__main__":
    arg = parser.parse_args()
    if arg.verbose:
        logging.basicConfig(level=logging.DEBUG)
    scheduler = Scheduler(arg.start, arg.end, arg.area, arg.db, arg.thread)
    scheduler.crawler()
