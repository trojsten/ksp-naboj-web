from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id: int
    trojsten_id = models.CharField(max_length=256)