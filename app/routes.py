from urllib.parse import urlsplit
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
import sqlalchemy as sa
from sqlalchemy import func, desc, select, asc
import json
import random
import datetime
from fileinput import filename 
import pytz
import os
import glob

import app.data_fetch as data

from app import app, db
from app.forms import LoginForm, RegistrationForm, PredictionForm, EditProfileForm
from app.models import User, Match, Prediction

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    user_id = current_user.id

    # Unpredicted matches
    predicted_match_ids = db.session.query(Prediction.matchId).\
        filter(Prediction.userId == user_id).all()
    # Convert the result to a flat list of IDs
    predicted_match_ids = [match_id for (match_id,) in predicted_match_ids]

    aest = pytz.timezone('Australia/Sydney')
    now_aest = datetime.datetime.now(aest)
    
    # Query for all matches that are not in the predicted list
    unpredicted_matches = Match.query.\
        filter(Match.id.notin_(predicted_match_ids)).\
        filter(Match.winner == None).\
        filter(Match.startTime > now_aest).\
        order_by(Match.tour, Match.startTime).\
        all()
    
    # Predicitions on upcoming matches
    upcoming_predictions = Prediction.query\
        .join(Match, Prediction.matchId == Match.id)\
        .filter(Match.winner == None)\
        .filter(Prediction.userId == current_user.id)\
        .order_by(Match.tour, Match.startTime)\
        .all()
    
    db.session.commit()

    curentTournament = db.session.execute(
            sa.select(Match.tournament)
            .order_by(desc(Match.id))
            .limit(1)
        ).scalar_one_or_none()

    # HANDLE ONLY SELECTING SOME
    prediction_array = []    
    for match in unpredicted_matches:
        data = {
            'name' : f"{match.id}",
            'label' : f"{match.round} - {match.player1} vs {match.player2}: {match.startTime.strftime('%a %I:%M %p')}",
            'options' : [(f"{match.player1}", f"{match.player1} | {match.player1Price}"), (f"{match.player2}", f"{match.player2} | {match.player2Price}")]
        }
        prediction_array.append(data)  
      
    if request.method == 'POST':
        # selected_options = {}
        options = []
        for group in prediction_array:
            option = {}
            # selected_options[group['name']] = request.form.get(group['name'])

            option['matchId'] = group['name']
            option['player'] = request.form.get(group['name'])
            options.append(option)
        
        print(options)
    
        # CREATE PREDICTIONS HERE
        # Get user
        user = db.session.scalar(sa.select(User).\
                                    where(User.id == current_user.id))
        for option in options:
            # skip if player not selected
            if option['player'] == None:
                continue

            # Get match
            match = db.session.scalar(sa.select(Match).\
                                     where(Match.id == option['matchId']))
            # Create Prediction
            prediction = Prediction(player = option['player'], maker = user, match = match)
            print(prediction)
            
            db.session.add(prediction)
            db.session.commit()

        return redirect(url_for('index'))

    return render_template('index.html', title='Home', matches = unpredicted_matches, upcoming_predictions = upcoming_predictions, radio_groups=prediction_array, currentTournament=curentTournament)

# Replaced with user profiles

# @app.route('/history', methods=['GET', 'POST'])
# @login_required
# def history():
# # Predicitions on completed matches
#     currentTournament = db.session.execute(
#         sa.select(Match.tournament)
#         .order_by(asc(Match.startTime))
#         .limit(1)
#     ).scalar_one_or_none()

#     settled_predictions = Prediction.query\
#         .join(Match, Prediction.matchId == Match.id)\
#         .filter(Match.winner != None)\
#         .filter(Prediction.userId == current_user.id)\
#         .order_by(Match.startTime)\
#         .all()
    
#     return render_template('history.html', title='History',settled_predictions = settled_predictions, currentTournament = currentTournament)

