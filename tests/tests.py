from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from django.template import Template, Context

import unittest
import threading

from argcache import registry, queued
from .caches import (get_calls, get_calls_reset, get_squared_calls,
                     set_value, get_value, get_value_slowly)
from .models import HashTag, Article, Comment, Reporter
from .templatetags.test_tags import counter, silly_inclusion_tag


class CacheTests(TestCase):
    def setUp(self):
        # create initial objects
        reporter1 = Reporter.objects.create(pk=1, first_name='John', last_name='Doe')
        reporter2 = Reporter.objects.create(pk=2, first_name='Jane', last_name='Roe')
        reporter3 = Reporter.objects.create(pk=3, first_name='Jim', last_name='Poe')
        article1 = Article.objects.create(pk=1, headline='Breaking News', content='Lorem ipsum dolor sit amet', reporter=reporter1)
        article2 = Article.objects.create(pk=2, headline='Article II', content='The executive Power shall be vested in a President', reporter=reporter1)
        article3 = Article.objects.create(pk=3, headline='Article II', content='He shall hold his Office during the Term', reporter=reporter3)
        comment1 = Comment.objects.create(pk=1, article=article1)
        comment2 = Comment.objects.create(pk=2, article=article1)
        hashtag1 = HashTag.objects.create(pk=1, label='#hashtag')
        hashtag2 = HashTag.objects.create(pk=2, label='#news')
        article1.hashtags.add(hashtag2)
        article2.hashtags.add(hashtag1)

    def test_caches_loaded(self):
        """
        Rudimentary test that the loading mechanism works as expected.
        """
        # pending lookups should be empty once everything is loaded
        self.assertEqual(queued.pending_lookups, {})

        # we should test that signals are connected properly, but this
        # is hard to do directly. hope that if there is a problem with
        # that part, it ought to trip the other tests anyway.

    def test_cached(self):
        """
        Basic functionality: cached functions are called only on a
        cache miss, and retrieve the expected result on a cache hit.
        """
        # check that we make the expected number of function calls,
        # and get the expected results for arguments of various types
        get_calls_reset()
        self.assertEqual(get_calls(1), 1)
        self.assertEqual(get_calls(()), 2)
        self.assertEqual(get_calls('a'), 3)
        self.assertEqual(get_calls(None), 4)
        self.assertEqual(get_calls(False), 5)
        self.assertEqual(get_calls(frozenset([2.0, 3.0])), 6)
        self.assertEqual(get_calls(frozenset([2.0, 3.0])), 6)
        self.assertEqual(get_calls(None), 4)
        self.assertEqual(get_calls(False), 5)
        self.assertEqual(get_calls(1), 1)
        self.assertEqual(get_calls(()), 2)
        self.assertEqual(get_calls('a'), 3)
        self.assertEqual(get_calls('b'), 7)

        # check that we get the same result from calling a cached method twice
        # (presumably from the cache the second time)
        reporter = Reporter.objects.get(pk=1)
        name1 = reporter.full_name()
        name2 = reporter.full_name()
        self.assertEqual(name1, name2)

        # use assertNumQueries to check that we aren't making DB queries
        # cache hits should not make queries
        article = Article.objects.get(pk=1)
        cnt1 = article.num_comments()
        with self.assertNumQueries(0):
            cnt2 = article.num_comments()
        self.assertEqual(cnt1, cnt2)

        article_ = Article.objects.get(pk=1)
        with self.assertNumQueries(0):
            cnt3 = article_.num_comments()
        self.assertEqual(cnt1, cnt3)

        top_article = reporter.top_article()
        self.assertEqual(top_article, max(reporter.articles.all(), key=Article.num_comments))
        with self.assertNumQueries(0):
            top_article_again = reporter.top_article()
        self.assertEqual(top_article, top_article_again)

        with_hashtag = reporter.articles_with_hashtag('#hashtag')
        with self.assertNumQueries(0):
            with_hashtag_again = reporter.articles_with_hashtag('#hashtag')
        self.assertEqual(with_hashtag, with_hashtag_again)

    def test_cache_none(self):
        """
        None values can be stored in the cache.
        """
        reporter = Reporter.objects.get(pk=2)
        top_article = reporter.top_article()
        self.assertIsNone(top_article)
        with self.assertNumQueries(0):
            top_article_again = reporter.top_article()
        self.assertIsNone(top_article_again)

    def test_kwargs(self):
        """
        Cached functions handle keyword arguments, *args, and **kwargs
        as expected.
        """
        reporter = Reporter.objects.get(pk=1)
        # with positional arg
        with_hashtag1 = reporter.articles_with_hashtag('#hashtag')
        with self.assertNumQueries(0):
            # with keyword arg
            with_hashtag1_again = reporter.articles_with_hashtag(hashtag='#hashtag')
        self.assertEqual(with_hashtag1, with_hashtag1_again)

        # with keyword arg
        with_hashtag2 = reporter.articles_with_hashtag(hashtag='#news')
        with self.assertNumQueries(0):
            # with *args and **kwargs
            args = ['#news']
            kwargs = {'hashtag': '#news'}
            with_hashtag2_args = reporter.articles_with_hashtag(*args)
            with_hashtag2_kwargs = reporter.articles_with_hashtag(**kwargs)
        self.assertEqual(with_hashtag2, with_hashtag2_args)
        self.assertEqual(with_hashtag2, with_hashtag2_kwargs)

    def test_optional_args(self):
        """
        Cached functions handle optional arguments as expected.
        """
        reporter = Reporter.objects.get(pk=1)
        # with positional arg
        with_hashtag1 = reporter.articles_with_hashtag('#hashtag')
        with self.assertNumQueries(0):
            # omitting optional arg (defaulting to '#hashtag')
            with_hashtag1_again = reporter.articles_with_hashtag()
        self.assertEqual(with_hashtag1, with_hashtag1_again)

    def test_depend_on_row(self):
        """
        depend_on_row triggers cache invalidation when models are updated.
        """
        # call the function, update the model, call the function again
        # should result in a cache miss
        article = Article.objects.get(pk=1)
        cnt1 = article.num_comments()
        article.comments.create(pk=3)
        with self.assertNumQueries(1):
            cnt2 = article.num_comments()
        self.assertEqual(cnt2, cnt1 + 1)

        # unrelated DB updates should not affect the cache
        article2 = Article.objects.get(pk=2)
        article2.comments.create(pk=4)
        with self.assertNumQueries(0):
            cnt3 = article.num_comments()
        self.assertEqual(cnt3, cnt2)

    def test_depend_on_row_with_dummy(self):
        """
        depend_on_row still works correctly when there are other arguments to the function.
        """
        # call the function, update the model, call the function again
        # should result in a cache miss
        article = Article.objects.get(pk=1)
        cnt1 = article.num_comments()
        article.comments.create(pk=3)
        with self.assertNumQueries(1):
            cnt2 = article.num_comments_with_dummy(None)
        self.assertEqual(cnt2, cnt1 + 1)

        # unrelated DB updates should not affect the cache
        article2 = Article.objects.get(pk=2)
        article2.comments.create(pk=4)
        with self.assertNumQueries(0):
            cnt3 = article.num_comments_with_dummy(None)
        self.assertEqual(cnt3, cnt2)

    def test_depend_on_row_multiple_arguments(self):
        '''Tests that depend_on_row works properly with multiple arguments (in this case, where all are used).'''
        reporter1 = Reporter.objects.get(pk=1)
        reporter3 = Reporter.objects.get(pk=3)
        # The first time around, each one should hit the cache.
        with self.assertNumQueries(1):
            arts1a = reporter1.articles_with_headline('Breaking News')
        with self.assertNumQueries(1):
            arts2a = reporter1.articles_with_headline('Article II')
        with self.assertNumQueries(1):
            arts3a = reporter3.articles_with_headline('Article II')
        
        # There were no updates, so we shouldn't hit the cache.
        with self.assertNumQueries(0):
            arts1b = reporter1.articles_with_headline('Breaking News')
            self.assertEqual(arts1a,arts1b)
        with self.assertNumQueries(0):
            arts2b = reporter1.articles_with_headline('Article II')
            self.assertEqual(arts2a,arts2b)
        with self.assertNumQueries(0):
            arts3b = reporter3.articles_with_headline('Article II')
            self.assertEqual(arts3a,arts3b)

        article1 = Article.objects.get(pk=1)
        article1.content = 'The news is broken.'
        article1.save()

        # The first query should be affected by the update, but the latter two shouldn't.
        with self.assertNumQueries(1):
            arts1c = reporter1.articles_with_headline('Breaking News')
            self.assertNotEqual(arts1b,arts1c)
        with self.assertNumQueries(0):
            arts2c = reporter1.articles_with_headline('Article II')
            self.assertEqual(arts2b,arts2c)
        with self.assertNumQueries(0):
            arts3c = reporter3.articles_with_headline('Article II')
            self.assertEqual(arts3b,arts3c)

        article2 = Article.objects.get(pk=2)
        article2.content = 'The executive Power shall be vested in a Prime Minister'
        article2.save()

        # Now only the second should be affected.
        with self.assertNumQueries(0):
            arts1d = reporter1.articles_with_headline('Breaking News')
            self.assertEqual(arts1c,arts1d)
        with self.assertNumQueries(1):
            arts2d = reporter1.articles_with_headline('Article II')
            self.assertNotEqual(arts2c,arts2d)
        with self.assertNumQueries(0):
            arts3d = reporter3.articles_with_headline('Article II')
            self.assertEqual(arts3c,arts3d)

        article3 = Article.objects.get(pk=3)
        article3.content = 'He shall hold his Office forever'
        article3.save()

        # Now only the third should be affected.
        with self.assertNumQueries(0):
            arts1e = reporter1.articles_with_headline('Breaking News')
            self.assertEqual(arts1d,arts1e)
        with self.assertNumQueries(0):
            arts2e = reporter1.articles_with_headline('Article II')
            self.assertEqual(arts2d,arts2e)
        with self.assertNumQueries(1):
            arts3e = reporter3.articles_with_headline('Article II')
            self.assertNotEqual(arts3d,arts3e)

    def test_depend_on_row_multiple_arguments_with_dummy(self):
        '''Tests for a bug when more than one but less than all of the arguments to the function are used in a depend_on_row.'''
        reporter1 = Reporter.objects.get(pk=1)
        reporter3 = Reporter.objects.get(pk=3)
        # The first time around, each one should hit the cache.
        with self.assertNumQueries(1):
            arts1a = reporter1.articles_with_headline_and_dummy(None, 'Breaking News')
        with self.assertNumQueries(1):
            arts2a = reporter1.articles_with_headline_and_dummy(None, 'Article II')
        with self.assertNumQueries(1):
            arts3a = reporter3.articles_with_headline_and_dummy(None, 'Article II')
        
        # There were no updates, so we shouldn't hit the cache.
        with self.assertNumQueries(0):
            arts1b = reporter1.articles_with_headline_and_dummy(None, 'Breaking News')
            self.assertEqual(arts1a,arts1b)
        with self.assertNumQueries(0):
            arts2b = reporter1.articles_with_headline_and_dummy(None, 'Article II')
            self.assertEqual(arts2a,arts2b)
        with self.assertNumQueries(0):
            arts3b = reporter3.articles_with_headline_and_dummy(None, 'Article II')
            self.assertEqual(arts3a,arts3b)

        article1 = Article.objects.get(pk=1)
        article1.content = 'The news is broken.'
        article1.save()

        # The first query should be affected by the update, but the latter two shouldn't.
        with self.assertNumQueries(1):
            arts1c = reporter1.articles_with_headline_and_dummy(None, 'Breaking News')
            self.assertNotEqual(arts1b,arts1c)
        with self.assertNumQueries(0):
            arts2c = reporter1.articles_with_headline_and_dummy(None, 'Article II')
            self.assertEqual(arts2b,arts2c)
        with self.assertNumQueries(0):
            arts3c = reporter3.articles_with_headline_and_dummy(None, 'Article II')
            self.assertEqual(arts3b,arts3c)

        article2 = Article.objects.get(pk=2)
        article2.content = 'The executive Power shall be vested in a Prime Minister'
        article2.save()

        # Now only the second should be affected.
        with self.assertNumQueries(0):
            arts1d = reporter1.articles_with_headline_and_dummy(None, 'Breaking News')
            self.assertEqual(arts1c,arts1d)
        with self.assertNumQueries(1):
            arts2d = reporter1.articles_with_headline_and_dummy(None, 'Article II')
            self.assertNotEqual(arts2c,arts2d)
        with self.assertNumQueries(0):
            arts3d = reporter3.articles_with_headline_and_dummy(None, 'Article II')
            self.assertEqual(arts3c,arts3d)

        article3 = Article.objects.get(pk=3)
        article3.content = 'He shall hold his Office forever'
        article3.save()

        # Now only the third should be affected.
        with self.assertNumQueries(0):
            arts1e = reporter1.articles_with_headline_and_dummy(None, 'Breaking News')
            self.assertEqual(arts1d,arts1e)
        with self.assertNumQueries(0):
            arts2e = reporter1.articles_with_headline_and_dummy(None, 'Article II')
            self.assertEqual(arts2d,arts2e)
        with self.assertNumQueries(1):
            arts3e = reporter3.articles_with_headline_and_dummy(None, 'Article II')
            self.assertNotEqual(arts3d,arts3e)

    def test_depend_on_cache(self):
        """
        depend_on_cache triggers cache invalidation when dependent caches
        are invalidated.
        """

        get_calls_reset()

        # get_squared_calls depends on get_calls
        self.assertEqual(get_calls('test depend on cache'), 1)
        self.assertEqual(get_squared_calls('test depend on cache'), 1)

        # still cached
        self.assertEqual(get_squared_calls('test depend on cache'), 1)
        self.assertEqual(get_calls('test depend on cache'), 1)

        # invalidate; both functions should be flushed now.
        get_calls.delete_all()
        self.assertEqual(get_calls('test depend on cache'), 2)
        self.assertEqual(get_squared_calls('test depend on cache'), 4)

        # again, but in the other order
        get_calls.delete_all()
        self.assertEqual(get_squared_calls('test depend on cache'), 9)
        self.assertEqual(get_calls('test depend on cache'), 3)

        # Reporter.top_article depends on Article.num_comments
        # so invalidating num_comments should invalidate top_article too
        reporter = Reporter.objects.get(pk=1)
        top_article = reporter.top_article()
        next_article = reporter.articles.exclude(pk=top_article.pk)[0]

        d = top_article.num_comments() - next_article.num_comments()
        for i in range(4, 5 + d):
            next_article.comments.create(pk=i)

        with self.assertNumQueries(0):
            top_article_comments = top_article.num_comments()
        with self.assertNumQueries(1):
            next_article_comments = next_article.num_comments()
        self.assertEqual(next_article_comments, top_article_comments + 1)

        # top_article should be a cache miss here
        with self.assertNumQueries(1):
            new_top_article = reporter.top_article()
        self.assertEqual(next_article, new_top_article)

    def test_depend_on_m2m(self):
        """
        depend_on_m2m triggers cache invalidation when new many-to-many
        relations are updated.
        """
        reporter = Reporter.objects.get(pk=1)
        article1 = Article.objects.get(pk=1)
        article2 = Article.objects.get(pk=2)
        hashtag1 = HashTag.objects.get(pk=1)
        hashtag2 = HashTag.objects.get(pk=2)

        # adding a hashtag to an article should invalidate articles_with_hashtag
        with_hashtag1 = reporter.articles_with_hashtag(hashtag1.label)
        article1.hashtags.add(hashtag1)
        with self.assertNumQueries(1):
            with_hashtag1_new = reporter.articles_with_hashtag(hashtag1.label)
        self.assertEqual(set(with_hashtag1_new), set(with_hashtag1 + [article1.headline]))
        self.assertEqual(len(with_hashtag1_new), len(with_hashtag1) + 1)

        # ...and with the second hashtag
        with_hashtag2 = reporter.articles_with_hashtag(hashtag2.label)
        hashtag2.articles.add(article2)
        with self.assertNumQueries(1):
            with_hashtag2_new = reporter.articles_with_hashtag(hashtag2.label)
        self.assertEqual(set(with_hashtag2_new), set(with_hashtag2 + [article2.headline]))
        self.assertEqual(len(with_hashtag2_new), len(with_hashtag2) + 1)

        # but the second hashtag shouldn't affect the first one's cache
        with self.assertNumQueries(0):
            with_hashtag1_again = reporter.articles_with_hashtag(hashtag1.label)
        self.assertEqual(with_hashtag1_again, with_hashtag1_new)

        # removing a hashtag should also invalidate
        article2.hashtags.remove(hashtag2)
        with self.assertNumQueries(1):
            with_hashtag2_removed = reporter.articles_with_hashtag(hashtag2.label)
        self.assertEqual(set(with_hashtag2_removed), set(with_hashtag2))
        self.assertEqual(len(with_hashtag2_removed), len(with_hashtag2))

        with self.assertNumQueries(0):
            with_hashtag1_again = reporter.articles_with_hashtag(hashtag1.label)
        self.assertEqual(with_hashtag1_again, with_hashtag1_new)

        # as should clearing
        hashtag1.articles.clear()
        with self.assertNumQueries(1):
            with_hashtag1_removed = reporter.articles_with_hashtag(hashtag1.label)
        self.assertEqual(set(with_hashtag1_removed), set())

        with self.assertNumQueries(0):
            with_hashtag2_again = reporter.articles_with_hashtag(hashtag2.label)
        self.assertEqual(with_hashtag2_again, with_hashtag2_removed)

    def test_depend_on_model(self):
        """
        depend_on_model triggers cache invalidation when any instance
        of the model is updated.
        """
        reporter = Reporter.objects.get(pk=1)
        hashtag1 = HashTag.objects.get(pk=1)
        with_hashtag1 = reporter.articles_with_hashtag(hashtag1.label)
        old_label = hashtag1.label

        hashtag1.label = '#updated'
        hashtag1.save()
        with self.assertNumQueries(1):
            with_hashtag1_old = reporter.articles_with_hashtag(old_label)
        self.assertEqual(with_hashtag1_old, [])
        with self.assertNumQueries(1):
            with_hashtag1_new = reporter.articles_with_hashtag(hashtag1.label)
        self.assertEqual(set(with_hashtag1_new), set(with_hashtag1))
        self.assertEqual(len(with_hashtag1_new), len(with_hashtag1))


