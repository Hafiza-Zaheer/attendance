import os
from PIL import Image
from calendar import monthrange
from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from datetime import datetime, date
import re

app = Flask(__name__, static_url_path='')


# Change this to your secret key (can be anything, it's for extra protection)
app.secret_key = 'your secret key'

# Enter your database connection details below
db_con = mysql.connector.connect(
    host='localhost',
    user='root',
    passwd='root',
    database='attendance_ms'
)

dbCursor = db_con.cursor(buffered=True, dictionary=True)

# return all days of current year and month
def date_iter(year, month):
    all_days = {'date': [], 'day': [], 'presence': []}
    for i in range(1, monthrange(year, month)[1] + 1):
        day = date(year, month, i).strftime('%A')
        # datetime.strptime('2021-08-20', '%Y-%m-%d').date().strftime('%A')
        all_days['date'].append(str(date(year, month, i)))
        all_days['day'].append(day)
        all_days['presence'].append('A')
    return all_days


@app.route('/', methods=['GET', 'POST'])
def login():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        if username and password:
            # Check if account exists using MySQL
            dbCursor.execute('SELECT * FROM users WHERE name = %s AND password = %s AND type = %s', (username, password, 0))
            # Fetch one record and return result
            account = dbCursor.fetchone()
            # If account exists in accounts table in out database
            if account:
                # Create session data, we can access this data in other routes
                session['loggedin'] = True
                session['id'] = account['user_id']
                session['username'] = account['name']
                # Redirect to home page
                return redirect(url_for('home'))
            else:
                # Account doesnt exist or username/password incorrect
                msg = 'Incorrect username/password!'
    # Show the login form with message (if any)
    return render_template('index.html', msg=msg)

    # http://localhost:5000/python/logout - this will be the logout page
@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    # Redirect to login page
    return redirect(url_for('login'))


# http://localhost:5000/pythinlogin/register - this will be the registration page, we need to use both GET and POST requests
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Output message if something goes wrong...
    msg = {
        "user_msg": "",
        "email_msg": "",
        "password_msg": "",
        "image_msg": "",
        "account_msg": "",
        "success_msg": "",
        "fill_msg": ""
    }
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form and 'address' in request.form:
        # Create variables for easy access
        username = request.form['username']
        email = request.form['email']
        address = request.form['address']
        password = request.form['password']
        image = request.files['file']
        confirm_password = request.form['confirm-password']
        if username and email and address and password and confirm_password:
            dbCursor.execute('SELECT * FROM users WHERE name = %s', (username,))
            account = dbCursor.fetchone()
            # If account exists show error and validation checks
            if account:
                msg["account_msg"] = 'Account already exists!'
            elif not re.match(r'^[A-Za-z0-9_]+$', username):
                msg["user_msg"] = 'Name must be characters/underscore/numbers!'
            elif not re.match(r'[\w][\w\d]+@[\w]+\.[\w]+', email):
                msg["email_msg"] = 'Invalid email address!'
            elif password != confirm_password:
                msg["password_msg"] = "Password don't match!"
            elif not image:
                msg["image_msg"] = "Please select an image."
            else:
                # convert into ASCII
                file_name = ''.join(str(ord(c)) for c in username)
                # join ASCII, . and file extention.
                im = Image.open(image)
                im = im.convert("RGB")
                im.save("static/pictures/" + file_name + ".jpg")
                # file_name = file_name + "." + image.filename.rsplit('.', 1)[1]
                # image.save(os.path.join('static/pictures', file_name))
                # Account doesnt exists and the form data is valid, now insert new account into accounts table
                dbCursor.execute('INSERT INTO users VALUES (NULL, %s, %s, %s, %s, %s)', (username, email, password, 0, address))
                db_con.commit()
                msg["success_msg"] = 'You have successfully registered!'
    # elif request.method == 'POST':
        # Form is empty... (no POST data)
        else:
            msg["fill_msg"] = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)


