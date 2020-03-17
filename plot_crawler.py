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


Plot_para = namedtuple(
    "Plot_para", ("show_name", "episode", "title", "detail"))

# 预编译常用正则表达式

EPISODE_RE = re.compile(
    r".*第([一二三四五六七八九十\d]+)集(?:韩剧|剧情|分集|简介|介绍|(?:第?\d+(?:-\d+)?集)|大结局|[()])*(.*)")
SHOW_NAME_RE = re.compile(
    r"(?:韩剧)?(.*?)(韩剧|剧情|分集|简介|介绍|(?:第?\d+(?:-\d+)?集)|大结局)+.*")
TITLE_LENGTH = 35


def get_full_content(dom):
    return "".join(dom.xpath(".//text()")).strip()


class PageNotFoundException(Exception):
    pass


class Urls:
    def __init__(self):
        self.todo = queue.Queue()
        self.done = queue.Queue()
        self.fail = queue.Queue()

    def get_url(self):
        url = self.todo.get()
        logging.debug(f"get_url returns {url}.")
        return url

    def done_url(self, url):
        self.done.put(url)
        logging.debug(f"{url} is done.")

    def fail_url(self, url):
        self.fail.put(url)
        logging.warning(f"{url} failed!")

    def add_urls(self, urls):
        for url in urls:
            if url:
                logging.info(f"{url} is added.")
                self.todo.put(url)


class Download:
    def download(self, url, encodeing="gbk"):
        r = requests.get(url)
        if r.status_code == 404:
            raise PageNotFoundException()
        r.encoding = encodeing
        return r.text


class PlotParser:
    @staticmethod
    def predicate(episode):
        """工厂函数，生产条件选择器

        允许p和u标签并且不含有第x集，或是含有第x集，且x=episode的标签
        """

        def f(r):
            if PlotParser.is_title(r):
                return False
            match = EPISODE_RE.match(
                "".join(r.xpath(".//text()")).strip())  # 规避None问题
            if r.tag in ("p", "u") and not match:
                return True
            else:
                try:
                    if match.group(1) == episode:
                        return True
                except (AttributeError,) as e:
                    # logging.warning(f"except an error when processing re: {e}")
                    # 遇到AttributeError说明匹配失败，匹配失败应该通过
                    return True
            return False
        return f

    def __init__(self, show_name, html, url=None):
        self.html = etree.HTML(html)
        self.show_name = show_name
        self.url = url

    @staticmethod
    def is_title(r):
        flag = bool(r.find("strong")) or len(
            get_full_content(r)) < TITLE_LENGTH
        logging.debug("len=", len(get_full_content(r)))
        logging.debug(f"{get_full_content(r)} is {flag}")

        return flag

    @staticmethod
    def skip_empty_lines(it):
        return takewhile(lambda r: bool(get_full_content(r)), it)

    def parse_html(self):
        logging.info(f"parsing {self.url}...")
        yield from self.get_plots()

    def get_plots(self):
        results = self.html.xpath(
            "//div[@id='AAA']/p[not(strong)] | //h4"
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
        results = iter(results)  # 保证results是迭代器
        logging.debug(f"getting plots...")
        # 尝试解决空格行的问题
        results = PlotParser.skip_empty_lines(results)
        title_dom = next(results)
        logging.debug(f"title_dom={title_dom.text}")

        # 匹配集数
        match = EPISODE_RE.search(get_full_content(title_dom))
        it1, it2 = tee(results)
        episode = match.group(1) if match else "0"
        predicate = self.predicate(episode)
        if match and match.group(2):
            title = match.group(2)
        else:
            # 匹配标题
            title_dom = next(results)
            title = get_full_content(title_dom)
            # 复制出两个迭代器，一个用于本循环，另一个用于返回
            it1, it2 = tee(results)
            # 尝试识别是否为标题，如果该行不加粗且字数超过30，认为该行属于正文
            if not PlotParser.is_title(title_dom):
                title, detail = "", title_dom.text.strip()
                logging.warning(f"{self.show_name}-{episode} missing title!")
        detail = "\n".join(
            map(
                lambda r: "".join(r.xpath(".//text()")).strip(),
                takewhile(predicate, it1)
            )
        )
        return dropwhile(predicate, it2), Plot_para(self.show_name, episode, title, detail)

    def get_next_url(self):
        intros = set(self.html.xpath(
            "//div[@class='intro']/a/@href"))-set([self.url, ])
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
            f"{base_url}.html"
        )
        yield from parser.parse_html()
        try:
            for i in range(2, self.limit):
                parser = PlotParser(
                    show_name,
                    self.download.download(f"{base_url}_{i}.html"),
                    base_url
                )
                yield from parser.parse_html()
        except PageNotFoundException:
            logging.info(f"crawler on {base_url} is done.")
            self.urls.done_url(f"{base_url}.html")

    def run(self):
        while not self.urls.todo.empty():
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
        "edit_time"	TEXT
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
        INSERT INTO plots (show_name,episode,title,detail,edit_time) VALUES(?,?,?,?,datetime("now"))
        """
        print(type(plots))
        print(type(next(plots)))
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scheduler = Scheduler()
    scheduler.crawler()