class CacheViewTests(TestCase):
    def setUp(self):
        staff_user = User.objects.create_user(username='testuser', password='testpass')
        staff_user.is_staff = True
        staff_user.save()

    def test_view_exists(self):
        c = Client()
        c.login(username='testuser', password='testpass')
        resp = c.get('/view_all')
        self.assertEqual(resp.status_code, 200)

    def test_view_lists_cached_functions(self):
        c = Client()
        c.login(username='testuser', password='testpass')
        resp = c.get('/view_all')
        cached_functions = [
            'Article.num_comments',
            'Reporter.full_name',
            'Reporter.top_article',
            'Reporter.articles_with_hashtag',
        ]
        for name in cached_functions:
            self.assertContains(resp, name)

    def test_view_flush(self):
        c = Client()
        c.login(username='testuser', password='testpass')
        resp = c.get('/view_all')
        self.assertContains(resp, 'get_calls')

        # XX: lazy brittle hack to get the first link appearing after get_calls
        _, s = resp.content.split('get_calls')
        _, s = s.split('<a href="', 1)
        s, _ = s.split('">Flush</a>', 1)
        flush_url = s

        resp = c.get(flush_url)
        self.assertRedirects(resp, '/view_all')

        a = get_calls('arg')
        b = get_calls('arg')
        _ = c.get(flush_url)
        c = get_calls('arg')
        self.assertEqual(a, b)
        self.assertNotEqual(b, c)


