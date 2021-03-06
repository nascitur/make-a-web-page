#!/usr/bin/python
#
# servepage.py
#
# Goal of this is to serve up the notes page with comments using Google
# app engine and datastore, and the python to build the page from
# the notes text file (buildhtmlfromnotes.py).  In real life you wouldnt
# rebuild the page every time someone navigated to it but I'm not going
# to worry about that.

"""
    This should build the html from the notes text file, allow comments
    and add the comments, and serve it all up on GAE
"""

# Import system modules

import cgi
import datetime
import re
#import time  # dev
#from tzlocal import get_localzone # dev - bug: wont import even after install

# Import GAE and Google datastore modules

from google.appengine.api import users
from google.appengine.ext import ndb
import webapp2

# Import custom modules

import buildhtmlfromnotes

# Default text for comment form entry
DEFAULT_SUBJECT = 'Your site'
DEFAULT_AUTHOR = 'Anonymous'
DEFAULT_LOCATION = 'Unknown'

# Raw number of comments to display on the site
NUM_COMMENTS = 10
# Number of days of comments to consider for display
RECENT = 3

# Trim any input text to these lengths
MAX_AUTHSUBJ = 40
MAX_COMMENT = 300


def comment_key(comment_subject=DEFAULT_SUBJECT):
    """
    Constructs a Datastore key for a commentpost entity.
    We use comment_subject as the key.
    """
    return ndb.Key('Guestbook', comment_subject)


class Author(ndb.Model):
    """Sub model for representing an author."""
    authorname = ndb.StringProperty(indexed=False)
    authorlocation = ndb.StringProperty(indexed=False)


class CommentPost(ndb.Model):
    """A main model for representing an individual coment entry."""
    author = ndb.StructuredProperty(Author)
    subject = ndb.StringProperty()
    content = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)


def strclean(stringtovalidate):
    """
    Cleans up a string to ensure valid input by restricting to safe characters
    """
    return re.sub('[^A-Za-z0-9 ?!,.]+', '', stringtovalidate)


class CommentsSection(webapp2.RequestHandler):
    """
    Build the main page with comment section
    """
    def get(self):
        """
        Page assembled on get, comment data is added on post
        """
        page_html = buildhtmlfromnotes.Page('<html><body>')

        recentdate = datetime.datetime.now() - datetime.timedelta(days=RECENT)

        this_query = str(self.request.query_string)
        if this_query.find('nocomment') != -1:
            useralert = True
        else:
            useralert = False

        greetings_query = ndb.gql('SELECT * FROM CommentPost WHERE date>:1 \
                                  ORDER BY date DESC', recentdate)
        greetings = greetings_query.fetch(NUM_COMMENTS)
        greeting_textblock = ''

        for greeting in greetings:
            author = greeting.author.authorname
            authorplace = greeting.author.authorlocation
            commentsubject = greeting.subject
            postdate = greeting.date
            #postdate = to_zone.normalize(greeting.date.replace(tzinfo=to_zone))
            greeting_textblock += '<li class="clist"><b>%(author)s</b> from \
                                   %(location)s wrote on %(date)s at %(time)s\
                                   about %(subj)s: <i>%(comment)s</i>' % \
                                {"author": cgi.escape(author),
                                 "location": cgi.escape(authorplace),
                                 "date": postdate.strftime("%B %d"),
                                 "time": postdate.strftime("%H:%M"),
                                 "subj": cgi.escape(commentsubject),
                                 "comment": cgi.escape(greeting.content)}

        form_args = (DEFAULT_SUBJECT,
                     DEFAULT_AUTHOR,
                     DEFAULT_LOCATION,
                     greeting_textblock,
                     MAX_AUTHSUBJ,
                     MAX_COMMENT,
                     useralert)

        self.response.write(page_html.Build('<html><body>', form_args))


class Guestbook(webapp2.RequestHandler):
    """
    Accept comments for the comment page
    """
    def post(self):
        """
        Page assembled on get, comment data is added on post
        """
        comment_subject = strclean(str(self.request.get('comment_subject',
                                           DEFAULT_SUBJECT))[:MAX_AUTHSUBJ])
        author_name = strclean(str(self.request.get('author_name',
                                       DEFAULT_AUTHOR))[:MAX_AUTHSUBJ])
        author_location = strclean(str(self.request.get('author_location',
                                           DEFAULT_LOCATION))[:MAX_AUTHSUBJ])

        greeting = CommentPost(parent=comment_key(comment_subject))

        greeting.author = Author(authorname=author_name,
                                 authorlocation=author_location)
        #to_zone = get_localzone() # development - havent figured out

        greeting.content = strclean(str(self.request.get('content'))[:MAX_COMMENT])
        greeting.subject = comment_subject
        if greeting.content.strip():
            greeting.put()
            #time.sleep(1)     #only required in local deployment
            self.redirect('/#comments')
        else:
            self.redirect('/?nocomment#comments')

# Defines what is executed by the webserver

app = webapp2.WSGIApplication([
    ('/', CommentsSection),
    ('/signed', Guestbook),
], debug=True)



