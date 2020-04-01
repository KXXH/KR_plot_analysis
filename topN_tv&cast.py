import requests
import requests.exceptions
import logging
import argparse
from TMDBApi import TMDBApi, load_key_from_file
from py2neo import Graph, Node, Relationship
from concurrent import futures

parser = argparse.ArgumentParser()
parser.add_argument("-k", "--key", help="API密钥")
parser.add_argument("-o", "--output", help="输出的目录", default="data")
parser.add_argument("-l", "--language", help="指定API查询语言", default="zh-CN")
parser.add_argument("-t", "--target", help="TOP100的目标",
                    default="tv", choices=("tv", "movie"))
parser.add_argument("-n", "--number", help="TOP数目", type=int, default=100)
parser.add_argument("--host", help="数据库URL", default="http://localhost")
parser.add_argument("--port", help="数据库端口", default=7474, type=int)
parser.add_argument("-u", "--user", help="数据库用户名", default="neo4j")
parser.add_argument("-p", "--password", help="数据库密码", default="neo4j")
parser.add_argument("-v", "--verbose", help="显示日志信息", action="store_true")
parser.add_argument("--thread", help="连接的线程数", type=int, default=8)
parser.add_argument("--retry", help="连接失败重传数", type=int, default=3)
parser.add_argument("--clearDB", help="是否在初始化时清空数据库原有内容", action="store_true")


def insert_if_not_exists(graph: Graph, id, label, **kwargs)->Node:
    logging.debug(f"检查节点{label}-{id}是否已经存在...")
    nodes = graph.nodes.match(label, id=id)
    if len(nodes) > 0:
        logging.debug(f"节点{label}-{id}已经存在")
        return nodes.first()
    else:
        logging.debug(f"节点{label}-{id}不存在，插入节点,kwargs: {kwargs}")
        node = Node(label, id=id, **kwargs)
        graph.create(node)
        return node


def download_credit_if_not_exists(graph: Graph, api: TMDBApi, id, label)->Node:
    logging.debug(f"检查演职员{label}-{id}是否已经存在...")
    nodes = graph.nodes.match(label, id=id)
    if not len(nodes):
        logging.debug(f"演职员{label}-{id}不存在，尝试获取信息")
        res = api.get_person_detail(id)
        return insert_if_not_exists(
            graph, id, label,
            popularity=res["popularity"],
            birthday=res["birthday"],
            deathday=res["deathday"],
            gender=res["gender"],
            place_of_birth=res["place_of_birth"],
            name=res["name"]
        )
    else:
        logging.debug(f"演职员{label}-{id}已经存在")
        return nodes.first()


def import_credit_info(graph, api, id, label, movie_node):
    # 导入演员关系
    logging.info(f"导入演员关系...")
    credits = api.get_credits(id, label)  # 获取电影的演职员表
    for title, credit_list in credits.items():
        if title == "id":
            continue
        for credit in credit_list:
            character = credit.get("character") or credit.get("job")
            order = credit.get("order", 0)
            credit_id = credit["id"]
            # 插入或搜索到节点
            credit_node = download_credit_if_not_exists(
                graph, api, credit_id, title)
            # 新增一条演员到电影的连线
            credit_to_movie = Relationship(
                movie_node, title, credit_node, character=character, order=order)
            graph.create(credit_to_movie)


def import_genre_info(graph, genre_ids, movie_node):
    logging.info(f"导入类型关系...")
    for genre_id in genre_ids:
        genre_nodes = graph.nodes.match("genre", id=genre_id)
        if not len(genre_nodes):
            logging.error(f"cannot find genre {genre_id}!")
        else:
            genre_node = genre_nodes.first()
            movie_to_genre = Relationship(movie_node, "is", genre_node)
            graph.create(movie_to_genre)


def import_country_info(graph, country_names, node):
    logging.info("导入国家关系...")
    for country_name in country_names:
        country_node = insert_if_not_exists(graph, country_name, "country")
        movie_to_country = Relationship(node, "origin_country", country_node)
        graph.create(movie_to_country)


def import_company_info(graph, companies, movie_node):
    logging.info("导入出品公司信息...")
    for company in companies:
        id = company["id"]
        name = company["name"]
        country = company.get("origin_country", None)
        company_node = insert_if_not_exists(graph, id, "company", name=name)
        import_country_info(graph, [country, ], company_node)
        movie_to_company = Relationship(
            movie_node, "production_company", company_node)
        graph.create(movie_to_company)


def import_created_by_info(graph, people, movie_node):
    logging.info("导入出品人信息...")
    for person in people:
        id = person["id"]
        name = person["name"]
        gender = person["gender"]
        person_node = insert_if_not_exists(
            graph, id, "producer", gender=gender, name=name)
        movie_to_person = Relationship(movie_node, "created_by", person_node)
        graph.create(movie_to_person)


if __name__ == "__main__":

    def process_info(info):
        try:
            id = info.get("id")  # 确定电影id
            info = api.get_details(id, arg.target)
            name = info.get("name") or info.get("title")  # 确定电影名
            logging.info(f"当前影片: {name}")

            popularity = info.get("popularity", 0)
            vote_average = info.get("vote_average", 0)
            genre_ids = info.get("genre_ids", []) or (genre["id"]
                                                      for genre in info.get("genres", []))
            origin_countries = info.get("origin_country", [])
            companies = info.get("production_companies", [])
            created_by = info.get("created_by", [])

            # 插入影片节点
            logging.info(f"尝试插入影片节点...")
            movie_node = insert_if_not_exists(
                graph, id=id,
                label=arg.target,
                popularity=popularity,
                vote_average=vote_average,
                name=name
            )

            # 导入演员关系
            import_credit_info(graph, api, id, arg.target, movie_node)

            # 导入类型关系
            import_genre_info(graph, genre_ids, movie_node)

            # 导入出品国信息
            import_country_info(graph, origin_countries, movie_node)

            # 导入出品公司信息
            import_company_info(graph, companies, movie_node)

            # 导入出品人信息
        except requests.exceptions.RequestException as e:
            logging.error(e)
            return f"fail at {info} because {e}"
        else:
            return "success"

    arg = parser.parse_args()
    if arg.verbose:
        logging.basicConfig(level=logging.DEBUG)
    api_key = arg.key or load_key_from_file("api.key")
    url = f"{arg.host}:{arg.port}"
    graph = Graph(url, username=arg.user, password=arg.password)
    if arg.clearDB:
        graph.delete_all()
    api = TMDBApi(api_key, arg.language, retry=arg.retry)

    # 插入题材节点
    for target in ("movie", "tv"):
        genre_list = api.get_genre_list(target)
        for genre in genre_list:
            insert_if_not_exists(
                graph, genre["id"], "genre", name=genre["name"])

    # 获取top列表
    topN = api.get_popular_iter(arg.target, limit=arg.number)
    with futures.ThreadPoolExecutor(arg.thread) as executor:
        results = executor.map(process_info, topN)
    for result in results:
        print(result)
