# coding: UTF-8
from google.appengine.ext import db

class User(db.Model):
    name = db.StringProperty()


# ------------------------------------------------------------------------------
#  MODELS.
# ------------------------------------------------------------------------------
class Record(db.Model):
    owner = db.UserProperty()
    desc = db.StringProperty(required=True)
    sound = db.BlobProperty()
    createTime = db.DateTimeProperty(auto_now=True)