class CacheInclusionTagTest(TestCase):
    # Makes use of the tags in tests/templatetags/test_tags.py
    # This is one giant test because the ordering matters.
    def test_rendering(self):
        # test that it renders
        t = Template("{% load test_tags %}{% silly_inclusion_tag arg %}")
        rendered = t.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 1")
        self.assertEqual(counter[0], 1)

        # test that it is cached
        rendered = t.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 1")
        rendered = t.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 1")
        self.assertEqual(counter[0], 1)

        # test that it doesn't depend on template identity
        t_ = Template("{% load test_tags %}{% silly_inclusion_tag arg %}")
        rendered = t_.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 1")
        rendered = t_.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 1")
        self.assertEqual(counter[0], 1)

        # test that it doesn't depend on the surrounding context
        rendered = t.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 1")
        rendered = t.render(Context({'arg': 'foo', 'unused': 'whatever'}))
        self.assertEqual(rendered, "foo 1")
        self.assertEqual(counter[0], 1)

        # test that it does depend on its arguments
        rendered = t.render(Context({'arg': 'bar'}))
        self.assertEqual(rendered, "bar 2")
        rendered = t.render(Context({'arg': 'bar', 'unused': 'lol'}))
        self.assertEqual(rendered, "bar 2")
        self.assertEqual(counter[0], 2)

        # test that expiring the cached function expires the cache
        silly_inclusion_tag.cached_function.delete_all()
        rendered = t.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 3")
        rendered = t.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 3")
        self.assertEqual(counter[0], 3)

        # test that a depend_on_row works correctly
        reporter1 = Reporter.objects.create(first_name="baz", last_name="quux")
        rendered = t.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 3")
        rendered = t.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 3")
        self.assertEqual(counter[0], 3)

        reporter2 = Reporter.objects.create(first_name="foo", last_name="quux")
        rendered = t.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 4")
        rendered = t.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 4")
        self.assertEqual(counter[0], 4)

        reporter1.last_name = "quuuuuuuuuuuuuuuuuuux"
        reporter1.save()
        rendered = t.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 4")
        rendered = t.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 4")
        self.assertEqual(counter[0], 4)

        reporter2.last_name = "quuuuuuuuuuuuuuuuuuux"
        reporter2.save()
        rendered = t.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 5")
        rendered = t.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 5")
        self.assertEqual(counter[0], 5)

        # test that a depend_on_model works correctly
        Article.objects.create(headline="exciting article",
                               content="no content",
                               reporter=reporter1)
        rendered = t.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 6")
        rendered = t.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 6")
        self.assertEqual(counter[0], 6)

        # test that the cache depends on Context attributes like autoescape
        t2 = Template("{% load test_tags %}{% autoescape off %}"
                      "{% silly_inclusion_tag arg %}{% endautoescape %}")
        rendered = t2.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 7")
        rendered = t2.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 7")
        rendered = t.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 6")
        rendered = t.render(Context({'arg': 'foo'}))
        self.assertEqual(rendered, "foo 6")
        self.assertEqual(counter[0], 7)


