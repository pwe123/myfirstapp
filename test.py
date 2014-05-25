__author__ = 'alexey'
# -*- coding: utf-8 -*-
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.ext.declarative import *

Base = declarative_base()


class Author(Base):
    __tablename__ = 'authors'
    author_id = Column(INTEGER, primary_key=True)
    name = Column(String)
    books = relationship('Book', secondary='aut_bks')

    def serialize(self):
        return {
            'id': self.author_id,
            'name': self.name
        }


class Book(Base):
    __tablename__ = 'books'
    book_id = Column(INTEGER, primary_key=True)
    title = Column(String)
    authors = relationship('Author', secondary='aut_bks')

    def serialize(self):
        return {
            'id': self.book_id,
            'title': self.title
        }


class AuthorBook(Base):
    __tablename__ = 'aut_bks'
    id = Column(INTEGER, primary_key=True)
    author_id = Column(INTEGER, ForeignKey('authors.author_id'))
    book_id = Column(INTEGER, ForeignKey('books.book_id'))


engine = create_engine('sqlite:///ellibrary.db')
Base.metadata.bind = engine

DBSession = sessionmaker(engine)
s = DBSession()

from flask import *
from flask import flash, get_flashed_messages

app = Flask(__name__)
app.secret_key = "7hnjbj8;smncuu"

from flask.ext.login import *
from flask.ext.login import login_required, login_user, logout_user, current_user


class User(Base):
    __tablename__ = 'users'
    id = Column('id', INTEGER, primary_key=True)
    username = Column('username', String, unique=True)
    password = Column('password', String)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)


lm = LoginManager()
lm.init_app(app)
lm.login_view = 'index'


@lm.user_loader
def load_user(id):
    s = DBSession()
    user = s.query(User).get(int(id))
    s.close()
    return user


from flask_wtf import Form
from wtforms import TextField
from wtforms.validators import Required


class AddBookForm(Form):
    title = TextField('title', validators=[Required()])


class AddAuthorForm(Form):
    name = TextField('name', validators=[Required()])


class RegistrationForm(Form):
    username = TextField('username', validators=[Required()])


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        s = DBSession()
        if request.form['search_type'] == 'by_title':
            books = s.query(Book).filter(Book.title == request.form["search_query"])
        else:
            books = s.query(Book).filter(Book.authors.any(Author.name == request.form["search_query"]))
        s.close()
        return jsonify(result=[book.serialize() for book in books])
    return render_template('templ.html', books=None)


@app.route('/guess')
def guess():
    if request.args.get('q'):
        if request.args.get('type') == 'by_title':
            s = DBSession()
            books = s.query(Book).filter(Book.title.startswith(request.args.get('q'))).limit(10).all()
            s.close()
            return jsonify(result=[book.title for book in books])
        else:
            s = DBSession()
            authors = s.query(Author).filter(Author.name.startswith(request.args.get('q'))).limit(10).all()
            s.close()
            return jsonify(result=[author.name for author in authors])
    return redirect(url_for('index'))


@app.route('/addbook', methods=['GET', 'POST'])
@login_required
def add_book():
    form = AddBookForm()
    if form.validate_on_submit():
        s = DBSession()
        book = Book(title=request.form['title'])
        s.add(book)
        s.commit()
        id = book.book_id
        s.close()
        return redirect(url_for('book', id=id))
    return render_template('addbook.html', form=form)


@app.route('/addauthor', methods=['GET', 'POST'])
@login_required
def add_author():
    form = AddAuthorForm()
    if form.validate_on_submit():
        s = DBSession()
        author = Author(name=request.form['name'])
        s.add(author)
        s.commit()
        id = author.author_id
        s.close()
        return redirect(url_for('author', id=id))
    return render_template('addauthor.html', form=form)


@app.route('/author')
def get_author():
    id = request.args.get('id')
    s = DBSession()
    author = s.query(Author).filter(Author.author_id == id)[0]
    books = author.books
    return render_template('authorview.html', name=author.name, books=books)


@app.route('/book/<id>')
def book(id):
    if id:
        s = DBSession()
        books = s.query(Book).filter(Book.book_id == id).all()
        authors = books[0].authors
        s.close()
        if books.count > 0:
            book = books[0]
            return render_template('bookview.html', book=books[0], authors=authors)
    return redirect(url_for('index'))


@app.route('/author/<id>')
def author(id):
    s = DBSession()
    authors = s.query(Author).filter(Author.author_id == id).all()
    books = authors[0].books
    s.close()
    if authors.count > 0:
        return render_template('authorview.html', author=authors[0], books=books)
    return redirect(url_for('index'))


@app.route('/delbook', methods=['GET', 'POST'])
@login_required
def delbook():
    if request.method == 'POST':
        s = DBSession()
        books = s.query(Book).filter(Book.title == request.form['title']).all()
        if len(books) > 0:
            s.delete(books[0])
            s.commit()
            s.close()
            return jsonify({'result': 'ok'})
        else:
            return jsonify({'result': 'error'})
    return render_template('delbook.html')


