import scrapy
import time
import re


class lubimchikSpider(scrapy.Spider):
    name = 'lubimchik'
    allowed_domains = ['lubimchik.ru']
    start_urls = [
        'https://www.lubimchik.ru/sukhoy-korm-dlya-sobak/?page=1'
        # 'https://www.lubimchik.ru/napolniteli-i-tualety-dlya-koshek/',
        # 'https://www.lubimchik.ru/vitaminy-i-pishchevye-dobavki-dlya-koshek/'
    ]
    headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'}# без headers была ошибка 500
    cookies = {'BITRIX_SM_REGION_ID': 14}# регион - Санкт-Петербург



    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse_pages, headers=self.headers, cookies=self.cookies)

    def parse_pages(self, response):#метод для обработки ссылок на страницы
        last_page = int(response.xpath('//a[@class="pagination__link js-pagination"]/text()').getall()[-1])
        for page_count in range(2, last_page + 1, 1):
            url_page = f'{response.url}?page={page_count}'
            yield scrapy.Request(url=url_page, callback=self.parse_item_page, headers=self.headers, cookies=self.cookies)


    def parse_item_page(self, response):#метод получает ссылки на товар
        urls = response.xpath('//a[@class="product-snippet__link"]/@href').getall()
        for url in urls:
            url = "https://www.lubimchik.ru/" + url
            yield scrapy.Request(url, callback=self.parse, headers=self.headers, cookies=self.cookies)
#  у каждой ссылки на товар, даже если нет вариантов, добавляется #id '
#  этим методом должен проходить по всем вариантам товара, но он не работает
    # def parse_item_page_id(self, response):
    #     urls_item_id = response.xpath("//div[@class = 'properties-selection']//@data-offer-id").getall()#находит список id
    #     for url_item_id in urls_item_id:
    #         url = f'{response.url}#{url_item_id}'
    #         yield scrapy.Request(url, callback=self.parse, headers=self.headers, cookies=self.cookies)


    def get_price_data(self, response):
        try:
            current = int(''.join(response.xpath('//div[@class="buy-bar__price "]//span/text()').get().split()))
        except:
            current = 0.0

        try:
            original = int(''.join(response.xpath('//div[@class="buy-bar__price-through "]//span/text()').get().split()))
            if original == 0:
                original = current
        except:
            original = current


        try:
            sales = int(100 - (current/original * 100))
        except:
            sales = 0

        if sales > 0:
            sales_tag = f"Скидка {sales}%"
        else:
            sales_tag = ''

        price_data = {"current": current, "original": original, "sale_tag": sales_tag}
        return price_data

    def get_stock(self, response):
        goods_in_stock = response.xpath('//p[@class="buy-bar__time"]/text()').get()
        # если есть товар, то есть тег p class="buy-bar__time"

        if goods_in_stock:
            in_stock = True
        else:
            in_stock = False
        stock = {"in_stock": in_stock, "count": 0}#"count": 0 т.к. нет возможности получить информацию о количестве оставшегося товара в наличии
        return stock

    def get_metadata(self, response):

         description = response.xpath('//div[@class="products-description__container"]').get()
         description = re.sub(r'<[^>]+>', '', description)
         description = description.replace('\n', '').replace('\r', '').replace('\t', '')


         composition = response.xpath('//div[@class="products-composition"]').get()
         composition = re.sub(r'<[^>]+>', '', composition)
         composition = composition.replace('\n', '').replace('\r', '').replace('\t', '')


         names = response.xpath('//div[contains(@class, "product-characteristic__name")]/text()').getall()
         values = response.xpath('//div[contains(@class, "product-characteristic__value")]/text()').getall()
         specifications = dict(zip(names, values))



         metadata = {'__description': description,
                    'composition': composition,
                    'specifications': specifications}

         return metadata

    def get_assets(self, response):
        main_image = response.xpath('//img[@class="product-gallery__img"]/@src').get()
        main_image = f'https://www.lubimchik.ru/{main_image}'
        images = response.xpath('//img[@class="product-gallery__img"]/@src').getall()
        number = int(len(response.xpath('//img[@class="product-gallery__img"]/@src').getall())/2)
        set_images = [f'https://www.lubimchik.ru/{image}' for image in images[:number]]
        assets = {"main_image": main_image, "set_images": set_images, "view360": [], "video": []}
        return assets

    def parse(self, response):
        timestamp = int(time.time())  # Текущее время в формате timestamp
        rpc = response.xpath('//div[@class="product-packing__span article"]//span/text()').get()  # {str} Уникальный код товара
        url = response.url  # {str} Ссылка на страницу товара
        name = response.xpath('//div[@class="hot-links__title"]/text()').get().strip()
        packing = response.xpath('//div[@class="product-packing__strong"]/text()').get()
        title = f'{name}, {packing}' #{str}Заголовок/название товара
        marketing_tag = response.xpath('//div[@class="hot-links page__hot-links"]//a[@class="product-feature tooltip"]/text()').getall()
        marketing_tag = set([item.strip() for item in marketing_tag])  # Список тегов
        brand = response.xpath('//a[@itemprop="brand"]/text()').get() # {str} Бренд товара
        sections = response.xpath('//a[@class="bread-crumbs__link"]/text()').getall()# Иерархия разделов
        variants = len(response.xpath('//span[@class="properties-selection__date"]').getall()) # Кол-во вариантов у товара в карточке проверить



        item = {
            "timestamp": timestamp,
            "RPC": rpc,
            "url": url,
            "title": title,
            "marketing_tags": marketing_tag,
            "brand": brand,
            "section": sections,
            "price_data": self.get_price_data(response),
            "stock": self.get_stock(response),
            "assets": self.get_assets(response),
            "metadata": self.get_metadata(response),
            "variants": variants
        }
        yield item

