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

    def test_url_exists_at_desired_location(self):
        """Проверка страниц доступных неавторизованному пользователю."""
        url_path = (
            ('posts:index', None),
            ('posts:group_list', {self.group.slug}),
            ('posts:profile', {self.author}),
            ('posts:post_detail', {self.post.id}),
        )
        for adress, args in url_path:
            with self.subTest(adress=adress):
                revers_name = reverse(adress, args=args)
                response = self.guest_client.get(revers_name)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_page_404(self):
        """Запрос к несуществующей странице вернёт ошибку 404"""
        response = self.guest_client.get('/404/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

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

    def test_urls_404_uses_correct_template(self):
        """Несуществующая страница вызывает шаблон "core/404.html"."""
        response = self.authorized_client.get('/404/')
        self.assertTemplateUsed(response, 'core/404.html')

    def test_post_edit_url_exists_at_desired_location(self):
        """Страница редактирования поста доступна автору поста."""
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_url_redirect_no_author_on_post_detail(self):
        """Страница редактирования поста перенаправляет
        пользователя - не автора.
        """
        response = self.authorized_client_2.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id})
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )

    def test_post_create_url_redirect_anonymous_on_login(self):
        """Страница создания поста перенаправит анонимного пользователя
        на страницу логина.
        """
        response = self.guest_client.get(reverse('posts:post_create'))
        self.assertRedirects(
            response, reverse('users:login') + '?next='
            + reverse('posts:post_create')
        )
