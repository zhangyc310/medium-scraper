import json

import scrapy

from medium.items import Post


class PostIdSpider(scrapy.Spider):

    ''' Crawl xml sitemap looking for post_id '''

    name = 'post_id'

    def start_requests(self):
        url = 'https://medium.com/sitemap/sitemap.xml'
        yield scrapy.Request(url, self.parse_sitemap)

    def parse_sitemap(self, response):
        s = scrapy.utils.sitemap.Sitemap(response.body)

        if s.type == 'sitemapindex':
            for loc in s:
                if self.url_filter() in loc['loc']:
                    yield scrapy.Request(
                        loc['loc'], callback=self.parse_sitemap
                    )
        elif s.type == 'urlset':
            for loc in s:
                post_id = loc['loc'].split('/')[-1].split('-')[-1]
                yield Post(post_id=post_id)

    def url_filter(self):
        url = '/posts/'
        if hasattr(self, 'year'):
            url += f'{self.year}/'
            if hasattr(self, 'month'):
                url += f'posts-{self.year}-{self.month}-'
                if hasattr(self, 'day'):
                    url += f'{self.day}'
        return url


class PostSpider(scrapy.Spider):

    ''' Exstract post data starting from post_id '''

    name = 'post'
    handle_httpstatus_list = [302]

    def start_requests(self):
        self.cur.execute(
            '''
            SELECT post_id
            FROM post
            WHERE available is NULL'''
        )
        for post_id in self.cur.fetchall():
            url = f'https://medium.com/_/api/posts/{post_id[0]}'
            yield scrapy.Request(url, self.parse_post)

    def parse_post(self, response):
        code = response.status

        if code == 200:
            yield self._post_200(response)

        elif code == 302:
            yield self._post_302(response)

        # add here other requests code if necessary

    def _post_200(self, response):
        data = json.loads(response.text[16:])
        post = data['payload']['value']

        return Post(
            post_id=post['id'],
            available=1,
            creator_id=post['creatorId'],
            language=post['detectedLanguage'],
            first_published_at=post['firstPublishedAt'],
        )

    def _post_302(self, response):
        post_id = response.url.split('/')[-1]
        self.logger.debug('The post {post_id} removed (user is blacklisted)')
        return Post(post_id=post_id, available=0)

    # TODO content = post['content']
    # TODO virtuals = post['virtuals']
