from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Permite login tanto com o nome de usuário quanto com o e-mail cadastrado.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None

        try:
            user = User.objects.get(email__iexact=username)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            try:
                user = User.objects.get(username__iexact=username)
            except User.DoesNotExist:
                # Executa o hasher mesmo assim para não vazar, por tempo de resposta,
                # se o usuário/e-mail existe ou não.
                User().set_password(password)
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
