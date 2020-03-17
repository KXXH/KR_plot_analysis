from plot_crawler import PlotParser
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
        # (make_filename("7.html"), ["5", "6", "7", "8", "9", "10"], [""]*6),
        (make_filename("8.html"), ["11", "12"], [""]*2)
    ]
)
def test_plot_parse(filename, episodes, titles):
    with open(filename, "r", encoding="gbk") as f:
        html = f.read()
        parser = PlotParser("test", html, filename)
        plot_it = parser.get_plots()
        for i, (episode, title) in enumerate(zip(episodes, titles)):
            print(i)
            plot = next(plot_it)
            pdb.set_trace()
            assert plot.episode == episode
            assert plot.title == title
            assert len(plot.detail) > 50
