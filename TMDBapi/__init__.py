import requests
import logging
from functools import lru_cache, partialmethod
from itertools import islice


def load_key_from_file(filename):
    with open(filename, "r") as f:
        return f.read()


class TMDBApi:
    def __init__(self, api_key, language, enable_https=False, retry=3):
        self.api_key = api_key
        self.language = language
        schema = "http" if not enable_https else "https"
        self.base_url = f"{schema}://api.themoviedb.org/3"
        self.base_params = {
            "api_key": self.api_key,
            "language": self.language
        }
        self.session = requests.Session()
        self.session.mount(
            self.base_url, requests.adapters.HTTPAdapter(max_retries=retry))

    def _merge_dict(self, d):
        base_params = self.base_params.copy()
        base_params.update(d)
        return base_params

    @lru_cache()
    def get_details(self, id, target):
        logging.info(f"downloading {target}-{id} detail...")
        url = f"{self.base_url}/{target}/{id}"
        r = self.session.get(url, params=self.base_params)
        return r.json()

    get_tv_details = partialmethod(get_details, target="tv")
    get_movie_details = partialmethod(get_details, target="movie")
    get_person_detail = partialmethod(get_details, target="person")

    @lru_cache()
    def get_credits(self, id, target):
        logging.info(f"downloading {target}-{id} credits...")
        url = f"{self.base_url}/{target}/{id}/credits"
        r = self.session.get(url, params=self.base_params)
        return r.json()
    get_tv_credits = partialmethod(get_credits, target="tv")
    get_movie_credits = partialmethod(get_credits, target="movie")

    @lru_cache()
    def search(self, query, target, page=1, first_air_date_year=None):
        logging.info(f"searching {query} {target}...")
        url = f"{self.base_url}/search/{target}"
        r = self.session.get(
            url,
            params=self._merge_dict({
                "query": query,
                "page": page,
                "first_air_date_year": first_air_date_year
            })
        )
        return r.json()

    @lru_cache()
    def get_popular(self, page, target):
        logging.info(f"get popular {target} at page {page}...")
        url = f"{self.base_url}/{target}/popular"
        r = self.session.get(
            url,
            params=self._merge_dict(
                {"page": page}
            )
        )
        return r.json()

    def get_popular_iter(self, target, limit=float("inf")):
        count = 0
        for page in range(1, 1000):
            j = self.get_popular(page, target)
            results = j["results"]
            item_nums = len(results)
            if count+item_nums >= limit:
                yield from islice(results, int(limit-count))
                break
            else:
                count += item_nums
                yield from results

    @lru_cache()
    def get_genre_list(self, target):
        logging.info(f"get genre list for {target}...")
        url = f"{self.base_url}/genre/{target}/list"
        r = self.session.get(url, params=self.base_params)
        return r.json().get("genres", [])

    get_tv_genre_list = partialmethod(get_genre_list, target="tv")
    get_movie_genre_list = partialmethod(get_genre_list, target="movie")
