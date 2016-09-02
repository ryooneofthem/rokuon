# coding: UTF-8

import settings

from flask import Flask
from google.appengine.ext.db import KindError
from google.appengine.api.datastore_errors import BadKeyError
import time
import datetime
app = Flask(__name__)
app.config.from_object('settings')

from flask import g
from flask import redirect
from flask import url_for
from flask import session
from flask import request
from flask import render_template
from flask import abort
from flask import flash
from flask import get_flashed_messages
from flask import json

from decorators import login_required, cache_page

from models import *

from gaeUtils.util import generate_key
from google.appengine.api.labs import taskqueue
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import blobstore

from werkzeug.contrib.cache import GAEMemcachedCache

app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024 #3M
cache = GAEMemcachedCache()

# ------------------------------------------------------------------------------
#  FILTERS FOR TEMPLETE.
# ------------------------------------------------------------------------------

@app.template_filter()
#def datetimeformat(value, format='%Y-%m-%d'):
def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    #time.localtime()
    new_time = (value+datetime.timedelta(hours=+8))
    #app.logger.debug('%s'% new_time)
    return new_time.strftime(format)

@app.template_filter()
def limliString(value):
    if len(value) > 100:
        return '%s...' % value[:100]
    return value

@app.template_filter()
def avatarImgUrl(value):
    return get_avatar(value)
# ------------------------------------------------------------------------------
#  METHODS.
# ------------------------------------------------------------------------------

@app.before_request
def before_request():
    """
    if the session includes a user_key it will also try to fetch
    the user's object from memcache (or the datastore).
    if this succeeds, the user object is also added to g.
    """
    if 'user_key' in session:
        user = cache.get(str(session['user_key']))
        #app.logger.debug("1:%s" % user)
        if user is None:
            # if the user is not available in memcache we fetch
            # it from the datastore
            #user = User.get_by_key_name(str(session['user_key']))
            user = users.get_current_user()
            #app.logger.debug("2:%s" % user)
            if user:
                # add the user object to memcache so we
                # don't need to hit the datastore next time
                #app.logger.debug("3:%s" % user)
                cache.set(str(session['user_key']), user)
        g.user = user
    else:
        g.user = None

@app.route('/help')
def help():
    return redirect('http://rokuon-develop.blogspot.com/2011/07/rokuon.html')

@app.route('/login')
def login():
    """
    process login
    """
    indexURL = url_for('index')
    user = users.get_current_user()
    if user:
        session['user_key'] = user
        return redirect(indexURL)
    else:
      pass
    return redirect(users.create_login_url(indexURL))

@app.route('/logout')
def logout():
    """
    process logout
    """
    indexURL = url_for('index')
    
    session['user_key'] = None
    cache.set(str(session['user_key']), None)
    g.user = None
    
    if g.user == None:
        return redirect(users.create_logout_url(indexURL))
    
    return redirect(users.create_logout_url('logout'))

@app.route('/upload', methods=['GET','POST'])
@login_required
def upload():
    """
    renders the upload page template & process upload file
    """
    #if request.method == 'POST' and 'sound' in request.files:
    app.logger.debug("%s" % 'start upload')
    if request.method == 'POST':
        app.logger.debug("%s" % 'has file')
        file = request.files['sound']
        app.logger.debug("uploaded file %s."% file.filename)
        app.logger.debug("%s."% file.content_type)
        
        rec = Record(desc=request.form['desc'])
        rec.owner = users.get_current_user()
        if(file):
            rec.sound = db.Blob(file.read())
        rec.put()
        app.logger.debug("recoder id:%s save success."% rec.key().id())
        #return render_template('index.html')
        nextURL = url_for('record_read',id=rec.key().id())
        setNextURL(nextURL)
        return redirect(nextURL)
    app.logger.debug("%s" % 'no file')
    return render_template('upload.html')

def setNextURL(next_url):
    session['next_url'] = next_url

@app.route('/getFile/<name>')
def getFile(name):
    try:
        rec = Record.get(name)
    except BadKeyError:
        abort(404)

    if rec is None:
        return "no file"
    else:
        #mimetype = 'application/octet-stream'
        #blob_reader = blobstore.BlobReader(blob_key)
        #blobstore.BlobReader(rec.sound)
        mimetype = 'audio/mpeg'
        return app.response_class(rec.sound,mimetype=mimetype,direct_passthrough=False)

@app.route('/del/<int:id>')
def record_delete(id):
    record = Record.get_by_id(id)
    if record and record.owner == users.get_current_user():
        record.delete()
    else:
        abort(404)
    return redirect(url_for('index'))

@app.route('/read/<int:id>')
def record_read(id):
    record = Record.get_by_id(id)
    if record is None:
        abort(404)
    
    avatar = get_avatar(record.owner.email)
    
    return render_template('record.html',avatar=avatar,user=g.user,record=record
                           , flashes=get_flashed_messages())

@app.route('/player/<int:id>')
def player(id):
    record = Record.get_by_id(id)
    if record is None:
        abort(404)    
    return render_template('player.html',record=record
                           , flashes=get_flashed_messages())
@app.route('/')
@app.route('/<int:page>')
def index(page=1):
    #user = users.get_current_user()
    #records = Record.all().filter('user =', user)
    try:
        next_url = session['next_url']
    except KeyError:
        next_url = None

    if next_url:
        del session['next_url']
        return redirect(next_url)
        
    PAGE_MAX_ROW = 50
    if (page - 1 < 1):
        page = 1
    page_offset = PAGE_MAX_ROW * (page - 1)
    
    records = Record.all().filter('createTime >=', datetime.datetime.strptime("2011-07-04", "%Y-%m-%d")).order('-createTime').fetch(PAGE_MAX_ROW,page_offset)
    #return dict(user=user, logout_url=users.create_logout_url('/'),
    #            records=records, flashes=get_flashed_messages())
    return render_template('list.html',user=g.user,records=records,
                            flashes=get_flashed_messages())

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

def get_avatar(email):
    email = str(email)
    # import code for encoding urls and generating md5 hashes
    import urllib, hashlib
    # Set your variables here
    #email = "someone@somewhere.com"
    #default = "http://www.example.com/default.jpg"
    size = 40
    # construct the url
    gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(email.lower()).hexdigest() + "?"
    #gravatar_url += urllib.urlencode({'d':default, 's':str(size)})
    gravatar_url += urllib.urlencode({'s':str(size)})
    return gravatar_url
#@app.route('/')
#def index():
#    """
#    renders the index page template
#    """
#    user = users.get_current_user()
#    #app.logger.debug("%s!" % user.email())
#    app.logger.debug("%s!" % user)
#    return render_template('index.html',user=user)
