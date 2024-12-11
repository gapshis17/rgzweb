from app import db
from datetime import datetime
import pytz

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Initiative(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    votes = db.relationship('Vote', backref='initiative', lazy=True)

    @property
    def current_rating(self):
        return sum(vote.vote_value for vote in self.votes)

    @property
    def local_date_created(self):
        # Преобразуем время из UTC в новосибирский часовой пояс (UTC+7)
        local_tz = pytz.timezone('Asia/Novosibirsk')
        local_time = self.date_created.replace(tzinfo=pytz.utc).astimezone(local_tz)
        return local_time.strftime('%Y-%m-%d %H:%M:%S')
    def count_negative_votes(self):
        """Подсчитывает количество отрицательных голосов."""
        return Vote.query.filter_by(initiative_id=self.id, vote_value=-1).count()


class Vote(db.Model):
    __tablename__ = 'vote'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    initiative_id = db.Column(db.Integer, db.ForeignKey('initiative.id'), nullable=False)
    vote_value = db.Column(db.Integer, nullable=False)



