# Stdlib imports
from base64 import (urlsafe_b64encode as b64encode,
                    urlsafe_b64decode as b64decode)
from datetime import datetime
from urlparse import urlparse, urljoin
# 3rd party imports
from flask import _app_ctx_stack, request, session, abort
from itsdangerous import TimedSerializer
from werkzeug.local import LocalProxy
from werkzeug.security import generate_password_hash, check_password_hash
# Pjuu imports
from pjuu import app, r


# Reserved names
reserved_names = ['about','access','account','accounts','add','address','adm',
                  'admin','administration','adult','advertising','affiliate',
                  'affiliates','ajax','analytics','android','anon','anonymous',
                  'api','app','apps','archive','atom','auth','authentication',
                  'avatar','backup','banner','banners','bin','billing','blog',
                  'blogs','board','bot','bots','business','chat','cache',
                  'cadastro','calendar','campaign','careers','cgi','client',
                  'cliente','code','comercial','compare','config','connect',
                  'contact','contest','create','code','compras','css',
                  'dashboard','data','db','design','delete','demo','design',
                  'designer','dev','devel','dir','directory','doc','docs',
                  'domain','download','downloads','edit','editor','email',
                  'ecommerce','forum','forums','faq','favorite','feed',
                  'feedback','flog','follow','followers','following','file',
                  'files','free','ftp','gadget','gadgets','games','guest',
                  'group','groups','help','home','homepage','host','hosting',
                  'hostname','html','http','httpd','https','hpg','info',
                  'information','image','img','images','imap','index','invite',
                  'intranet','indice','java','javascript','job','jobs','js',
                  'knowledgebase','log','login','logs','logout','list','lists',
                  'mail','mail1','mail2','mail3','mail4','mail5','mailer',
                  'mailing','mx','manager','marketing','master','me','media',
                  'message','microblog','microblogs','mine','mp3','msg','msn',
                  'mysql','messenger','mob','mobile','movie','movies','music',
                  'musicas','my','name','named','net','network','new','news',
                  'newsletter','nick','nickname','notes','noticias','ns',
                  'ns1','ns2','ns3','ns4','old','online','operator','order',
                  'orders','page','pager','pages','panel','password','perl',
                  'pic','pics','photo','photos','photoalbum','php','pjuu','plugin',
                  'plugins','pop','pop3','post','postmaster','postfix','posts',
                  'profile','project','projects','promo','pub','public',
                  'random','register','registration','root','rss','sale',
                  'sales','sample','samples','script','scripts','secure',
                  'send','service','shop','sql','signup','signin','search',
                  'security','settings','setting','setup','site','sites',
                  'sitemap','smtp','soporte','ssh','stage','staging','start',
                  'subscribe','subdomain','suporte','support','stat','static',
                  'stats','status','store','stores','system','tablet',
                  'tablets','tech','telnet','test','test1','test2','test3',
                  'teste','tests','theme','themes','tmp','todo','task','tasks',
                  'tools','tv','talk','update','upload','url','user','username',
                  'usuario','usage','vendas','video','videos','visitor','win',
                  'ww','www','www1','www2','www3','www4','www5','www6','www7',
                  'wwww','wws','wwws','web','webmail','website','websites',
                  'webmaster','workshop','xxx','xpg']


# Signers
activate_signer = TimedSerializer(app.config['TOKEN_KEY'], salt=app.config['SALT_ACTIVATE'])
forgot_signer = TimedSerializer(app.config['TOKEN_KEY'], salt=app.config['SALT_FORGOT'])
email_signer = TimedSerializer(app.config['TOKEN_KEY'], salt=app.config['SALT_EMAIL'])


# Can be used anywhere to get the current logged in user.
# This will return None if the user is not logged in.
current_user = LocalProxy(lambda: _get_user())


def _get_user():
    """
    Used to create the current_user local proxy.
    """
    return getattr(_app_ctx_stack.top, 'user', None)


@app.before_request
def _load_user():
    """
    If the user is logged in, will place the user object on the
    application context.
    """
    user = None
    if 'uid' in session:
        user = r.hgetall('user:%d' % session['uid'])
    _app_ctx_stack.top.user = user


def get_uid(username):
    """
    Returns a user_id from username.
    This can be an e-mail or username.
    """
    username = username.lower()
    uid = r.get('uid:%s' % username)
    if uid: uid = int(uid)
    return uid


def get_user(username):
    """
    Similar to above but will return the user dict (calls above).
    """
    uid = get_uid(username)
    if uid:
        return r.hgetall('user:%d' % uid)
    else:
        return None


def check_username(username):
    """
    Used to check for username availablity inside the signup form.
    Returns true if the name is free, false otherwise
    """
    username = username.lower()
    taken = username in reserved_names
    if not taken:
        taken = r.exists('uid:%s' % username)
    return False if taken else True


def create_user(username, email, password):
    """
    Creates a user account.
    """
    # Get next uid
    uid = r.incr('global:uid')
    # Create user dictionary ready for HMSET
    user = {
        'uid': uid,
        'username': username,
        'email': email,
        'password': generate_password_hash(password),
        'created': datetime.now(),
        'last_login': -1,
        'active': 0,
        'banned': 0,
        'op': 0,
        'about': "",
        'score': 0
    }
    # Only create the user if it does not exist. This step is for safety
    if not r.exists('user:%d' % uid):
        # Transactional
        pipe = r.pipeline()
        pipe.hmset('user:%d' % uid, user)
        # Create look up keys for auth system (these are lowercase)
        pipe.set('uid:%s' % username.lower(), uid)
        pipe.set('uid:%s' % email.lower(), uid)
        pipe.execute()
        return uid
    return None


def authenticate(username, password):
    """
    Will authenticate a username/password combination.
    If successful will return a user object else will return None.
    """
    uid = get_uid(username)
    if uid and check_password_hash(r.hget('user:%d' % uid, 'password'), password):
        return uid
    return None


def login(uid):
    """
    Logs the user in. Will add user_id to session.
    Will also update the users last_login time.
    """
    session['uid'] = uid
    # update last login
    r.hset('user:%d' % uid, 'last_login', datetime.now())

    
def logout():
    """
    Removes the user id from the session. If it isn't there then
    nothing bad happens.
    """
    session.pop('uid', None)


def activate(uid):
    """
    Activates a user after signup
    """
    return r.hset('user:%d' % uid, 'active', True)


def change_password(uid, password):
    """
    Changes user with uid's password
    """
    password = generate_password_hash(password)
    return r.hset('user:%d' % uid, 'password', password)


def change_email(uid, email):
    """
    Changes the user with uid's e-mail address.
    Has to remove old lookup index and add the new one
    """
    pipe = r.pipeline()
    old_email = pipe.hget('user:%d' % uid, 'email')
    pipe.delete('uid:%s' % old_email)
    pipe.set('uid:%s' % email, uid)
    result = pipe.hset('user:%d' % uid, 'email', email)
    pipe.execute()
    return result


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


def generate_token(signer, data):
    """
    Generates a token using the signer passed in.
    """
    try:
        token = b64encode(signer.dumps(data).encode('ascii'))
    except:
        return None
    return token


def check_token(signer, token):
    """
    Checks a token againt the passed in signer.
    If it fails returns None if it works the data from the
    original token will me passed back.
    """
    try:
        data = signer.loads(b64decode(token.encode('ascii')), max_age=86400)
    except:
        return None
    return data
