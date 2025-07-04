from datetime import datetime, timezone
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login


class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True,
                                                unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True,
                                             unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))

    profile_picture : so.Mapped[str] = so.mapped_column(sa.String(140), nullable=True)

    predictions: so.WriteOnlyMapped['Prediction'] = so.relationship(
        back_populates='maker')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    def get_total_predictions(self):
        return db.session.scalar(
            sa.select(sa.func.count(Prediction.id)).where(Prediction.userId == self.id)
        )
    
    def get_success_rate(self):
        # Get predictions where match has a winner (settled matches)
        settled_predictions = db.session.scalars(
            sa.select(Prediction)
            .join(Match)
            .where(Prediction.userId == self.id)
            .where(Match.winner.is_not(None))
        ).all()
        
        if not settled_predictions:
            return 0
        
        correct = sum(1 for pred in settled_predictions if pred.player == pred.match.winner)
        return round((correct / len(settled_predictions)) * 100, 1)
    
    def get_correct_predictions(self):
        return db.session.scalar(
            sa.select(sa.func.count(Prediction.id))
            .join(Match)
            .where(Prediction.userId == self.id)
            .where(Match.winner == Prediction.player)
        )
    
@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))

class Match(db.Model):
    id : so.Mapped[int] = so.mapped_column(primary_key=True)
    tournament : so.Mapped[str] = so.mapped_column(sa.String(64))
    round : so.Mapped[str] = so.mapped_column(sa.String(64))
    startTime: so.Mapped[datetime] = so.mapped_column(sa.DateTime, index=True)
    player1 : so.Mapped[str] = so.mapped_column(sa.String(140))
    player1Price : so.Mapped[float] = so.mapped_column(index=True)
    player2 : so.Mapped[str] = so.mapped_column(sa.String(140))
    player2Price : so.Mapped[float] = so.mapped_column(index=True)
    tour : so.Mapped[str] = so.mapped_column(sa.String(140), nullable=True)
    winner : so.Mapped[Optional[str]] = so.mapped_column(sa.String(140), nullable=True)

    predictions: so.WriteOnlyMapped['Prediction'] = so.relationship(
        back_populates='match', passive_deletes=True)

    def __repr__(self):
        return f"<Match {self.player1} ({self.player1Price}) vs {self.player2} ({self.player2Price}) winner: {self.winner}>"

    def get_player_price(self, player):
        if player == self.player1:
            return self.player1Price
        elif player == self.player2:
            return self.player2Price
        else:
            return "Error"


class Prediction(db.Model):
    id : so.Mapped[int] = so.mapped_column(primary_key=True)
    matchId : so.Mapped[int] = so.mapped_column(sa.ForeignKey(Match.id),
                                                index=True)
    userId : so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id),
                                                index=True)
    player : so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc)) 
    
    maker : so.Mapped[User] = so.relationship(back_populates='predictions')
    match : so.Mapped[Match] = so.relationship(back_populates='predictions')

    def __repr__(self):
        return f"<Match: {self.match.player1} vs {self.match.player2} | picked {self.player} @ ${self.match.get_player_price(self.player)} | by {self.maker.username}>"
