from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from email_validator import validate_email, EmailNotValidError
from functools import wraps

class RegisterForm(Form):
    name = StringField("Name Lastname: ", validators=[validators.length(min=3,max=25)])
    username = StringField("Username: ", validators=[validators.length(min=4,max=15)])
    email = StringField("Email Adress", validators=[validators.Email(message = "Please enter a valid email address!")])
    password = PasswordField("Password: ", validators=[
        validators.DataRequired(message = "Please enter a password!"),
        validators.EqualTo(fieldname = "confirm",message="Your password does not match...")
        ])
    confirm = PasswordField("Password Confirm")

class LogInForm(Form):
    username = StringField("Username: ")
    password = PasswordField("Password: ")
app = Flask(__name__)
app.secret_key = "memo"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWOORD"] = ""
app.config["MYSQL_DB"] = "firstdb"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Login to access this page.","danger")
            return redirect(url_for("login")) 
    return decorated_function

@app.route("/")
def res():
    return render_template("res.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles"
    result = cursor.execute(sorgu)

    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html", articles = articles)
    else:
        return render_template("articles.html")

@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * from articles where id = %s"
    result = cursor.execute(sorgu, (id,))
    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article = article)
    else:
        return render_template("article.hmtl")

@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles where author = %s"
    result = cursor.execute(sorgu,(session["username"],))
    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles = articles)
    else:
        return render_template("dashboard.html")

@app.route("/register", methods = ["GET", "POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        
        cursor = mysql.connection.cursor()
        sorgu = "Insert into users(name,email,username,password) VALUES(%s, %s, %s, %s)"
        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit()
        cursor.close()
        flash("You have successfully registered...", "success")
        
        return redirect(url_for("login"))
    else:
        return render_template("register.html", form = form)

@app.route("/login", methods = ["GET", "POST"])
def login():
    form = LogInForm(request.form)
    if request.method == "POST" and form.validate():
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()
        sorgu = "Select * From users where username = %s"
        result = cursor.execute(sorgu,(username,))
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered, real_password):
                flash("Login success..","success")
                session["logged_in"] = True
                session["username"] = username
                return redirect(url_for("res"))
            else:
                flash("Password wrong..","danger")
                return redirect(url_for("login"))
                
        else:
            flash("User not found..","danger")
            return redirect(url_for("login"))
    
    else:    
        return render_template("login.html", form = form)

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "success")
    return redirect(url_for("res"))

@app.route("/addarticle", methods = ["GET", "POST"])
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        
        cursor = mysql.connection.cursor()
        sorgu = "Insert into articles(title, author, content) VALUES(%s, %s, %s)"
        cursor.execute(sorgu,(title, session["username"], content))
        mysql.connection.commit()
        cursor.close()

        flash("Article successfully added..", "success")
        return redirect(url_for("dashboard"))
    return render_template("addarticle.html", form = form)

@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles where author = %s and id = %s"
    result = cursor.execute(sorgu, (session["username"], id))
    if result > 0:
        sorgu2 = "Delete from articles where id = %s"
        cursor.execute(sorgu2, (id,))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for("dashboard"))
    else:
        flash("You dont have permission to delete this article", "danger")
        return redirect(url_for("res"))

@app.route("/edit/<string:id>", methods = ["GET", "POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "Select * from articles where id = %s and author = %s"
        result = cursor.execute(sorgu, (id, session["username"]))
        if result == 0:
            flash("There is no such article or you are not authorized to take this action", "danger")
            return redirect(url_for("res"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html", form = form)
    else:
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data
        sorgu2 = "Update articles Set title = %s, content = %s where id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2, (newTitle,newContent,id))
        mysql.connection.commit()
        cursor.close()
        flash("Article successfully updated..", "success")
        return redirect(url_for("dashboard"))

class ArticleForm(Form):
    title = StringField("Article Title", validators=[validators.length(min=4,max=50)])
    content = TextAreaField("Article Content", validators=[validators.length(min=5)])

@app.route("/search", methods = ["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("res"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE title like '%"+str(keyword)+"%'"
        result = cursor.execute(sorgu)
        if result == 0:
            flash("The article containing the searched word was not found..", "warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html", articles = articles)

if __name__ == "__main__":
    app.run(debug = True)
