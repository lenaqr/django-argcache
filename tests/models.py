from django.db import models
from argcache.function import cache_function, depend_on_row, ensure_token
from argcache.key_set import wildcard
from argcache.extras.derivedfield import DerivedField

# some test models

class HashTag(models.Model):
    label = models.CharField(max_length=40, unique=True)

    def __unicode__(self):
        return self.label

class Article(models.Model):
    headline = models.CharField(max_length=200)
    content = models.TextField()
    reporter = models.ForeignKey('Reporter', related_name='articles')
    hashtags = models.ManyToManyField('HashTag', related_name='articles')

    @cache_function([
        depend_on_row('tests.Comment', lambda comment: {'self': comment.article})
    ])
    def num_comments(self):
        return self.comments.count()

    @cache_function([
        ensure_token(('self',)),
        depend_on_row('tests.Comment', lambda comment: {'self': comment.article}),
    ])
    def num_comments_with_dummy(self, dummy):
        return self.comments.count()

    def __unicode__(self):
        return self.headline

class Comment(models.Model):
    article = models.ForeignKey('Article', related_name='comments')

class Reporter(models.Model):
    first_name = models.CharField(max_length=70)
    last_name = models.CharField(max_length=70)

    @cache_function
    def full_name(self):
        return self.first_name + ' ' + self.last_name
    full_name.depend_on_row('tests.Reporter', lambda reporter: {'self': reporter})

    @cache_function
    def get_backward_name(self):
        return self.last_name + ' ' + self.first_name
    get_backward_name.depend_on_row('tests.Reporter', lambda reporter: {'self': reporter}, filter=lambda reporter: (reporter.backward_name != reporter.last_name + ' ' + reporter.first_name))

    backward_name = DerivedField(models.CharField, get_backward_name)(max_length=140)

    @cache_function
    def top_article(self):
        articles = self.articles.all()
        if articles:
            return max(articles, key=Article.num_comments)
        else:
            return None
    top_article.depend_on_row(Article, lambda article: {'self': article.reporter})
    top_article.depend_on_cache(Article.num_comments, lambda self=wildcard: {'self': self.reporter})

    @cache_function
    def articles_with_hashtag(self, hashtag='#hashtag'):
        return list(self.articles.filter(hashtags__label=hashtag).values_list('headline', flat=True))
    articles_with_hashtag.depend_on_model(HashTag)
    articles_with_hashtag.depend_on_row(Article, lambda article: {'self': article.reporter})
    articles_with_hashtag.depend_on_m2m(Article, 'hashtags', lambda article, hashtag: {'self': article.reporter, 'hashtag': hashtag.label})

    @cache_function
    def articles_with_headline(self, headline):
        return list(self.articles.filter(headline=headline).values_list('content', flat=True))
    articles_with_headline.depend_on_row(Article, lambda article: {'self': article.reporter, 'headline': article.headline})

    @cache_function
    def articles_with_headline_and_dummy(self, dummy, headline):
        return list(self.articles.filter(headline=headline).values_list('content', flat=True))
    articles_with_headline_and_dummy.get_or_create_token(('self', 'headline'))
    articles_with_headline_and_dummy.depend_on_row(Article, lambda article: {'self': article.reporter, 'headline': article.headline})

    def __unicode__(self):
        return self.full_name()
