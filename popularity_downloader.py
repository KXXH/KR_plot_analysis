import requests
from datetime import date, timedelta
from concurrent import futures
import argparse
from pathlib import Path

URL = "http://files.tmdb.org/p/exports/tv_series_ids_%m_%d_%Y.json.gz"
FILENAME = "data/tv_series_ids_%m_%d_%Y.json.gz"

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--path", help="下载数据的目录", default="data", type=Path)
parser.add_argument("-t", "--thread", help="并行线程数", type=int)
parser.add_argument("-s", "--start", help="日报的开始日期", default=str(
    date.today()), type=date.fromisoformat)
# 根据网站客服提供的技术信息，daily report只能访问90天内的导出
parser.add_argument("-n", help="要下载的天数", default=1, type=int)


def download(cur_date: date)->str:
    """下载日期为cur_date的daily export

    返回结果字符串。
    """

    target_url = cur_date.strftime(URL)
    print(f"下载{target_url}...")
    r = requests.get(target_url)
    content = r.content
    if len(content) < 1000 and b"Access Denied" in content:
        print(f"{target_url}无法访问!")
        return f"{target_url}无法访问!"
    else:
        target_filename = cur_date.strftime(FILENAME)
        with open(target_filename, "wb") as f:
            f.write(content)
        print(f"成功保存至{target_filename}")
        return f"成功保存至{target_filename}"


if __name__ == "__main__":
    arg = parser.parse_args()
    START_DATE = arg.start
    todo = (START_DATE+n*timedelta(days=1) for n in range(arg.n))
    with futures.ThreadPoolExecutor(arg.thread) as exeutor:
        results = exeutor.map(download, todo)
    for result in results:
        print(result)
