import shutil
import tempfile
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Follow, Group, Post, User
from posts.views import AMOUNT_POSTS

AMOUND_POSTS_ADD = 13
AMOUND_POSTS_SECOND_PAGE = 3

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.author = User.objects.create_user(username='test_user')
        cls.no_author = User.objects.create_user(username='no_author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.group2 = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug2',
            description='Тестовое описание2',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
            group=cls.group,
            image=cls.uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Авторизация
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsPagesTests.author)
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(PostsPagesTests.no_author)

    def test_pages_uses_correct_template_quest_user(self):
        """URL-адрес использует соответствующие шаблоны для guest_users"""
        templates_pages_names = {
            'posts/index.html': reverse('posts:index'),
            'posts/group_list.html':
                reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            'posts/profile.html':
                reverse('posts:profile', kwargs={'username': self.author}),
            'posts/post_detail.html':
                reverse('posts:post_detail', kwargs={'post_id': self.post.id}
                        ),
        }
        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_pages_uses_correct_template_auth_user(self):
        """URL-адрес использует соответствующие шаблоны для auth_users"""
        templates_pages_names = {
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': self.post.id}
            ): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def assert_post_response(self, response):
        """Функция для проверки ожидаемых типов полей формы"""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_create_page_with_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client_2.get(reverse('posts:post_create'))
        self.assert_post_response(response)

    def test_post_edit_page_with_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        self.assert_post_response(response)

    def assert_post_context(self, post):
        """Функция для проверки context на страницах index, group_list,
        profile
        """
        self.assertEqual(post.id, self.post.id)
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.group, self.post.group)
        self.assertEqual(post.image, self.post.image)

    def test_page_index_group_list_profile_correct_context(self):
        """Шаблон index, group_list, profile
        сформирован с правильным контекстом.
        Тестовый пост отображается на страницах
        """
        url = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': 'test_user'}),
        )
        for adress in url:
            with self.subTest():
                response = self.authorized_client.get(adress)
                first_object = response.context['page_obj'][0]
                self.assert_post_context(first_object)

    def test_post_detail_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом.
        Тестовый пост отображается на странице
        """
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        first_object = response.context.get('post')
        self.assert_post_context(first_object)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.authorized_author = Client()
        cls.author = User.objects.create_user(username='test_user2')
        cls.group = Group.objects.create(
            title='Тестовая группа2',
            description='Тестовое описание2',
            slug='test-slug2'
        )

    def setUp(self):
        Post.objects.bulk_create([Post(
            text='тестовый_текст', author=self.author,
            group=self.group) for i in range(13)])

    def for_test_pagination(self, url_params, expected_count):
        templates_pages_names = {
            'posts/index.html': reverse('posts:index') + url_params,
            'posts/group_list.html': (reverse(
                'posts:group_list', kwargs={'slug': self.group.slug})
                + url_params),
            'posts/profile.html': (reverse(
                'posts:profile', kwargs={'username': self.author})
                + url_params),
        }
        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                self.assertEqual(
                    len(response.context['page_obj']), expected_count
                )

    def test_first_page_contains_ten_records(self):
        self.for_test_pagination("", AMOUNT_POSTS)

    def test_second_page_contains_three_records(self):
        self.for_test_pagination("?page=2", AMOUND_POSTS_SECOND_PAGE)


class PostCacheTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()

    def test_index_cache(self):
        """Проверка кеширования главной страницы."""
        post = Post.objects.create(
            text='Тестовый пост',
            author=PostCacheTest.author,
        )
        response1 = self.guest_client.get(reverse('posts:index'))
        Post.objects.filter(pk=post.pk).delete()
        response2 = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(response1.content, response2.content)
        cache.clear()
        response3 = self.guest_client.get(reverse('posts:index'))
        self.assertNotEqual(response1.content, response3.content)


class FollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='following')
        cls.user = User.objects.create_user(username='follower')
        cls.another_author = User.objects.create_user(username='author_Vanya')
        cls.post = Post.objects.create(
            text='Тестовый текст интересного блогера following',
            author=cls.author,
        )
        cls.post2 = Post.objects.create(
            text='Тестовый текст интересного блогера Vanya',
            author=cls.another_author,
        )
        cls.post3 = Post.objects.create(
            text='Тестовый текст2 интересного блогера Vanya',
            author=cls.another_author,
        )

    def setUp(self):
        self.follower_client = Client()
        self.follower_client.force_login(FollowTest.user)
        self.following_client = Client()
        self.following_client.force_login(FollowTest.author)
        self.another_author_client = Client()
        self.another_author_client.force_login(FollowTest.another_author)

    def test_authorized_client_can_follow_post_exist(self):
        """Авторизованный пользователь может подписываться
        на других пользователей.
        При подписке запись пользователя появляется у подписчика.
        """
        self.follower_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': 'following'})
        )
        response = self.follower_client.get(reverse(
            'posts:follow_index')
        )
        author = response.context['page_obj'][0].author
        self.assertEqual(author, FollowTest.author)
        self.assertIn(self.post, response.context['page_obj'])

    def test_authorized_client_can_unfollow_post_not_exist(self):
        """Авторизованный пользователь может отписываться
        от избранных пользователей.
        При отписке запись пользователя пропадает у бывшего подписчика.
        """
        Follow.objects.bulk_create([Follow(
            author=(User.objects.get(username='following')),
            user=User.objects.get(username='follower')),
            Follow(
                author=(User.objects.get(username='author_Vanya')),
                user=User.objects.get(username='follower'))
        ])
        self.follower_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': 'following'})
        )
        response = self.follower_client.get(reverse(
            'posts:follow_index')
        )
        author = response.context['page_obj'][0].author
        self.assertNotEqual(author, FollowTest.author)
        self.assertNotIn(self.post, response.context['page_obj'])

    def test_not_double_follow(self):
        """Авторизованный пользователь может подписываться
        на конкретного пользователя только один раз.
        """
        Follow.objects.create(
            author=(User.objects.get(
                username='following')), user=User.objects.get(
                    username='follower')
        )
        follow_count = Follow.objects.count()
        self.follower_client.get(reverse(
            'posts:profile_follow', kwargs={'username': 'following'})
        )
        self.assertEqual(Follow.objects.count(), follow_count)
