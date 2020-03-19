import requests
from lxml import etree
import logging
from collections import namedtuple
import re
from itertools import dropwhile, takewhile, tee, chain
import sqlite3
from time import sleep
from concurrent import futures
import queue
from functools import wraps
from threading import Lock

Plot_para = namedtuple(
    "Plot_para", ("show_name", "episode", "title", "detail", "url"))

# 预编译常用正则表达式

EPISODE_RE = re.compile(
    r".*第?([一二三四五六七八九十\d]+)[集回](?:韩剧|剧情|分集|简介|介绍|(?:第?\d+(?:-\d+)?[集回])|大结局|[()])*[《]?([^《》]*)[》：:]*.*")
EXTRACT_EPISODE_RE = re.compile(r"第?([\d一二三四五六七八九十百]+)[集回]")
SHOW_NAME_RE = re.compile(
    r"(?:韩剧)?(.*?)(韩剧|剧情|分集|简介|介绍|(?:第?\d+(?:-\d+)?[集回])|大结局)+.*")
TITLE_LENGTH = 35


def get_full_content(dom):
    return "".join(dom.xpath(".//text()")).strip()


def debug_tool(func):

    def dom2text(dom):
        if isinstance(dom, etree._Element):
            return get_full_content(dom)
        else:
            return dom

    @wraps(func)
    def inner(*args, **kwargs):
        ans = func(*args, **kwargs)
        logging.debug(
            f"{func.__name__} {list(map(dom2text, args))} {kwargs} {ans}")
        return ans
    return inner


class PageNotFoundException(Exception):
    pass


class Urls:
    def __init__(self):
        self.todo = set()
        self.done = set()
        self.fail = queue.Queue()
        self.lock = Lock()

    def get_url(self):
        self.lock.acquire()
        url = self.todo.pop()
        logging.debug(f"get_url returns {url}.")
        self.lock.release()
        return url

    def done_url(self, url):
        self.lock.acquire()
        self.done.add(url)
        self.lock.release()
        logging.debug(f"{url} is done.")

    def is_done(self, url):
        self.lock.acquire()
        flag = url in self.done
        self.lock.release()
        return flag

    def fail_url(self, url):
        self.fail.put(url)
        logging.warning(f"{url} failed!")

    def add_urls(self, urls):
        self.lock.acquire()
        self.todo = self.todo.union(urls)
        if None in self.todo:
            self.todo.remove(None)
        self.lock.release()

    def empty(self):
        self.lock.acquire()
        flag = bool(len(self.todo) == 0)
        self.lock.release()
        return flag


class Download:
    def download(self, url, encodeing="gbk"):
        r = requests.get(url)
        if r.status_code == 404:
            raise PageNotFoundException()
        r.encoding = encodeing
        return r.text


