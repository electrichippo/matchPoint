# from urllib.parse import urlsplit
# from flask import render_template, flash, redirect, url_for, request
# from flask_login import login_user, logout_user, current_user, login_required
# import sqlalchemy as sa
# from sqlalchemy import func, desc, select, asc
# import json
# import random
# import datetime
# from fileinput import filename 

# import app.data_fetch as data

# from app import app, db
# from app.forms import LoginForm, RegistrationForm, PredictionForm
# from app.models import User, Match, Prediction    

# match = db.session.scalar(sa.select(Match).\
#                             where(Match.tournament == tournament_name)
#                 sa.and_(Match.player1 == player1, Match.player2 == player2)
#             )

# ms = Match.query.\
#         where(Match.tournament == tournament).\
#         where((Match.player1 == player) | (Match.player2 == player)).\
#         all()

# u = User.query.\
#     where(User.username == "ben.ganko").\
#     first()

# for m in ms:
#     print(m)

# predictions_to_delete = db.session.scalars(
#     sa.select(Prediction).where(Prediction.matchId == 138)
# ).all()

# for p in predictions_to_delete:
#     print(p)
#     db.session.delete(p)

# matchCount = 

# print(db.session.execute(sa.select(sa.func.count(Match.id)).\
#                                                     where(Match.tournament == "French Open").\
#                                                     where((Match.round == "R1"))).scalar_one())

# print(db.session.execute(sa.select(sa.func.count(Prediction.id)).\
#                                                     join(Match, Prediction.matchId == Match.id, isouter=True).\
#                                                     filter(Match.tournament == "French Open").\
#                                                     filter((Match.round == "R1"))).scalar_one())