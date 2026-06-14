"""
光核安利漂流瓶 — Flask 主应用
==============================
投递 → 打捞 → 展示 三步闭环
7大分类 · 任务系统 · 后台管理 · CSRF保护
"""
import os
import secrets
import uuid
from datetime import date, datetime, timezone
from functools import wraps
import re

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, send_from_directory, session, url_for)
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from PIL import Image

from config import Config
from models import (AdminLog, BottleLike, DailyTask, DriftBottle, PromoCode,
                    SalvageRecord, ShareRecord, User, db)

# ── 应用初始化 ──────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)
app.jinja_env.auto_reload = True

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录～'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


@login_manager.user_loader
def load_user(uid):
    return User.query.get(int(uid))


# ══════════════════════════════════════════════════
# CSRF 保护
# ══════════════════════════════════════════════════

def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']


@app.context_processor
def inject_csrf():
    return {'csrf_token': generate_csrf_token()}


@app.context_processor
def inject_helpers():
    """向模板注入工具函数"""
    return {
        'get_category': Config.get_category,
        'category_choices': Config.get_category_choices(),
    }


def csrf_required(f):
    """装饰器：对 POST/PUT/DELETE/PATCH 请求校验 CSRF token"""

    @wraps(f)
    def wrapper(*a, **k):
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            if request.is_json:
                token = request.headers.get('X-CSRF-Token', '')
            else:
                token = request.form.get('_csrf_token', '')
            expected = session.get('_csrf_token', '')
            if not token or not expected or not secrets.compare_digest(token, expected):
                if request.is_json:
                    return jsonify({'success': False, 'error': 'CSRF 校验失败，请刷新页面重试'}), 403
                flash('CSRF 校验失败，请刷新页面重试', 'error')
                return redirect(request.referrer or url_for('index'))
        return f(*a, **k)

    return wrapper


def admin_required(f):
    """装饰器：要求管理员权限"""

    @wraps(f)
    def wrapper(*a, **k):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('需要管理员权限', 'error')
            return redirect(url_for('index'))
        return f(*a, **k)

    return wrapper


# ══════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════

def allowed_file(fn):
    return '.' in fn and fn.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def save_upload_image(file):
    """保存上传图片 + 生成缩略图；失败时抛 ValueError"""
    ext = file.filename.rsplit('.', 1)[1].lower()
    uname = f"{uuid.uuid4().hex}.{ext}"
    now = datetime.now(timezone.utc)
    sub = os.path.join(app.config['UPLOAD_FOLDER'], str(now.year), f"{now.month:02d}")
    os.makedirs(sub, exist_ok=True)
    ipath = os.path.join(sub, uname)
    file.save(ipath)
    try:
        tname = f"thumb_{uname}"
        tpath = os.path.join(sub, tname)
        img = Image.open(ipath)
        img.thumbnail(app.config['THUMBNAIL_SIZE'], Image.LANCZOS)
        img.save(tpath)
    except Exception:
        os.remove(ipath)
        raise ValueError('图片处理失败，请上传有效的 JPG/PNG/WebP 图片')
    ri = os.path.relpath(ipath, BASE_DIR).replace('\\', '/')
    rt = os.path.relpath(tpath, BASE_DIR).replace('\\', '/')
    return ri, rt


def load_sensitive_words():
    fp = app.config['SENSITIVE_WORDS_FILE']
    if not os.path.exists(fp):
        return []
    with open(fp, 'r', encoding='utf-8') as f:
        return [l.strip() for l in f if l.strip() and not l.startswith('#')]


