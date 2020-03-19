import sqlite3
from collections import Counter
import jieba
import matplotlib.pyplot as plt
import wordcloud

FONTS = r"C:\Windows\Fonts\simfang.ttf\msyh.ttc"


def stopwordslist():
    stopwords = set(line.strip() for line in open(
        'edited_baidu_stopwords.txt', encoding='UTF-8').readlines())
    return stopwords


conn = sqlite3.connect("tv.db")
cur = conn.cursor()
sql = "SELECT detail FROM plots"
cur.execute(sql)
it = cur.fetchone()
word_freq = Counter()
record_count = 0
word_count = 0
stopwords = stopwordslist()
while it:
    detail = it[0]
    record_count += 1
    word_count += len(detail)
    cut_result = jieba.cut(detail)
    filtered_result = filter(lambda x: x not in stopwords, cut_result)
    word_freq.update(filtered_result)
    print(f"已处理了{record_count}条记录，共{word_count}个字符")
    it = cur.fetchone()
wc = wordcloud.WordCloud(
    font_path=FONTS, background_color="white", width=1920, height=1080)
wc.generate_from_frequencies(word_freq)

plt.imshow(wc)
plt.axis('off')
plt.show()
wc.to_file("wc.jpg")
wc.to_html
