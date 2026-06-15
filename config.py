"""
光核安利漂流瓶 — 配置文件
======================
7大内容分类 · 活动规则 · 服务器配置
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """全局配置"""

    # ── Flask 核心 ──────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY', 'guanghe-bottle-2026-seaside-v5')
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'
    TEMPLATES_AUTO_RELOAD = True

    # ── 数据库 ──────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{os.path.join(BASE_DIR, "instance", "bottle.db")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── 上传 ────────────────────────────────────
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads', 'bottles')
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024   # 20 MB
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
    THUMBNAIL_SIZE = (400, 300)

    # ── 敏感词 ──────────────────────────────────
    SENSITIVE_WORDS_FILE = os.path.join(BASE_DIR, 'sensitive_words.txt')

    # ── 分页 ────────────────────────────────────
    BOTTLES_PER_PAGE = 12

    # ══════════════════════════════════════════════
    # 活动规则
    # ══════════════════════════════════════════════

    # 每日投递次数上限
    DAILY_THROW_LIMIT = 5

    # 每日基础打捞次数
    DAILY_SALVAGE_LIMIT = 1

    # 任务奖励（次数）
    TASK_THROW_REWARD = 1       # 投递一个瓶子
    TASK_SHARE_REWARD = 1       # 分享活动/安利墙/瓶子
    TASK_REFERRAL_REWARD = 1    # 拉新成功（每人）
    TASK_REFERRAL_DAILY_MAX = 2  # 每日拉新上限（人）

    # 每日打捞总上限（999+ 给测试账号留空间）
    DAILY_SALVAGE_MAX = 5

    # 字数限制
    TITLE_MIN_LENGTH = 1
    TITLE_MAX_LENGTH = 30
    FIELD_MIN_LENGTH = 5
    FIELD_MAX_LENGTH = 200
    RECOMMENDATION_MIN_LENGTH = 5
    RECOMMENDATION_MAX_LENGTH = 200

    # 防刷冷却（秒）
    THROW_COOLDOWN_SECONDS = 10
    SALVAGE_COOLDOWN_SECONDS = 2

    # 安利墙
    WALL_MAX_ITEMS = 9
    WALL_LAYOUTS = ['nine', 'four']

    # ── 动画时间（毫秒） ─────────────────────────
    TRANSITION_PAUSE_MS = 400     # 背景切换停留（缩短，减少等待）
    WHITE_SCREEN_MS = 350         # 过渡遮罩（缩短，柔化体验）

    # ══════════════════════════════════════════════
    # 7 大内容分类
    # ══════════════════════════════════════════════
    CATEGORIES = [
        {
            'id': 'epic_screenshot',
            'name': '炸裂截图',
            'icon': '📸',
            'description': (
                '快把你相册里那张极具张力的神仙构图或"抽象行为"截图分享出来，'
                '它可能复刻了游戏的经典站位，也可能代表你目前抽象的精神状态，'
                '别光顾着自己乐，快用这些炸裂的截图，经典的站位，抽象的精神状态，'
                '狠狠给人安利一波！告诉TA，这游戏值得入坑！'
            ),
            'field_a_label': '这张图发生的前提',
            'field_b_label': '最绝的地方在于',
            'field_a_hint': '简述当时的离谱状况/绝佳的构图时机...',
            'field_b_hint': '难以达成的情景/物理引擎崩坏/教科书站位...',
        },
        {
            'id': 'stunning_scene',
            'name': '绝美场景',
            'icon': '🌅',
            'description': (
                '晒出那个让你舍不得移开视线的游戏风景——无论是宏伟的建筑、唯美的画风，'
                '还是与剧情完美契合的场面，或者是那个让你觉得设计精妙的游戏场景，'
                '这样的视觉调度绝对值得TA亲自走一趟。'
            ),
            'field_a_label': '打卡地/时机',
            'field_b_label': '这画面神在哪里',
            'field_a_hint': '打完boss后的黄昏/地图边缘的隐藏山峰...',
            'field_b_hint': '体积光/粒子雾/材质反射/巨物感/整体氛围叙事...',
        },
        {
            'id': 'character_design',
            'name': '人物塑造',
            'icon': '💖',
            'description': (
                '有没有一张脸，让你第一眼就沉沦？有没有一个角色，让你通关许久以后仍念念不忘？'
                '无论是最惊艳的外观设计还是最深刻的性格塑造，向陌生的玩家疯狂安利TA吧，'
                '让大家看看这款游戏的人物塑造到底有多神！'
            ),
            'field_a_label': 'TA是谁',
            'field_b_label': '为什么让我印象深刻',
            'field_a_hint': '主角捏脸/某个NPC/BOSS...',
            'field_b_hint': '模型细节/高光行为/意难平瞬间...',
        },
        {
            'id': 'art_appreciation',
            'name': '美术鉴赏',
            'icon': '🎨',
            'description': (
                '晒出游戏中你认为最具设计感的皮肤、涂装，装修理念甚至美术风格。'
                '向捞瓶子的人安利这游戏的审美有多绝。'
            ),
            'field_a_label': '皮肤/外观名',
            'field_b_label': '设计最戳我的点',
            'field_a_hint': '武器名称/皮肤名称/车辆涂装...',
            'field_b_hint': '元素设计/纹样/色彩搭配/材质光泽...',
        },
        {
            'id': 'story_screening',
            'name': '剧情放映',
            'icon': '🎬',
            'description': (
                '一句动人的台词，一段过场分镜、一个意难平的结局，一个深刻共鸣的故事让你过目不忘。'
                '把这个让你头皮发麻的神级剧本，快快安利给下一个人入坑吧。'
            ),
            'field_a_label': '这是什么情节',
            'field_b_label': '当时的心理活动',
            'field_a_hint': '苦战后的告别/序章的惊天反转...',
            'field_b_hint': '头皮发麻、爆哭或极其震撼的情绪...',
        },
        {
            'id': 'hardcore_showdown',
            'name': '硬核博弈',
            'icon': '⚔️',
            'description': (
                '它可以不只是干瘪的结算面板！快晒出你残局反杀的高光时刻，'
                '值得纪念的游戏博弈截图和你认为值得宣传的对战瞬间，'
                '告诉捞起瓶子的人这游戏的博弈有多爽，直接拉TA入坑！'
            ),
            'field_a_label': '当时的境况',
            'field_b_label': '决定性瞬间',
            'field_a_hint': '队友全倒/Boss一丝血/无伤挑战...',
            'field_b_hint': '极限操作/完美弹反/拉枪线...',
        },
        {
            'id': 'beyond_screen',
            'name': '屏幕外回响',
            'icon': '🌟',
            'description': (
                '游戏是虚拟的，但带给你的力量是真实的，'
                '它或许经历了你和朋友度过的愉快时光也或许见证了无数令人感动的玩家故事。'
                '用你的经历写下一段最真诚的安利，告诉陌生人这款游戏如何惊艳了你的时光，走进了你的生活。'
            ),
            'field_a_label': '经历游戏时的现实背景',
            'field_b_label': '游戏/陪我玩的人给了我什么',
            'field_a_hint': '室友开黑/大学毕业/工作最迷茫的低谷期...',
            'field_b_hint': '一段真实的陪伴、治愈或从游戏角色身上汲取的力量...',
        },
    ]

    # ── 分类辅助方法 ────────────────────────────
    @classmethod
    def get_category(cls, category_id):
        """根据分类 ID 返回完整分类信息"""
        for cat in cls.CATEGORIES:
            if cat['id'] == category_id:
                return cat
        return None

    @classmethod
    def get_category_choices(cls):
        """返回 [(id, display_name), ...] 用于表单"""
        return [(cat['id'], f"{cat['icon']} {cat['name']}") for cat in cls.CATEGORIES]
