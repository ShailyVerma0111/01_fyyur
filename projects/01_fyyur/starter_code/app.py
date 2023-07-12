#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from models import db, Show, Venue, Artist
from flask_moment import Moment
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
import sys
from datetime import datetime
from sqlalchemy import text
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
migrate = Migrate(app, db)
app.app_context().push()
db.init_app(app)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

db.create_all()

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

def format_currentDateTime():
   current_date = datetime.now()
   return current_date.strftime("%Y-%m-%d %H:%M:%S")

def format_genres(genres):
   genres = genres.replace('"','')
   return genres.strip('{}').split(',')

app.jinja_env.filters['datetime'] = format_datetime

def artist_detail_filter(show):
   artist_details = {}
   artist = Artist.query.get(show.artist_id)
   artist_details['artist_id'] = artist.id
   artist_details['artist_name'] = artist.name
   artist_details['artist_image_link'] = artist.image_link
   artist_details['start_time'] = show.start_time
   return artist_details

def venue_detail_filter(show):
   venue_details = {}
   venue = Venue.query.get(show.venue_id)
   venue_details['venue_id'] = venue.id
   venue_details['venue_name'] = venue.name
   venue_details['venue_image_link'] = venue.image_link
   venue_details['start_time'] = show.start_time
   return venue_details

current_date = format_currentDateTime()

def upcoming_shows_filter(id, searchType):
   if searchType == 'venue':
      return Show.query.filter(Show.venue_id == id, Show.start_time >= current_date).order_by('start_time').all()
   else:
      return Show.query.filter(Show.artist_id == id, Show.start_time >= current_date).order_by('start_time').all()

def past_shows_filter(id, searchType):
   if searchType == 'venue':
      return Show.query.filter(Show.venue_id == id, Show.start_time < current_date).order_by('start_time').all()
   else:
      return Show.query.filter(Show.artist_id == id, Show.start_time < current_date).order_by('start_time').all()

def num_upcoming_shows_filter(id, searchType):
   if searchType == 'venue':
      return Show.query.filter(Show.venue_id == id, Show.start_time >= current_date).count()
   else:
      return Show.query.filter(Show.artist_id == id, Show.start_time >= current_date).count()

def num_past_shows_filter(id, searchType):
   if searchType == 'venue':
      return Show.query.filter(Show.venue_id == id, Show.start_time < current_date).count()
   else:
      return Show.query.filter(Show.artist_id == id, Show.start_time < current_date).count()

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  query = text('SELECT city, state, string_agg(CAST(id as text),\',\') as venue_ids FROM "Venue" GROUP BY city, state;')
  venues = db.session.execute(query)
  response = []
  
  for venue in venues:
     venue_details = {}
     shows_details = []
     venue_details['city'] = venue.city
     venue_details['state'] = venue.state
     venue_id = venue.venue_ids.split(',')
     for id in venue_id:
         venue_detail = Venue.query.get(id)
         num_upcoming_shows = num_upcoming_shows_filter(id, 'venue')
         show_venue_detail = {}
         show_venue_detail['id'] = venue_detail.id
         show_venue_detail['name'] = venue_detail.name
         show_venue_detail['num_upcoming_shows'] = num_upcoming_shows
         shows_details.append(show_venue_detail)
     venue_details['venues'] = shows_details
     response.append(venue_details)

  return render_template('pages/venues.html',
                         areas=response);

