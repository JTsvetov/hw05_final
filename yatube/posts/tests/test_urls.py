from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from posts.models import Group, Post

User = get_user_model()


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
            id=12345,
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
            '/posts/12345/',
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
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/posts/12345/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            '/posts/12345/edit/': 'posts/create_post.html',
            '/profile/test_user/': 'posts/profile.html',
            '/404/': 'core/404.html',
        }
        for adress, template in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                self.assertTemplateUsed(response, template)

    # Проверка доступности страницы post_edit для автора
    def test_post_edit_url_exists_at_desired_location(self):
        """Страница posts/<post_id>/edit/ доступна автору поста."""
        response = self.authorized_client.get('/posts/12345/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    # Проверяем редирект для авторизованного пользователя - не автора
    def test_post_edit_url_redirect_no_author_on_post_detail(self):
        """Страница post_edit/ перенаправляет пользователя - не автора."""
        response = self.authorized_client_2.get(
            '/posts/12345/edit/', follow=True)
        self.assertRedirects(
            response, ('/posts/12345/'))

    # Проверяем редиректы для неавторизованного пользователя
    def test_post_create_url_redirect_anonymous_on_login(self):
        """Страница /create/ перенаправит анонимного пользователя
        на страницу логина.
        """
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(
            response, '/auth/login/?next=/create/')