def check_sensitive(text):
    """检测敏感内容：词库匹配 + 正则（手机号/链接/微信号/空格绕过）

    策略：
    - CJK/长词：不区分大小写子串匹配
    - 短拉丁词（≤3字符）：单词边界匹配，避免 AV→have, IS→this 等误伤
    - 去空格版同步检测，防止「加 微 信」类绕过
    """
    words = load_sensitive_words()

    # 去空格文本（防 "加 微 信" 绕过）
    no_space = re.sub(r'\s+', '', text)

    # 预编译小写的原文和去空格版
    text_lower = text.lower()
    no_space_lower = no_space.lower()

    matched = []
    for w in words:
        w_lower = w.lower()

        # 纯 ASCII 词 → 单词边界匹配，避免误伤（如 ISIS 匹配 thisis, AV 匹配 have）
        if w.isascii():
            pattern = re.compile(
                r'(?<![a-zA-Z])' + re.escape(w) + r'(?![a-zA-Z])',
                re.IGNORECASE
            )
            if pattern.search(text) or pattern.search(no_space):
                matched.append(w)
        else:
            # CJK 词 → 不区分大小写子串匹配（CJK 字符极少意外组成其他词）
            if w_lower in text_lower or w_lower in no_space_lower:
                matched.append(w)

    # 正则检测
    regex_rules = [
        ('手机号', r'1[3-9]\d{9}'),
        ('URL链接', r'https?://|www\.|\.com|\.cn'),
        ('微信号', r'[vV]\s*[xX]\s*[:：]\s*\w'),
        ('QQ号', r'[qQ]{2}\s*[:：]\s*\d{5,}'),
        # 短词兜底：空格绕过场景中 AV/IS 等可能已通过单词边界，此处补充独立出现
        ('IS组织', r'(?<![a-zA-Z])IS(?![a-zA-Z])'),
    ]
    for label, pattern in regex_rules:
        if re.search(pattern, text) or re.search(pattern, no_space):
            if label not in matched:
                matched.append(label)

    return len(matched) == 0, matched


def get_or_create_task(uid):
    today = date.today()
    t = DailyTask.query.filter_by(user_id=uid, task_date=today).first()
    if not t:
        t = DailyTask(user_id=uid, task_date=today)
        db.session.add(t)
        db.session.commit()
    return t


def today_salvage_used(uid):
    """今日已打捞次数"""
    ts = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return SalvageRecord.query.filter(
        SalvageRecord.user_id == uid,
        SalvageRecord.salvaged_at >= ts
    ).count()


def remaining_salvage(uid):
    """计算剩余打捞次数"""
    t = get_or_create_task(uid)
    limit = app.config['DAILY_SALVAGE_LIMIT']
    if t.throw_claimed:
        limit += app.config['TASK_THROW_REWARD']
    if t.share_claimed:
        limit += app.config['TASK_SHARE_REWARD']
    limit += t.referral_count * app.config['TASK_REFERRAL_REWARD']
    limit = min(limit, app.config['DAILY_SALVAGE_MAX'])
    return max(0, limit - today_salvage_used(uid))


def today_throw_count(uid):
    """今日已投递瓶子次数"""
    ts = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return DriftBottle.query.filter(
        DriftBottle.user_id == uid,
        DriftBottle.created_at >= ts
    ).count()


def remaining_throws(uid):
    """计算剩余投递次数"""
    return max(0, app.config['DAILY_THROW_LIMIT'] - today_throw_count(uid))


# ══════════════════════════════════════════════════
# 静态文件服务
# ══════════════════════════════════════════════════

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    upload_root = os.path.dirname(app.config['UPLOAD_FOLDER'])
    return send_from_directory(upload_root, filename)


# ══════════════════════════════════════════════════
# 首页
# ══════════════════════════════════════════════════

@app.route('/')
def index():
    ref = request.args.get('ref', type=int)
    has_task = False
    rem = 0
    rem_throw = app.config['DAILY_THROW_LIMIT']
    if current_user.is_authenticated:
        t = get_or_create_task(current_user.id)
        has_task = not t.share_claimed
        rem = remaining_salvage(current_user.id)
        rem_throw = remaining_throws(current_user.id)
    total = DriftBottle.query.filter_by(
        is_approved=True, is_deleted=False).count()
    return render_template('index.html',
                           has_new_task=has_task,
                           remaining_salvage=rem,
                           remaining_throws=rem_throw,
                           ref_id=ref,
                           total_bottles=total)


# ══════════════════════════════════════════════════
# 认证
# ══════════════════════════════════════════════════

@app.route('/auth/login', methods=['GET', 'POST'])
@csrf_required
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        pw = request.form.get('password', '')
        u = User.query.filter_by(email=email).first()
        if u and u.check_password(pw):
            login_user(u, remember=True)
            nxt = request.args.get('next', url_for('index'))
            flash(f'🌊 欢迎回来，{u.display_name()}！', 'success')
            return redirect(nxt)
        flash('邮箱或密码错误', 'error')
    return render_template('login.html')