@app.route('/venues/search', methods=['POST'])
def search_venues():
  search_term = request.form.get('search_term')
  response = {}
  data = []
  venues = Venue.query.filter(Venue.name.ilike(f"%{search_term}%")).all()
  response['count'] = len(venues)
  for venue in venues :
      num_upcoming_shows = num_upcoming_shows_filter(venue.id, 'venue')
      venue_detail = {}
      venue_detail['id'] = venue.id
      venue_detail['name'] = venue.name
      venue_detail['num_upcoming_shows'] = num_upcoming_shows
      data.append(venue_detail)
  response['data'] = data

  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  venue_details = Venue.query.get(venue_id)
  response = {}
  response['id'] = venue_details.id
  response['name'] = venue_details.name
  genres = format_genres(venue_details.genres)
  response['genres'] = genres
  response['address'] = venue_details.address
  response['city'] = venue_details.city
  response['state'] = venue_details.state
  response['phone'] = venue_details.phone
  response['website'] = venue_details.website_link
  response['facebook_link'] = venue_details.facebook_link
  response['seeking_talent'] = venue_details.looking_for_talent
  response['seeking_description'] = venue_details.seeking_description
  response['image_link'] = venue_details.image_link

  num_upcoming_shows = num_upcoming_shows_filter(venue_details.id, 'venue')
  num_past_show =  num_past_shows_filter(venue_details.id, 'venue')

  upcoming_shows = upcoming_shows_filter(venue_details.id, 'venue')
  past_shows = past_shows_filter(venue_details.id, 'venue')

  upcoming_shows_details = []
  past_shows_details = []

  for show in upcoming_shows:
     artist_details = artist_detail_filter(show)
     upcoming_shows_details.append(artist_details)

  for show in past_shows:
     artist_details = artist_detail_filter(show)
     past_shows_details.append(artist_details) 

  response['past_shows'] =  past_shows_details
  response['upcoming_shows'] = upcoming_shows_details
  response['past_shows_count'] = num_past_show
  response['upcoming_shows_count'] = num_upcoming_shows

  return render_template('pages/show_venue.html', venue=response)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  error = False
  try:
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    address = request.form['address']
    phone = request.form['phone']
    genres = request.form.getlist('genres')
    image_link = request.form['image_link']
    facebook_link = request.form['facebook_link']
    website_link = request.form['website_link']
    seeking_talent = request.form.get('seeking_talent')
    if seeking_talent == 'y':
       looking_for_talent = True
    else:
       looking_for_talent = False   
    seeking_description = request.form['seeking_description']
    venue = Venue(name=name, city=city,state=state,address=address,phone=phone,genres=genres,
                image_link=image_link,facebook_link=facebook_link,website_link=website_link,looking_for_talent=looking_for_talent,
                seeking_description=seeking_description
                )
    db.session.add(venue)
    db.session.commit()
  except:
     error= True
     db.session.rollback()
     print(sys.exc_info())
  finally:
     db.session.close()  

  if not error:
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
  else:
     flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
  return render_template('pages/home.html')

