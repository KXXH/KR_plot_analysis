from plot_crawler import PlotParser, Urls, PlotScheduler
import pytest
from lxml import etree
import pdb


def make_filename(filename):
    return "./tests/plots/"+filename


@pytest.mark.parametrize(
    "filename,episodes,titles",
    [
        (make_filename("1.html"), ["30", ], ["", ]),
        (make_filename("2.html"), ["1", "2"], ["案件发生帅气警官变花样爷爷", "新婚夫妇被杀案件"]),
        (make_filename("3.html"), ["1", "2"], [
         "子欲养而亲不待朴世路无父何怙", "为父亲含冤入狱朴世路复仇之路开启"]),
        (make_filename("4.html"), ["1", "2"],
         ["安娜与交往8年女友分后十分伤感 徐妍对自己是否坚持梦想始终不明", "安娜与母亲争吵后关系和解 宥拉智亨两小无猜因搬家而中断"]),
        (make_filename("5.html"), ["1", "2"], ["朴达乡入京科考", "大元帅金自点秘谋造反"]),
        (make_filename("7.html"), ["一", "二"], [
         "再见教练", "没有犯人的杀人夜"]),
        (make_filename("8.html"), ["11", "12"], [""]*2),
        (make_filename("9.html"), ["8", ], ["", ]),
        (make_filename("10.html"), ["16", ], ["", ]),
        (make_filename("11.html"), ["66", ], ["", ])
    ]
)
def test_plot_parse(filename, episodes, titles):
    urls = Urls()
    with open(filename, "r", encoding="gbk") as f:
        html = f.read()
        parser = PlotParser("test", html, filename, urls)
        plot_it = parser.parse_html()
        for i, (episode, title, plot) in enumerate(zip(episodes, titles, plot_it)):
            #plot = next()
            # pdb.set_trace()
            print(plot)
            assert plot.episode == episode
            assert plot.title == title
            assert len(plot.detail) > 50


"""
@pytest.mark.parametrize("filename,links", [
    (make_filename("10.html"), [
        "http://www.bjxyxd.com/7/29375.html",
        "http://www.bjxyxd.com/3/23175.html",
        "http://www.bjxyxd.com/3/23091.html",
        "http://www.bjxyxd.com/3/22252.html",
        "http://www.bjxyxd.com/9/22095.html",

    ])
])
def test_links(filename, links):
    urls = Urls()
    with open(filename, "r", encoding="gbk") as f:
        html = f.read()
        parser = PlotParser("test", html, filename, urls)
        plot_it = parser.put_urls()
        s = set(map(lambda x: x[0], urls.todo))
        print(s)
        assert s == set(links)
"""


@pytest.mark.parametrize(
    "base_url,episodes", [
        ("http://www.bjxyxd.com/3/50417.html", 12)
    ]
)
def test_episodes(base_url, episodes):
    urls = Urls()
    urls.add_urls([base_url, ])
    scheduler = PlotScheduler(urls)
    plots = scheduler.get_plots(base_url.rstrip(".html"), "test")
    for ep in range(1, episodes+1):
        plot = next(plots)
        print(plot)
        assert plot.episode == str(ep)