class PlotParser:
    @staticmethod
    def predicate(episode, title_matched=True):
        """工厂函数，生产条件选择器

        允许p和u标签并且不含有第x集，或是含有第x集，且x=episode的标签
        """

        @debug_tool
        def f(r):
            nonlocal title_matched
            logging.debug(f"episode={episode}, title_matched={title_matched}")
            content = get_full_content(r)
            if PlotParser.is_episode(r, episode):
                return False
            elif not title_matched and PlotParser.is_title(r):
                title_matched = True
                return False
            else:
                return True
        return f

    def __init__(self, show_name, html, url, urls):
        self.html = etree.HTML(html)
        self.show_name = show_name
        self.url = url
        self.urls = urls

    @staticmethod
    @debug_tool
    def is_episode(r, episode=""):
        content = get_full_content(r)
        match = EPISODE_RE.match(content)
        if match and match.group(1) and match.group(1) != episode and len(content) < TITLE_LENGTH:
            return True
        else:
            return False

    @staticmethod
    @debug_tool
    def is_title(r, episode="", skip_episode=False):
        flag = (bool(r.tag == "strong") or len(
            get_full_content(r)) < TITLE_LENGTH) and (skip_episode or not PlotParser.is_episode(r, episode))
        logging.debug(f"len={len(get_full_content(r))}")
        logging.debug(f"{get_full_content(r)} is {flag}")

        return flag

    @staticmethod
    def skip_empty_lines(it):
        return takewhile(lambda r: bool(get_full_content(r)), it)

    def parse_html(self):
        logging.info(f"parsing {self.url}...")
        # self.put_urls()
        yield from self.get_plots()
        self.urls.done_url(self.url)
        logging.info(f"{self.url}已经完成")

    def get_plots(self):
        results = self.html.xpath(
            "//div[@id='AAA']/p | //h4"
        )
        try:
            while True:
                results, plot = self.get_plot(results)
                logging.debug(
                    f"find a new plot {plot.title:.10s}:{plot.detail:.10s}... from {self.url}.")
                yield plot
        except StopIteration:
            logging.info(f"{self.url} parse is done.")
        except TypeError as e:
            logging.warning(f"except type error! error is {e}")
            raise

    def get_plot(self, results):
        #results = list(results)
        #print("results=", list(map(get_full_content, results)))
        results = iter(results)  # 保证results是迭代器
        logging.debug(f"getting plots...")

        # 尝试解决空格行的问题
        #results = PlotParser.skip_empty_lines(results)
        episode_dom = next(results)
        logging.debug(f"episode_dom={episode_dom.text}")

        # 匹配集数
        episode_title = get_full_content(episode_dom)
        match = EPISODE_RE.search(episode_title)
        if match:
            episode = EXTRACT_EPISODE_RE.search(episode_title).group(1)
        else:
            episode = "0"

        # 创建条件判别函数
        predicate = self.predicate(episode, title_matched=True)
        # 剧情详细描述
        detail = ""

        if match and match.group(2):
            # 如果第x集后有标题，则设置标题
            title = match.group(2)
            if len(match.group(2)) > TITLE_LENGTH:
                # 如果提取出的标题太长，说明已经进入正文，标题视为没有匹配到
                title, detail = "", title
            else:
                # 重置判别函数，设置为已经匹配标题
                predicate = self.predicate(episode, title_matched=True)
        else:
            # 否则需要匹配标题(下一行)
            title_dom = next(results)
            title = get_full_content(title_dom)
            # 尝试识别是否为标题，如果该行不加粗且字数超过30，认为该行属于正文
            if not PlotParser.is_title(title_dom, skip_episode=True):
                title, detail = "", title
                logging.warning(f"{self.show_name}-{episode} missing title!")
            else:
                predicate = self.predicate(episode, title_matched=True)

        rest_it = results
        for line in results:
            logging.debug(f"line={get_full_content(line)}")
            if predicate(line):
                detail += get_full_content(line)
            else:
                rest_it = chain([line, ], results)
                break
        return rest_it, Plot_para(self.show_name, episode, title, detail, self.url)

    def put_urls(self):
        intros = self.html.xpath('//ul[contains(@class,"c2")]//a')
        for intro in intros:
            url = intro.get("href")
            text = get_full_content(intro)
            if PlotParser.is_episode(intro) and not self.urls.is_done(url):
                self.urls.add_urls([(url, self.show_name), ])
                logging.debug(f"put {url} into urls")
        return intros


class PlotScheduler:
    def __init__(self, urls,  limit=100):
        self.limit = limit
        self.download = Download()
        self.urls = urls

    def get_plots(self, base_url, show_name):
        parser = PlotParser(
            show_name,
            self.download.download(f"{base_url}.html"),
            f"{base_url}.html",
            self.urls
        )
        yield from parser.parse_html()
        try:
            for i in range(2, self.limit):
                url = f"{base_url}_{i}.html"
                html = self.download.download(url)
                parser = PlotParser(show_name, html, url, self.urls)
                yield from parser.get_plots()
        except PageNotFoundException:
            logging.info(f"{show_name}-{base_url} is done.")

    def run(self):
        while not self.urls.empty():
            base_url, show_name = self.urls.get_url()
            base_url = base_url.rstrip(".html")
            yield from self.get_plots(base_url, show_name)


