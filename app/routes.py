from app import myapp

@myapp.route('/')
@myapp.route('/index')
def index():
    user = {'username': 'Tua'}
    return '''
<html>
    <head>
        <title>Home Page - Microblog</title>
    </head>
    <body>
        <h1>Hi, ''' + user['username'] + '''!</h1>
        <p>We are so glad to see you</p> <!-- A paragraph -->
        <h1>Bye, ''' + user['username'] + '''!</h1>
    </body>
</html>'''