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
DEFAULT_AVATAR = 'shanana.png'
VALID_IDENTIFIERS = 'ids.txt'
THUMB_SIZE = 128
#SERVER_NAME = '/samplereg'

app = Flask(__name__)
app.config.from_object(__name__)

class RegistrationException(Exception) :
    pass

class UserException(Exception) :
    pass

class ImageException(Exception) :
    pass

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
    # check that the user actually filled out the form
    if not form['username'] or          \
       not form['realname'] or          \
       not form['password'] or          \
       not form['password_check'] or    \
       not form['team'] :
        raise UserException( 'Looks like you\'re not done filling out the form!' )
    
    # check that the passwords match
    if not form['password'] == form['password_check'] :
        raise UserException( 'Those passwords don\'t match!' )
    
    # check to see if the user already exists
    if get_user( form['username'] ) :
        raise UserException( 'This user already exists!' )
    
    # try to save the user's avatar file, or use the default one
    if request.files['avatar'] :
        file = request.files['avatar']
        
        # check that it's an allowed file type
        if not allowed_file( file.filename ) :
            raise UserException( 'This image file type is not supported.' )
        ext = file.filename.lower().split('.')[-1]
        filename = secure_filename( form['username'] + '.' + ext )
        file_path = path.join( app.config['UPLOAD_FOLDER'], filename )
        file.save( file_path )
    else :
        file_path = path.join( app.config['UPLOAD_FOLDER'], app.config['DEFAULT_AVATAR'] )
    
    thumb_path = make_thumbnail( file_path )
    
    values = (  form['username'], 
                md5( form['password'] ).hexdigest(),
                form['realname'],
                form['city'], form['state'], form['country'], 
                form['team'], file_path, thumb_path )   
    
    # SQL is gross
    g.db.execute('insert into users (username, password, realname, city, state, country, team, avatar, thumb) values (?,?,?,?,?,?,?,?,?)', values )
    g.db.commit()

def update_avatar( username, file ) :
    
    # check that it's an allowed file type
    if not allowed_file( file.filename ) :
        raise UserException( 'This image file type is not suppported.' )
    ext = file.filename.lower().split('.')[-1]
    filename = secure_filename( username + '.' + ext )
    file_path = path.join( app.config['UPLOAD_FOLDER'], filename )
    file.save( file_path )
    thumb_path = make_thumbnail( file_path )
    values = ( file_path, thumb_path, username )
    g.db.execute('update users set avatar=? and thumb=? where username=?', values )
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
        raise RegistrationException( 'Unknown sample identifier.' )

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
            raise RegistrationException( 'Something is wrong with the ' + photo + ' photo.' )
   
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
            flash( 'Who are you again?', 'alert-error' )
            return redirect( url_for( 'login' ) )
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
        try :
            add_user( request.form )
        except UserException as e :
            flash( e.message, 'alert-error' )
            return redirect( url_for( 'signup' ) )
        flash( 'New user added', 'alert-success' )
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
    if not 'username' in session :
        flash( 'You must create an account to register samples!', 'alert-error' )
        return redirect( url_for( 'index' ) )
    
    username = session['username']
    if request.method == 'POST' :
        user = get_user( username )
        result = add_record( user, request.form )
        if not result :
            flash( 'Something has gone wrong. Sample not registered.', 'alert-error' )
            return redirect( url_for( 'register') )
        else :
            flash( 'Sample ' + request.form['identifier'] + ' registered!', 'alert-success' )
            return redirect( url_for( 'profile', username=username ) )
    else :
        if 'username' in session :
            return render_template( 'register.html',
                                    username = session['username'],
                                    authenticated = True )
        else :
            return render_template( 'register.html' )

@app.route( '/newavatar', methods = ['POST'] )
def newavatar() :
    """
    Update a user's avatar.
    """
    # You have to be logged in to update avatars
    if not 'username' in session :
        flash( 'You must be logged in to update your avatar.', 'alert-error' )
        return redirect( url_for( 'index' ) )
    
    username = session['username']
    if not 'avatar' in request.files :
        flash( 'Wern\'t you uploading a file or something', 'alert-error' )
        return redirect( url_for( 'profile', username=username ) )
    file = request.files['avatar']
    update_avatar( username, file )
    #flash( 'Your avatar has been updated!', 'alert-success' )
    return redirect( url_for( 'profile', username=username ) )    

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


