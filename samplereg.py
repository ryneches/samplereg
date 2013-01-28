#!/usr/bin/env python

from flask import Flask
from flask import request, session, redirect, url_for
from flask import render_template
from flask import g, flash
from os import path
from md5 import md5
from datetime import datetime
from contextlib import closing
from werkzeug import secure_filename
import sqlite3

# configuration
DATABASE = 'samplereg.db'
DEBUG = True
SECRET_KEY = 'OMG so secret'
USERNAME = 'admin'
PASSWORD = 'default'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)
app.config.from_object(__name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    """Create new database tables"""
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    g.db.close()

def get_user( username ) :
    cur = g.db.execute('select username, password, realname, city, state, country, team, avatar from users where username = ? order by id desc', (username,) )
    row = cur.fetchone()
    
    # the user isn't in the database
    if not row :
        return False
    
    # bag it up
    user = dict(    username    = row[0],
                    password    = row[1],
                    realname    = row[2],
                    city        = row[3],
                    state       = row[4],
                    country     = row[5],
                    team        = row[6],
                    avatar      = row[7] )
    return user

def get_user_records( username ) :
    cur = g.db.execute('select identifier, date, name, description, audited from records where user = ? order by id desc', (username,) )
    rows = cur.fetchall()
    records = []
    
    # bag 'em up
    for row in rows :
        record = dict(  identifer   = row[0],
                        date        = row[1],
                        name        = row[2],
                        description = row[3],
                        audited     = row[4] )
        records.append(record)
    
    return records

def add_user( form, avatar_path ) :
    values = (  form['username'], 
                md5( form['password'] ).hexdigest(),
                form['realname'],
                form['city'], form['state'], form['country'], 
                form['team'], avatar_path )   
    # SQL is gross
    g.db.execute('insert into users (username, password, realname, city, state, country, team, avatar) values (?,?,?,?,?,?,?,?)', values )
    g.db.commit()

def valid_login( username, password ) :
    p = md5( password ).hexdigest()
    user = get_user( username )
    if user and user.password == p :
        return True
    else :
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

@app.route( '/signup', methods = ['GET', 'POST'] )
def signup() :
    if request.method == 'POST' :
        file = request.files['file']
        if file and allowed_file( file.filename ) :
            filename = secure_filename( file.filename )
            avatar_path = path.join( app.config['UPLOAD_FOLDER'], filename )
            file.save( avatar_path )
        add_user( request.form, avatar_path )
        flash( 'New user added' )
        return redirect( url_for( 'profile', username=request.form['username'] ) )
    else :
        return render_template( 'signup.html' )

@app.route( '/user/<username>' )
def profile( username ) :
    
    user = get_user( username )
    
    if not user :
        
        return 'User does not exist.'
        
    else :
    
        records = get_user_records( username )
        if 'username' in session :
            return render_template( 'profile.html', 
                                    username = username,
                                    records = records,
                                    authenticated = True )
        else :
            return render_template( 'profile.html',
                                    records = records, 
                                    username = username )

if __name__ == '__main__' :
    app.debug = True
    app.run()


