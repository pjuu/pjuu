# -*- coding: utf8 -*-

"""Post backend tests.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

import io
import gridfs

from flask import current_app as app

from pjuu import mongo as m, redis as r
from pjuu.auth.backend import create_account, delete_account, activate
from pjuu.auth.utils import get_user
from pjuu.lib import keys as K, timestamp
from pjuu.posts.backend import (
    AlreadyVoted, CantVoteOnOwn, CommentingAlert, SubscriptionReasons,
    TaggingAlert, check_post, create_post, delete_post, get_post, get_posts,
    get_replies, is_subscribed, subscribe, unsubscribe, vote_post,
    get_hashtagged_posts, has_voted)
from pjuu.posts.stats import get_stats
from pjuu.users.backend import (
    follow_user, get_alerts, get_feed, approve_user
)

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
        self.assertEqual(post.get('_id'), post1)
        self.assertEqual(post.get('user_id'), user1)
        self.assertEqual(post.get('body'), 'Test post')
        self.assertEqual(post.get('score'), 0)
        self.assertEqual(post.get('comment_count'), 0)
        # Check the memebers we don't know the answer to
        self.assertIsNotNone(post.get('created'))
        self.assertNotIn('upload', post)

        # Ensure this post is the users feed (populate_feed)
        self.assertIn(post1, r.zrange(K.USER_FEED.format(user1), 0, -1))

        # Testing getting post with invalid arguments
        # Test getting a post that does not exist
        self.assertIsNone(get_post(K.NIL_VALUE))

        # Create a post with an image
        image = io.BytesIO(
            open('tests/upload_test_files/otter.jpg', 'rb').read())
        post2 = create_post(user1, 'user1', 'Test post #2', upload=image)

        self.assertIsNotNone(post2)

        post = get_post(post2)
        self.assertIn('upload', post)
        self.assertIsNotNone(post.get('upload'))

        image = io.BytesIO(
            open('tests/upload_test_files/otter.gif', 'rb').read())
        post3 = create_post(user1, 'user1', 'Test post #2', upload=image)

        self.assertIsNotNone(post3)

        post = get_post(post3)
        self.assertIn('upload', post)
        self.assertIn('upload_animated', post)
        self.assertIsNotNone(post.get('upload'))
        self.assertIsNotNone(post.get('upload_animated'))

        # Create a post with a broken image, ensure it's handled correctly
        image = io.BytesIO()
        post4 = create_post(user1, 'user1', 'Test post #3', upload=image)
        self.assertIsNone(post4)
        post4 = get_post(post4)
        self.assertIsNone(post4)

    def test_approved_feed_population(self):
        """Ensure only approved users get approved posts but in there feed."""
        # Create a user to test creating post
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        user3 = create_account('user3', 'user3@pjuu.com', 'Password')

        follow_user(user2, user1)
        follow_user(user3, user1)
        approve_user(user1, user2)

        create_post(user1, 'user1', 'Test post',
                    permission=K.PERM_APPROVED)

        self.assertEqual(len(get_feed(user2).items), 1)
        self.assertEqual(len(get_feed(user3).items), 0)

    def test_create_reply(self):
        """Test that a reply can be made on a post

        """
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        # Create a second test user to test commenting on someone else post
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        # Create post
        post1 = create_post(user1, 'user1', 'Test post')
        # Create comment
        reply1 = create_post(user1, 'user1', 'Test comment', post1)
        # Check the comment was created
        self.assertIsNotNone(get_post(reply1))
        # Create a comment by the second user
        reply2 = create_post(user2, 'user1', 'Test comment', post1)
        # Check the comment was created
        self.assertIsNotNone(get_post(reply2))

        # Check the comment hash has the data we expect, we will do this with
        # comment1
        comment = get_post(reply1)
        self.assertIsNotNone(comment)
        self.assertEqual(comment.get('_id'), reply1)
        self.assertEqual(comment.get('user_id'), user1)
        self.assertEqual(comment.get('reply_to'), post1)
        self.assertEqual(comment.get('body'), 'Test comment')
        self.assertEqual(comment.get('score'), 0)
        self.assertIsNotNone(comment.get('created'))
        self.assertNotIn('upload', comment)

        # Create a post with an image
        image = io.BytesIO(
            open('tests/upload_test_files/otter.jpg', 'rb').read())
        reply1 = create_post(user1, 'user1', 'Test post #2', reply_to=post1,
                             upload=image)

        self.assertIsNotNone(reply1)

        comment = get_post(reply1)
        self.assertIn('upload', comment)
        self.assertIsNotNone(comment.get('upload'))

        # Create a post with a broken image, ensure it's handled correctly
        image = io.BytesIO()
        reply2 = create_post(user1, 'user1', 'Test post #3', reply_to=post1,
                             upload=image)
        self.assertIsNone(reply2)
        comment = get_post(reply2)
        self.assertIsNone(comment)

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
        self.assertIn(post1, r.zrange(K.USER_FEED.format(user1), 0, -1))

        # Create a second user, make 1 follow them, make then post and ensure
        # that the new users post appears in user 1s feed
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        follow_user(user1, user2)

        post2 = create_post(user2, 'user2', 'Test post')
        # Check user 1's feed for the next item
        self.assertEqual(len(get_feed(user1).items), 2)
        self.assertEqual(get_feed(user1).total, 2)
        # Ensure the item is in Redis
        self.assertIn(post2, r.zrange(K.USER_FEED.format(user1), 0, -1))
        # Delete user 2 and ensure user 1's feed cleans itself
        delete_account(user2)
        self.assertEqual(len(get_feed(user1).items), 1)
        self.assertEqual(get_feed(user1).total, 1)
        # Ensure the item is not in Redis
        self.assertNotIn(post2, r.zrange(K.USER_FEED.format(user1), 0, -1))

    def test_get_feed_pagination_sizes(self):
        """Ensure that getting the feed at different pagination sizes work"""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        user2 = create_account('user2', 'user2@pjuu.com', 'Password')
        follow_user(user1, user2)

        # Create lots of posts so they apear in user1's feed.
        for i in range(101):
            create_post(user2, 'user2', 'Post {}'.format(i))

        FEED_ITEMS_PER_PAGE = app.config.get('FEED_ITEMS_PER_PAGE')

        self.assertEqual(len(get_feed(user1).items), FEED_ITEMS_PER_PAGE)
        self.assertEqual(len(get_feed(user1, per_page=25).items), 25)
        self.assertEqual(len(get_feed(user1, per_page=50).items), 50)
        self.assertEqual(len(get_feed(user1, per_page=100).items), 100)

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

    def test_get_posts_pagination_sizes(self):
        """Ensure get_posts works with various pagination sizes"""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')

        # Create loads of posts
        for i in range(100):
            create_post(user1, 'user1', 'Test post {}'.format(i))

        FEED_ITEMS_PER_PAGE = app.config.get('FEED_ITEMS_PER_PAGE')

        self.assertEqual(len(get_posts(user1).items), FEED_ITEMS_PER_PAGE)
        self.assertEqual(len(get_posts(user1, per_page=25).items), 25)
        self.assertEqual(len(get_posts(user1, per_page=50).items), 50)
        self.assertEqual(len(get_posts(user1, per_page=100).items), 100)

    def test_get_replies(self):
        """Test getting all replies for a post

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

        reply1 = create_post(user1, 'user1', 'Test comment', post1)
        reply2 = create_post(user1, 'user1', 'Test comment', post2)
        reply3 = create_post(user2, 'user2', 'Test comment', post1)
        reply4 = create_post(user2, 'user2', 'Test comment', post2)
        # Ensure each comment appears in each users list
        self.assertEqual(len(get_replies(post1).items), 2)
        self.assertEqual(len(get_replies(post2).items), 2)
        # Ensure the totals are correct
        self.assertEqual(get_replies(post1).total, 2)
        self.assertEqual(get_replies(post2).total, 2)
        # Ensure comments are in MongoDB
        comment_ids = \
            [doc['_id'] for doc in m.db.posts.find({'reply_to': post1})]
        self.assertIn(reply1, comment_ids)
        self.assertIn(reply3, comment_ids)
        comment_ids = \
            [doc['_id'] for doc in m.db.posts.find({'reply_to': post2})]
        self.assertIn(reply2, comment_ids)
        self.assertIn(reply4, comment_ids)

        # Delete 1 comment from post1 and ensure it does not exist
        delete_post(reply1)
        # Check that is has gone
        self.assertEqual(len(get_replies(post1).items), 1)
        self.assertEqual(get_replies(post1).total, 1)

    def test_get_replies_pagination_sizes(self):
        """Ensure get_posts works with various pagination sizes"""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')
        post1 = create_post(user1, 'user1', 'Test post')

        # Create loads of posts
        for i in range(100):
            create_post(user1, 'user1', 'Test post {}'.format(i), post1)

        REPLIES_ITEMS_PER_PAGE = app.config.get('REPLIES_ITEMS_PER_PAGE')

        self.assertEqual(len(get_replies(post1).items), REPLIES_ITEMS_PER_PAGE)
        self.assertEqual(len(get_replies(post1, per_page=25).items), 25)
        self.assertEqual(len(get_replies(post1, per_page=50).items), 50)
        self.assertEqual(len(get_replies(post1, per_page=100).items), 100)

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
        comment1 = create_post(user1, 'user1', 'Test comment', post1)
        comment2 = create_post(user2, 'user2', 'Test comment', post1)

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

        # Get user 3 to downvote
        self.assertEqual(vote_post(user3, post1, amount=-1), -1)
        # Ensure post score has been adjusted
        self.assertEqual(get_post(post1).get('score'), -1)
        # Ensure user score has been adjusted
        self.assertEqual(get_user(user1).get('score'), -1)

        # Check that a user can reverse their vote within TIMEOUT
        self.assertEqual(vote_post(user3, post1, amount=-1), 0)
        self.assertEqual(get_post(post1).get('score'), 0)
        self.assertEqual(get_user(user1).get('score'), 0)

        # Get user 2 to upvote
        self.assertEqual(vote_post(user2, post1), 1)
        # Ensure post score has been adjusted
        self.assertEqual(get_post(post1).get('score'), 1)
        # Ensure user score has been adjusted
        self.assertEqual(get_user(user1).get('score'), 1)

        # Ensure user 1 can not vote on there own post
        self.assertRaises(CantVoteOnOwn, lambda: vote_post(user1, post1))
        # Ensure the scores have not been adjusted
        self.assertEqual(get_post(post1).get('score'), 1)
        self.assertEqual(get_user(user1).get('score'), 1)

        # Ensure the user has voted
        self.assertTrue(has_voted(user2, post1))

        # Check that a user can reverse their vote within TIMEOUT
        self.assertEqual(vote_post(user2, post1), 0)
        self.assertEqual(get_post(post1).get('score'), 0)
        self.assertEqual(get_user(user1).get('score'), 0)

        # Ensure the user has voted
        self.assertFalse(has_voted(user2, post1))

        # Check that the score reflects an opposite vote within TIMEOUT
        self.assertEqual(vote_post(user2, post1, 1), 1)
        self.assertEqual(get_post(post1).get('score'), 1)
        self.assertEqual(get_user(user1).get('score'), 1)

        self.assertTrue(has_voted(user2, post1))

        self.assertEqual(vote_post(user2, post1, -1), -1)
        self.assertEqual(get_post(post1).get('score'), -1)
        self.assertEqual(get_user(user1).get('score'), -1)

        self.assertTrue(has_voted(user2, post1))

        # Check that a user can not reverse there vote after the TIMEOUT
        self.assertRaises(AlreadyVoted,
                          lambda: vote_post(user2, post1, -1,
                                            timestamp() + K.VOTE_TIMEOUT + 1))

        self.assertRaises(AlreadyVoted,
                          lambda: vote_post(user2, post1, 1,
                                            timestamp() + K.VOTE_TIMEOUT + 1))

        # Repeat the same tests on a comment
        # Create a comment by user 1
        comment1 = create_post(user1, 'user1', 'Test comment', post1)

        # Let's cheat and set user1's score back to 0
        m.db.users.update({'_id': user1},
                          {'$set': {'score': 0}})

        # Get user 3 to downvote
        self.assertEqual(vote_post(user3, comment1, amount=-1), -1)
        # Ensure post score has been adjusted
        self.assertEqual(get_post(comment1).get('score'), -1)
        self.assertEqual(get_user(user1).get('score'), -1)

        # Reverse user3's vote just so it's not confusing
        self.assertEqual(vote_post(user3, comment1, amount=-1), 0)
        self.assertEqual(get_post(comment1).get('score'), 0)
        self.assertEqual(get_user(user1).get('score'), 0)

        # Ensure user 1 can not vote on there own comment
        self.assertRaises(CantVoteOnOwn, lambda: vote_post(user1, comment1))
        # Ensure post score has been adjusted
        self.assertEqual(get_post(comment1).get('score'), 0)
        # Ensure user score has been adjusted
        self.assertEqual(get_user(user1).get('score'), 0)

        # Get user 2 to upvote
        self.assertEqual(vote_post(user2, comment1), 1)
        # Ensure post score has been adjusted
        self.assertEqual(get_post(comment1).get('score'), 1)
        # Ensure user score has been adjusted
        self.assertEqual(get_user(user1).get('score'), 1)

        self.assertTrue(has_voted(user2, comment1))

        # Check that a user can reverse their vote within TIMEOUT
        self.assertEqual(vote_post(user2, comment1), 0)
        self.assertEqual(get_post(comment1).get('score'), 0)
        self.assertEqual(get_user(user1).get('score'), 0)

        self.assertFalse(has_voted(user2, comment1))

        # Check that the score reflects an opposite vote within TIMEOUT
        self.assertEqual(vote_post(user2, comment1, -1), -1)
        self.assertEqual(get_post(comment1).get('score'), -1)
        self.assertEqual(get_user(user1).get('score'), -1)

        self.assertTrue(has_voted(user2, comment1))

        self.assertEqual(vote_post(user2, comment1, 1), 1)
        self.assertEqual(get_post(comment1).get('score'), 1)
        self.assertEqual(get_user(user1).get('score'), 1)

        self.assertTrue(has_voted(user2, comment1))

        # Check that a user can not reverse there vote after the TIMEOUT
        self.assertRaises(AlreadyVoted,
                          lambda: vote_post(user2, comment1, -1,
                                            timestamp() + K.VOTE_TIMEOUT + 1))

        self.assertRaises(AlreadyVoted,
                          lambda: vote_post(user2, comment1, 1,
                                            timestamp() + K.VOTE_TIMEOUT + 1))

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
        post1 = create_post(user1, 'user1', 'Test post')
        # Create multiple comments
        reply1 = create_post(user1, 'user1', 'Test comment 1', post1)
        reply2 = create_post(user2, 'user2', 'Test comment 2', post1)
        reply3 = create_post(user1, 'user1', 'Test comment 3', post1)
        reply4 = create_post(user2, 'user2', 'Test comment 4', post1)

        # Check the comment count on post1 is correct
        self.assertEqual(get_post(post1).get('comment_count'), 4)

        # Test deleting one comment
        # This function does not actually test to see if the user has the
        # the rights to delete the post. This should be tested in the frontend
        # Check a comment can be deleted
        self.assertIsNone(delete_post(reply4))

        # Check that getting the comment returns None
        self.assertIsNone(get_post(reply4))

        # Ensure the comment count on post1 is correct
        self.assertEqual(get_post(post1).get('comment_count'), 3)

        # Delete the post. This should delete all the comments, we will check
        self.assertIsNone(delete_post(post1))
        # Check that the post does not exist
        self.assertIsNone(get_post(post1))
        # Check that non of the comments exist
        self.assertIsNone(get_post(reply1))
        self.assertIsNone(get_post(reply2))
        self.assertIsNone(get_post(reply3))

        # Test deleting posts with uploads
        # Ensuring that the images are gone.
        # The actual deleting is tested in 'test_uploads.py'
        image = io.BytesIO(
            open('tests/upload_test_files/otter.jpg', 'rb').read())
        post1 = create_post(user1, 'user1', 'Test post #2', upload=image)
        self.assertIsNotNone(post1)
        post1_filename = get_post(post1).get('upload')

        # Reset the file position in the image
        image.seek(0)
        reply1 = create_post(user1, 'user1', 'Test comment 1', post1,
                             upload=image)
        self.assertIsNotNone(reply1)
        reply1_filename = get_post(reply1).get('upload')

        image.seek(0)
        reply2 = create_post(user2, 'user2', 'Test comment 2', post1,
                             upload=image)
        self.assertIsNotNone(reply2)
        reply2_filename = get_post(reply2).get('upload')

        # Create GridFS file checker
        grid = gridfs.GridFS(m.db, 'uploads')

        # Check that each file exists
        self.assertTrue(grid.exists({'filename': post1_filename}))
        self.assertTrue(grid.exists({'filename': reply1_filename}))
        self.assertTrue(grid.exists({'filename': reply2_filename}))

        self.assertIsNone(delete_post(post1))

        # Check that all the files no longer exist
        self.assertFalse(grid.exists({'filename': post1_filename}))
        self.assertFalse(grid.exists({'filename': reply1_filename}))
        self.assertFalse(grid.exists({'filename': reply2_filename}))

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

        activate(user1)
        activate(user2)
        activate(user3)

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
        create_post(user1, 'user1', 'Test comment', post1)

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
        create_post(user1, 'user1', 'Test comment @user1', post1)

        # Ensure we are subscribed
        self.assertTrue(is_subscribed(user1, post1))

        # Check that our reason HAS changed
        self.assertEqual(r.zscore(K.POST_SUBSCRIBERS.format(post1), user1),
                         SubscriptionReasons.COMMENTER)

        # Create a comment as test2 and ensure this user becomes subscribed for
        # the same reason
        create_post(user2, 'user2', 'Test comment', post1)
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
        create_post(user2, 'user2', 'Test comment @user3', post1)
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

        activate(user1)
        activate(user2)
        activate(user3)

        # User1 tag user2 in a post
        post1 = create_post(user1, 'user1', 'Hello @user2')

        # Get alerts for test2 and check that it is correct
        alert = get_alerts(user2).items[0]
        self.assertTrue(isinstance(alert, TaggingAlert))
        self.assertEqual(alert.user['username'], 'user1')
        self.assertEqual(alert.user['email'], 'user1@pjuu.com')
        self.assertIn('tagged you in a', alert.prettify())

        # Have user2 comment on a the post and check that user1 has the alert
        create_post(user2, 'user2', 'Hello', post1)
        # User 1 should now have a commenting alert from user2
        alert = get_alerts(user1).items[0]
        self.assertTrue(isinstance(alert, CommentingAlert))
        self.assertEqual(alert.user['username'], 'user2')
        self.assertEqual(alert.user['email'], 'user2@pjuu.com')
        # Please remember that prettify requires a uid to format it to
        self.assertIn('commented on a', alert.prettify(user1))
        self.assertIn('you posted', alert.prettify(user1))

        # Create a comment as user3 so they become subscribed
        create_post(user3, 'user3', 'Hello', post1)

        # Check that if user1 posts a comment user2 get a tagging alert
        create_post(user1, 'user1', 'Hello', post1)
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
        r.zincrby(K.POST_SUBSCRIBERS.format(post1), 100, user3)
        # Check the new prettify message
        alert = get_alerts(user3).items[0]
        self.assertTrue(isinstance(alert, CommentingAlert))
        self.assertIn('you are subscribed to', alert.prettify(user3))

    def test_stats(self):
        """Ensure the ``pjuu.posts`` exposed stats are correct

        """
        stats = dict(get_stats())

        self.assertEqual(stats.get('Total posts'), 0)
        self.assertEqual(stats.get('Total uploads'), 0)
        self.assertIsNone(stats.get('Last post'))

        user1 = create_account('user1', 'user1@pjuu.com', 'Password')

        post1 = create_post(user1, 'user1', 'Test post 1')
        create_post(user1, 'user1', 'Test reply 1', post1)

        image = io.BytesIO(
            open('tests/upload_test_files/otter.jpg', 'rb').read())
        create_post(user1, 'user1', 'Test post #2', upload=image)

        stats = dict(get_stats())
        self.assertEqual(stats.get('Total posts'), 3)
        self.assertEqual(stats.get('Total uploads'), 1)
        self.assertIsNotNone(stats.get('Last post'))

    def test_get_hashtagged_posts_pagination_sizes(self):
        """Ensure the correct number of hashtagged posts are returned when
        pagination sizes have been changed.
        """
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')

        # Create loads of posts
        for i in range(100):
            create_post(user1, 'user1', 'Test post {} #test'.format(i))

        FEED_ITEMS_PER_PAGE = app.config.get('FEED_ITEMS_PER_PAGE')

        self.assertEqual(
            len(get_hashtagged_posts('test').items), FEED_ITEMS_PER_PAGE)
        self.assertEqual(
            len(get_hashtagged_posts('test', per_page=25).items), 25)
        self.assertEqual(
            len(get_hashtagged_posts('test', per_page=50).items), 50)
        self.assertEqual(
            len(get_hashtagged_posts('test', per_page=100).items), 100)

    def test_permission_setting(self):
        """Test that a post can have correct permissions set"""
        user1 = create_account('user1', 'user1@pjuu.com', 'Password')

        # Create post with each permission
        post1 = create_post(user1, 'user1', 'Test post', permission=0)
        post2 = create_post(user1, 'user1', 'Test post', permission=1)
        post3 = create_post(user1, 'user1', 'Test post', permission=2)

        post = get_post(post1)
        self.assertEqual(post.get('permission'), 0)

        post = get_post(post2)
        self.assertEqual(post.get('permission'), 1)

        post = get_post(post3)
        self.assertEqual(post.get('permission'), 2)
