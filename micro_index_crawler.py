import argparse
import requests
import re
import pandas as pd
import logging

SEARCH_API_URL = "https://data.weibo.com/index/ajax/newindex/searchword"
DATA_API_URL = "https://data.weibo.com/index/ajax/newindex/getchartdata"
DATE_GROUP_CHOICES = ("1hour", "1day", "1month", "3month")
WID_RE = re.compile(r'wid="(\d+)"')

# 规避CSRF检测
headers = {
    "referer": "https://data.weibo.com/index/newindex?visit_type=search"
}


class NoKeyWord(Exception):
    pass


class EmptyHTML(Exception):
    pass


def make_session(headers):
    s = requests.Session()
    s.headers.update(headers)
    return s


def search_word(word, session=None):
    logging.info(f"查找{word}关键字的wid...")
    s = session or make_session(headers)
    r = s.post(SEARCH_API_URL, data={
        "word": word
    })
    d = r.json()
    code = d["code"]
    if code == 101:
        raise NoKeyWord(f"找不到关键词\"{word}\"!")
    else:
        assert code == 100, "code 应该为100"
        html = d["html"]
        if not html:
            raise EmptyHTML(f"\"{word}\" 关键字的返回HTML体是空的，可能是由于关键词不够长，加长试试")
        else:
            return WID_RE.search(html).group(1)


def get_chart_data(wid, dateGroup, session=None):
    logging.info(f"查找{wid}时间范围为{dateGroup}的数据...")
    s = session or make_session(headers)
    r = s.post(DATA_API_URL, data={
        "wid": wid,
        "dateGroup": dateGroup
    })
    d = r.json()
    trend = d["data"][0]["trend"]
    return zip(trend["x"], trend["s"])


parser = argparse.ArgumentParser()
parser.add_argument("word", help="查询的关键词")
parser.add_argument("dateGroup", help="查询日期范围", choices=DATE_GROUP_CHOICES)
parser.add_argument("-o", "--output", help="输出的文件名",
                    default="data\micro_index_{word}_{dateGroup}.csv")
parser.add_argument("-v", "--verbose", help="显示日志输出", action="store_true")

if __name__ == "__main__":
    arg = parser.parse_args()
    if arg.verbose:
        logging.basicConfig(level=logging.INFO)
    s = make_session(headers)
    wid = search_word(arg.word, s)
    logging.info(f"{arg.word}关键字wid是{wid}.")
    data = get_chart_data(wid, arg.dateGroup, s)
    df = pd.DataFrame(list(data), columns=["x", "s"])
    filename = arg.output.format(word=arg.word, dateGroup=arg.dateGroup)
    logging.info(f"写入{filename}中...")
    df.to_csv(filename)
    print(f"文件已写入{filename}")
