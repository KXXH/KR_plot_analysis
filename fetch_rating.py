from pathlib import Path
import requests
import json

from TMDBApi import TMDBApi, load_key_from_file
tmdb_key = load_key_from_file("api.key")

api = TMDBApi(tmdb_key, "zh-CN")
KEY = ["k_FS90bMM6", "k_68tfLT53", "k_YDWk2fjE", ]
api_key = KEY[1]
TVs = (x for x in Path("./data/TVs").iterdir() if x.is_dir())
for tv in TVs:
    filenames = [x.name for x in tv.iterdir()]
    if "meta.json" in filenames and "ratings.json" not in filenames:
        d = json.load(open(tv/"meta.json", "r", encoding="utf8"))
        tv_id = d['tv_id']
        ids = api.get_external_ids("tv", tv_id)
        if "imdb_id" in ids:
            url = f"https://imdb-api.com/en/API/Ratings/{api_key}/{ids['imdb_id']}"
            r = requests.get(url)
            ratings = r.json()
            json.dump(ratings, open(tv/"ratings.json", "w"))
            print(f"成功保存{tv}的rating!")
            print("TMDB", "✔"if ratings.get("theMovieDb") else "❌")
            print("metacritic", "✔"if ratings.get("metacritic") else "❌")
            print("imDb", "✔"if ratings.get("imDb") else "❌")
            print("rottenTomatoes", "✔"if ratings.get(
                "rottenTomatoes") else "❌")
        else:
            print(f"❌:{tv}没有imdb的id")
    else:
        print(
            f"❌:{tv}没有meta.json" if "meta.json" not in filenames else f"✔:{tv}已经存在ratings")
