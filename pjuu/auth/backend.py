# Stdlib imports
from base64 import (urlsafe_b64encode as b64encode,
                    urlsafe_b64decode as b64decode)
from urlparse import urlparse, urljoin

# 3rd party imports
from flask import _app_ctx_stack, request, session, abort
from itsdangerous import TimedSerializer
from werkzeug.local import LocalProxy
from werkzeug.security import generate_password_hash, check_password_hash

# Pjuu imports
from pjuu import app, db
from pjuu.users.models import User


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
                  'pic','pics','photo','photos','photoalbum','php','plugin',
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
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    _app_ctx_stack.top.user = user


def get_username(username):
    """
    Return a user object from a username. Will check if username is an e-mail.
    Return None if it does not locate a user
    """
    if '@' in username:
        user = User.query.filter(User.email.ilike(username)).first()
    else:
        user = User.query.filter(User.username.ilike(username)).first()
    return user


def check_username(username):
    """
    Used to check for username availablity inside the signup form.
    Returns true if the name is free false otherwise
    """
    reserved = username.lower() in reserved_names
    exists = User.query.filter(User.username.ilike(username)).first()
    if reserved or exists:
        return False
    else:
        return True


def create_account(username, email, password):
    """
    Creates a user account. If this task fails a 500 will be thrown.
    Returns the user account.
    """
    try:
        new_user = User(username, email, password)
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        # The Otter is broken
        print "ERROR: create_account: ", e
        db.session.rollback()
        abort(500)
    return new_user


def authenticate(username, password):
    """
    Will authenticate a username/password combination.
    If successful will return a user object else will return None.
    """
    user = get_username(username)
    if user and check_password_hash(user.password, password):
        return user
    return None


def login(user):
    """
    Logs the user in. Will add user id to session.
    Will also update the users last_login time.
    """
    session['user_id'] = user.id
    try:
        user.last_login = db.func.now()
        db.session.add(user)
        db.session.commit()
    except:
        # The Otter is broken
        db.session.rollback()
        # Lets make sure to log the user out. THIS WILL HAVE HAPPENED
        logout()
        abort(500)

    
def logout():
    """
    Removes the user id from the session. If it isn't there then
    nothing bad happens.
    """
    session.pop('user_id', None)


def activate(user):
    """
    Sets the user account to active.
    """
    try:
        user.active = True
        db.session.add(user)
        db.session.commit()
    except:
        # The Otter is broken
        db.session.rollback()
        abort(500)


def change_password(user, password):
    """
    Sets `user`s password to `password`.
    """
    try:
        user.password = generate_password_hash(password)
        db.session.add(user)
        db.session.commit()
    except:
        # The Otter is broken
        db.session.rollback()
        abort(500)


def change_email(user, email):
    """
    Set `user`s email to `email`
    """
    try:
        user.email = email
        db.session.add(user)
        db.session.commit()
    except:
        # The Otter is broken
        db.session.rollback()
        abort(500)


def is_safe_url(target):
    """
    Not sure what the point of checking a URL is at the moment.
    I am using this because at some point it will be important.
    """
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
