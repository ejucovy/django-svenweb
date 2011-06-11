from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from restclient import POST

def url(username):
    return "%s/people/%s/get-hash" % (settings.OPENCORE_ROOT_URL.rstrip('/'),
                                      username)

class OpenCoreBackend(ModelBackend):
    # Create a User object if not already in the database?
    create_unknown_user = True

    def authenticate(self, username=None, password=None):
        """
        The username passed as ``remote_user`` is considered trusted.  This
        method simply returns the ``User`` object with the given username,
        creating a new ``User`` object if ``create_unknown_user`` is ``True``.

        Returns None if ``create_unknown_user`` is ``False`` and a ``User``
        object with the given username is not found in the database.
        """
        if not username or not password:
            return

        data = {'__ac_password': password}
        resp, content = POST(url(username), data, resp=True, async=False)

        if resp.status != 200:
            return

        import pdb; pdb.set_trace()
        user = None
        username = self.clean_username(username)

        # Note that this could be accomplished in one try-except clause, but
        # instead we use get_or_create when creating unknown users since it has
        # built-in safeguards for multiple threads.
        if self.create_unknown_user:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user = self.configure_user(user)
        else:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                pass
        return user

    def clean_username(self, username):
        """
        Performs any cleaning on the "username" prior to using it to get or
        create the user object.  Returns the cleaned username.

        By default, returns the username unchanged.
        """
        return username

    def configure_user(self, user):
        """
        Configures a user after creation and returns the updated user.

        By default, returns the user unmodified.
        """
        return user
