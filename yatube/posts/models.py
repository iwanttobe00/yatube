from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class Group(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()

    class Meta:
        verbose_name = "Группа"
        verbose_name_plural = "Группы"

    def __str__(self) -> str:
        return self.title


class Post(models.Model):
    text = models.TextField(
        "Текст поста",
        help_text="Введите текст поста"
    )
    pub_date = models.DateTimeField(auto_now_add=True, db_index=True)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="posts"
    )

    group = models.ForeignKey(
        Group,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="posts",
        verbose_name="Категория",
        help_text="Категория, в которой будет пост"
    )

    image = models.ImageField(
        "Картинка",
        upload_to="posts/",
        blank=True
    )

    class Meta():
        ordering = ["-pub_date"]

    def __str__(self) -> str:
        return self.text


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="comments"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="comments"
    )
    text = models.TextField(
        "Текст комментария",
        help_text="Введите текст комментария"
    )
    created = models.DateTimeField("Дата публикации", auto_now_add=True)

    class Meta():
        ordering = ["-created"]

    def __str__(self) -> str:
        return self.text


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="follower"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="following"
    )
