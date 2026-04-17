#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人中博客系统 - Flask + MongoDB + MySQL
完整功能包括用户注册、文章管理、评论系统、管理员后台、文章发表等
"""
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from bson import ObjectId
from pymongo import MongoClient
import json
import random
import os
import shutil
from database import engine, Base, MySQLSession, SessionLocal
import pandas as pd
from functools import wraps
import time
from flask_babel import Babel
from datetime import datetime
from sqlalchemy import text
app = Flask(__name__)
app.secret_key = 'renzhong-blog-secret-key-2024-complete-mongodb-mysql'
with engine.begin() as conn:
    Base.metadata.create_all(bind=engine)
# MongoDB配置
mongo_client = MongoClient('mongodb://localhost:27017/')
mongo_db = mongo_client['renzhong']

# MySQL配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:123456@localhost/rz'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# MongoDB集合
articles_collection = mongo_db['articles']
likes_collection = mongo_db['likes']
favorites_collection = mongo_db['favorites']
search_history_collection = mongo_db['search_history']
logs_collection = mongo_db['logs']
categories_collection = mongo_db['categories']
users_collection = mongo_db['users']

# MySQL模型
class Comment(db.Model):
    """评论模型 - 存储在MySQL中"""
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    article_id = db.Column(db.String(50), nullable=False, index=True)
    user_id = db.Column(db.String(50), nullable=False, index=True)
    username = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, nullable=True, index=True)
    like_count = db.Column(db.Integer, default=0)
    publish_time = db.Column(db.DateTime, default=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'article_id': self.article_id,
            'user_id': self.user_id,
            'username': self.username,
            'content': self.content,
            'parent_id': self.parent_id,
            'like_count': self.like_count,
            'publish_time': self.publish_time.isoformat()
        }

class Author(db.Model):
    """作者信息模型 - 存储在MySQL中"""
    __tablename__ = 'authors'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    author_url = db.Column(db.String(200))
    fans_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'author_url': self.author_url,
            'fans_count': self.fans_count,
            'created_at': self.created_at.isoformat()
        }

class User(UserMixin):
    """用户模型 - 用于Flask-Login"""
    def __init__(self, user_data):
        self.id       = str(user_data['_id'])
        self.username = user_data['username']
        self.role     = user_data.get('role', 'user')
        self.phone    = user_data.get('phone', '')
        # 把值存到私有变量，再由 property 暴露
        self._is_active = user_data.get('is_active', True)

    # 只读
    @property
    def is_active(self):
        return self._is_active

    # 可写（Flask-Login 需要）
    @is_active.setter
    def is_active(self, value):
        self._is_active = bool(value)

    @staticmethod
    def get(user_id):
        user_data = users_collection.find_one({'_id': ObjectId(user_id)})
        return User(user_data) if user_data else None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# JSON编码器
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

app.json_encoder = JSONEncoder

# 记录日志
def log_action(user_id, action, details):
    log_entry = {
        'user_id': user_id,
        'action': action,
        'details': details,
        'timestamp': datetime.now(),
        'ip': request.remote_addr
    }
    logs_collection.insert_one(log_entry)

# 首页
@app.route('/')
def index():
    try:
        # 获取所有分类
        categories = list(categories_collection.find())
        
        # 获取排序参数
        sort_by = request.args.get('sort', 'publish_time')
        order = request.args.get('order', 'desc')
        category_filter = request.args.get('category', '')
        
        # 构建查询
        query = {}
        if category_filter:
            query['main_category'] = category_filter
        
        # 排序
        sort_field = sort_by if sort_by in ['like_count', 'collect_count', 'comment_count', 'publish_time', 'read_count', 'content_length'] else 'publish_time'
        sort_order = -1 if order == 'desc' else 1
        
        # 获取文章
        articles = list(articles_collection.find(query).sort(sort_field, sort_order).limit(20))
        
        return render_template('index.html', 
                             articles=articles, 
                             categories=categories,
                             current_sort=sort_by,
                             current_order=order,
                             current_category=category_filter)
    except Exception as e:
        print(f"Index error: {e}")
        flash('页面加载失败', 'danger')
        return redirect(url_for('index'))

# 刷新推荐
@app.route('/refresh')
@login_required
def refresh():
    """根据用户行为推荐文章"""
    user_id = current_user.id
    
    # 获取用户点赞和评论过的文章标签
    user_likes = list(likes_collection.find({'user_id': user_id, 'type': 'article'}))
    user_comments = list(Comment.query.filter_by(user_id=user_id).all())
    
    # 收集用户感兴趣的标签
    interested_tags = set()
    
    for like in user_likes:
        article = articles_collection.find_one({'_id': ObjectId(like['target_id'])})
        if article:
            interested_tags.add(article.get('main_category', ''))
            interested_tags.add(article.get('sub_category', ''))
    
    for comment in user_comments:
        article = articles_collection.find_one({'_id': ObjectId(comment.article_id)})
        if article:
            interested_tags.add(article.get('main_category', ''))
            interested_tags.add(article.get('sub_category', ''))
    
    # 如果没有行为数据，随机推荐
    if not interested_tags:
        articles = list(articles_collection.aggregate([{'$sample': {'size': 20}}]))
    else:
        # 根据感兴趣的标签推荐
        query = {
            '$or': [
                {'main_category': {'$in': list(interested_tags)}},
                {'sub_category': {'$in': list(interested_tags)}}
            ]
        }
        articles = list(articles_collection.find(query).limit(20))
        
        # 如果标签相关文章不足，补充随机文章
        if len(articles) < 20:
            remaining = 20 - len(articles)
            exclude_ids = [str(a['_id']) for a in articles]
            random_articles = list(articles_collection.aggregate([
                {'$match': {'_id': {'$nin': [ObjectId(id) for id in exclude_ids]}}},
                {'$sample': {'size': remaining}}
            ]))
            articles.extend(random_articles)
    
    # 随机打乱
    random.shuffle(articles)
    
    log_action(user_id, 'refresh', '刷新推荐文章')
    return jsonify({'status': 'success', 'articles': articles})

# 搜索
@app.route('/search')
def search():
    keyword = request.args.get('q', '').strip()
    
    if not keyword:
        return redirect(url_for('index'))
    
    # 保存搜索历史
    if current_user.is_authenticated:
        search_history = {
            'user_id': current_user.id,
            'keyword': keyword,
            'timestamp': datetime.now()
        }
        search_history_collection.insert_one(search_history)
    
    # 搜索文章
    query = {
        '$or': [
            {'title': {'$regex': keyword, '$options': 'i'}},
            {'author': {'$regex': keyword, '$options': 'i'}},
            {'main_category': {'$regex': keyword, '$options': 'i'}},
            {'sub_category': {'$regex': keyword, '$options': 'i'}}
        ]
    }
    
    articles = list(articles_collection.find(query))
    
    # 记录日志
    if current_user.is_authenticated:
        log_action(current_user.id, 'search', f'搜索关键词: {keyword}')
    
    return render_template('search_results.html', articles=articles, keyword=keyword)

# 搜索历史


@app.route('/search_history')
@login_required
def get_search_history():
    user_id = current_user.id

    try:
        with MySQLSession() as session:
            # 查询搜索历史
            sql = text("""
                SELECT id, search_query AS query, timestamp 
                FROM search_history 
                WHERE user_id = :user_id 
                ORDER BY timestamp DESC 
                LIMIT 50
            """)
            result = session.execute(sql, {'user_id': user_id}).mappings().all()
            history = [dict(row) for row in result]

        # 转换timestamp为ISO格式
        for item in history:
            if 'timestamp' in item and hasattr(item['timestamp'], 'isoformat'):
                item['timestamp'] = item['timestamp'].isoformat()

        return jsonify({'status': 'success', 'history': history})

    except Exception as e:
        app.logger.error(f"获取搜索历史失败: {str(e)}")
        return jsonify({'status': 'error', 'message': '获取搜索历史失败'}), 500


@app.route('/delete_search_history/<history_id>', methods=['DELETE'])
@login_required
def delete_search_history(history_id):
    user_id = current_user.id

    # 验证history_id是否为数字
    if not history_id.isdigit():
        return jsonify({'status': 'error', 'message': '无效的历史ID格式'}), 400

    try:
        with MySQLSession() as session:
            sql = text("""
                DELETE FROM search_history 
                WHERE id = :history_id AND user_id = :user_id
            """)
            result = session.execute(sql, {
                'history_id': int(history_id),
                'user_id': user_id
            })
            deleted_count = result.rowcount

        if deleted_count > 0:
            # 记录操作日志（如果已实现）
            try:
                log_action(user_id, 'delete_search_history', f'删除搜索历史: {history_id}')
            except:
                pass  # 日志记录失败不应影响主要功能

            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': '删除失败或记录不存在'}), 404

    except Exception as e:
        app.logger.error(f"删除搜索历史失败: {str(e)}")
        return jsonify({'status': 'error', 'message': '服务器内部错误'}), 500




# 注册
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()
        
        # 验证
        if not username or not password:
            flash('用户名和密码不能为空', 'danger')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('密码长度至少6位', 'danger')
            return render_template('register.html')
        
        # 检查用户名是否存在
        existing_user = users_collection.find_one({'username': username})
        if existing_user:
            flash('用户名已存在', 'danger')
            return render_template('register.html')
        
        # 创建用户
        new_user = {
            'username': username,
            'password': generate_password_hash(password),
            'phone': phone,
            'role': 'user',
            'created_at': datetime.now(),
            'last_login': None,
            'is_active': True
        }
        
        result = users_collection.insert_one(new_user)
        
        # 创建作者信息
        author = Author(username=username, author_url='', fans_count=0)
        db.session.add(author)
        db.session.commit()
        
        log_action(str(result.inserted_id), 'register', '用户注册')
        
        flash('注册成功，请登录', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# 登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('用户名和密码不能为空', 'danger')
            return render_template('login.html')
        
        # 检查管理员账户
        if username == 'admin' and password == 'admin123':
            admin_user = users_collection.find_one({'username': 'admin'})
            if not admin_user:
                # 创建管理员账户
                admin_user = {
                    'username': 'admin',
                    'password': generate_password_hash('admin123'),
                    'phone': '13800138000',
                    'role': 'admin',
                    'created_at': datetime.now(),
                    'last_login': datetime.now(),
                    'is_active': True
                }
                result = users_collection.insert_one(admin_user)
                admin_user['_id'] = result.inserted_id
            
            if check_password_hash(admin_user['password'], 'admin123'):
                user_obj = User(admin_user)
                login_user(user_obj)
                
                # 更新最后登录时间
                users_collection.update_one(
                    {'_id': admin_user['_id']},
                    {'$set': {'last_login': datetime.now()}}
                )
                
                log_action(str(admin_user['_id']), 'login', '管理员登录')
                flash('管理员登录成功', 'success')
                return redirect(url_for('admin_dashboard'))
        
        # 查找用户
        user = users_collection.find_one({'username': username})
        
        if user and check_password_hash(user['password'], password):
            if not user.get('is_active', True):
                flash('账户已被禁用', 'danger')
                return render_template('login.html')
            
            user_obj = User(user)
            login_user(user_obj)
            
            # 更新最后登录时间
            users_collection.update_one(
                {'_id': user['_id']},
                {'$set': {'last_login': datetime.now()}}
            )
            
            log_action(str(user['_id']), 'login', '用户登录')
            flash('登录成功', 'success')
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误', 'danger')
    
    return render_template('login.html')

# 退出登录
@app.route('/logout')
@login_required
def logout():
    log_action(current_user.id, 'logout', '用户退出')
    logout_user()
    flash('已退出登录', 'success')
    return redirect(url_for('index'))

# 文章详情
@app.route('/article/<article_id>')
def article_detail(article_id):
    try:
        article = articles_collection.find_one({'_id': ObjectId(article_id)})
        if not article:
            flash('文章不存在', 'danger')
            return redirect(url_for('index'))
        
        # 增加阅读次数
        articles_collection.update_one(
            {'_id': ObjectId(article_id)},
            {'$inc': {'read_count': 1}}
        )
        
        # 获取评论（嵌套结构）
        comments = Comment.query.filter_by(article_id=article_id, parent_id=None).order_by(Comment.publish_time.desc()).all()
        
        # 递归获取嵌套评论
        def get_nested_comments(parent_id):
            nested = Comment.query.filter_by(article_id=article_id, parent_id=parent_id).order_by(Comment.publish_time.desc()).all()
            result = []
            for comment in nested:
                comment_dict = comment.to_dict()
                comment_dict['replies'] = get_nested_comments(comment.id)
                result.append(comment_dict)
            return result
        
        comments_data = []
        for comment in comments:
            comment_dict = comment.to_dict()
            comment_dict['replies'] = get_nested_comments(comment.id)
            comments_data.append(comment_dict)
        
        # 检查用户是否点赞
        user_liked = False
        user_favorited = False
        if current_user.is_authenticated:
            like_record = likes_collection.find_one({
                'user_id': current_user.id,
                'target_id': article_id,
                'type': 'article'
            })
            user_liked = like_record is not None
            
            favorite_record = favorites_collection.find_one({
                'user_id': current_user.id,
                'article_id': article_id
            })
            user_favorited = favorite_record is not None
        
        # 记录日志
        if current_user.is_authenticated:
            log_action(current_user.id, 'view_article', f'查看文章: {article["title"]}')
        
        return render_template('article_detail.html', 
                             article=article, 
                             comments=comments_data,
                             user_liked=user_liked,
                             user_favorited=user_favorited)
    
    except Exception as e:
        print(f"Article detail error: {e}")
        flash('文章不存在', 'danger')
        return redirect(url_for('index'))

# 发表评论
@app.route('/comment', methods=['POST'])
@login_required
def add_comment():
    article_id = request.form.get('article_id')
    content = request.form.get('content', '').strip()
    parent_id = request.form.get('parent_id', None)
    
    if not content:
        return jsonify({'status': 'error', 'message': '评论内容不能为空'})
    
    # 检查文章是否存在
    article = articles_collection.find_one({'_id': ObjectId(article_id)})
    if not article:
        return jsonify({'status': 'error', 'message': '文章不存在'})
    
    # 创建评论
    comment = Comment(
        article_id=article_id,
        user_id=current_user.id,
        username=current_user.username,
        content=content,
        parent_id=parent_id,
        like_count=0,
        publish_time=datetime.now()
    )
    
    db.session.add(comment)
    db.session.commit()
    
    # 更新文章评论数
    articles_collection.update_one(
        {'_id': ObjectId(article_id)},
        {'$inc': {'comment_count': 1}}
    )
    
    log_action(current_user.id, 'comment', f'发表评论: {content[:50]}...')
    
    return jsonify({
        'status': 'success',
        'comment_id': comment.id,
        'username': current_user.username,
        'publish_time': comment.publish_time.isoformat()
    })

# 发表文章
@app.route('/publish', methods=['GET', 'POST'])
@login_required
def publish_article():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        main_category = request.form.get('main_category', '').strip()
        sub_category = request.form.get('sub_category', '').strip()
        
        # 验证
        if not title or not content or not main_category or not sub_category:
            flash('所有字段都必须填写', 'danger')
            return render_template('publish.html')
        
        # 检查字数限制
        min_length = 50  # 最小字数
        if len(content) < min_length:
            flash(f'文章内容至少需要 {min_length} 个字符', 'danger')
            return render_template('publish.html')
        
        # 创建文章
        article = {
            'title': title,
            'author': current_user.username,
            'author_url': '',
            'main_category': main_category,
            'sub_category': sub_category,
            'content': content,
            'url': '',
            'publish_time': datetime.now(),
            'read_count': 0,
            'like_count': 0,
            'collect_count': 0,
            'comment_count': 0,
            'content_length': len(content),
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        result = articles_collection.insert_one(article)
        
        # 添加分类
        if not categories_collection.find_one({'name': main_category}):
            categories_collection.insert_one({
                'name': main_category,
                'type': 'main',
                'created_at': datetime.now()
            })
        
        if not categories_collection.find_one({'name': sub_category}):
            categories_collection.insert_one({
                'name': sub_category,
                'type': 'sub',
                'created_at': datetime.now()
            })
        
        log_action(current_user.id, 'publish_article', f'发表文章: {title}')
        flash('文章发表成功', 'success')
        return redirect(url_for('article_detail', article_id=str(result.inserted_id)))
    
    # GET请求 - 显示发表页面
    return render_template('publish.html')

# 点赞/取消点赞
@app.route('/like/<target_type>/<target_id>', methods=['POST'])
@login_required
def toggle_like(target_type, target_id):
    user_id = current_user.id
    
    # 检查是否已经点赞
    existing_like = likes_collection.find_one({
        'user_id': user_id,
        'target_id': target_id,
        'type': target_type
    })
    
    if existing_like:
        # 取消点赞
        likes_collection.delete_one({'_id': existing_like['_id']})
        
        # 更新点赞数
        if target_type == 'article':
            articles_collection.update_one(
                {'_id': ObjectId(target_id)},
                {'$inc': {'like_count': -1}}
            )
        elif target_type == 'comment':
            comment = Comment.query.get(int(target_id))
            if comment:
                comment.like_count -= 1
                db.session.commit()
        
        log_action(user_id, 'unlike', f'取消点赞 {target_type}: {target_id}')
        return jsonify({'status': 'success', 'action': 'unliked'})
    else:
        # 添加点赞
        like = {
            'user_id': user_id,
            'target_id': target_id,
            'type': target_type,
            'timestamp': datetime.now()
        }
        likes_collection.insert_one(like)
        
        # 更新点赞数
        if target_type == 'article':
            articles_collection.update_one(
                {'_id': ObjectId(target_id)},
                {'$inc': {'like_count': 1}}
            )
        elif target_type == 'comment':
            comment = Comment.query.get(int(target_id))
            if comment:
                comment.like_count += 1
                db.session.commit()
        
        log_action(user_id, 'like', f'点赞 {target_type}: {target_id}')
        return jsonify({'status': 'success', 'action': 'liked'})

# 收藏/取消收藏
@app.route('/favorite/<article_id>', methods=['POST'])
@login_required
def toggle_favorite(article_id):
    user_id = current_user.id
    
    # 检查是否已经收藏
    existing_favorite = favorites_collection.find_one({
        'user_id': user_id,
        'article_id': article_id
    })
    
    if existing_favorite:
        # 取消收藏
        favorites_collection.delete_one({'_id': existing_favorite['_id']})
        
        # 更新收藏数
        articles_collection.update_one(
            {'_id': ObjectId(article_id)},
            {'$inc': {'collect_count': -1}}
        )
        
        log_action(user_id, 'unfavorite', f'取消收藏文章: {article_id}')
        return jsonify({'status': 'success', 'action': 'unfavorited'})
    else:
        # 添加收藏
        favorite = {
            'user_id': user_id,
            'article_id': article_id,
            'timestamp': datetime.now()
        }
        favorites_collection.insert_one(favorite)
        
        # 更新收藏数
        articles_collection.update_one(
            {'_id': ObjectId(article_id)},
            {'$inc': {'collect_count': 1}}
        )
        
        log_action(user_id, 'favorite', f'收藏文章: {article_id}')
        return jsonify({'status': 'success', 'action': 'favorited'})

# 用户后台
@app.route('/user/dashboard')
@login_required
def user_dashboard():
    user_id = current_user.id
    
    # 获取用户信息
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    
    # 获取收藏的文章
    favorites = list(favorites_collection.find({'user_id': user_id}))
    favorite_articles = []
    for fav in favorites:
        article = articles_collection.find_one({'_id': ObjectId(fav['article_id'])})
        if article:
            favorite_articles.append(article)
    
    # 获取用户发表的评论
    comments = Comment.query.filter_by(user_id=user_id).order_by(Comment.publish_time.desc()).all()
    
    # 获取点赞记录
    likes = list(likes_collection.find({'user_id': user_id, 'type': 'article'}))
    liked_articles = []
    for like in likes:
        article = articles_collection.find_one({'_id': ObjectId(like['target_id'])})
        if article:
            liked_articles.append(article)
    
    log_action(user_id, 'view_dashboard', '查看用户后台')
    
    return render_template('user_dashboard.html',
                         user=user,
                         favorite_articles=favorite_articles,
                         comments=comments,
                         liked_articles=liked_articles)

# 管理员后台
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():

    # 检查是否是管理员
    if current_user.role != 'admin':
        flash('需要管理员权限', 'danger')
        return redirect(url_for('index'))
    
    # 获取统计数据
    user_count = users_collection.count_documents({})
    article_count = articles_collection.count_documents({})
    comment_count = Comment.query.count()
    log_count = logs_collection.count_documents({})
    
    # 获取最近的用户
    recent_users = list(users_collection.find().sort('created_at', -1).limit(10))
    
    # 获取最近的日志
    recent_logs = list(logs_collection.find().sort('timestamp', -1).limit(20))
    
    # 获取用户信息
    for log in recent_logs:
        user = users_collection.find_one({'_id': ObjectId(log['user_id'])})
        log['username'] = user['username'] if user else '未知用户'
    
    return render_template('admin_dashboard.html',
                         user_count=user_count,
                         article_count=article_count,
                         comment_count=comment_count,
                         log_count=log_count,
                         recent_users=recent_users,
                         recent_logs=recent_logs)
    deployment_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template('admin_dashboard.html', deployment_time=deployment_time)
# 用户管理
@app.route('/admin/users')
@login_required
def admin_users():
    # 检查是否是管理员
    if current_user.role != 'admin':
        flash('需要管理员权限', 'danger')
        return redirect(url_for('index'))
    
    page = int(request.args.get('page', 1))
    per_page = 20
    skip = (page - 1) * per_page
    
    users = list(users_collection.find().skip(skip).limit(per_page).sort('created_at', -1))
    total_users = users_collection.count_documents({})
    total_pages = (total_users + per_page - 1) // per_page
    
    return render_template('admin_users.html',
                         users=users,
                         page=page,
                         total_pages=total_pages)

# 编辑用户
@app.route('/admin/edit_user/<user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    # 检查是否是管理员
    if current_user.role != 'admin':
        flash('需要管理员权限', 'danger')
        return redirect(url_for('index'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    
    if not user:
        flash('用户不存在', 'danger')
        return redirect(url_for('admin_users'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'user')
        is_active = request.form.get('is_active') == 'on'
        
        update_data = {
            'username': username,
            'phone': phone,
            'role': role,
            'is_active': is_active
        }
        
        if password:
            update_data['password'] = generate_password_hash(password)
        
        users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': update_data}
        )
        
        log_action(current_user.id, 'edit_user', f'修改用户信息: {username}')
        flash('用户信息已更新', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin_edit_user.html', user=user)

# 删除用户
@app.route('/admin/delete_user/<user_id>', methods=['DELETE'])
@login_required
def admin_delete_user(user_id):
    # 检查是否是管理员
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': '需要管理员权限'})
    
    # 不能删除自己
    if user_id == current_user.id:
        return jsonify({'status': 'error', 'message': '不能删除自己'})
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    if not user:
        return jsonify({'status': 'error', 'message': '用户不存在'})
    
    # 删除用户相关数据
    users_collection.delete_one({'_id': ObjectId(user_id)})
    likes_collection.delete_many({'user_id': user_id})
    favorites_collection.delete_many({'user_id': user_id})
    Comment.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    search_history_collection.delete_many({'user_id': user_id})
    
    log_action(current_user.id, 'delete_user', f'删除用户: {user["username"]}')
    return jsonify({'status': 'success'})

# 文章管理
@app.route('/admin/articles')
@login_required
def admin_articles():
    # 检查是否是管理员
    if current_user.role != 'admin':
        flash('需要管理员权限', 'danger')
        return redirect(url_for('index'))
    
    page = int(request.args.get('page', 1))
    per_page = 20
    skip = (page - 1) * per_page
    
    articles = list(articles_collection.find().skip(skip).limit(per_page).sort('publish_time', -1))
    total_articles = articles_collection.count_documents({})
    total_pages = (total_articles + per_page - 1) // per_page
    
    return render_template('admin_articles.html',
                         articles=articles,
                         page=page,
                         total_pages=total_pages)

# 编辑文章
@app.route('/admin/edit_article/<article_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_article(article_id):
    # 检查是否是管理员
    if current_user.role != 'admin':
        flash('需要管理员权限', 'danger')
        return redirect(url_for('index'))
    
    article = articles_collection.find_one({'_id': ObjectId(article_id)})
    
    if not article:
        flash('文章不存在', 'danger')
        return redirect(url_for('admin_articles'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        main_category = request.form.get('main_category', '').strip()
        sub_category = request.form.get('sub_category', '').strip()
        
        if not title or not content:
            flash('标题和内容不能为空', 'danger')
            return render_template('admin_edit_article.html', article=article)
        
        # 检查字数限制
        min_length = 50  # 最小字数
        if len(content) < min_length:
            flash(f'文章内容至少需要 {min_length} 个字符', 'danger')
            return render_template('admin_edit_article.html', article=article)
        
        update_data = {
            'title': title,
            'content': content,
            'main_category': main_category,
            'sub_category': sub_category,
            'content_length': len(content),
            'updated_at': datetime.now()
        }
        
        articles_collection.update_one(
            {'_id': ObjectId(article_id)},
            {'$set': update_data}
        )
        
        log_action(current_user.id, 'edit_article', f'修改文章: {title}')
        flash('文章已更新', 'success')
        return redirect(url_for('admin_articles'))
    
    return render_template('admin_edit_article.html', article=article)

# 删除文章
@app.route('/admin/delete_article/<article_id>', methods=['DELETE'])
@login_required
def admin_delete_article(article_id):
    # 检查是否是管理员
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': '需要管理员权限'})
    
    article = articles_collection.find_one({'_id': ObjectId(article_id)})
    if not article:
        return jsonify({'status': 'error', 'message': '文章不存在'})
    
    # 删除文章相关数据
    articles_collection.delete_one({'_id': ObjectId(article_id)})
    Comment.query.filter_by(article_id=article_id).delete()
    db.session.commit()
    likes_collection.delete_many({'target_id': article_id})
    favorites_collection.delete_many({'article_id': article_id})
    
    log_action(current_user.id, 'delete_article', f'删除文章: {article["title"]}')
    return jsonify({'status': 'success'})

# 评论管理
@app.route('/admin/comments')
@login_required
def admin_comments():
    # 检查是否是管理员
    if current_user.role != 'admin':
        flash('需要管理员权限', 'danger')
        return redirect(url_for('index'))
    
    page = int(request.args.get('page', 1))
    per_page = 20
    
    comments = Comment.query.order_by(Comment.publish_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # 获取文章信息
    for comment in comments.items:
        article = articles_collection.find_one({'_id': ObjectId(comment.article_id)})
        comment.article_title = article['title'] if article else '未知文章'
    
    return render_template('admin_comments.html',
                         comments=comments.items,
                         page=page,
                         total_pages=comments.pages)

# 删除评论
@app.route('/admin/delete_comment/<comment_id>', methods=['DELETE'])
@login_required
def admin_delete_comment(comment_id):
    # 检查是否是管理员
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': '需要管理员权限'})
    
    comment = Comment.query.get(comment_id)
    if not comment:
        return jsonify({'status': 'error', 'message': '评论不存在'})
    
    # 删除评论及其回复
    Comment.query.filter_by(id=comment_id).delete()
    Comment.query.filter_by(parent_id=comment_id).delete()
    db.session.commit()
    
    # 更新文章评论数
    articles_collection.update_one(
        {'_id': ObjectId(comment.article_id)},
        {'$inc': {'comment_count': -1}}
    )
    
    log_action(current_user.id, 'delete_comment', f'删除评论: {comment.content[:50]}...')
    return jsonify({'status': 'success'})

# 日志管理
@app.route('/admin/logs')
@login_required
def admin_logs():
    # 检查是否是管理员
    if current_user.role != 'admin':
        flash('需要管理员权限', 'danger')
        return redirect(url_for('index'))
    
    page = int(request.args.get('page', 1))
    per_page = 30
    skip = (page - 1) * per_page
    
    logs = list(logs_collection.find().skip(skip).limit(per_page).sort('timestamp', -1))
    total_logs = logs_collection.count_documents({})
    total_pages = (total_logs + per_page - 1) // per_page
    
    # 获取用户信息
    for log in logs:
        user = users_collection.find_one({'_id': ObjectId(log['user_id'])})
        log['username'] = user['username'] if user else '未知用户'
    
    return render_template('admin_logs.html',
                         logs=logs,
                         page=page,
                         total_pages=total_pages)

# 数据库备份
@app.route('/admin/backup')
@login_required
def backup_database():
    # 检查是否是管理员
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': '需要管理员权限'})
    
    try:
        backup_dir = f'/mnt/okcomputer/output/backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        os.makedirs(backup_dir, exist_ok=True)
        
        # 备份MongoDB集合
        mongo_collections = ['articles', 'likes', 'favorites', 'search_history', 'logs', 'categories', 'users']
        
        for collection_name in mongo_collections:
            collection = mongo_db[collection_name]
            data = list(collection.find())
            
            # 转换为JSON可序列化格式
            for item in data:
                if '_id' in item:
                    item['_id'] = str(item['_id'])
                if 'timestamp' in item:
                    item['timestamp'] = item['timestamp'].isoformat()
                if 'publish_time' in item:
                    item['publish_time'] = item['publish_time'].isoformat()
                if 'created_at' in item:
                    item['created_at'] = item['created_at'].isoformat()
                if 'last_login' in item and item['last_login']:
                    item['last_login'] = item['last_login'].isoformat()
            
            with open(f'{backup_dir}/{collection_name}.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 备份MySQL数据
        mysql_tables = ['comments', 'authors']
        for table_name in mysql_tables:
            if table_name == 'comments':
                comments = Comment.query.all()
                data = [comment.to_dict() for comment in comments]
            elif table_name == 'authors':
                authors = Author.query.all()
                data = [author.to_dict() for author in authors]
            
            with open(f'{backup_dir}/{table_name}.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        log_action(current_user.id, 'backup', f'数据库备份到: {backup_dir}')
        
        # 创建压缩包
        shutil.make_archive(backup_dir, 'zip', backup_dir)
        
        return jsonify({'status': 'success', 'backup_path': f'{backup_dir}.zip'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# 静态文件
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    # 创建MySQL表
    with app.app_context():
        db.create_all()
    
    # 确保MongoDB索引存在
    users_collection.create_index('username', unique=True)
    articles_collection.create_index('title')
    articles_collection.create_index('main_category')
    articles_collection.create_index('publish_time')
    
    app.run(debug=True, host='0.0.0.0', port=5000)