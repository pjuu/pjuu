from pjuu import app


@app.template_filter('following')
def following_filter(user_id):
    '''
    Checks if current user is following the user with id piped to filter 
    '''
    pass