@app.route('/auth/register', methods=['GET', 'POST'])
@csrf_required
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    # 支持 ?ref=<id> 和 ?via=<referral_code>
    ref = request.args.get('ref', type=int)
    via = request.args.get('via', '').strip()
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        pw = request.form.get('password', '')
        pw2 = request.form.get('password_confirm', '')
        nick = request.form.get('nickname', '').strip()
        promo = request.form.get('promo_code', '').strip()

        errors = []
        if User.query.filter_by(email=email).first():
            errors.append('该邮箱已注册')
        if len(pw) < 6:
            errors.append('密码至少6位')
        if pw != pw2:
            errors.append('两次密码不一致')
        if not nick:
            nick = email.split('@')[0]
        # 重名检测
        if User.query.filter_by(nickname=nick).first():
            errors.append('该用户名已被使用，请换一个')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('register.html', ref_id=ref, via=via)

        # 生成唯一 referral_code
        base_code = nick
        code = base_code
        suffix = 1
        while User.query.filter_by(referral_code=code).first():
            code = f"{base_code}{suffix}"
            suffix += 1

        u = User(email=email, nickname=nick, referral_code=code)
        u.set_password(pw)
        db.session.add(u)
        db.session.commit()

        # 处理推广码
        if promo and app.config['PROMO_CODE_ENABLED']:
            pc = PromoCode.query.filter(
                PromoCode.code == promo,
                PromoCode.used_by.is_(None),
                PromoCode.is_active == True
            ).first()
            if pc and pc.is_available:
                pc.use(u.id)
                u.promo_code_used = promo
                db.session.commit()
            elif pc:
                flash(f'推广码 {promo} 已失效', 'warning')
            else:
                flash(f'推广码 {promo} 不存在', 'warning')

        # 拉新奖励：优先 via（referral_code），回退 ref（id）
        ref_user = None
        if via:
            ref_user = User.query.filter_by(referral_code=via).first()
        if not ref_user and ref:
            ref_user = User.query.get(ref)
        if ref_user and ref_user.id != u.id:
            u.referrer_id = ref_user.id
            rt = get_or_create_task(ref_user.id)
            if rt.referral_count < app.config['TASK_REFERRAL_DAILY_MAX']:
                rt.referral_count += 1
                db.session.commit()
            sr = ShareRecord(sharer_id=ref_user.id, shared_type='activity', new_user_id=u.id)
            db.session.add(sr)
            db.session.commit()

        login_user(u, remember=True)
        flash('🎉 注册成功！', 'success')
        return redirect(url_for('index'))

    return render_template('register.html', ref_id=ref, via=via)