@app.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))

    # Predicitions on completed matches
    currentTournament = db.session.execute(
        sa.select(Match.tournament)
        .order_by(desc(Match.startTime))
        .limit(1)
    ).scalar_one_or_none()

    settled_predictions = Prediction.query\
        .join(Match, Prediction.matchId == Match.id)\
        .filter(Match.winner != None)\
        .filter(Prediction.userId == user.id)\
        .filter(Match.tournament == currentTournament)\
        .order_by(desc(Match.startTime))\
        .all()
    
    points_subquery = (
        db.session.query(
            User.id.label('user_id'),
            sa.func.coalesce(
                sa.func.sum(
                    sa.case(
                        (Prediction.player == Match.winner, 
                         sa.case(
                             (Prediction.player == Match.player1, Match.player1Price),
                             (Prediction.player == Match.player2, Match.player2Price),
                             else_=0
                         )),
                        else_=0
                    )
                ), 0
            ).label('total_points')
        )
        .outerjoin(Prediction, User.id == Prediction.userId)
        .outerjoin(Match, sa.and_(
            Prediction.matchId == Match.id,
            Match.tournament == currentTournament,
            Match.winner.is_not(None)
        ))
        .group_by(User.id)
        .subquery()
    )
    
    # Query to get rankings
    rankings = (
        db.session.query(
            User.id,
            User.username,
            points_subquery.c.total_points,
            sa.func.rank().over(order_by=points_subquery.c.total_points.desc()).label('rank')
        )
        .join(points_subquery, User.id == points_subquery.c.user_id)
        .order_by(points_subquery.c.total_points.desc())
        .all()
    )
    
    # Find user's position
    user_position = None
    for ranking in rankings:
        if ranking.id == user.id:
            user_position = ranking.rank
            break
    
    return render_template('user.html', title='User',settled_predictions = settled_predictions, currentTournament = currentTournament, user=user, user_position = user_position)

@app.route('/match/<match_name>')
@login_required
def match(match_name):
    # user = db.first_or_404(sa.select(User).where(User.username == username))
    currentTournament = db.session.execute(
        sa.select(Match.tournament)
        .order_by(desc(Match.startTime))
        .limit(1)
    ).scalar_one_or_none()

    # Split by the VS so that it works even for 2+ word names
    match_fields = match_name.split(" vs ")
    player1 = match_fields[0]
    player2 = match_fields[1]

    match = Match.query\
        .where(Match.tournament == currentTournament)\
        .where(Match.player1 == player1)\
        .where(Match.player2 == player2)\
        .first()
    
    if not match:
        flash('Match not found', 'error')
        return redirect(url_for('index'))
    
    predictions = db.session.scalars(
    sa.select(Prediction).where(Prediction.matchId == match.id)
        ).all()
    
    for p in predictions:
        print(f"user: {p.maker.username} predicted: {p.player}")
    
    return render_template('match_view.html', title='History', match = match, predictions = predictions)


@app.route('/leaderboard', methods=['GET', 'POST'])
@login_required
def leaderboard():
    curentTournament = db.session.execute(
        sa.select(Match.tournament)
        .order_by(desc(Match.id))
        .limit(1)
    ).scalar_one_or_none()

    selected_round = request.form.get('round') or request.args.get('round', 'all')
    selected_gender = request.form.get('gender') or request.args.get('gender', 'all')
    
    # Available rounds
    available_rounds = ["R1", "R2", "R3", "R4", "QF", "SF", "F"]

    available_genders = ["All","M", "W"]

    # Base query
    query = db.session.query(
        User.id,
        User.username,
        User.profile_picture,
        func.coalesce(func.sum(
            sa.case(
                (Prediction.player == Match.winner,
                 sa.case(
                     (Prediction.player == Match.player1, Match.player1Price),
                     (Prediction.player == Match.player2, Match.player2Price),
                     else_=0
                 )),
                else_=0
            )
        ), 0).label('total_points'),
        func.coalesce(func.sum(
            sa.case(
                (Prediction.player == Match.winner, 1),
                else_=0
            )
        ), 0).label('correct_predictions_count'),
        func.coalesce(func.count(Prediction.id), 0).label('total_predictions_count')
    ).join(Prediction, User.id == Prediction.userId, isouter=True).\
        join(Match, Prediction.matchId == Match.id, isouter=True).\
        filter(Match.tournament == curentTournament)
    
    # Add round filter if not 'all'
    if selected_round != 'all':
        query = query.filter(Match.round == selected_round)

    # Add gender filter if not 'both'
    if selected_gender == 'M':
        query = query.filter(Match.tour == 'ATP')
    elif selected_gender == 'W':
        query = query.filter(Match.tour == 'WTA')
    # If 'both', no additional filter is applied
    
    user_results = query.group_by(User.id, User.username).\
        order_by(desc('total_points')).\
        all()
        
    return render_template('leaderboard.html', 
                         title='Leaderboard', 
                         userResults=user_results, 
                         currentTournament=curentTournament,
                         available_rounds=available_rounds,
                         available_genders=available_genders,
                         selected_round=selected_round,
                         selected_gender=selected_gender)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

