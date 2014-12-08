# -*- coding: utf8 -*-

"""
Description:
    Posts package unit tests

Licence:
    Copyright 2014 Joe Doherty <joe@pjuu.com>

    Pjuu is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Pjuu is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# Pjuu imports
from pjuu import redis as r
from pjuu.auth.backend import create_account, get_user
from pjuu.lib import keys as K
from pjuu.posts.backend import *
from pjuu.users.backend import get_alerts
# Tests imports
from tests import BackendTestCase


class PostBackendTests(BackendTestCase):
    """This case will test ALL post backend functions.

    """

    def test_create_post(self):
        """Tests creating and getting a post

        """
        # Create a user to test creating post
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        # Create post
        post1 = create_post(user1, 'user1', 'Test post')
        # Check the post actually exists
        self.assertIsNotNone(post1)

        # Check that all the hash members are what we expect
        post = get_post(post1)
        self.assertIsNotNone(post)
        self.assertEqual(post.get('pid'), post1)
        self.assertEqual(post.get('uid'), user1)
        self.assertEqual(post.get('body'), 'Test post')
        self.assertEqual(post.get('score'), 0)
        self.assertEqual(post.get('comment_counet'), 0)
        # Check the memebers we don't know the answer to
        self.assertIsNotNone(post.get('created'))

        # Ensure the post gets added to the users 'posts' list
        # Remember redis returns everything as a string
        self.assertIn(post1, r.lrange(K.USER_POSTS.format(user1), 0, -1))
        # Ensure this post is the users feed (populate_feed)
        self.assertIn(post1, r.lrange(K.USER_FEED.format(user1), 0, -1))

        # Testing getting post with invalid arguments
        # Test getting a post that does not exist
        self.assertIsNone(get_post(K.NIL_VALUE))

    def test_create_comment(self):
        """
        Tests that a comment can be created on a post
        """
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        # Create a second test user to test commenting on someone else post
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        # Create post
        post1 = create_post(user1, 'user1', 'Test post')
        # Create comment
        comment1 = create_comment(user1, 'user1', post1, 'Test comment')
        # Check the comment was created
        self.assertIsNotNone(get_comment(comment1))
        # Create a comment by the second user
        comment2 = create_comment(user2, 'user1', post1, 'Test comment')
        # Check the comment was created
        self.assertIsNotNone(get_comment(comment2))
        # Ensure the comment is the posts 'comment' list and that the comment
        # is in the users 'comment' list
        self.assertIn(comment1, r.lrange(K.POST_COMMENTS.format(post1), 0, -1))
        # Ensure the comment is also in the users 'comments' list
        self.assertIn(comment1, r.lrange(K.USER_COMMENTS.format(user1), 0, -1))
        # Ensure the same applies for the second users post
        self.assertIn(comment2, r.lrange(K.POST_COMMENTS.format(post1), 0, -1))
        # Ensure the comment is also in the users 'comments' list
        self.assertIn(comment2, r.lrange(K.USER_COMMENTS.format(user2), 0, -1))

        # Check the comment hash has the data we expect, we will do this with
        # comment1
        comment = get_comment(comment1)
        self.assertIsNotNone(comment)
        self.assertEqual(comment.get('cid'), comment1)
        self.assertEqual(comment.get('uid'), user1)
        self.assertEqual(comment.get('pid'), post1)
        self.assertEqual(comment.get('body'), 'Test comment')
        self.assertEqual(comment.get('score'), '0')
        self.assertEqual(comment.get('post_author'), 'user1')
        self.assertIsNotNone(comment.get('created'))

    def test_get_feed(self):
        """
        Attempt to get a users feed under certain circumstances.
        """
        # Get test user
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        # Ensure an empty feed is returned. Remember these are paginations
        self.assertEqual(len(get_feed(user1).items), 0)
        # Ensure a users own post is added to thier feed
        post1 = create_post(user1, 'user1', 'Test post')
        # Ensure the list is the correct length
        self.assertEqual(len(get_feed(user1).items), 1)
        self.assertEqual(get_feed(user1).total, 1)
        # Ensure the item is in Redis
        self.assertIn(post1, r.lrange(K.USER_FEED.format(user1), 0, -1))

        # Create a second user, make 1 follow them, make then post and ensure
        # that the new users post appears in user 1s feed
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        follow_user(user1, user2)

        post2 = create_post(user2, 'user2', 'Test post')
        # Check user 1's feed for the next item
        self.assertEqual(len(get_feed(user1).items), 2)
        self.assertEqual(get_feed(user1).total, 2)
        # Ensure the item is in Redis
        self.assertIn(post2, r.lrange(K.USER_FEED.format(user1), 0, -1))
        # Delete user 2 and ensure user 1's feed cleans itself
        delete_account(user2)
        self.assertEqual(len(get_feed(user1).items), 1)
        self.assertEqual(get_feed(user1).total, 1)
        # Ensure the item is not in Redis
        self.assertNotIn(post2, r.lrange(K.USER_FEED.format(user1), 0, -1))

    def test_get_posts(self):
        """
        Test users post list works correctly
        """
        # Create test user
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        # Ensure the users post list is empty
        self.assertEqual(len(get_posts(user1).items), 0)

        # Create a few test posts, ensure they appears in the users list
        post1 = create_post(user1, 'user1', 'Test post 1')
        post2 = create_post(user1, 'user1', 'Test post 2')
        create_post(user1, 'user1', 'Test post 3')
        self.assertEqual(len(get_posts(user1).items), 3)
        self.assertEqual(get_posts(user1).total, 3)

        # Delete one of the posts and ensure that it does not appear in the
        # list.
        delete_post(post1)

        # Ensure the above is now correct with post1 missing
        self.assertEqual(len(get_posts(user1).items), 2)
        self.assertEqual(get_posts(user1).total, 2)

        # Delete a post from MongoDB with the driver
        m.db.posts.remove({'_id': post2})
        # Ensure the above is now correct with post2 missing
        self.assertEqual(len(get_posts(user1).items), 1)
        self.assertEqual(get_posts(user1).total, 1)

        # Done

    def test_get_comments(self):
        """
        Ensure a posts comments are stored correctly in post:$pid:comments list
        """
        # Create two test users
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        # Create a post for each user and a comment on each for both user
        post1 = create_post(user1, 'user1', 'Test post')
        post2 = create_post(user2, 'user2', 'Test post')
        # Ensure the comment lists are empty
        self.assertEqual(len(get_replies(post1).items), 0)
        self.assertEqual(len(get_replies(post2).items), 0)

        comment1 = create_post(user1, 'user1', post1, 'Test comment')
        comment2 = create_post(user1, 'user1', post2, 'Test comment')
        comment3 = create_post(user2, 'user2', post1, 'Test comment')
        comment4 = create_post(user2, 'user2', post2, 'Test comment')
        # Ensure each comment appears in each users list
        self.assertEqual(len(get_replies(post1).items), 2)
        self.assertEqual(len(get_replies(post2).items), 2)
        # Ensure the totals are correct
        self.assertEqual(get_replies(post1).total, 2)
        self.assertEqual(get_replies(post2).total, 2)
        # Ensure comments are in MongoDB
        comment_ids = \
            [doc['_id'] for doc in m.db.comments.find({'pid': post1})]
        self.assertIn(comment1, comment_ids)
        self.assertIn(comment3, comment_ids)
        comment_ids = \
            [doc['_id'] for doc in m.db.comments.find({'pid': post2})]
        self.assertIn(comment2, comment_ids)
        self.assertIn(comment4, comment_ids)

        # Delete 1 comment from post1 and ensure it does not exist
        delete_post(comment1)
        # Check that is has gone
        self.assertEqual(len(get_replies(post1).items), 1)
        self.assertEqual(get_replies(post1).total, 1)

        # Delete a comment from inside Redis. This will trigger the self
        # cleaning list feature. We call these orphaned cids.
        delete_post(comment3)
        # Check that it has gone when get_comments is called
        self.assertEqual(len(get_replies(post2).items), 1)
        self.assertEqual(get_replies(post2).total, 1)

    def test_check_post(self):
        """
        Will test that check_post returns the correct value with various
        combinations.

        Note: Bare with this one it is quite tedious.
        """
        # Create two test users
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        # Create a post
        post1 = create_post(user1, 'user1', 'Test post')
        # check_post should be True when user 1 creates post 1
        self.assertTrue(check_post(user1, post1))
        # check_post should be false, user 2 didn't create post 1
        self.assertFalse(check_post(user2, post1))
        # Create a couple of comments
        comment1 = create_comment(user1, 'user1', post1, 'Test comment')
        comment2 = create_comment(user2, 'user2', post1, 'Test comment')

        # Ensure the check_post is fine for all
        self.assertTrue(check_post(user1, post1, comment1))
        # This does not look correct but is. See backend.py@check_post
        self.assertTrue(check_post(user1, post1, comment1))

        # Ensure the function isn't broken on comments
        self.assertFalse(check_post(user2, post1, comment1))
        self.assertFalse(check_post(user1, K.NIL_VALUE, comment1))
        self.assertFalse(check_post(user2, K.NIL_VALUE, comment2))

    def test_votes(self):
        """
        Test that the voting mechanism will adjust the relevant score counters
        on users, posts and comments, etc...
        """
        # Create three test users
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        user3 = create_account('user3', 'user3@pjuu.com', 'Password')

        # Create a post by user 1
        post1 = create_post(user1, 'user1', 'Test post')

        # Get user 3 to downvote, this will test that the user can not go
        # negative yet the post can
        self.assertIsNone(vote_post(user3, post1, amount=-1))
        # Ensure post score has been adjusted
        self.assertEqual(get_post(post1).get('score'), '-1')
        # Ensure user score has NOT been adjusted
        self.assertEqual(get_user(user1).get('score'), '0')

        # Get user 2 to upvote
        self.assertIsNone(vote_post(user2, post1))
        # Ensure post score has been adjusted
        self.assertEqual(get_post(post1).get('score'), '0')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(user1).get('score'), '1')

        # Ensure user 1 can not vote on there own post
        self.assertRaises(CantVoteOnOwn, lambda: vote_post(user1, post1))
        # Ensure the scores have not been adjusted
        self.assertEqual(get_post(post1).get('score'), '0')
        self.assertEqual(get_user(user1).get('score'), '1')

        # Check to see if a user can vote twice on a post
        self.assertRaises(AlreadyVoted, lambda: vote_post(user2, post1))
        # Ensure the scores have not been adjusted
        self.assertEqual(get_post(post1).get('score'), '0')
        self.assertEqual(get_user(user1).get('score'), '1')

        # Repeat the same tests on a comment
        # Create a comment by user 1
        comment1 = create_comment(user1, 'user1', post1, 'Test comment')

        # Let's cheat and set user1's score back to 0 so we can check it will
        # not be lowered in the user3 downvote
        r.hset(K.USER.format(user1), 'score', 0)

        # Get user 3 to downvote
        self.assertIsNone(vote_comment(user3, comment1, amount=-1))
        # Ensure post score has been adjusted
        self.assertEqual(get_comment(comment1)['score'], '-1')
        # Ensure user score has NOT been adjusted
        self.assertEqual(get_user(user1)['score'], '0')

        # Get user 2 to upvote
        self.assertIsNone(vote_comment(user2, comment1))
        # Ensure post score has been adjusted
        self.assertEqual(get_comment(comment1).get('score'), '0')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(user1).get('score'), '1')

        # Ensure user 1 can not vote on there own comment
        self.assertRaises(CantVoteOnOwn, lambda: vote_comment(user1, comment1))
        # Ensure post score has been adjusted
        self.assertEqual(get_comment(comment1).get('score'), '0')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(user1).get('score'), '1')

        # Check to see if a user can vote twice on a comment
        self.assertRaises(AlreadyVoted, lambda: vote_comment(user2, comment1))
        # Ensure post score has been adjusted
        self.assertEqual(get_comment(comment1).get('score'), '0')
        # Ensure user score has been adjusted
        self.assertEqual(get_user(user1).get('score'), '1')

    def test_delete(self):
        """
        Tests delete_post() does what it should.
        This will in turn test delete_comments() as this will be triggered when
        a post is deleted.
        """
        # Create three test users
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')

        # Create a post
        post1 = create_post(user1, 'Test post')
        # Create multiple comments
        comment1 = create_comment(user1, 'user1', post1, 'Test comment 1')
        comment2 = create_comment(user2, 'user2', post1, 'Test comment 2')
        comment3 = create_comment(user1, 'user1', post1, 'Test comment 3')
        comment4 = create_comment(user2, 'user2', post1, 'Test comment 4')

        # Test deleting one comment
        # This function does not actually test to see if the user has the
        # the rights to delete the post. This should be tested in the frontend
        # Check a comment can be deleted
        self.assertIsNone(delete_comment(comment4))
        # Check that getting the comment returns None
        self.assertIsNone(get_comment(comment4))
        # Ensure the comment is no longer in the posts comment list and no
        # longer in the users comment list (that comment was by user2)
        self.assertNotIn(comment4,
                         r.lrange(K.POST_COMMENTS.format(post1), 0, -1))
        self.assertNotIn(comment4,
                         r.lrange(K.USER_COMMENTS.format(user2), 0, -1))

        # Just ensure that the previous comment is in user 2's comment list
        # and inside the post list
        self.assertIn(comment2, r.lrange(K.POST_COMMENTS.format(post1), 0, -1))
        self.assertIn(comment2, r.lrange(K.USER_COMMENTS.format(user2), 0, -1))

        # Delete the post. This should delete all the comments, we will check
        self.assertIsNone(delete_post(post1))
        # Check that the post does not exist
        self.assertIsNone(get_post(post1))
        # Check that non of the comments exist
        self.assertIsNone(get_comment(comment1))
        self.assertIsNone(get_comment(comment2))
        self.assertIsNone(get_comment(comment3))
        # Ensure that the posts comment list has been deleted
        self.assertFalse(r.exists(K.POST_COMMENTS.format(post1)))
        # Ensure that non of the comments appear in the users comments lists
        self.assertNotIn(comment1,
                         r.lrange(K.USER_COMMENTS.format(user1), 0, -1))
        self.assertNotIn(comment2,
                         r.lrange(K.USER_COMMENTS.format(user2), 0, -1))
        self.assertNotIn(comment3,
                         r.lrange(K.USER_COMMENTS.format(user1), 0, -1))

    def test_subscriptions(self):
        """
        Test the backend subscription system.

        This includes subscribe(), unsubscribe() and is_subscribed().

        This will also test the correct subscriptions after a post, comment or
        tagging.
        """
        # Create a couple of test accounts
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        user3 = create_account('user3', 'user3@pjuu.com', 'Password')

        # Post as user 1 and ensure user 1 exists in Redis
        post1 = create_post(user1, 'user1', 'Test post 1')
        self.assertIsNotNone(r.zrank(K.POST_SUBSCRIBERS.format(post1), user1))

        # Even though it is exactly the same as the above ensure that
        # is_subscribed() returns True
        self.assertTrue(is_subscribed(user1, post1))
        # Lets ensure this actually fails! And see if user2 is a subscriber
        self.assertFalse(is_subscribed(user2, post1))

        # Ensure that the REASON (zset score) is set to the correct value
        self.assertEqual(r.zscore(K.POST_SUBSCRIBERS.format(post1), user1),
                         SubscriptionReasons.POSTER)

        # Post a comment as user 1 and ensure the reason does NOT changes
        create_comment(user1, 'user1', post1, 'Test comment')

        # Ensure our reason did not change
        # If we were not subscribed we would be given reason 2 (COMMENTER)
        self.assertNotEqual(r.zscore(K.POST_SUBSCRIBERS.format(post1), user1),
                            SubscriptionReasons.COMMENTER)

        # Test unsubscribe
        self.assertTrue(unsubscribe(user1, post1))
        # Ensure that is_subscribed shows correct
        self.assertFalse(is_subscribed(user1, post1))
        # Test that if we unsubscribe again we get a False result
        self.assertFalse(unsubscribe(user1, post1))
        # Check that unsubscribing some that was never subscribed returns false
        self.assertFalse(unsubscribe(user2, post1))

        # Let's test that commenting subscribes us to the post with the correct
        # reason. Try tag yourself at the same time
        create_comment(user1, 'user1', post1, 'Test comment @user1')

        # Ensure we are subscribed
        self.assertTrue(is_subscribed(user1, post1))

        # Check that our reason HAS changed
        self.assertEqual(r.zscore(K.POST_SUBSCRIBERS.format(post1), user1),
                         SubscriptionReasons.COMMENTER)

        # Create a comment as test2 and ensure this user becomes subscribed for
        # the same reason
        create_comment(user2, 'user2', post1, 'Test comment')
        self.assertTrue(is_subscribed(user2, post1))
        self.assertEqual(r.zscore(K.POST_SUBSCRIBERS.format(post1), user2),
                         SubscriptionReasons.COMMENTER)

        # Create a new post as test1 and tag test2 and test3 in it
        # ensure all 3 are subscribed and test2 and test3 have the correct
        # reason.
        # Also try and tag ourselves this should have no affect
        # Try tagging someone that does not even exist
        post2 = create_post(user1, 'user1',
                            'Test post @user1 @user2 @user3 @user4')
        self.assertTrue(is_subscribed(user2, post2))
        self.assertTrue(is_subscribed(user3, post2))
        self.assertEqual(r.zscore(K.POST_SUBSCRIBERS.format(post2), user2),
                         SubscriptionReasons.TAGEE)
        self.assertEqual(r.zscore(K.POST_SUBSCRIBERS.format(post2), user3),
                         SubscriptionReasons.TAGEE)

        # Test tagging user 3 in a comment on post1. This ensures that tags
        # in comments do work.
        create_comment(user2, 'user2', post1, 'Test comment @user3')
        self.assertTrue(is_subscribed(user3, post1))
        self.assertEqual(r.zscore(K.POST_SUBSCRIBERS.format(post1), user3),
                         SubscriptionReasons.TAGEE)

        # Unsubscribe user2 and user3
        self.assertTrue(unsubscribe(user2, post2))
        self.assertFalse(is_subscribed(user2, post2))
        self.assertTrue(unsubscribe(user3, post2))
        self.assertFalse(is_subscribed(user3, post2))

        # Ensure that subscribe doe not happen when it is not a valid post
        self.assertFalse(subscribe(user1, K.NIL_VALUE,
                                   SubscriptionReasons.POSTER))

    def test_alerts(self):
        """
        Unlike the test_alerts() definition in the users package this just
        tests that TaggingAlert and CommentingAlert are generated in the right
        situation
        """
        # Create 3 test users
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        user3 = create_account('user3', 'user3@pjuu.com', 'Password')
        # No need to activate the accounts

        # User1 tag user2 in a post
        post1 = create_post(user1, 'user1', 'Hello @user2')

        # Get alerts for test2 and check that it is correct
        alert = get_alerts(user2).items[0]
        self.assertTrue(isinstance(alert, TaggingAlert))
        self.assertEqual(alert.get_username(), 'user1')
        self.assertEqual(alert.get_email(), 'user1@pjuu.com')
        self.assertIn('tagged you in a', alert.prettify())

        # Have user2 comment on a the post and check that user1 has the alert
        create_comment(user2, 'user2', post1, 'Hello')
        # User 1 should now have a commenting alert from user2
        alert = get_alerts(user1).items[0]
        self.assertTrue(isinstance(alert, CommentingAlert))
        self.assertEqual(alert.get_username(), 'user2')
        self.assertEqual(alert.get_email(), 'user2@pjuu.com')
        # Please remember that prettify requires a uid to format it too
        self.assertIn('commented on a', alert.prettify(user1))
        self.assertIn('you posted', alert.prettify(user1))

        # Create a comment as user3 so they become subscribed
        create_comment(user3, 'user3', post1, 'Hello')

        # Check that if user1 posts a comment user2 get a tagging alert
        create_comment(user1, 'user1', post1, 'Hello')
        # Check alerts for user2
        alert = get_alerts(user2).items[0]
        self.assertTrue(isinstance(alert, CommentingAlert))
        self.assertIn('you were tagged in', alert.prettify(user2))
        # Check alerts for user3
        alert = get_alerts(user3).items[0]
        self.assertTrue(isinstance(alert, CommentingAlert))
        self.assertIn('you commented on', alert.prettify(user3))

        # To check that an invalid subscription reason returns the generic
        # reason. This should not happen on the site.
        # Manually change the score in Redis to a high number
        r.zincrby(K.POST_SUBSCRIBERS.format(post1), user3, 100)
        # Check the new prettify message
        alert = get_alerts(user3).items[0]
        self.assertTrue(isinstance(alert, CommentingAlert))
        self.assertIn('you are subscribed too', alert.prettify(user3))

        # Done for now
