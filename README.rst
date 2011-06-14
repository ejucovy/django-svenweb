This will be a Django project for managing bazaar-backed wikis and producing static websites.

Installation::

    virtualenv.py .
    git clone git@github.com:ejucovy/django-svenweb svenweb
    . ./bin/activate
    cd svenweb
    pip install -r req.txt
    ./manage.py syncdb
    ./manage.py runserver