@app.route('/delauthor', methods=['GET', 'POST'])
@login_required
def delauthor():
    if request.method == 'POST':
        s = DBSession()
        authors = s.query(Author).filter(Author.name == request.form['name']).all()
        if len(authors) > 0:
            s.delete(authors[0])
            s.commit()
            s.close()
            return jsonify({'result': 'ok'})
        else:
            return jsonify({'result': 'error'})
    return render_template('delauthor.html')


@app.route('/editname')
@login_required
def editname():
    if request.args.get('id') and request.args.get('newname'):
        s = DBSession()
        authors = s.query(Author).filter(Author.author_id == request.args.get('id')).all()
        if len(authors) > 0:
            authors[0].name = request.args.get('newname')
            s.commit()
        s.close()
        return jsonify({'status': 'ok'})
    return redirect(url_for('index'))


@app.route('/edittitle')
@login_required
def edittitle():
    if request.args.get('id') and request.args.get('newtitle'):
        s = DBSession()
        books = s.query(Book).filter(Book.book_id == request.args.get('id')).all()
        if len(books) > 0:
            books[0].title = request.args.get('newtitle')
            s.commit()
        s.close()
        return jsonify({'status': 'ok'})
    return redirect(url_for('index'))


@app.route('/addbktoaut')
@login_required
def addbktoaut():
    if request.args.get('id') and request.args.get('title'):
        s = DBSession()
        author = s.query(Author).filter(Author.author_id == request.args.get('id')).first()
        book = s.query(Book).filter(Book.title == request.args.get('title')).first()
        if author and book:
            if book in author.books:
                return jsonify({'result': 'already exist'})
            author.books.append(book)
            s.commit()
            book_id = book.book_id
            s.close()
            return jsonify({'result': 'ok', 'id': book_id})
        if not author:
            s.close()
            return jsonify({'result': 'error'})
        if not book:
            if request.args.get('force'):
                book = Book(title=request.args.get('title'))
                author.books.append(book)
                s.commit()
                book_id = book.book_id
                s.close()
                return jsonify({'result': 'ok', 'id': book_id})
            else:
                s.close()
                return jsonify({'result': 'no book'})
    return redirect(url_for('index'))


@app.route('/delbkfromaut', methods=['POST'])
@login_required
def delbkfromaut():
    s = DBSession()
    aut = s.query(Author).filter(Author.author_id == request.form['author_id']).first()
    book = s.query(Book).filter(Book.book_id == request.form['book_id']).first()
    aut.books.remove(book)
    s.commit()
    s.close()
    return jsonify({'result': 'ok'})


@app.route('/addauttobk')
@login_required
def addauttobk():
    if request.args.get('id') and request.args.get('name'):
        s = DBSession()
        book = s.query(Book).filter(Book.book_id == request.args.get('id')).first()
        author = s.query(Author).filter(Author.name == request.args.get('name')).first()
        if author and book:
            if author in book.authors:
                return jsonify({'result': 'already exist'})
            book.authors.append(author)
            s.commit()
            author_id = author.author_id
            s.close()
            return jsonify({'result': 'ok', 'id': author_id})
        if not book:
            s.close()
            return jsonify({'result': 'error'})
        if not author:
            if request.args.get('force'):
                author = Author(name=request.args.get('name'))
                book.authors.append(author)
                s.commit()
                author_id = author.author_id
                s.close()
                return jsonify({'result': 'ok', 'id': author_id})
            else:
                s.close()
                return jsonify({'result': 'no author'})
    return redirect(url_for('index'))


@app.route('/delautfrombk', methods=['POST'])
@login_required
def delautfrombk():
    s = DBSession()
    author = s.query(Author).filter(Author.author_id == request.form['author_id']).first()
    book = s.query(Book).filter(Book.book_id == request.form['book_id']).first()
    book.authors.remove(author)
    s.commit()
    s.close()
    return jsonify({'result': 'ok'})


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    user = User(username=request.form['username'], password=request.form['password'])
    s = DBSession()
    s.add(user)
    s.commit()
    s.close()
    return redirect(url_for('index'))


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'GET':
        return render_template('templ.html')
    username = request.form['username']
    password = request.form['password']
    s = DBSession()
    registered_user = s.query(User).filter_by(username=username,password=password).first()
    s.close()
    if registered_user is None:
        flash('Incorrect username or password', 'error')
        return redirect(url_for('index'))
    login_user(registered_user)
    flash('You are welcome!')
    return redirect(url_for('index'))


@app.route('/signout')
def signout():
    logout_user()
    return redirect(url_for('index'))


@app.before_request
def before_request():
    g.user = current_user


app.run()