def get_available_images():
    """Get list of images from static/images/ directory"""
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.webp']
    images = []
    
    images_path = os.path.join(app.static_folder, 'images')
    
    if os.path.exists(images_path):
        for extension in image_extensions:
            pattern = os.path.join(images_path, extension)
            found_images = glob.glob(pattern, recursive=False)
            # Convert full paths to relative paths for web serving
            for img_path in found_images:
                filename = os.path.basename(img_path)
                images.append(filename)
    
    return sorted(images)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    available_images = get_available_images()

    form.selected_image.choices = [(img, img) for img in available_images]
    if form.validate_on_submit():
        current_user.profile_picture = form.selected_image.data
        current_user.username = form.username.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form, images=available_images)

@app.route('/refresh')
def refresh():

    return redirect(url_for('index'))

@app.route('/removep')
def removep():
    predictions = Prediction.query.all()
    for p in predictions:
        db.session.delete(p)

        db.session.commit()

    return redirect(url_for('index'))

@app.route('/removem')
def removem():
    predictions = Match.query.all()
    for p in predictions:
        db.session.delete(p)
        db.session.commit()

    return redirect(url_for('index'))

@app.route('/createm')
def createm():

    players = [
    "Jannik Sinner",
    "Alexander Zverev",
    "Carlos Alcaraz",
    "Taylor Fritz",
    "Novak Djokovic",
    "Jack Draper",
    "Alex de Minaur",
    "Andrey Rublev",
    "Holger Rune",
    "Daniil Medvedev"
    ]
    tournaments = ["French Open 2025"]
    rounds = {'0':"R1", '1':"R2", '2' : "R3", '3' : "R4", '4':"QF", '5':"SF", '6':"F"}

    for _ in range(10):
        player1 = random.choice(players)
        player2 = random.choice([p for p in players if p != player1])
        start_time = datetime.datetime(2025, random.randint(6, 8), random.randint(1, 30), random.randint(10, 18), random.randint(0, 59))
        player1_price = round(100*round(random.uniform(1.1, 5.0), 2))
        player2_price = round(100*(1/(1 - (1/(player1_price/100)))))
        tournament = random.choice(tournaments)

        match_count = db.session.query(Match).\
        filter(Match.tournament == tournament).\
        filter((Match.player1 == player1) | (Match.player2 == player1)).\
        count()
        round_name = rounds[str(match_count)]
        winner = None

        match = Match(
            tournament=tournament,
            round=round_name,
            startTime=start_time,
            player1=player1,
            player1Price=player1_price,
            player2=player2,
            player2Price=player2_price,
            winner=winner
        )
        db.session.add(match)
        db.session.commit()

    return redirect(url_for('index'))

