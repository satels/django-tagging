import random
import pytest
from django.conf import settings
from django.db import connection


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    if settings.DATABASE_ENGINE == 'mysql':
        with django_db_blocker.unblock():
            cur = connection.cursor()
            cur.execute('ALTER DATABASE tagging DEFAULT CHARACTER SET utf8;')
            cur.execute('ALTER TABLE tagging_tag DEFAULT CHARACTER SET utf8;')
            cur.execute('ALTER TABLE tagging_tag CONVERT TO CHARACTER SET utf8;')