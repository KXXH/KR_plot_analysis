from pathlib import Path
import jieba
from plot_analysis_tool.movie_tokenizer import Movie_Tokenizer
from collections import Counter
import json

tokenizer = Movie_Tokenizer()
tokenizer.import_stopwords()
p = Path("./data/TVs")
tv_dirs = (x for x in p.iterdir() if x.is_dir())
for tv_dir in tv_dirs:
    print(f"处理{tv_dir}...")
    c = Counter()
    plots = (x for x in tv_dir.iterdir() if x.match("plot_*.txt"))
    for plot in plots:
        print(f"打开{plot}...")
        tokenizer.set_text(open(plot, encoding="utf8").read())
        c.update(tokenizer.word_freq())
    json.dump(c, open(tv_dir/"word_freq.json", "w"))
