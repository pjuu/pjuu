Endpoints
=========

AUTH
----

/signin                                     GET, POST       NEXT
    signin()

/signout                                    GET
    signout()

/signup                                     GET, POST
    signup()

/signup/<token>                             GET
    activate(token)

/forgot                                     GET, POST
    forgot()

/forgot/<token>                             GET, POST
    reset(token)

/settings/account                           GET
    settings_account()

/settings/change_password                   POST
    change_password()

/settings/change_email                      POST
    change_email()

/settings/change_email/<token>              GET
    change_email_confirm()

/settings/delete_account                    POST
    delete_account()

USERS
-----

/                                           GET             PAGINATION
    feed()

/<username>                                 GET             PAGINATION
    profile(username)

/<username>/followers                       GET             PAGINATION
    followers(username)

/<username>/folowing                        GET             PAGINATION
    following(username)

/<username>/follow                          GET             NEXT
    follow(username)

/<username>/unfollow                        GET             NEXT
    unfollow(username)

/settings/profile                           GET, POST
    settings_profile()

/notifications                              GET             PAGINATION
    notifications()

/search                                     GET, POST       PAGINATION
    search()

POSTS
-----

/post                                       POST
    post()

/<username/<post_id>                        GET             PAGINATION
    view_post(username, post_id)

/<username>/<post_id>/comment               POST            NEXT
    comment(username, post_id)

/<username>/<post_id>/up                    GET             NEXT
/<username>/<post_id>/<comment_id>/up       GET             NEXT
    upvote(username, post_id, comment_id=None)

/<username>/<post_id>/down                  GET             NEXT
/<username>/<post_id>/<comment_id>/down     GET             NEXT
    downvote(username, post_id, comment_id=None)

/<username>/<post_id>/delete                GET             NEXT
/<username>/<post_id>/<comment_id>/delete   GET
    delete_post(username, post_id, comment_id=None)





*NEXT means will redirect to ?next=s if it safe to do so
*PAGINATION means excepts ?page=n for large lists
