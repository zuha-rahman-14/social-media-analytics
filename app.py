from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os, json
from datetime import datetime
from ml_modules.image_detector import ImageTamperDetector
from ml_modules.text_detector import TextManipulationDetector

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

image_detector = ImageTamperDetector()
text_detector = TextManipulationDetector()


# ── Models ────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship('Post', backref='author', lazy=True)

    def set_password(self, p): self.password_hash = generate_password_hash(p)
    def check_password(self, p): return check_password_hash(self.password_hash, p)


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    caption = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    likes = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    shares = db.Column(db.Integer, default=0)
    engagement_score = db.Column(db.Float, default=0.0)
    image_tamper_score = db.Column(db.Float, default=0.0)
    image_tamper_label = db.Column(db.String(50), default='N/A')
    text_manipulation_score = db.Column(db.Float, default=0.0)
    text_manipulation_label = db.Column(db.String(50), default='N/A')
    is_flagged = db.Column(db.Boolean, default=False)
    flag_reason = db.Column(db.Text)
    platform = db.Column(db.String(50), default='Instagram')
    posted_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def compute_engagement(self):
        self.engagement_score = round(self.likes * 1.0 + self.comments_count * 2.0 + self.shares * 3.0, 2)


@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

def allowed_file(fn): return '.' in fn and fn.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Auth Routes ───────────────────────────────────────────────────────
@app.route('/')
def index(): return redirect(url_for('dashboard') if current_user.is_authenticated else url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user); return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uname = request.form.get('username')
        if User.query.filter_by(username=uname).first():
            flash('Username taken', 'danger'); return render_template('register.html')
        u = User(username=uname, email=request.form.get('email'))
        u.set_password(request.form.get('password'))
        db.session.add(u); db.session.commit(); login_user(u)
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout(): logout_user(); return redirect(url_for('login'))


# ── Dashboard ─────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    uid = current_user.id
    posts = Post.query.filter_by(user_id=uid).order_by(Post.created_at.desc()).limit(6).all()
    total = Post.query.filter_by(user_id=uid).count()
    flagged = Post.query.filter_by(user_id=uid, is_flagged=True).count()
    avg_eng = db.session.query(db.func.avg(Post.engagement_score)).filter_by(user_id=uid).scalar() or 0

    chart_posts = Post.query.filter_by(user_id=uid).order_by(Post.created_at.desc()).limit(7).all()
    labels = [p.posted_at.strftime('%b %d') for p in reversed(chart_posts)]
    eng_data = [p.engagement_score for p in reversed(chart_posts)]
    tamper_data = [round(p.image_tamper_score * 100, 1) for p in reversed(chart_posts)]

    return render_template('dashboard.html',
        posts=posts, total=total, flagged=flagged, avg_engagement=round(avg_eng, 1),
        chart_labels=json.dumps(labels),
        chart_engagement=json.dumps(eng_data),
        chart_tamper=json.dumps(tamper_data))


# ── Analyze ───────────────────────────────────────────────────────────
@app.route('/analyze', methods=['GET', 'POST'])
@login_required
def analyze():
    if request.method == 'POST':
        caption = request.form.get('caption', '')
        likes = int(request.form.get('likes', 0))
        comments_count = int(request.form.get('comments_count', 0))
        shares = int(request.form.get('shares', 0))
        platform = request.form.get('platform', 'Instagram')
        image_path = None

        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            fname = secure_filename(f"{datetime.utcnow().timestamp()}_{file.filename}")
            fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
            file.save(fpath)
            image_path = os.path.join('uploads', fname)

        img_score, img_label = (0.0, 'No Image')
        if image_path:
            img_score, img_label = image_detector.detect(os.path.join('static', image_path))

        txt_score, txt_label, txt_details = (0.0, 'No Caption', [])
        if caption:
            txt_score, txt_label, txt_details = text_detector.detect(caption)

        post = Post(
            user_id=current_user.id, caption=caption, image_path=image_path,
            likes=likes, comments_count=comments_count, shares=shares, platform=platform,
            image_tamper_score=img_score, image_tamper_label=img_label,
            text_manipulation_score=txt_score, text_manipulation_label=txt_label,
        )
        post.compute_engagement()

        if img_score > 0.65 or txt_score > 0.65:
            post.is_flagged = True
            reasons = []
            if img_score > 0.65: reasons.append(f"Image tamper: {img_score:.0%}")
            if txt_score > 0.65: reasons.append(f"Text manipulation: {txt_score:.0%}")
            post.flag_reason = ' | '.join(reasons)

        db.session.add(post); db.session.commit()
        return render_template('result.html', post=post, txt_details=txt_details)

    return render_template('analyze.html')


# ── Posts List ────────────────────────────────────────────────────────
@app.route('/posts')
@login_required
def posts():
    page = request.args.get('page', 1, type=int)
    flag_filter = request.args.get('flagged', 'all')
    q = Post.query.filter_by(user_id=current_user.id)
    if flag_filter == 'flagged': q = q.filter_by(is_flagged=True)
    elif flag_filter == 'clean': q = q.filter_by(is_flagged=False)
    paged = q.order_by(Post.created_at.desc()).paginate(page=page, per_page=12)
    return render_template('posts.html', posts=paged, filter_flag=flag_filter)


@app.route('/post/<int:pid>/delete', methods=['POST'])
@login_required
def delete_post(pid):
    post = Post.query.get_or_404(pid)
    if post.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    db.session.delete(post); db.session.commit()
    return redirect(url_for('posts'))


# ── API ───────────────────────────────────────────────────────────────
@app.route('/api/stats')
@login_required
def api_stats():
    all_posts = Post.query.filter_by(user_id=current_user.id).all()
    return jsonify({
        'total': len(all_posts),
        'flagged': sum(1 for p in all_posts if p.is_flagged),
        'avg_engagement': round(sum(p.engagement_score for p in all_posts) / max(len(all_posts), 1), 2),
        'tampered_images': sum(1 for p in all_posts if p.image_tamper_score > 0.65),
        'manipulated_text': sum(1 for p in all_posts if p.text_manipulation_score > 0.65),
    })


@app.route('/api/quick-text-check', methods=['POST'])
@login_required
def quick_text_check():
    data = request.get_json()
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    score, label, details = text_detector.detect(text)
    return jsonify({'score': score, 'label': label, 'details': details})

# Create tables on startup (for Render)
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
