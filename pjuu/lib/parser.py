# -*- coding: utf8 -*-

"""Parsers for extracting @mentions, #hashtags and URLs from posts.

.. note: These have been split appart from posts backend so they can be
         maintained more easily.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""


import re

from pjuu.auth.utils import get_uid_username
from pjuu.lib import fix_url


# Regular expressions for highlighting URLs, @mentions and #hashtags
# URL matching pattern; thanks to John Gruber @ http://daringfireball.net/
# https://gist.github.com/gruber/8891611
URL_RE_PATTERN = (
    r'(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|'
    r'gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|'
    r'tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|'
    r'bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|'
    r'ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|'
    r'er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|'
    r'gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|'
    r'jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|'
    r'mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|'
    r'nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|'
    r'qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|'
    r'su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|'
    r'uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}'
    r'\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\(['
    r'^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’])|(?:(?<'
    r'!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|'
    r'biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|'
    r'ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|'
    r'bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|'
    r'cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|'
    r'fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|'
    r'hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|'
    r'kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|'
    r'ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|'
    r'nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|'
    r'sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|'
    r'td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|'
    r've|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))'
)
URL_RE = re.compile(URL_RE_PATTERN)

DELIMITERS = r'\(\)\[\]\{\}\.\;\,\:\?\!\ \t\r\n\'\"'

MENTION_RE = re.compile(
    r'(?:^|(?<=[{0}]))@(\w{{3,16}})(?:$|(?=[{0}]))'.format(DELIMITERS)
)

HASHTAG_RE = re.compile(
    r'(?:^|(?<=[{0}]))#(\w{{2,32}})(?:$|(?=[{0}]))'.format(DELIMITERS)
)


def parse_links(body):
    """Parses URLs out of a post.

    .. note: This will need to be refined as edge cases are discovered.

    """
    links = URL_RE.finditer(body)

    result = []
    for link in links:
        result.append({
            'link': fix_url(link.group(0)),
            'span': link.span()
        })

    return result


def parse_mentions(body, check_user=True):
    """Parses @mentions out of a post.

    .. note: This will need to be refined as edge cases are discovered.

    """
    mentions = MENTION_RE.finditer(body)

    result = []
    for mention in mentions:
        username = mention.group(1)
        if check_user:
            user_id = get_uid_username(username)
        else:
            user_id = 'NA'

        if user_id:
            result.append({
                'user_id': user_id,
                'username': username,
                'span': mention.span()
            })

    return result


def parse_hashtags(body):
    """Parsed #hashtags out of a post.

    .. note: This will need to be refined as edge cases are discovered.

    """
    hashtags = HASHTAG_RE.finditer(body)

    result = []
    for hashtag in hashtags:
        result.append({
            'hashtag': hashtag.group(1).lower(),
            'span': hashtag.span()
        })

    return result


def parse_post(body):
    """Calls the individual parsers and returns them all in a multiple return
    statement.

    """
    links = parse_links(body)
    mentions = parse_mentions(body)
    hashtags = parse_hashtags(body)

    return links, mentions, hashtags
