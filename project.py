from flask import Flask, render_template, request, redirect,\
    jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, MenuItem, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
from functools import wraps

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "CatalogApp"

# Connect to Database and create database session
engine = create_engine('sqlite:///catalogitemwithusers.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.
                                  digits)for x in range(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    request.get_data()
    code = request.data.decode('utf-8')
    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    response = h.request(url, 'GET')[1]
    str_response = response.decode('utf-8')
    result = json.loads(str_response)

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('''Current user is already
                       connected.'''), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    user_id = getUserId(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += '''<"style = "width: 300px; height: 300px;border-radius:150px;
                 -webkit-border-radius: 150px;-moz-border-radius: 150px;">'''
    flash("you are now logged in as %s" % login_session['username'])
    return output


def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserId(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        # print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'),
                                 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s' % access_token
    print 'User name is: '
    print login_session['username']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        # response = redirect(url_for('showCategories'))
        # flash("You are now logged out")
        return response
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view Restaurant Information
@app.route('/category/<string:category_name>/items/JSON')
def categoryMenuJSON(category_name):
    categories = session.query(Category).order_by(asc(Category.name))
    category = session.query(Category).filter_by(name=category_name).one()
    creator = getUserInfo(category.user_id)
    items = session.query(MenuItem).filter_by(
            category_name=category_name).all()
    return jsonify(MenuItems=[i.serialize for i in items])


@app.route('/category/<string:category_name>/<string:item_name>/JSON')
def menuItemJSON(category_name, item_name):
    Menu_Item = session.query(MenuItem).filter_by(name=item_name).one()
    return jsonify(Menu_Item=Menu_Item.serialize)


@app.route('/category/JSON')
def categoriesJSON():
    categories = session.query(Category).all()
    return jsonify(categories=[r.serialize for r in categories])


# Show all categories
@app.route('/')
@app.route('/category/')
def showCategories():
    categories = session.query(Category).order_by(Category.name).all()
    items = session.query(MenuItem).order_by(MenuItem.id.desc()).limit(10)
    if 'username' not in login_session:
        return render_template('publicCategories.html', items=items,
                               login_session=login_session,
                               categories=categories)
    else:
        return render_template('categories.html', categories=categories,
                               items=items,
                               login_session=login_session)


# Create a new restaurant
@app.route('/category/new/', methods=['GET', 'POST'])
def newCategory():
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    else:
        if request.method == 'POST':
            newCategory = Category(name=request.form['name'],
                                   user_id=login_session['user_id'])
            session.add(newCategory)
            session.commit()
            flash('New Category %s Successfully Created' % newCategory.name)
            return redirect(url_for('showCategories'))

        else:
            return render_template('newCategory.html',
                                   login_session=login_session)


# Edit a Category
@app.route('/category/<string:category_name>/edit/', methods=['GET', 'POST'])
def editCategory(category_name):
    editedCategory = session.query(Category).filter_by(
                                             name=category_name).one()
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    else:
        if editedCategory.user_id != login_session['user_id']:
            flash("you are not allowed to edit this category")
            return redirect(url_for('showCategories'))
        if request.method == 'POST':
            if request.form['name']:
                editedCategory.name = request.form['name']
                session.add(editedCategory)
                session.commit()
                flash('Category Successfully Edited %s' % editedCategory.name)
                return redirect(url_for('showCategories'))
        else:
            return render_template('editCategory.html',
                                   category=editedCategory,
                                   login_session=login_session)


# Delete a category
@app.route('/category/<string:category_name>/delete/', methods=['GET', 'POST'])
def deleteCategory(category_name):
    categoryToDelete = session.query(Category).filter_by(
        name=category_name).one()
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    if categoryToDelete.user_id != login_session['user_id']:
        flash("You are not allowed to delete this category.")
        return redirect(url_for('showCategories'))
    if request.method == 'POST':
        session.delete(categoryToDelete)
        session.commit()
        flash('%s Successfully Deleted' % categoryToDelete.name)
        items = session.query(MenuItem).filter_by(
            category_name=category_name).all()
        for item in items:
            session.delete(item)
            session.commit()
        return redirect(url_for('showCategories'))
    else:
        return render_template('deleteCategory.html',
                               category=categoryToDelete,
                               login_session=login_session)


# Show a category menu
@app.route('/category/items/<string:category_name>/')
def showMenu(category_name):
    items = session.query(MenuItem).filter_by(
                category_name=category_name).all()
    category = session.query(Category).filter_by(name=category_name).one()
    categories = session.query(Category).order_by(asc(Category.name))
    creator = getUserInfo(category.user_id)
    if ('username'not in login_session or
            creator.id != login_session['user_id']):
        return render_template('publicMenu.html',
                               items=items,
                               category=category,
                               creator=creator,
                               login_session=login_session,
                               categories=categories)
    else:
        return render_template('menu.html',
                               items=items,
                               category=category,
                               creator=creator,
                               login_session=login_session,
                               categories=categories)


# show a specific menu item
@app.route('/category/<string:category_name>/<string:item_name>')
def showItem(category_name, item_name):
    category = session.query(Category).filter_by(name=category_name).one()
    item = session.query(MenuItem).filter_by(name=item_name).one()
    creator = getUserInfo(category.user_id)
    error = ''
    if not item:
        error = "This is not available."
    else:
        if ('username' not in login_session or
                creator.id != login_session['user_id']):
            return render_template('publicItem.html',
                                   item=item,
                                   creator=creator,
                                   login_session=login_session,
                                   error=error)
        else:
            return render_template('Item.html',
                                   item=item,
                                   creator=creator,
                                   login_session=login_session,
                                   error=error)


# Create a new menu item
@app.route('/category/movies/'
           '<string:category_name>/new', methods=['GET', 'POST'])
def newMenuItem(category_name):
    category = session.query(Category).filter_by(name=category_name).one()
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    else:
        if request.method == 'POST':
            if request.form['name'] and request.form['price']:
                newItem = MenuItem(name=request.form['name'],
                                   description=request.form['description'],
                                   price=request.form['price'],
                                   category_name=category_name,
                                   user_id=category.user_id)
                session.add(newItem)
                session.commit()
                flash('New Movie %s Item Successfully Created'
                      % (newItem.name))
                return redirect(url_for('showMenu',
                                        category_name=category_name,
                                        login_session=login_session,
                                        category=category))

        else:
            return render_template('newMenuItem.html',
                                   category_name=category_name,
                                   login_session=login_session,
                                   category=category)


# Edit a menu item
@app.route('/category/<string:category_name>/item/<string:item_name>/edit',
           methods=['GET', 'POST'])
def editMenuItem(category_name, item_name):
    editedItem = session.query(MenuItem).filter_by(name=item_name).one()
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    else:
        if editedItem.user_id != login_session['user_id']:
            flash("You are not allowed to modify this movie")
            return redirect(url_for('showMenu', category_name=category_name))
        if request.method == 'POST':
            if request.form['name']:
                editedItem.name = request.form['name']
            if request.form['description']:
                editedItem.description = request.form['description']
            if request.form['price']:
                editedItem.price = request.form['price']
            session.add(editedItem)
            session.commit()
            flash(' Movie Item Successfully Edited')
            return redirect(url_for('showMenu', category_name=category_name))
        else:
            return render_template('editMenuItem.html',
                                   category_name=category_name,
                                   login_session=login_session,
                                   item=editedItem,)


# Delete a menu item
@app.route('/category/<string:category_name>/item/<string:item_name>/delete',
           methods=['GET', 'POST'])
def deleteMenuItem(category_name, item_name):
    itemToDelete = session.query(MenuItem).filter_by(name=item_name).one()
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    else:
        if itemToDelete.user_id != login_session['user_id']:
            flash("you are not allowed to delete this movie.")
            return redirect(url_for('showMenu', category_name=category_name))
        if request.method == 'POST':
            session.delete(itemToDelete)
            session.commit()
            flash('Movie Item Successfully Deleted')
            return redirect(url_for('showMenu', category_name=category_name))
        else:
            return render_template('deleteMenuItem.html',
                                   item=itemToDelete,
                                   category_name=category_name,
                                   login_session=login_session)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    #app.run(host='0.0.0.0', port=5000)
