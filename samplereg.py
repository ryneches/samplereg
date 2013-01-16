#!/usr/bin/env python

from flask import Flask
from flask import request, session, redirect, url_for
from flask import render_template
from md5 import md5

app = Flask(__name__)

app.secret_key = 'OMG so secret.'

users = []
users.append( { 'username' : 'test', 
                'password' : 'acbd18db4cc2f85cedef654fccc4a4d8' } )

def valid_login( username, password ) :
    p = md5( password ).hexdigest()
    for user in users :
        if user['username'] == username and user['password'] == p :
            return True
    return False

@app.route( '/' )
def index() :
    if 'username' in session :
        return 'The index page. You\'re logged in as ' + session['username']
    else :
        return 'The index page. You\'re not logged in.'

@app.route( '/login', methods = ['GET', 'POST'] )
def login() :
    '''
    Handle login requests.
    '''
    if request.method == 'POST' :
        username = request.form['username']
        password = request.form['password']
        if valid_login( username, password ) :
            session['username'] = username
            return redirect(url_for('profile', username=username ))
        else :
            return 'who are you again?'
    else : 
        return render_template( 'login.html' )

@app.route( '/logout' )
def logout() :
    '''
    Log the user out.
    '''
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route( '/user/<username>' )
def profile( username ) :
    if 'username' in session :
        return render_template( 'profile.html', 
                                username = username,
                                authenticated = True )
    else :
        return render_template( 'profile.html', 
                                username = username )

if __name__ == '__main__' :
    app.debug = True
    app.run()