# http://localhost:5000/pythinlogin/home - this will be the home page, only accessible for loggedin users
@app.route('/home', methods=['GET', 'POST'])
def home():
    # Check if user is loggedin
    if 'loggedin' in session and "username" in session and 'id' in session:
        msg = ''
        attendance = 0
        date1 = datetime.now().date().strftime('%d-%b-%Y')
        sqldate = datetime.now().date().strftime('%Y-%m-%d')
        day = datetime.now().date().strftime('%A')
        file_name = 'pictures/' + ''.join(str(ord(c)) for c in session["username"]) + ".jpg"

        dbCursor.execute('SELECT * FROM attendances WHERE user_id = %s AND date = %s', (session['id'], sqldate))
        record = dbCursor.fetchone()
        if record:
            attendance = record['attendance']

        if request.method == 'GET':
            return render_template('home.html', username=session['username'], img=file_name, date=date1, msg=msg,
                                   attendance=attendance)

        elif request.method == 'POST' and 'attendance' in request.form and attendance == 0:
            dbCursor.execute('INSERT INTO attendances VALUES(NULL, %s, %s, %s, %s)',
                             (sqldate, day, 1, session['id']))
            db_con.commit()
            msg = "You have successfully marked your attendance."
            # User is loggedin show them the home page
            return render_template('home.html', username=session['username'], img=file_name, date=date1, msg=msg,
                                   attendance=1)
        elif request.method == 'POST' and 'attendance' in request.form and attendance == 1:
            msg = 'You have already marked your attendance.'
            return render_template('home.html', username=session['username'], img=file_name, date=date1, msg=msg,
                                   attendance=attendance)
        elif request.method == 'POST' and ('attendance' not in request.form) and attendance == 0:
            msg = 'Please mark your attendance and click on submit!'
            return render_template('home.html', username=session['username'], img=file_name, date=date1, msg=msg,
                                   attendance=attendance)
        else:
            return render_template('home.html', username=session['username'], img=file_name, date=date1, msg=msg,
                                   attendance=attendance)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


# http://localhost:5000/pythinlogin/profile - this will be the profile page, only accessible for loggedin users
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    # Check if user is loggedin
    if 'loggedin' in session and "id" in session and "username" in session:
        # We need all the account info for the user so we can display it on the profile page
        dbCursor.execute('SELECT * FROM users WHERE user_id = %s', (session['id'],))
        account = dbCursor.fetchone()
        image_path = 'pictures/' + ''.join(str(ord(c)) for c in session["username"]) + ".jpg"
        # Show the profile page with account info
        if account:
            if request.method == 'GET':
                return render_template('profile.html', account=account, img=image_path)
            elif request.method == 'POST':
                image = request.files['file']
                file_name = ''.join(str(ord(c)) for c in session["username"])
                im = Image.open(image)
                im = im.convert("RGB")
                im.save("static/pictures/" + file_name + ".jpg")
                return render_template('profile.html', account=account, img=image_path)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

# @app.route("/attandance", methods=['GET', 'POST'])
# def attendance():
#     return render_template('attendance.html')

@app.route("/view", methods=['GET', 'POST'])
def view():
    if 'loggedin' in session and "username" in session and 'id' in session:
        msg = ''
        month = request.args.get("month", default="", type=str)
        date1 = {}

        date1['month'] = datetime.now().date().strftime('%B')
        date1['year'] = datetime.now().date().year
        file_name = 'pictures/' + ''.join(str(ord(c)) for c in session["username"]) + ".jpg"
        if month:
            all_days = date_iter(date1['year'], int(month))
            date1['month'] = date(2021, int(month), 20).strftime('%B')
        else:
            all_days = date_iter(date1['year'], datetime.now().date().month)
        dbCursor.execute('SELECT * FROM attendances WHERE user_id = %s', (session['id'],))
        record = dbCursor.fetchall()
        if record:
            for item in record:
                if str(item['date']) in all_days['date']:
                    all_days['presence'][all_days['date'].index(str(item['date']))] = 'P'


            return render_template('view.html', username=session['username'], date=date1, img=file_name, all_days=all_days)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(FLASK_DEBUG=True)