@app.route('/auth/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# ══════════════════════════════════════════════════
# 投递漂流瓶
# ══════════════════════════════════════════════════

@app.route('/throw', methods=['GET', 'POST'])
@login_required
@csrf_required
def throw_bottle():
    if request.method == 'POST':
        # 每日投递次数检查
        if remaining_throws(current_user.id) <= 0:
            flash(f'今日投递次数已用完（每日 {app.config["DAILY_THROW_LIMIT"]} 次），明天再来吧～', 'warning')
            return redirect(url_for('throw_bottle'))

        # 冷却检查
        last = DriftBottle.query.filter_by(
            user_id=current_user.id
        ).order_by(DriftBottle.created_at.desc()).first()
        if last:
            elapsed = (datetime.now(timezone.utc) -
                       last.created_at.replace(tzinfo=timezone.utc)).total_seconds()
            if elapsed < app.config['THROW_COOLDOWN_SECONDS']:
                flash(f'请等待 {int(app.config["THROW_COOLDOWN_SECONDS"] - elapsed)} 秒后再投递', 'warning')
                return redirect(url_for('throw_bottle'))

        title = request.form.get('title', '').strip()
        game = request.form.get('game_name', '').strip()
        cat = request.form.get('category', '').strip()
        fa = request.form.get('field_a', '').strip()
        fb = request.form.get('field_b', '').strip()
        rec = request.form.get('recommendation', '').strip()

        cat_info = Config.get_category(cat)
        if not cat_info:
            flash('请选择分类', 'error')
            return render_template('throw.html', categories=Config.CATEGORIES,
                           remaining_throws=remaining_throws(current_user.id))

        # 校验
        errors = []
        if len(title) < app.config['TITLE_MIN_LENGTH'] or len(title) > app.config['TITLE_MAX_LENGTH']:
            errors.append(f'标题需 {app.config["TITLE_MIN_LENGTH"]}-{app.config["TITLE_MAX_LENGTH"]} 字')
        if not game:
            errors.append('请填写游戏名称')
        if len(fa) < app.config['FIELD_MIN_LENGTH']:
            errors.append(f'「{cat_info["field_a_label"]}」至少 {app.config["FIELD_MIN_LENGTH"]} 字')
        if len(fb) < app.config['FIELD_MIN_LENGTH']:
            errors.append(f'「{cat_info["field_b_label"]}」至少 {app.config["FIELD_MIN_LENGTH"]} 字')
        if len(rec) < app.config['RECOMMENDATION_MIN_LENGTH']:
            errors.append(f'「强力安利」至少 {app.config["RECOMMENDATION_MIN_LENGTH"]} 字')

        # 图片校验
        if 'image' not in request.files:
            errors.append('请上传图片')
        else:
            f = request.files['image']
            if f.filename == '':
                errors.append('请选择图片')
            elif not allowed_file(f.filename):
                errors.append('仅支持 JPG/PNG/WebP')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('throw.html', categories=Config.CATEGORIES,
                           remaining_throws=remaining_throws(current_user.id))

        f = request.files['image']
        try:
            ip, tp = save_upload_image(f)
        except (ValueError, OSError) as e:
            flash(str(e), 'error')
            return render_template('throw.html', categories=Config.CATEGORIES,
                           remaining_throws=remaining_throws(current_user.id))

        # 敏感词检查
        is_clean, matched = check_sensitive(title + game + fa + fb + rec)

        bottle = DriftBottle(
            user_id=current_user.id,
            image_path=ip,
            thumbnail_path=tp,
            title=title,
            game_name=game,
            field_a=fa,
            field_b=fb,
            recommendation=rec,
            category=cat,
            is_approved=False,  # 全部进审核
            review_note=('' if is_clean else
                         f'命中敏感词: {",".join(matched)}')
        )
        db.session.add(bottle)
        db.session.commit()

        # 完成投递任务
        t = get_or_create_task(current_user.id)
        if not t.throw_claimed:
            t.throw_claimed = True
            db.session.commit()

        if is_clean:
            flash('🌊 漂流瓶已投出！等待管理员审核后上架～', 'success')
        else:
            flash('⚠️ 内容涉及敏感信息，已标记为有风险，等待管理员审核', 'warning')
        return redirect(url_for('index'))

    return render_template('throw.html', categories=Config.CATEGORIES,
                           remaining_throws=remaining_throws(current_user.id))


# ══════════════════════════════════════════════════
# 打捞漂流瓶
# ══════════════════════════════════════════════════

@app.route('/salvage')
@login_required
def salvage_page():
    return render_template('salvage.html',
                           remaining=remaining_salvage(current_user.id))


@app.route('/api/salvage/remaining')
@login_required
def api_remaining():
    return jsonify({'success': True,
                    'remaining': remaining_salvage(current_user.id)})


@app.route('/api/salvage', methods=['POST'])
@login_required
@csrf_required
def api_salvage():
    # 冷却
    last = SalvageRecord.query.filter_by(
        user_id=current_user.id
    ).order_by(SalvageRecord.salvaged_at.desc()).first()
    if last:
        elapsed = (datetime.now(timezone.utc) -
                   last.salvaged_at.replace(tzinfo=timezone.utc)).total_seconds()
        if elapsed < app.config['SALVAGE_COOLDOWN_SECONDS']:
            return jsonify({'success': False,
                            'error': f'请等待 {int(app.config["SALVAGE_COOLDOWN_SECONDS"] - elapsed)} 秒'})

    rem = remaining_salvage(current_user.id)
    if rem <= 0:
        return jsonify({'success': False, 'error': '今日打捞次数已用完'})

    # 排除已打捞 + 自己投的
    salvaged_ids = db.session.query(
        SalvageRecord.bottle_id
    ).filter_by(user_id=current_user.id).subquery()
    own_ids = db.session.query(
        DriftBottle.id
    ).filter_by(user_id=current_user.id).subquery()

    # 优先非预设
    bottle = DriftBottle.query.filter(
        DriftBottle.is_approved == True,
        DriftBottle.is_deleted == False,
        ~DriftBottle.id.in_(salvaged_ids),
        ~DriftBottle.id.in_(own_ids),
        DriftBottle.is_preset == False
    ).order_by(db.func.random()).first()

    if not bottle:
        bottle = DriftBottle.query.filter(
            DriftBottle.is_approved == True,
            DriftBottle.is_deleted == False,
            ~DriftBottle.id.in_(salvaged_ids),
            ~DriftBottle.id.in_(own_ids),
            DriftBottle.is_preset == True
        ).order_by(db.func.random()).first()

    if not bottle:
        return jsonify({'success': False, 'error': '暂时没有可打捞的漂流瓶'})

    db.session.add(SalvageRecord(user_id=current_user.id, bottle_id=bottle.id))
    db.session.commit()

    bd = bottle.to_dict(current_user)
    cat_info = Config.get_category(bottle.category)
    if cat_info:
        bd['category_name'] = cat_info['name']
        bd['category_icon'] = cat_info['icon']
        bd['field_a_label'] = cat_info['field_a_label']
        bd['field_b_label'] = cat_info['field_b_label']

    return jsonify({
        'success': True,
        'bottle': bd,
        'remaining': remaining_salvage(current_user.id)
    })


# ══════════════════════════════════════════════════
# 点赞系统
# ══════════════════════════════════════════════════

@app.route('/api/bottle/<int:bid>/like', methods=['POST'])
@login_required
@csrf_required
def api_toggle_like(bid):
    bottle = DriftBottle.query.get_or_404(bid)
    existing = BottleLike.query.filter_by(
        user_id=current_user.id, bottle_id=bid
    ).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'success': True, 'liked': False,
                        'like_count': bottle.like_count})
    else:
        db.session.add(BottleLike(user_id=current_user.id, bottle_id=bid))
        db.session.commit()
        return jsonify({'success': True, 'liked': True,
                        'like_count': bottle.like_count})


