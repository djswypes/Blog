from functools import wraps
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager,current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
import smtplib
from flask_login import LoginManager
login_manager = LoginManager()


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)


gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

MY_EMAIL = "testpython107@gmail.com"
MY_PASSWORD = '1234!@#$'
TO_EMAIL = "olaoluwaolorede8@gmail.com"

##CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    user_name = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(100))
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    
    #***************Parent Relationship*************#
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(250), nullable=False)
    time = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    
    #***************Child Relationship*************#
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
db.create_all()



def login_required(function):
    @wraps(function)
    def nested_function(*args, **kwargs):
        if current_user.is_authenticated:
            return function(*args, **kwargs)
        return redirect(url_for('login'))
    return nested_function


def admin_only(function):
    @wraps(function)
    def nested_function(*args, **kwargs):
        print(current_user.get_id)
        if current_user.is_authenticated:
            if current_user.id == 1:
                return function(*args, **kwargs)
        return abort(403)
    return nested_function


@app.route('/')
def get_all_posts():
    # blog of a particular user
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)
    


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if db.session.query(User).filter_by(email=form.email.data).first():
            flash("The Email already exists. Login instead!")
        elif db.session.query(User).filter_by(user_name=form.user_name.data.title()).first():
            flash("The Username is already taken. Try another one!")
        else:
            hash_and_salted_password = generate_password_hash(
                form.password.data,
                method='pbkdf2:sha256',
                salt_length=8
            )
            new_user = User(
                name=form.name.data.title(), 
                email=form.email.data, 
                password=hash_and_salted_password,
                user_name = form.user_name.data.title()
                )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect("/")
    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.query(User).filter_by(email=form.email.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash("Incorrect Password. Please try again!")
        else:
            flash("The email does not exist. Try signing up instead!")
    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form = CommentForm()

    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                comment_author=current_user,
                text=form.comment.data,
                parent_post=requested_post,
                date=datetime.now().strftime("%B %d, %Y"),
                time = datetime.now().strftime("%H:%M")
            )
            db.session.add(new_comment)
            db.session.commit()

        else:
            flash("You need to login to comment.")

    if requested_post:
        return render_template("post.html", post=requested_post, form=form, current_user=current_user)
        
    else:
        return abort(404)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            author=current_user,
            img_url=form.img_url.data,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    if post:
        edit_form = CreatePostForm(
            title=post.title,
            subtitle=post.subtitle,
            img_url=post.img_url,
            author=post.author,
            body=post.body
        )
        if edit_form.validate_on_submit():
            post.title = edit_form.title.data
            post.subtitle = edit_form.subtitle.data
            post.img_url = edit_form.img_url.data
            post.body = edit_form.body.data
            db.session.commit()
            return redirect(url_for("show_post", post_id=post.id))

        return render_template("make-post.html", form=edit_form)
    return render_template("make-post.html", form=edit_form)

@app.route("/delete/<int:post_id>")
@login_required
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    if post_to_delete:
        db.session.delete(post_to_delete)
        db.session.commit()
    return redirect(url_for('get_all_posts'))

@app.errorhandler(404)
def page_not_found(error):
    return render_template('error-page.html'), 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
