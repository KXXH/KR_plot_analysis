import sqlite3
from datetime import date, timedelta
import logging
import requests
import time
import json
import pandas as pd
import argparse

logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument("start", help="分析开始的日期【请确保已经存在文件！】",
                    type=date.fromisoformat)
parser.add_argument("days", help="总共分析的天数【请确保所有日期文件都已经存在！】", type=int)
parser.add_argument("-k", "--key", help="API密钥")
parser.add_argument("-o", "--output", help="输出文件名，支持使用{start_date}和{end_date}格式化",
                    default="data/top10_{start_date}_{end_date}.csv")


def get_api_from_file():
    with open("api.key", "r") as f:
        key = f.read()
    return key


def fetch_top10(cur_date):
    logging.info(
        f"fetching top10 tvs at date {cur_date.strftime('%Y-%m-%d')}...")
    start_time = time.time()
    cur.execute(sql, (f"{cur_date.year}-{cur_date.month}-{cur_date.day}",))
    end_time = time.time()
    ans = cur.fetchall()
    logging.info(
        f"fetch top10 tvs at date {cur_date} complete. Time use: {end_time-start_time}s. Ans={ans}")
    return ans


def id2info(id):
    url = API_ENDPOINT.format(tv_id=id)
    logging.info(f"connect to {url}...")
    r = requests.get(url, params={
        "api_key": API_KEY,
        "language": "zh-CN"
    })
    j = r.json()
    d = {
        "name": j["name"],
        "region": j['origin_country'][0] if j['origin_country'] else "",
        "image_url": IMAGE_URL.format(country=j['origin_country'][0] if j['origin_country'] else "")
    }
    logging.info(
        f"successfully download {j['name']} info. original country is {j['origin_country']}")
    return d


if __name__ == "__main__":
    conn = sqlite3.connect("tv.db")
    sql = "SELECT id,popularity FROM popularity WHERE create_at=? ORDER BY popularity DESC LIMIT 10"
    cur = conn.cursor()
    arg = parser.parse_args()
    start_date = arg.start
    days = arg.days
    tv_infos = {}
    API_KEY = arg.key or get_api_from_file()
    API_ENDPOINT = "http://api.themoviedb.org/3/tv/{tv_id}"
    IMAGE_URL = "https://www.countryflags.io/{country}/flat/64.png"

    date_list = list(start_date+n*timedelta(days=1) for n in range(days))
    top10_lists = (fetch_top10(d) for d in date_list)

    # 下载id对应的影视信息
    for top10_list, cur_date in zip(top10_lists, date_list):
        id_sets = set(item[0] for item in top10_list)
        id_sets -= tv_infos.keys()
        cur_tv_info = ((id, id2info(id)) for id in id_sets)
        tv_infos.update(cur_tv_info)
        for id, popularity in top10_list:
            tv_infos[id][cur_date.strftime('%Y-%m-%d')] = popularity
        time.sleep(.1)

    df = pd.DataFrame(list(tv_infos.values()), columns=(
        "name", "region", "image_url", *map(str, date_list)))
    filename = arg.filename.format(
        start_date=start_date, end_date=start_date+timedelta(days=days))
    df.to_csv(filename, na_rep="0")