class DerivedFieldTest(TestCase):
    def setUp(self):
        # create initial objects
        reporter1 = Reporter.objects.create(pk=1, first_name='John', last_name='Doe')
        reporter2 = Reporter.objects.create(pk=2, first_name='Jane', last_name='Roe')
        reporter3 = Reporter.objects.create(pk=3, first_name='Jim', last_name='Poe')

    def test_derived_agrees_with_cached_function(self):
        reporter = Reporter.objects.get(pk=1)
        n1 = reporter.backward_name
        n2 = reporter.get_backward_name()
        self.assertEqual(n1, n2)

        reporter.first_name = 'Ron'
        reporter.save()

        reporter = Reporter.objects.get(pk=1)
        n3 = reporter.backward_name
        n4 = reporter.get_backward_name()
        self.assertEqual(n3, n4)
        self.assertNotEqual(n3, n1)

    def test_derived_is_queryable(self):
        with self.assertNumQueries(1):
            reporters = list(Reporter.objects.order_by('backward_name'))
        self.assertEqual([reporter.pk for reporter in reporters], [1, 3, 2])


class CacheConcurrencyTest(TestCase):
    def call_concurrently(self, funcs):
        """
        Helper function to run multiple functions concurrently, re-raising
        exceptions on the main thread.
        """
        threads = []
        exceptions = []

        def capture_exceptions(func):
            def wrapper(*args, **kwargs):
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    exceptions.append(e)
                    raise
            return wrapper

        for f in funcs:
            threads.append(threading.Thread(target=capture_exceptions(f)))
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        for e in exceptions:
            raise e

    @unittest.skip("Known issue, see Github #2")
    def test_race_cached_function(self):
        set_value(1)
        def a():
            x = get_value_slowly()
            self.assertEqual(x, 1)
        def b():
            set_value(2)
            x = get_value()
            self.assertEqual(x, 2)
        self.call_concurrently([a, b])
        x = get_value()
        y = get_value_slowly()
        self.assertEqual(x, y)
