#!/usr/bin/env python

from flask import Flask
from flask import request, session, redirect, url_for
from flask import render_template
from flask import g, flash, send_from_directory
from os import path
from md5 import md5
from datetime import datetime
import time
from contextlib import closing
from werkzeug import secure_filename
from PIL import Image
import sqlite3

# configuration
DATABASE = 'samplereg.db'
DEBUG = True
TRAP_BAD_REQUEST_KEY_ERRORS = True
TRAP_HTTP_EXCEPTIONS = True
SECRET_KEY = 'OMG so secret'
USERNAME = 'admin'
PASSWORD = 'default'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
VALID_IDENTIFIERS = 'ids.txt'
THUMB_SIZE = 128
#SERVER_NAME = '/samplereg'

app = Flask(__name__)
app.config.from_object(__name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

def make_thumbnail( infile ) :
    """
    Take a path to an image file, and make a thumbnail sized verson of
    it.
    """
    size = app.config['THUMB_SIZE'],  app.config['THUMB_SIZE']
    file, ext = path.splitext(infile)
    im = Image.open(infile)
    im.thumbnail(size, Image.ANTIALIAS)
    thumb_filename = file + "_thumb.png"
    im.save( thumb_filename, "PNG")
    return thumb_filename

def get_user( username ) :
    """
    Get the details on a user.
    """
    cur = g.db.execute('select username, password, realname, city, state, country, team, avatar, thumb from users where username = ? order by id desc', (username,) )
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
                    avatar      = row[7],
                    thumb       = row[8] )
    return user

def get_user_records( username ) :
    """
    Get summary information for records registered by a user.
    """
    cur = g.db.execute('select identifier, date, name, description, context_thumb, audited from records where user = ? order by id desc', (username,) )
    rows = cur.fetchall()
    records = []
    
    # bag 'em up
    for row in rows :
        record = dict(  identifier  = row[0],
                        date        = row[1],
                        name        = row[2],
                        description = row[3],
                        thumb       = row[4],
                        audited     = row[5] )
        records.append(record)
    
    return records

def add_user( form ) :
    """
    Create a new user in the database.
    """
    # save the user's avatar file
    file = request.files['avatar']
    if file and allowed_file( file.filename ) :
        ext = file.filename.split('.')[-1]
        filename = secure_filename( form['username'] + '.' + ext )
        file_path = path.join( app.config['UPLOAD_FOLDER'], filename )
        file.save( file_path )
        thumb_path = make_thumbnail( file_path )
    else :
        return False

    values = (  form['username'], 
                md5( form['password'] ).hexdigest(),
                form['realname'],
                form['city'], form['state'], form['country'], 
                form['team'], file_path, thumb_path )   
    # SQL is gross
    g.db.execute('insert into users (username, password, realname, city, state, country, team, avatar, thumb) values (?,?,?,?,?,?,?,?,?)', values )
    g.db.commit()

def add_record( user, form ) :
    """
    Register a new record.
    """
    app.logger.debug( request.files['context'].filename )
    # make sure submitted identifier is in our allowed list
    # return False otherwise
    ids = open( app.config['VALID_IDENTIFIERS'] ).read().strip().split('\n')
    if not ids.__contains__(form['identifier']) :
        return False

    # save the photos
    photos = { 'context' : '', 'closeup' : '' }
    thumbs = { 'context' : '', 'closeup' : '' }
    for photo in photos.keys() :
        file = request.files[photo]
        if file and allowed_file( file.filename ) :
            ext = file.filename.split('.')[-1]
            filename = secure_filename( form['identifier'] + '_' + photo + '.' + ext )
            file_path = path.join( app.config['UPLOAD_FOLDER'], filename )
            file.save( file_path )
            thumbs[photo] = make_thumbnail( file_path )
            photos[photo] = file_path
        else :
            return False
   
    # all new records are created with audited=False
    values = (  form['identifier'],
                user['username'],
                int(time.time()),
                float(form['lat']),
                float(form['lng']),
                form['surface_material'],
                form['surface_condition'],
                form['surface_humidity'],
                form['context_type'],
                form['inorout'],
                bool(form['direct_sunlight']),
                float(form['temp']),
                photos['closeup'],
                thumbs['closeup'],
                photos['context'],
                thumbs['context'],
                form['name'],
                form['description'],
                False )
    g.db.execute('insert into records (identifier, user, date, lat, lng, surface_material, surface_condition, surface_humidity, context_type, inorout, direct_sunlight, temp, closeup, closeup_thumb, context, context_thumb, name, description, audited) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', values )
    g.db.commit()
    return True

def valid_login( username, password ) :
    """
    Check to see if a user's submitted password matches the stored
    hash.
    """
    p = md5( password ).hexdigest()
    user = get_user( username )
    if user and user['password'] == p :
        return True
    else :
        return False

# uploaded content
#@app.route('/<path:filename>')
#def uploads(filename):
#    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route( '/' )
def index() :
    """
    The application root.
    """
    if 'username' in session :
        return render_template( 'index.html', 
                                username=session['username'],
                                authenticated = True )
    else :
        return render_template( 'index.html' )

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
    """
    Sign up a new user.
    """
    if request.method == 'POST' :
        username = request.form['username']
        add_user( request.form )
        flash( 'New user added' )
        session['username'] = username
        return redirect( url_for( 'profile', username=username ) )
    else :
        if 'username' in session :
            return render_template( 'signup.html',
                                    username = session['username'],
                                    authenticated = True )
        else :
            return render_template( 'signup.html' )

@app.route( '/register', methods = ['GET', 'POST'] )
def register() :
    """
    Register a new sample.
    """
    if request.method == 'POST' :
        username = session['username']
        if not 'username' in session :
            return 'You must create an account to register samples!'
        else :
            user = get_user( username )
            result = add_record( user, request.form )
            if not result :
                return 'Something went wrong. Sample not registered.'
            else :
                return redirect( url_for( 'profile', username=username ) )
    else :
        if 'username' in session :
            return render_template( 'register.html',
                                    username = session['username'],
                                    authenticated = True )
        else :
            return render_template( 'register.html' )

@app.route( '/user/<username>' )
def profile( username ) :
    """
    The user profile page.
    """
    user = get_user( username )
    
    if not user :
        return 'User does not exist.'
    else :
        records = get_user_records( username )
        if 'username' in session :
            return render_template( 'profile.html', 
                                    user = user,
                                    records = records,
                                    authenticated = True )
        else :
            return render_template( 'profile.html',
                                    user = user,
                                    records = records ) 

@app.route( '/favicon.ico' )
def favicon() :
    return redirect( url_for( 'static', filename='favicon.ico' ) )

if __name__ == '__main__' :
    app.debug = True
    app.run()


