

import scrapy
import re

class SstruyenSpider(scrapy.Spider):
    name = "sstruyen_spider"
    allowed_domains = ["sstruyen.vn"]
    
    # Danh sách các thể loại cần cào
    categories = [
        'quan-su', 'tien-hiep', 'dam-my', 'light-novel', 'kiem-hiep', 'dong-phuong', 'trinh-tham', 'doan-van', 'co-dai', 'linh-di'
    ]
    
    # Tạo danh sách các URL từ trang 1 đến trang 20 cho mỗi thể loại
    start_urls = [
        f'https://sstruyen.vn/the-loai/{category}/trang-{i}/' 
        for category in categories 
        for i in range(1, 20)
    ]

    def parse(self, response):
        # Lấy tiêu đề của thể loại (ví dụ: "Tiên Hiệp", "Quân Sự", v.v.)
        genre_title = response.css('h1.title::text').get()

        # Lấy danh sách các truyện từ trang
        stories = response.css('div.table-list tr')

        for story in stories:
            title = story.css('h3.rv-home-a-title a::text').get()
            author = story.css('p a[itemprop="author"]::text').get()
            rating = story.css('div.rate::text').get()
            views = story.css('div.view::text').get()
            status = story.css('p::text').re_first('Trạng thái: (.*)')
            categories = ', '.join(story.css('p a[itemprop="genre"]::text').getall())
            story_link = response.urljoin(story.css('h3.rv-home-a-title a::attr(href)').get())  # Lấy link của truyện
            latest_chapter_number = story.css('td.chap a::text').re_first(r'Chương (\d+)')  # Lấy số chương mới nhất

            # Chuyển hướng đến trang chi tiết của truyện để lấy thêm thông tin (ngày đăng và thời gian cập nhật)
            if all([title, author, rating, views, status, categories, latest_chapter_number, story_link]):
                yield scrapy.Request(url=story_link, callback=self.parse_detail, meta={
                    'genre_title': genre_title,
                    'title': title,
                    'author': author,
                    'rating': rating,
                    'views': views,
                    'status': status,
                    'categories': categories,
                    'latest_chapter_number': latest_chapter_number
                })

    def parse_detail(self, response):
        # Lấy ngày đăng từ trang chi tiết của truyện
        published_date_text = response.css('p:contains("Ngày đăng") span.rv-sr-s-a::text').get(default='Không có thông tin')
        published_date_in_days = self.convert_time_to_days(published_date_text)  # Chuyển đổi thành số ngày

        # Lấy thời gian cập nhật từ trang chi tiết và chuyển đổi thành số ngày
        updated_time_text = response.css('p:contains("Cập nhật") span.rv-sr-s-a::text').get(default='Không có thông tin')
        updated_time_in_days = self.convert_time_to_days(updated_time_text)

        # Lấy các thông tin từ meta
        genre_title = response.meta['genre_title']
        title = response.meta['title']
        author = response.meta['author']
        rating = self.get_exact_rating(response.meta['rating'])  # Lấy chính xác giá trị rating
        views = response.meta['views']
        status = response.meta['status']
        categories = response.meta['categories']
        latest_chapter_number = response.meta['latest_chapter_number']

        # Trả về thông tin đầy đủ bao gồm số ngày đăng và số ngày cập nhật
        yield {
            'genre_title': genre_title,
            'title': title,
            'author': author,
            'rating': rating,  # Giá trị rating không làm tròn
            'views': views,
            'status': status,
            'categories': categories,
            'published_date_in_days': published_date_in_days,  # Số ngày từ ngày đăng
            'updated_time_in_days': updated_time_in_days,  # Số ngày cập nhật từ trang chi tiết
            'latest_chapter_number': latest_chapter_number  # Số chương mới nhất
        }

    def get_exact_rating(self, rating_text):
        """
        Lấy chính xác giá trị rating, ví dụ '7.5/10' -> 7.5
        """
        if rating_text:
            rating_match = re.search(r'(\d+\.\d+|\d+)', rating_text)  # Tìm giá trị số thập phân hoặc số nguyên
            if rating_match:
                return float(rating_match.group(1))  # Trả về giá trị rating đầy đủ
        return None  # Nếu không có rating, trả về None

    def convert_time_to_days(self, time_text):
        """
        Chuyển đổi các chuỗi thời gian như '5 giờ trước', '1 tuần trước', '1 năm trước' thành số ngày.
        """
        if not time_text:
            return None

        # Các quy tắc chuyển đổi đơn vị thời gian sang ngày
        time_conversion_rules = {
            'giờ': 1 / 24,      # 1 giờ = 1/24 ngày
            'ngày': 1,          # 1 ngày = 1 ngày
            'tuần': 7,          # 1 tuần = 7 ngày
            'tháng': 30,        # 1 tháng = 30 ngày (giả định trung bình)
            'năm': 365          # 1 năm = 365 ngày
        }

        # Kiểm tra đơn vị thời gian trong chuỗi văn bản
        for unit, multiplier in time_conversion_rules.items():
            if unit in time_text:
                time_value = re.search(r'(\d+)', time_text)  # Tìm giá trị số trong chuỗi
                if time_value:
                    return int(time_value.group(1)) * multiplier
        
        return None