# ══════════════════════════════════════════════════
# 瓶子详情
# ══════════════════════════════════════════════════

@app.route('/bottle/<int:bid>')
def bottle_detail(bid):
    b = DriftBottle.query.get_or_404(bid)
    # 管理员可查看所有瓶子（含已删除），普通用户不可见已删除
    if b.is_deleted and not (current_user.is_authenticated and current_user.is_admin):
        abort(404)
    return render_template('bottle_detail.html',
                           bottle=b,
                           cat_info=Config.get_category(b.category))


@app.route('/s/bottle/<int:bid>')
def shared_bottle(bid):
    """分享的漂流瓶链接（无需登录可查看）"""
    b = DriftBottle.query.get_or_404(bid)
    if b.is_deleted:
        abort(404)
    return render_template('shared_bottle.html',
                           bottle=b,
                           cat_info=Config.get_category(b.category))


# ══════════════════════════════════════════════════
# 安利墙
# ══════════════════════════════════════════════════

@app.route('/wall')
@login_required
def my_wall():
    items = SalvageRecord.query.filter_by(
        user_id=current_user.id,
        is_saved_to_wall=True
    ).order_by(SalvageRecord.salvaged_at.desc()).all()
    return render_template('wall.html',
                           bottles=[r.bottle for r in items],
                           is_mine=True)


@app.route('/s/wall/<int:uid>')
def shared_wall(uid):
    """分享的安利墙（无需登录可查看）"""
    u = User.query.get_or_404(uid)
    items = SalvageRecord.query.filter_by(
        user_id=uid,
        is_saved_to_wall=True
    ).order_by(SalvageRecord.salvaged_at.desc()).all()
    return render_template('wall_public.html',
                           bottles=[r.bottle for r in items],
                           wall_user=u)


@app.route('/api/bottle/<int:bid>/save-wall', methods=['POST'])
@login_required
@csrf_required
def api_save_wall(bid):
    r = SalvageRecord.query.filter_by(
        user_id=current_user.id, bottle_id=bid
    ).first()
    if not r:
        return jsonify({'success': False, 'error': '请先打捞该漂流瓶'})
    if SalvageRecord.query.filter_by(
            user_id=current_user.id, is_saved_to_wall=True
    ).count() >= app.config['WALL_MAX_ITEMS']:
        return jsonify({'success': False,
                        'error': f'最多收藏 {app.config["WALL_MAX_ITEMS"]} 条'})
    r.is_saved_to_wall = True
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/bottle/<int:bid>/remove-wall', methods=['POST'])
@login_required
@csrf_required
def api_remove_wall(bid):
    r = SalvageRecord.query.filter_by(
        user_id=current_user.id, bottle_id=bid
    ).first()
    if r:
        r.is_saved_to_wall = False
        db.session.commit()
    return jsonify({'success': True})