@app.route('/createmlive')
def createmlive():
    rounds = {'0':"R1", '1':"R2", '2' : "R3", '3' : "R4", '4':"QF", '5':"SF", '6':"F"}
    all_matches = data.get_data(172136, "ATP Rome")
    for match in all_matches:
        player1 = match['homeTeam']
        player2 = match['awayTeam']
        start_time = datetime.datetime.strptime(match['startsAt'], '%Y-%m-%d %H:%M:%S')
        player1_price = round(match['homeTeamPrice'] * 100)
        player2_price = round(100*(1/(1 - (1/(player1_price/100)))))
        tournament = match['tournamentName'].replace("WTA", "", 1).replace("ATP", "", 1)

        match_count = db.session.query(Match).\
        filter(Match.tournament == tournament).\
        filter((Match.player1 == player1) | (Match.player2 == player1)).\
        count()
        round_name = rounds[str(match_count)]
        winner = None

        existing_match = db.session.query(Match).\
            filter(Match.tournament == tournament).\
            filter(
                ((Match.player1 == player1) & (Match.player2 == player2)) |
                ((Match.player1 == player2) & (Match.player2 == player1))
            ).\
            first()
        
        if not existing_match:
            match = Match(
                tournament=tournament,
                round=round_name,
                startTime=start_time,
                player1=player1,
                player1Price=player1_price,
                player2=player2,
                player2Price=player2_price,
                winner=winner
            )
            db.session.add(match)
            db.session.commit()
        else:
            print("match exists... skipping")

    return redirect(url_for('index'))

@app.route('/assignm')
def assignm():
    matches = Match.query.all()
    for m in matches:
        if m.winner == None:
            m.winner = random.choice([m.player1, m.player2, None])
        db.session.commit()

    return redirect(url_for('index'))

@app.route('/upload')   
def upload():   
    return render_template("upload.html") 

@app.route('/success', methods = ['POST'])   
def success():
    rounds = ["R1", "R2", "R3", "R4", "QF", "SF", "F"]
    if request.method == 'POST':   
        f = request.files['file'] 
        f.save(f.filename)
        with open(f.filename, 'r') as f:
            all_matches = json.load(f) 

        for match in all_matches:
            player1 = match['homeTeam']
            player2 = match['awayTeam']
            start_time = datetime.datetime.strptime(match['startsAt'], '%Y-%m-%d %H:%M:%S')

            if "ATP" in match['tournamentName'] or "Men's" in match['tournamentName']: 
                tour = "ATP"
            else: 
                tour = "WTA"
            tournament = match['tournamentName'].replace("WTA", "", 1).replace("ATP", "", 1).replace("Men's", "", 1).replace("Women's", "", 1).strip()

            match_count_player2 = db.session.execute(sa.select(sa.func.count(Match.id)).\
                                                    where(Match.tournament == tournament).\
                                                    where((Match.player1 == player2) | (Match.player2 == player2))).\
                                                    scalar_one()

            match_count_player1 = db.session.execute(select(func.count(Match.id)).\
                                                    where(Match.tournament == tournament).\
                                                    where((Match.player1 == player1) | (Match.player2 == player1))).\
                                                    scalar_one()

            if match_count_player1 > match_count_player2: matchCount = match_count_player1
            else: matchCount = match_count_player2

            try:
                round_name = rounds[matchCount]
            except:
                round_name = ""
            
            player1_price = round(10.0 * match['homeTeamPrice'] * 2**float(matchCount), 1)
            player2_price = round(10.0 * match['awayTeamPrice'] * 2**float(matchCount), 1)

            winner = None

            existing_match = db.session.query(Match).\
                filter(Match.tournament == tournament).\
                filter(
                    ((Match.player1 == player1) & (Match.player2 == player2)) |
                    ((Match.player1 == player2) & (Match.player2 == player1))
                ).\
                first()
            
            # Update winners for player1           
            players_matches = Match.query.\
                    filter(Match.tournament == tournament).\
                    filter(((Match.player1 == player1) | (Match.player2 == player1))).\
                    filter(Match.winner == None).\
                    all()
                
            for match in players_matches:
                if not (match.player1 == player1 and match.player2 == player2) or (match.player1 == player2 and match.player2 == player1):
                    match.winner = player1
            
            # Update winners for player2
            players_matches = Match.query.\
                    filter(Match.tournament == tournament).\
                    filter(((Match.player1 == player2) | (Match.player2 == player2))).\
                    filter(Match.winner == None).\
                    all()
                
            for match in players_matches:
                if not (match.player1 == player1 and match.player2 == player2) or (match.player1 == player2 and match.player2 == player1):
                    match.winner = player2
    
            db.session.commit()
            
            if not existing_match:
                match = Match(
                    tournament = tournament,
                    round = round_name,
                    startTime = start_time,
                    player1 = player1,
                    player1Price = player1_price,
                    player2 = player2,
                    player2Price = player2_price,
                    tour = tour,
                    winner = winner
                )
                db.session.add(match)
                db.session.commit()
            else:
                print(f"Match exists. Updating start time to: {start_time}")
                existing_match.startTime = start_time
                db.session.commit()
            
    return redirect(url_for('index'))
         
        
