# Stdlib
from datetime import datetime
# Pjuu imports
from pjuu import r


def create_post(uid, body):
    """
    Creates a new post. Does all the other stuff to like prepend to feeds,
    post list, etc...
    """
    pid = int(r.incr('global:pid'))
    post = {
        'pid': pid,
        'uid': uid,
        'body': body,
        'created': datetime.now().isoformat(),
        'score': 0
    }
    # Transactional
    pipe = r.pipeline()
    pipe.hmset('post:%d' % pid, post)
    pipe.lpush('posts:%d' % uid, pid)
    pipe.lpush('feed:%d' % uid, pid)
    pipe.execute()
    # Append to all followers feeds
    # TODO This needs putting in to Celery at some point
    followers = r.smembers('followers:%d' % uid)
    for fid in followers:
        # Transactional
        pipe = r.pipeline()
        pipe.lpush('feed:%s' % fid, pid)
        pipe.ltirm('feed:%s' % fid, 0, 999)
        pipe.execute()
    return pid


def create_comment(uid, pid, body):
    """
    Create a new comment.
    """
    cid = int(r.incr('global:cid'))
    comment = {
        'cid': cid,
        'uid': uid,
        'pid': pid,
        'body': body,
        'created': datetime.now().isoformat(),
        'score': 0
    }
    # Transactional
    pipe = r.pipeline()
    pipe.hmset('comment:%d' % cid, comment)
    pipe.lpush('comments:%d' % pid, cid)
    pipe.execute()
    return cid


def get_post(pid):
    post = r.hgetall('post:%d' % pid)
    post['user_username'] = r.hget('user:%s' % post['uid'], 'username')
    post['user_email'] = r.hget('user:%s' % post['uid'], 'email')
    post['user_score'] = r.hget('user:%s' % post['uid'], 'score')
    post['comment_count'] = r.llen('comments:%d' % pid)
    return post