# ══════════════════════════════════════════════════
# 任务中心
# ══════════════════════════════════════════════════

@app.route('/tasks')
@login_required
def tasks_page():
    t = get_or_create_task(current_user.id)
    ts = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    has_shared = ShareRecord.query.filter(
        ShareRecord.sharer_id == current_user.id,
        ShareRecord.created_at >= ts
    ).first() is not None

    return render_template('tasks.html',
                           task=t,
                           remaining=remaining_salvage(current_user.id),
                           today_used=today_salvage_used(current_user.id),
                           has_shared=has_shared,
                           daily_limit=app.config['DAILY_SALVAGE_LIMIT'],
                           daily_max=app.config['DAILY_SALVAGE_MAX'],
                           throw_reward=app.config['TASK_THROW_REWARD'],
                           share_reward=app.config['TASK_SHARE_REWARD'],
                           referral_reward=app.config['TASK_REFERRAL_REWARD'],
                           referral_max=app.config['TASK_REFERRAL_DAILY_MAX'])


@app.route('/api/tasks/claim-share', methods=['POST'])
@login_required
@csrf_required
def api_claim_share():
    t = get_or_create_task(current_user.id)
    if t.share_claimed:
        return jsonify({'success': False, 'error': '今日已领取'})
    ts = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if not ShareRecord.query.filter(
            ShareRecord.sharer_id == current_user.id,
            ShareRecord.created_at >= ts
    ).first():
        return jsonify({'success': False, 'error': '请先分享再领取'})
    t.share_claimed = True
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'+{app.config["TASK_SHARE_REWARD"]} 次打捞机会！',
        'remaining': remaining_salvage(current_user.id)
    })


# ══════════════════════════════════════════════════
# 分享追踪
# ══════════════════════════════════════════════════

@app.route('/api/share/track', methods=['POST'])
@login_required
@csrf_required
def api_track():
    """记录分享行为，并自动领取每日分享奖励（如未领取）"""
    d = request.json or {}
    sr = ShareRecord(
        sharer_id=current_user.id,
        shared_type=d.get('type', 'activity'),
        shared_target_id=d.get('target_id')
    )
    db.session.add(sr)
    db.session.commit()

    # 自动领取每日分享奖励
    share_claimed = False
    share_reward = 0
    t = get_or_create_task(current_user.id)
    if not t.share_claimed:
        t.share_claimed = True
        db.session.commit()
        share_claimed = True
        share_reward = app.config['TASK_SHARE_REWARD']

    return jsonify({
        'success': True,
        'share_claimed': share_claimed,
        'share_reward': share_reward,
        'remaining': remaining_salvage(current_user.id)
    })


# ══════════════════════════════════════════════════
# 推广码管理
# ══════════════════════════════════════════════════

@app.route('/admin/promo', methods=['GET', 'POST'])
@login_required
@admin_required
@csrf_required
def manage_promo():
    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'generate':
            count = int(request.form.get('count', 5))
            channel = request.form.get('channel_name', '').strip()
            max_uses = int(request.form.get('max_uses', 1))
            codes = []
            for _ in range(count):
                pc = PromoCode(
                    code=f'GUANGHE{uuid.uuid4().hex[:8].upper()}',
                    channel_name=channel,
                    created_by=current_user.id,
                    max_uses=max_uses
                )
                db.session.add(pc)
                codes.append(pc.code)
            db.session.commit()
            admin_log = AdminLog(admin_id=current_user.id, action='generate_promo',
                         note=f'生成 {count} 个推广码，渠道: {channel}', target_type='promo')
            db.session.add(admin_log)
            db.session.commit()
            flash(f'已生成 {count} 个推广码：{", ".join(codes)}', 'success')

        elif action == 'deactivate':
            code_id = request.form.get('code_id', type=int)
            pc = PromoCode.query.get(code_id)
            if pc:
                pc.is_active = False
                AdminLog(admin_id=current_user.id, action='deactivate_promo',
                         target_type='promo', target_id=code_id,
                         note=f'停用推广码 {pc.code}')
                db.session.commit()
                flash(f'已停用推广码 {pc.code}', 'success')

    codes = PromoCode.query.order_by(PromoCode.created_at.desc()).limit(50).all()
    return render_template('admin/promo.html', codes=codes)


