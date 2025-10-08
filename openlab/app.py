import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# === DB接続設定（Postgres/SQLite両対応） ===
db_url = os.environ.get("DATABASE_URL", "sqlite:///openlab.db")

# RenderのURLは 'postgres://' 形式のことがあるので、SQLAlchemy用に置換
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://"):
    # 明示的にpsycopgドライバ指定（任意）
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

# sslmodeが無い場合の保険（通常はExternal URLに付いてる）
if "postgresql+psycopg://" in db_url and "sslmode=" not in db_url:
    sep = "&" if "?" in db_url else "?"
    db_url = f"{db_url}{sep}sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# 接続の生存確認（再接続）を有効化して安定化
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}

db = SQLAlchemy(app)

# 投稿モデル
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.now)

# コメントモデル
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    parent_id = db.Column(db.Integer, nullable=True)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.now)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    categories = db.session.query(Post.category).distinct().all()
    posts = Post.query.order_by(Post.date.desc()).all()
    return render_template('index.html', posts=posts, categories=categories)

@app.route('/category/<name>')
def category(name):
    posts = Post.query.filter_by(category=name).order_by(Post.date.desc()).all()
    return render_template('category.html', posts=posts, category=name)

@app.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    comments = Comment.query.filter_by(post_id=id).all()

    # コメント投稿
    if request.method == 'POST':
        content = request.form['content']
        parent_id = request.form.get('parent_id')
        comment = Comment(post_id=id, parent_id=parent_id, content=content)
        db.session.add(comment)
        db.session.commit()
        return redirect(url_for('post', id=id))

    return render_template('post.html', post=post, comments=comments)

@app.route('/new', methods=['GET', 'POST'])
def new():
    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        content = request.form['content']
        post = Post(title=title, category=category, content=content)
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('index'))
    return '''
    <h2>新しい投稿を作成</h2>
    <form method="POST">
      タイトル: <input name="title"><br>
      カテゴリ: <input name="category"><br>
      本文:<br><textarea name="content" rows="5" cols="50"></textarea><br>
      <button type="submit">投稿</button>
    </form>
    '''

if __name__ == '__main__':
    app.run(debug=True)
