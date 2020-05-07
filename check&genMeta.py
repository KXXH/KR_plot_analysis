from pathlib import Path
from TMDBApi import TMDBApi, load_key_from_file
import json
import itertools
import re
import warnings

skip = {"3年A班-从现在起，大家都是人质", "东京大饭店"}

api = TMDBApi(load_key_from_file("api.key"), "zh-CN")
TV_paths = (p for p in Path("./data/TVs").iterdir()
            if p.is_dir() and p.name not in skip)


def check_json(filename):
    d = json.load(open(filename, "r", encoding="utf8"))
    if not d:
        warnings.warn(f"{filename}是空的")
    return True


def check_txt(filename):
    f = open(filename, "r", encoding="utf8").read()
    if not f:
        warnings.warn(f"{filename}是空的")
    return True


for TV_path in TV_paths:
    print(TV_path)
    cps = sorted(TV_path.glob("CP_S*E*.json"))
    fps = sorted(TV_path.glob("FP_S*E*.json"))
    plots = sorted(TV_path.glob("plot_S*E*.txt"))
    assert len(cps) == len(fps) and len(
        cps) == len(plots), f"共现矩阵数量、频繁模式数量、剧情数量相等, cp={len(cps)}, fp={len(fps)}, plot={len(plots)}"
    assert all(check_json(f) for f in itertools.chain(
        cps, fps)), f"所有JSON都应该以utf8编码且可以被正常解析"
    assert all(check_txt(f) for f in plots), "剧本文件是utf8编码"
    se = [re.match("FP_S(\d+)E(\d+).json", t.name).groups() for t in fps]
    if len(se) == 0:
        warnings.warn(f"{TV_path}不包含FP")
    else:
        assert all(t[0] == se[0][0] for t in se), "不允许跨季"
        season = se[0][0]
        episodes = [int(t[1]) for t in se]
        name = re.sub("\s*第.季", "", TV_path.name)
        res = api.search(name, "tv")
        tv_id = res['results'][0]['id'] if len(res['results']) > 0 else 0
        json.dump({
            "tv_id": tv_id,
            "season": int(season),
            "episodes": episodes
        }, open(TV_path/"meta.json", "w"))
