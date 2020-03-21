# 基于TMDB等数据的电视剧可视化

本项目旨在通过对TMDB等电影电视数据库和分集剧情网等剧情信息提供平台，以及微博、收视率等信息的综合分析，提供一个较好的可视化分析工具，用以分析电视剧剧情对收视率和影片评价、演员之间联系、不同国家和地区之间电视剧影响力的传播等。

![韩剧剧情高频词](data/wc.jpg)

## 项目结构

目前项目结构如下：

| 文件/目录                  | 作用                                            |
| -------------------------- | ----------------------------------------------- |
| plot_crawler.py            | 分集剧情网爬虫                                  |
| plot_to_cloud.py           | 剧情词频分析和词云图生成                        |
| popularity_downloader.py   | TMDB的每日欢迎度信息下载工具（提供CLI）         |
| read_daily_exports.py      | TMDB每日欢迎度信息分析解压和导出工具（提供CLI） |
| analysis_daily_export.py   | 每日欢迎度信息分析工具（提供CLI）               |
| nielsen_kr_top20.py        | 尼尔森韩国收视率TOP20爬虫（提供CLI）            |
| micro_index_crawler.py     | 微博指数爬虫（提供CLI）                         |
| api.key                    | 保存TMDB的API密钥。未上传。                     |
| edited_baidu_stopwords.txt | 根据分词结果修改后的百度停用词库                |
| data/                      | 目前已经整理完成的数据集成果                    |

## TODO

- ~~韩国尼尔森收视率网站爬虫~~
- 豆瓣爬虫
- ~~微博指数获取~~
- TMDB演员信息收集和分析工具
- TMDB影视元信息下载

