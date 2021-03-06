import re
from jieba import Tokenizer
from itertools import chain, filterfalse, combinations
from collections import defaultdict, Counter, namedtuple
from efficient_apriori import apriori


class Movie_Tokenizer:
    SKIP_SPACE_RE = re.compile(r"^\s*$")
    BREAK_SENTENCE_RE = re.compile(r"[。;；.……!！]")
    STOPWORDS = set()

    def __init__(self):
        self.dt = Tokenizer()
        self.dt.initialize()  # 预加载字典，避免界面卡顿
        self.name_dict = {}
        self.reversed_name_dict = {}

        self.text = None
        self._cut_result = []
        self.splited_result = []

    def set_text(self, text):
        text = text.strip()
        if self.text != text:
            self.text = text
            self._split_text()
            self._cache_expired()  # 缓存过期

    def _split_text(self):
        self.splited_result = list(self._filter_empty(
            self.BREAK_SENTENCE_RE.split(self.text)))
        return self.splited_result

    def _filter_empty(self, result):
        return list(filterfalse(lambda text: self.SKIP_SPACE_RE.match(text), result))

    def _generate_words_dict(self):
        d = self.name_dict
        res = set(chain.from_iterable(d.values())).union(d.keys())
        return res

    def _cache_expired(self):
        self._cut_result = []

    def cut(self):
        if self._cut_result:
            return self._cut_result
        if not self.splited_result:
            self._split_text()
        words_dict = self._generate_words_dict()
        for word in words_dict:
            self.dt.add_word(word)
        res = map(self.dt.cut, self.splited_result)
        res = list(self._filter_empty(line_cut) for line_cut in res)
        self._cut_result = res
        return res

    def add_name(self, name):
        self.name_dict.setdefault(name, set())
        self._cache_expired()

    def add_alias(self, name, alias):
        self.name_dict[name].add(alias)
        self.reversed_name_dict[alias] = name
        self._cache_expired()

    def get_alias(self, name):
        return self.name_dict[name]

    def get_names(self):
        return set(self.name_dict.keys())

    def del_name(self, name):
        for alias in self.name_dict[name]:
            del self.reversed_name_dict[alias]
        del self.name_dict[name]
        self._cache_expired()

    def del_alias(self, name, alias):
        del self.reversed_name_dict[alias]
        self.name_dict[name].discard(alias)
        self._cache_expired()

    def initialize_tokenizer(self):
        self.dt = Tokenizer()
        self.dt.initialize()
        self._cache_expired()

    def names_by_sentence(self, drop_empty=False):
        cut_result = self.cut()
        words_dict = self._generate_words_dict()
        for line in cut_result:
            # 替换角色名
            word_set = set(self.reversed_name_dict.get(
                word) or word for word in line)
            # 过滤停用词
            word_set_without_stopwords = set(filter(
                lambda word: word not in self.STOPWORDS, word_set))
            # 取剩余结果和角色名字典的交集
            name_set = word_set_without_stopwords & words_dict
            if drop_empty and not name_set:
                continue
            yield name_set

    def co_present(self):
        res = defaultdict(lambda: defaultdict(int))
        for name_set in self.names_by_sentence():
            for name1, name2 in combinations(name_set, 2):
                res[name1][name2] += 1
                res[name2][name1] += 1
        return res

    def word_freq(self):
        word_list = self.cut()
        words_without_stopwords = filterfalse(
            lambda x: x in self.STOPWORDS, chain.from_iterable(word_list))
        res = Counter(words_without_stopwords)
        return res

    def import_name_dict(self, name_dict):
        self.name_dict = name_dict
        for name in name_dict:
            for alias in name_dict[name]:
                self.reversed_name_dict.setdefault(alias, name)
        self._cache_expired()

    def import_stopwords(self, filename="edited_baidu_stopwords.txt"):
        self.STOPWORDS = set(line.strip() for line in open(
            filename, encoding="utf8").readlines())
        self._cache_expired()

    def apriori(self, min_support=0.01):
        names_by_sentence = list(self.names_by_sentence(drop_empty=True))
        itemsets, rule = apriori(names_by_sentence, min_support=min_support)
        return itemsets