class MainPageParser:
    def __init__(self, html, url=None):
        self.html = etree.HTML(html)
        self.url = url

    def parse_html(self):
        logging.info(f"parsing {self.url}...")

    def get_shows(self):
        show_links = self.html.xpath('//ul[contains(@class,"ico1")]/li/a')
        return map(MainPageParser.pre_process, show_links)

    @staticmethod
    def pre_process(show_link):
        try:
            show_name = SHOW_NAME_RE.match(show_link.text).group(1)
            href = show_link.get("href")
            logging.info(f"find {show_name} at {href}")
            return href, show_name
        except TypeError:
            logging.warning(f"failed to parse name at {show_link}")
        except AttributeError:
            logging.warning(
                f"re failed to find show_name. text={show_link.text}")
            if not re.search(r"\u6F14\u5458\u8868", show_link.text):
                raise

    @staticmethod
    def process(show):
        yield from PlotScheduler(show[0], show_name=show[1]).get_plots()


class MainPageScheduler:
    def __init__(self, base_url, limit=100, urls=None):
        self.base_url = base_url.rstrip(".html")
        self.limit = limit
        self.download = Download()
        self.urls = urls

    def get_shows(self):
        """尝试不断增加页码，直到404

        解析页面上所有的剧名和链接，放入任务队列
        """

        try:
            for i in range(1, self.limit):
                url = f"{self.base_url}_{i}.html"
                self.urls.add_urls(
                    MainPageParser(self.download.download(
                        url), url).get_shows()
                )
        except PageNotFoundException:
            logging.info(f"crawler on {self.base_url} is done.")


class Output:

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS "plots" (
        "show_name"	TEXT,
        "episode"	TEXT,
        "title"	TEXT,
        "detail"	TEXT,
        "edit_time"	TEXT,
        "url" TEXT
    );
    """

    INIT_SQL = """
    DELETE FROM plots WHERE datetime("now")>plots.edit_time;
    """

    def __init__(self):
        pass

    def __enter__(self):
        return self

    def open_db(self, filename):
        self.conn = sqlite3.connect(filename)
        self.conn.execute(self.SCHEMA)
        self.conn.execute(self.INIT_SQL)
        self.conn.commit()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()
        if exc_type:
            raise

    def store_to_db(self, plots):
        sql = """
        INSERT INTO plots (show_name,episode,title,detail,edit_time,url) VALUES(?,?,?,?,?,datetime("now"))
        """
        self.conn.executemany(sql, plots)
        self.conn.commit()


class Scheduler:
    def __init__(self):
        self.urls = Urls()
        self.mainPageScheduler = MainPageScheduler(
            "http://www.bjxyxd.com/3/list_3.html", limit=58, urls=self.urls)
        self.plotScheduler = PlotScheduler(self.urls)
        self.output = Output()

    def crawler(self):
        self.mainPageScheduler.get_shows()
        input(
            f"韩剧索引已完成，共找到剧集链接{len(self.mainPageScheduler.urls.todo)}，任意键继续")
        with self.output.open_db("tv.db") as output:
            with futures.ThreadPoolExecutor(8) as executor:
                todo_list = []
                for i in range(8):
                    future = executor.submit(self.plotScheduler.run)
                    todo_list.append(future)
                results = futures.as_completed(todo_list)
                # 把所得结果拍扁以后传给数据库
                output.store_to_db(chain.from_iterable(
                    map(lambda i: i.result(), results)))


logging.basicConfig(level=logging.INFO, filename="log.log")
if __name__ == "__main__":

    scheduler = Scheduler()
    scheduler.crawler()
