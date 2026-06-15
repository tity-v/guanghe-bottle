"""
光核安利漂流瓶 — 数据库模型
==============================
7 张表：User, DriftBottle, SalvageRecord, BottleLike,
         DailyTask, ShareRecord, AdminLog
"""
from datetime import datetime, date, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


def utcnow():
    """返回带时区的 UTC 当前时间"""
    return datetime.now(timezone.utc)


# ── 1. 用户表 ──────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    qq = db.Column(db.String(20), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    nickname = db.Column(db.String(50), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    # 拉新追踪
    referrer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    referral_code = db.Column(db.String(60), unique=True, nullable=True)  # 分享链接标识

    created_at = db.Column(db.DateTime, default=utcnow)

    # 关系
    bottles = db.relationship('DriftBottle', backref='author', lazy='dynamic')
    salvage_records = db.relationship('SalvageRecord', backref='user', lazy='dynamic')
    daily_tasks = db.relationship('DailyTask', backref='user', lazy='dynamic')

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    def display_name(self):
        return self.nickname or self.qq

    def __repr__(self):
        return f'<User {self.qq}>'


# ── 2. 漂流瓶表 ────────────────────────────────
class DriftBottle(db.Model):
    __tablename__ = 'drift_bottles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # 图片
    image_path = db.Column(db.String(500), nullable=False)
    thumbnail_path = db.Column(db.String(500), default='')

    # 内容
    title = db.Column(db.String(30), nullable=False)
    game_name = db.Column(db.String(100), nullable=False)
    field_a = db.Column(db.Text, default='')
    field_b = db.Column(db.Text, default='')
    recommendation = db.Column(db.Text, default='')

    # 分类
    category = db.Column(db.String(30), nullable=False)

    # 审核
    is_preset = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)  # 默认待审
    is_deleted = db.Column(db.Boolean, default=False)   # 软删除
    review_note = db.Column(db.String(200), default='')

    created_at = db.Column(db.DateTime, default=utcnow)

    # 关系
    salvage_records = db.relationship('SalvageRecord', backref='bottle', lazy='dynamic')
    likes = db.relationship('BottleLike', backref='bottle', lazy='dynamic')

    @property
    def like_count(self):
        return BottleLike.query.filter_by(bottle_id=self.id).count()

    def to_dict(self, user=None):
        d = {
            'id': self.id,
            'title': self.title,
            'game_name': self.game_name,
            'field_a': self.field_a,
            'field_b': self.field_b,
            'recommendation': self.recommendation,
            'category': self.category,
            'image_path': self.image_path,
            'thumbnail_path': self.thumbnail_path,
            'author_nickname': self.author.display_name() if self.author else '匿名投递者',
            'is_preset': self.is_preset,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else '',
            'like_count': self.like_count,
        }
        if user and user.is_authenticated:
            d['user_liked'] = BottleLike.query.filter_by(
                bottle_id=self.id, user_id=user.id
            ).first() is not None
        else:
            d['user_liked'] = False
        return d

    def __repr__(self):
        return f'<Bottle {self.id}: {self.title}>'


# ── 3. 打捞记录表 ──────────────────────────────
class SalvageRecord(db.Model):
    __tablename__ = 'salvage_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bottle_id = db.Column(db.Integer, db.ForeignKey('drift_bottles.id'), nullable=False)

    is_saved_to_wall = db.Column(db.Boolean, default=False)
    wall_position = db.Column(db.Integer, nullable=True)

    salvaged_at = db.Column(db.DateTime, default=utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'bottle_id', name='uq_user_bottle'),
    )

    def __repr__(self):
        return f'<Salvage u={self.user_id} b={self.bottle_id}>'


# ── 4. 点赞表 ──────────────────────────────────
class BottleLike(db.Model):
    __tablename__ = 'bottle_likes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bottle_id = db.Column(db.Integer, db.ForeignKey('drift_bottles.id'), nullable=False)

    created_at = db.Column(db.DateTime, default=utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'bottle_id', name='uq_user_bottle_like'),
    )

    def __repr__(self):
        return f'<Like u={self.user_id} b={self.bottle_id}>'


# ── 5. 每日任务表 ──────────────────────────────
class DailyTask(db.Model):
    __tablename__ = 'daily_tasks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    task_date = db.Column(db.Date, nullable=False, default=date.today)

    throw_claimed = db.Column(db.Boolean, default=False)
    share_claimed = db.Column(db.Boolean, default=False)
    referral_count = db.Column(db.Integer, default=0)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'task_date', name='uq_user_date'),
    )

    def __repr__(self):
        return f'<DailyTask u={self.user_id} d={self.task_date}>'


# ── 6. 分享记录表 ──────────────────────────────
class ShareRecord(db.Model):
    __tablename__ = 'share_records'

    id = db.Column(db.Integer, primary_key=True)
    sharer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    shared_type = db.Column(db.String(20), nullable=False)    # activity / bottle / wall
    shared_target_id = db.Column(db.Integer, nullable=True)
    new_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=utcnow)

    sharer = db.relationship('User', foreign_keys=[sharer_id], backref='shares_sent')
    new_user = db.relationship('User', foreign_keys=[new_user_id], backref='referred_by_share')

    def __repr__(self):
        return f'<Share {self.shared_type} by u={self.sharer_id}>'


# ── 7. 管理员日志 ──────────────────────────────
class AdminLog(db.Model):
    __tablename__ = 'admin_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)       # approve / reject / delete / export
    target_type = db.Column(db.String(30), nullable=True)   # bottle / user
    target_id = db.Column(db.Integer, nullable=True)
    note = db.Column(db.String(200), default='')

    created_at = db.Column(db.DateTime, default=utcnow)

    admin = db.relationship('User', backref='admin_logs')

    def __repr__(self):
        return f'<AdminLog {self.action} by a={self.admin_id}>'
