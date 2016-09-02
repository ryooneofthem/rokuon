import os
DEBUG = os.environ.get('SERVER_SOFTWARE', 'Dev').startswith('Dev')
SECRET_KEY = '?????'

# CSRF_ENABLED=True
# CSRF_SESSION_LKEY=''