@app.route('/admin', methods=['GET', 'POST'])   
def admin():

    incomplete_matches = Match.query\
            .filter(Match.winner == None)\
            .all()
    
    match_array = []    
    for match in incomplete_matches:
        data = {
            'name' : f"{match.id}",
            'label' : f"{match.round} - {match.player1} vs {match.player2}: {match.startTime.strftime('%a %I:%M %p')}",
            'options' : [(f"{match.player1}", f"{match.player1}"), (f"{match.player2}", f"{match.player2}")]
        }
        match_array.append(data)  
      
    if request.method == 'POST':
        # selected_options = {}
        options = []
        for group in match_array:
            option = {}
            # selected_options[group['name']] = request.form.get(group['name'])

            option['matchId'] = group['name']
            option['player'] = request.form.get(group['name'])
            options.append(option)
    
        user = db.session.scalar(sa.select(User).\
                                    where(User.id == current_user.id))
        for option in options:
            # skip if player not selected
            if option['player'] == None:
                continue

            # Get match
            match = db.session.scalar(sa.select(Match).\
                                     where(Match.id == option['matchId']))
            
            match.winner = option['player']
            
            db.session.commit()

        return redirect(url_for('admin'))
        # Add this: Get ALL matches for the management table
    all_matches = Match.query.order_by(Match.startTime.desc()).all()
        
    return render_template('admin.html', 
                         title='Admin', 
                         radio_groups=match_array,
                         all_matches=all_matches)

@app.route('/admin/edit_match/<int:match_id>', methods=['GET', 'POST'])
def edit_match(match_id):
    match = db.session.scalar(sa.select(Match).where(Match.id == match_id))
    if not match:
        flash('Match not found', 'error')
        return redirect(url_for('admin'))
    
    if request.method == 'POST':
        # Update all editable fields
        match.round = request.form.get('round')
        match.player1 = request.form.get('player1')
        match.player1Price = request.form.get('player1Price')
        match.player2 = request.form.get('player2')
        match.player2Price = request.form.get('player2Price')
        match.winner = request.form.get('winner') if request.form.get('winner') != '' else None
        
        # Handle datetime parsing
        try:
            start_time_str = request.form.get('start_time')
            match.startTime = datetime.datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date/time format', 'error')
            return render_template('edit_match.html', match=match)
        
        db.session.commit()
        flash('Match updated successfully!', 'success')
        return redirect(url_for('admin'))
    
    return render_template('edit_match.html', match=match)

@app.route('/admin/delete_match/<int:match_id>', methods=['POST'])
def delete_match(match_id):
    match = db.session.scalar(sa.select(Match).where(Match.id == match_id))
    if not match:
        flash('Match not found', 'error')
        return redirect(url_for('admin'))
    
    predictions_to_delete = db.session.scalars(
    sa.select(Prediction).where(Prediction.matchId == match_id)
        ).all()

    for p in predictions_to_delete:
        db.session.delete(p)
    
    db.session.delete(match)
    db.session.commit()
    flash('Match deleted successfully!', 'success')
    return redirect(url_for('admin'))
    
    