# ══════════════════════════════════════════════════
# 后台管理
# ══════════════════════════════════════════════════

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    stats = {
        'total_users': User.query.count(),
        'total_bottles': DriftBottle.query.filter_by(is_deleted=False).count(),
        'approved': DriftBottle.query.filter_by(
            is_approved=True, is_deleted=False).count(),
        'pending': DriftBottle.query.filter(
            DriftBottle.is_approved == False,
            DriftBottle.is_deleted == False,
            (DriftBottle.review_note == '') |
            (DriftBottle.review_note.is_(None))
        ).count(),
        'risky': DriftBottle.query.filter(
            DriftBottle.is_approved == False,
            DriftBottle.is_deleted == False,
            DriftBottle.review_note.like('命中敏感词:%')
        ).count(),
        'rejected': DriftBottle.query.filter_by(is_deleted=True).count(),
        'salvages': SalvageRecord.query.count(),
        'wall_saves': SalvageRecord.query.filter_by(is_saved_to_wall=True).count(),
        'shares': ShareRecord.query.count(),
        'promo_used': PromoCode.query.filter(PromoCode.used_by.isnot(None)).count(),
    }

    # 各分类占比
    from sqlalchemy import func
    cat_stats = db.session.query(
        DriftBottle.category,
        func.count(DriftBottle.id)
    ).group_by(DriftBottle.category).all()
    cat_data = []
    for cat_id, cnt in cat_stats:
        info = Config.get_category(cat_id)
        cat_data.append({
            'name': info['name'] if info else cat_id,
            'icon': info['icon'] if info else '',
            'count': cnt
        })

    return render_template('admin/dashboard.html', stats=stats, cat_data=cat_data)


@app.route('/admin/review')
@login_required
@admin_required
def admin_review():
    """审核页：三栏——有风险 / 未审核 / 已审核"""
    page = request.args.get('page', 1, type=int)
    tab = request.args.get('tab', 'risky')

    if tab == 'risky':
        q = DriftBottle.query.filter_by(is_deleted=False)
        # 命中敏感词，待审
        q = q.filter(
            DriftBottle.is_approved == False,
            DriftBottle.review_note.like('命中敏感词:%')
        )
    elif tab == 'pending':
        q = DriftBottle.query.filter_by(is_deleted=False)
        # 干净，待审
        q = q.filter(
            DriftBottle.is_approved == False,
            (DriftBottle.review_note == '') |
            (DriftBottle.review_note.is_(None))
        )
    else:
        # 已审核：通过的 + 驳回的（不含 is_deleted 预过滤，否则打回瓶不显示）
        q = DriftBottle.query.filter(
            (DriftBottle.is_approved == True) |
            (DriftBottle.review_note.like('驳回:%')) |
            (DriftBottle.is_deleted == True)
        )

    bottles = q.order_by(DriftBottle.created_at.desc()).paginate(
        page=page, per_page=app.config.get('BOTTLES_PER_PAGE', 20),
        error_out=False
    )
    return render_template('admin/review.html',
                           bottles=bottles, tab=tab)


@app.route('/api/admin/review/<int:bid>', methods=['POST'])
@login_required
@admin_required
@csrf_required
def api_review(bid):
    b = DriftBottle.query.get_or_404(bid)
    action = (request.json or {}).get('action', 'approve')
    note = (request.json or {}).get('note', '')
    if action == 'approve':
        b.is_approved = True
        b.is_deleted = False
        b.review_note = note or '管理员审核通过'
        al = AdminLog(admin_id=current_user.id, action='approve',
                      target_type='bottle', target_id=bid, note=note)
    elif action == 'reject':
        # 打回：软删除 + 从所有安利墙移除
        b.is_approved = False
        b.is_deleted = True
        b.review_note = f'驳回: {note}' if note else '驳回: 内容违规'
        # 清除所有收藏记录
        SalvageRecord.query.filter_by(bottle_id=bid).delete()
        al = AdminLog(admin_id=current_user.id, action='reject',
                      target_type='bottle', target_id=bid, note=note)
    elif action == 'unreject':
        # 撤销驳回：回到未审核状态
        b.is_approved = False
        b.is_deleted = False
        b.review_note = ''
        al = AdminLog(admin_id=current_user.id, action='unreject',
                      target_type='bottle', target_id=bid, note=note)
    elif action == 'delete':
        # 硬删除
        SalvageRecord.query.filter_by(bottle_id=bid).delete()
        db.session.delete(b)
        al = AdminLog(admin_id=current_user.id, action='delete',
                      target_type='bottle', target_id=bid, note=note)
    db.session.add(al)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/admin/data')
