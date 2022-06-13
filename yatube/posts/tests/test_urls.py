from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, User


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_user')
        cls.no_author = User.objects.create_user(username='no_author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
            group=cls.group,
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Авторизация
        self.authorized_client = Client()
        self.authorized_client.force_login(StaticURLTests.author)
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(StaticURLTests.no_author)

    # Проверка доступности страниц для неавторизованного пользователя
    def test_url_exists_at_desired_location(self):
        """Проверка страниц доступных любому пользователю."""
        url_path = (
            '/',
            '/group/test-slug/',
            '/profile/test_user/',
            f'/posts/{self.post.id}/',
        )
        for adress in url_path:
            with self.subTest():
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    # Проверка, что запрос к несуществующей странице вернёт ошибку 404.
    def test_page_404(self):
        response = self.guest_client.get('/404/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Проверка вызываемых шаблонов для каждого адреса
    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = (
            ('posts:index', None, 'posts/index.html'),
            ('posts:group_list', {self.group.slug}, 'posts/group_list.html'),
            ('posts:profile', {self.author}, 'posts/profile.html'),
            ('posts:post_detail', {self.post.id}, 'posts/post_detail.html'),
            ('posts:post_edit', {self.post.id}, 'posts/create_post.html'),
            ('posts:post_create', None, 'posts/create_post.html'),
        )
        for adress, args, template in templates_url_names:
            with self.subTest(adress=adress):
                revers_name = reverse(adress, args=args)
                response = self.authorized_client.get(revers_name)
                self.assertTemplateUsed(response, template)

    # Проверка вызываемого шаблона для несуществующего адреса
    def test_urls_404_uses_correct_template(self):
        """Страница /404/ вызывает шаблон "core/404.html"."""
        response = self.authorized_client.get('/404/')
        self.assertTemplateUsed(response, 'core/404.html')

    # Проверка доступности страницы post_edit для автора
    def test_post_edit_url_exists_at_desired_location(self):
        """Страница posts/<post_id>/edit/ доступна автору поста."""
        response = self.authorized_client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    # Проверяем редирект для авторизованного пользователя - не автора
    def test_post_edit_url_redirect_no_author_on_post_detail(self):
        """Страница post_edit/ перенаправляет пользователя - не автора."""
        response = self.authorized_client_2.get(
            f'/posts/{self.post.id}/edit/', follow=True)
        self.assertRedirects(
            response, (f'/posts/{self.post.id}/'))

    # Проверяем редиректы для неавторизованного пользователя
    def test_post_create_url_redirect_anonymous_on_login(self):
        """Страница /create/ перенаправит анонимного пользователя
        на страницу логина.
        """
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(
            response, '/auth/login/?next=/create/')