@app.route('/venues/<int:venue_id>/delete', methods=['POST','DELETE'])
def delete_venue(venue_id):

  if request.method == 'POST' or request.method == 'DELETE':
    error = False
    try: 
      venue = Venue.query.get(venue_id)
      venue_name = venue.name
      shows = Show.query.filter(Show.venue_id == venue_id).all()
      for show in shows :
        db.session.delete(show)
      db.session.delete(venue)
      db.session.commit()
    except Exception as e:
      logging.exception(e)
      error = True
      db.session.rollback()
    finally:
      db.session.close() 
  
  if not error:
    flash('Venue \'' + venue_name+ '\' was successfully deleted!')
  else:
     flash('An error occurred. Venue \'' + venue_name + '\' could not be deleted.')
  return render_template('pages/home.html')

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  artist = Artist.query.all()
  return render_template('pages/artists.html', artists=artist)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  response = {}
  data = []
  search_term = request.form.get('search_term', '')
  artists = Artist.query.filter(Artist.name.ilike(f"%{search_term}%")).all()
  num_matching_artist = len(artists)
  response['count'] = num_matching_artist
  for artist in artists:
     artist_details = {}
     num_upcoming_shows = num_upcoming_shows_filter(artist.id, 'artist')
     artist_details['id'] = artist.id
     artist_details['name'] = artist.name
     artist_details['num_upcoming_shows'] = num_upcoming_shows
     data.append(artist_details)

  response['data'] = data
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  response = {}
  artist = Artist.query.get(artist_id)
  response['id'] = artist.id
  response['name'] = artist.name
  response['genres'] = format_genres(artist.genres)
  response['city'] = artist.city
  response['state'] = artist.state
  response['phone'] = artist.phone
  response['website'] = artist.website_link
  response['facebook_link'] = artist.facebook_link
  response['seeking_venue'] = artist.looking_for_venues
  response['seeking_description'] = artist.seeking_description
  response['image_link'] = artist.image_link

  num_upcoming_shows = num_upcoming_shows_filter(artist.id, 'artist')
  num_past_show =  num_past_shows_filter(artist.id, 'artist')

  upcoming_shows = upcoming_shows_filter(artist.id, 'artist')
  past_shows = past_shows_filter(artist.id, 'artist')

  upcoming_shows_details = []
  past_shows_details = []

  for show in upcoming_shows:
     venuu_details = venue_detail_filter(show)
     upcoming_shows_details.append(venuu_details)

  for show in past_shows:
     venuu_details = venue_detail_filter(show)
     past_shows_details.append(venuu_details) 

  response['past_shows'] =  past_shows_details
  response['upcoming_shows'] = upcoming_shows_details
  response['past_shows_count'] = num_past_show
  response['upcoming_shows_count'] = num_upcoming_shows

  return render_template('pages/show_artist.html', artist=response)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  artist = Artist.query.get(artist_id)
  artist.genres = format_genres(artist.genres)
  artist.seeking_venue = artist.looking_for_venues  
  form = ArtistForm(obj=artist)

  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  
  try:
      artist = Artist.query.get(artist_id)
      if request.form['name'] != artist.name:
         artist.name = request.form['name']
      if request.form['city'] != artist.city : 
         artist.city = request.form['city']
      if request.form['state'] != artist.state : 
         artist.state = request.form['state']
      if request.form['phone'] != artist.phone:
         artist.phone = request.form['phone']
      if request.form['website_link'] != artist.website_link:
         artist.website_link = request.form['website_link']
      if request.form['facebook_link'] != artist.facebook_link : 
         artist.facebook_link = request.form['facebook_link']
      seeking_venue = request.form.get('seeking_venue')
      if seeking_venue == 'y':
          looking_for_venues = True
      else:
          looking_for_venues = False
      if looking_for_venues != artist.looking_for_venues : 
          artist.looking_for_venues = looking_for_venues
      if request.form['seeking_description'] != artist.seeking_description: 
         artist.seeking_description = request.form['seeking_description']
      if request.form.getlist('genres') != artist.genres:
         artist.genres =  request.form.getlist('genres')

      db.session.add(artist)
      db.session.commit()  
  except:
     db.session.rollback()
     print(sys.exc_info())
  finally:
     db.session.close()              

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue = Venue.query.get(venue_id)
  venue.genres = format_genres(venue.genres)
  venue.seeking_talent = venue.looking_for_talent  
  form = VenueForm(obj=venue)
  
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  
  try:
      venue = Venue.query.get(venue_id)
      if request.form['name'] != venue.name:
         venue.name = request.form['name']
      if request.form['city'] != venue.city : 
         venue.city = request.form['city']
      if request.form['state'] != venue.state : 
         venue.state = request.form['state']
      if request.form['phone'] != venue.phone:
         venue.phone = request.form['phone']
      if request.form['website_link'] != venue.website_link:
         venue.website_link = request.form['website_link']
      if request.form['facebook_link'] != venue.facebook_link : 
         venue.facebook_link = request.form['facebook_link']
      seeking_talent = request.form.get('seeking_talent')
      if seeking_talent == 'y':
          seeking_talent = True
      else:
          seeking_talent = False
      if seeking_talent != venue.looking_for_talent : 
          venue.looking_for_talent = seeking_talent
      if request.form['seeking_description'] != venue.seeking_description: 
         venue.seeking_description = request.form['seeking_description']
      if request.form.getlist('genres') != venue.genres:
         venue.genres =  request.form.getlist('genres')

      db.session.add(venue)
      db.session.commit()  
  except:
     db.session.rollback()
     print(sys.exc_info())
  finally:
     db.session.close()

  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  
  error = False
  try:
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    phone = request.form['phone']
    genres = request.form.getlist('genres')
    image_link = request.form['image_link']
    facebook_link = request.form['facebook_link']
    website_link = request.form['website_link']
    seeking_venue = request.form.get('seeking_venue')
    if seeking_venue == 'y':
       looking_for_venues = True
    else:
       looking_for_venues = False   
    seeking_description = request.form['seeking_description']
    artist = Artist(name=name, city=city,state=state,phone=phone,genres=genres,
                image_link=image_link,facebook_link=facebook_link,website_link=website_link,looking_for_venues=looking_for_venues,
                seeking_description=seeking_description
                )
    db.session.add(artist)
    db.session.commit()
  except:
     error= True
     db.session.rollback()
     print(sys.exc_info())
  finally:
     db.session.close()  

  if not error:
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  else:
    flash('An error occurred. Artist ' + request.form['name']  + ' could not be listed.')
  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():

  shows = Show.query.filter(Show.start_time >= current_date).all()
  response = [] 
  for show in shows:
     show_details = {}
     venue = Venue.query.get(show.venue_id)
     artist = Artist.query.get(show.artist_id)     
     show_details['venue_id'] = venue.id
     show_details['venue_name'] = venue.name
     show_details['artist_id'] = artist.id
     show_details['artist_name'] = artist.name
     show_details['artist_image_link'] = artist.image_link
     show_details['start_time'] = show.start_time
     response.append(show_details)

  return render_template('pages/shows.html', shows=response)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  error = False
  try:
    venue_id = request.form['venue_id']
    artist_id = request.form['artist_id']
    start_time = request.form['start_time']
  
    show = Show(venue_id=venue_id, artist_id=artist_id, start_time=start_time
                )
    db.session.add(show)
    db.session.commit()
  except:
     error= True
     db.session.rollback()
     print(sys.exc_info())
  finally:
     db.session.close()

  # on successful db insert, flash success
  if not error:
    flash('Show was successfully listed!')
  else:
    flash('An error occurred. Show could not be listed.')
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