@login_required
@admin_required
def admin_data():
    from sqlalchemy import func

    # 每日活跃用户
    dau = db.session.query(
        func.date(SalvageRecord.salvaged_at),
        func.count(func.distinct(SalvageRecord.user_id))
    ).group_by(func.date(SalvageRecord.salvaged_at)).order_by(
        func.date(SalvageRecord.salvaged_at).desc()
    ).limit(30).all()

    # 每日投递量
    daily_throws = db.session.query(
        func.date(DriftBottle.created_at),
        func.count(DriftBottle.id)
    ).group_by(func.date(DriftBottle.created_at)).order_by(
        func.date(DriftBottle.created_at).desc()
    ).limit(30).all()

    return render_template('admin/data.html',
                           dau=dau,
                           daily_throws=daily_throws)


# ══════════════════════════════════════════════════
# 初始化数据库
# ══════════════════════════════════════════════════

def init_db():
    """创建表 + 自动迁移旧库 + 写入种子数据"""
    with app.app_context():
        db.create_all()

        # ── 自动迁移：兼容旧数据库 ──
        import sqlite3
        db_path = os.path.join(app.instance_path, 'bottle.db')
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            # 获取现有列
            cur.execute("PRAGMA table_info(users)")
            cols = {row[1] for row in cur.fetchall()}
            # 补 referral_code 列
            if 'referral_code' not in cols:
                cur.execute("ALTER TABLE users ADD COLUMN referral_code VARCHAR(60)")
                print('[迁移] 已添加 users.referral_code 列')
            # 补 is_deleted 列（drift_bottles 表）
            cur.execute("PRAGMA table_info(drift_bottles)")
            bottle_cols = {row[1] for row in cur.fetchall()}
            if 'is_deleted' not in bottle_cols:
                cur.execute("ALTER TABLE drift_bottles ADD COLUMN is_deleted BOOLEAN DEFAULT 0")
                print('[迁移] 已添加 drift_bottles.is_deleted 列')
            conn.commit()
            conn.close()

        # ── 补充旧用户的 referral_code ──
        users_no_code = User.query.filter(User.referral_code.is_(None)).all()
        for u in users_no_code:
            u.referral_code = u.nickname or u.email.split('@')[0]
        if users_no_code:
            db.session.commit()
            print(f'[迁移] 已为 {len(users_no_code)} 个旧用户生成 referral_code')

        # ── 管理员账号 ──
        admins = [
            ('admin1@guanghe.com', 'admin1'),
            ('admin2@guanghe.com', 'admin2'),
            ('admin3@guanghe.com', 'admin3'),
        ]
        for email, nick in admins:
            if not User.query.filter_by(email=email).first():
                a = User(email=email, nickname=nick, is_admin=True, referral_code=nick)
                a.set_password('admin123')
                db.session.add(a)

        # ── 测试玩家 ──
        if not User.query.filter_by(email='player@guanghe.com').first():
            p = User(email='player@guanghe.com', nickname='player', referral_code='player')
            p.set_password('player123')
            db.session.add(p)

        db.session.commit()

        # ── 种子瓶子 ──
        if DriftBottle.query.count() == 0:
            from seed_data import seed_bottles
            for s in seed_bottles:
                db.session.add(DriftBottle(
                    title=s['title'],
                    game_name=s['game_name'],
                    category=s['category'],
                    field_a=s['field_a'],
                    field_b=s['field_b'],
                    recommendation=s['recommendation'],
                    image_path='static/images/placeholder.png',
                    thumbnail_path='static/images/placeholder_thumb.png',
                    is_preset=True,
                    is_approved=True,
                ))
            db.session.commit()

        # ── 初始推广码 ──
        if PromoCode.query.count() == 0:
            for _ in range(10):
                db.session.add(PromoCode(
                    code=f'GUANGHE{uuid.uuid4().hex[:8].upper()}',
                    channel_name='初始渠道',
                    created_by=1,
                    max_uses=1
                ))
            db.session.commit()


# ══════════════════════════════════════════════════
# 启动
# ══════════════════════════════════════════════════

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    print('=' * 50)
    print('  光核安利漂流瓶 v5  StarrySea')
    print(f'  URL: http://localhost:{port}')
    print('=' * 50)
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
