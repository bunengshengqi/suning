# -*- coding: utf-8 -*-
import scrapy
import re
from copy import deepcopy
from pprint import pprint


class SuningSpider(scrapy.Spider):
    name = 'suning'
    allowed_domains = ['suning.com']
    start_urls = ['https://book.suning.com/']  # 这个url是否包含我们想要抓取的大中小分类,包含就行,不包含就不行

    def parse(self, response):
        # 获取大分类
        div_list = response.xpath('//div[@class="menu-list"]/div[@class="menu-item"]')
        div_sub_list = response.xpath('//div[@class="menu-list"]/div[@class="menu-sub"]')
        for div in div_list[:1]:
            item = {}
            # 大分类的名字
            item["b_cate"] = div.xpath('.//h3/a/text()').extract_first()
            # 当前大分类的所有中间分类的位置
            current_sub_list = div_sub_list[div_list.index(div)]
            # 获取中间分类的分组
            p_list = current_sub_list.xpath('.//div[@class="submenu-left"]/p[@class="submenu-item"]')
            for p in p_list:
                item["m_cate"] = p.xpath('./a/text()').extract_first()
                # 获取小分类的分组
                li_list = p.xpath("./following-sibling::ul[1]/li")
                for li in li_list[:1]:
                    # 获取小分类的名字
                    item["s_cate"] = li.xpath('./a/text()').extract_first()
                    # 小分类的url地址
                    item["s_href"] = li.xpath('./a/@href').extract_first()

                    # 请求图书列表页
                    yield scrapy.Request(
                        item["s_href"],
                        callback=self.parse_book_list,
                        meta={"item": deepcopy(item)}
                    )

                    # 发送请求,获取列表页,第一页后一部分的数据,因为这个页面数据隐藏了,另外一半需要通过抓包,拿到数据

                    # https: // list.suning.com / emall / showProductList.do?ci = 502687 & pg = 03 & cp = 0 & il = 0 & iy = 0 & adNumber = 0 & n = 1 & ch = 4 & prune = 0 & sesab = ACBAAB & id = IDENTIFYING & cc = 512 & paging = 1 & sub = 0
                    # 下一页的url地址(翻页的情况)
                    # https://list.suning.com/emall/showProductList.do?ci=502687&pg=03&cp=1&il=0&iy=0&adNumber=0&n=1&ch=4&prune=0&sesab=ACBAAB&id=IDENTIFYING&cc=512

                    # 另一个分类
                    # https: // list.suning.com / emall / showProductList.do?ci = 502329 & pg = 03 & cp = 0 & il = 0 & iy = 0 & adNumber = 0 & n = 1 & ch = 4 & prune = 0 & sesab = ACBAAB & id = IDENTIFYING & paging = 1 & sub = 0
                    #
                    # 下一页的前半部分
                    # https: // list.suning.com / emall / showProductList.do?ci = 502329 & pg = 03 & cp = 1 & il = 0 & iy = 0 & adNumber = 0 & n = 1 & ch = 4 & prune = 0 & sesab = ACBAAB & id = IDENTIFYING & cc = 512
                    #
                    # 下一页的后半部分
                    # https: // list.suning.com / emall / showProductList.do?ci = 502329 & pg = 03 & cp = 1 & il = 0 & iy = 0 & adNumber = 0 & n = 1 & ch = 4 & prune = 0 & sesab = ACBAAB & id = IDENTIFYING & cc = 512 & paging = 1 & sub = 0
                    # ci 表示分类,cp表示页数,最后有参数说明是后半部分(隐藏的),无参数说明是前半部分
                    next_part_url_temp = "https://list.suning.com/emall/showProductList.do?ci={}&pg=03&cp=0&il=0&iy=0&adNumber=0&n=1&ch=4&prune=0&sesab=ACBAAB&id=IDENTIFYING&cc=512&paging=1&sub=0"
                    # 获取url地址的ci
                    ci = item["s_href"].split("-")[1]
                    next_part_url = next_part_url_temp.format(ci)
                    yield scrapy.Request(
                        next_part_url,
                        callback=self.parse_book_list,
                        meta={"item": deepcopy(item)}
                    )

    def parse_book_list(self, response):  # 处理图书列表页内容
        item = response.meta["item"]
        # 获取图书列表页的分组
        # li_list = response.xpath('//div[@id="filter-results"]/ul/li')
        li_list = response.xpath('//li[contains(@class,"product      book ")]')
        for li in li_list:
            # 书名
            item["book_name"] = li.xpath('.//p[@class="sell-point"]/a/text()').extract_first().strip()
            # 书的地址,不完整
            item["book_href"] = li.xpath('.//p[@class="sell-point"]/a/@href').extract_first()
            # 书店的名字,卖书的店铺
            item["book_store_name"] = li.xpath('.//div[@class="res-info"]/p/@salesname').extract_first()

            # 发送详情页的请求
            yield response.follow(
                item["book_href"],
                callback=self.parse_book_detail,
                meta={"item": deepcopy(item)}
            )
            # 列表页翻页
            # 前半部分数据的url地址
            next_url_1 = "https://list.suning.com/emall/showProductList.do?ci={}&pg=03&cp={}&il=0&iy=0&adNumber=0&n=1&ch=4&sesab=ABBAAA&id=IDENTIFYING&cc=010"
            # 后半部分数据的url地址
            next_url_2 = "https://list.suning.com/emall/showProductList.do?ci={}&pg=03&cp={}&il=0&iy=0&adNumber=0&n=1&ch=4&sesab=ABBAAA&id=IDENTIFYING&cc=010&paging=1&sub=0"
            ci = item["s_href"].split("-")[1]
            # 当前的页码数
            current_page = re.findall('param.currentPage = "(.*?)";', response.body.decode())[0]
            # 总的页码数
            total_page = re.findall('param.pageNumbers = "(.*?)";', response.body.decode())[0]
            if int(current_page) < int(total_page):
                next_page_num = int(current_page) + 1
                next_url_1 = next_url_1.format(ci, next_page_num)  # 组装前半部分URL
                yield scrapy.Request(
                    next_url_1,
                    callback=self.parse_book_list,
                    meta={"item": item}
                )
                # 构造后半部分数据的请求
                next_url_2 = next_url_2.format(ci, next_page_num)
                yield scrapy.Request(
                    next_url_2,
                    callback=self.parse_book_list,
                    meta={"item": item}
                )

    def parse_book_detail(self, response):  # 处理图书详情页内容
        item = response.meta["item"]
        price_temp_url = "https://pas.suning.com/nspcsale_0_000000000{}_000000000{}_{}_10_010_0100101_226503_1000000_9017_10106____{}_{}.html"
        p1 = response.url.split("/")[-1].split(".")[0]
        p3 = response.url.split("/")[-2]
        p4 = re.findall('"catenIds":"(.*?)",', response.body.decode())
        if len(p4) > 0:
            p4 = p4[0]
            p5 = re.findall('"weight":"(.*?)",', response.body.decode())[0]
            price_url = price_temp_url.format(p1, p1, p3, p4, p5)
            yield scrapy.Request(
                price_url,
                callback=self.parse_book_pirce,
                meta={"item": item}
            )

    def parse_book_pirce(self, response):  # 提取图书的价格
        item = response.meta["item"]
        item["book_price"] = re.findall('"netPrice":"(.*?)"', response.body.decode())[0]
        pprint(item)

