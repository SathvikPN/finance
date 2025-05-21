import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/addcash", methods=["POST"])
@login_required
def addcash():
    """Add cash to user's account"""
    # Ensure cash was submitted
    if not request.form.get("cash"):
        return apology("must provide cash", 403)

    # Ensure cash is a positive number
    cash = request.form.get("cash")
    if not cash or float(cash) <= 0:
        return apology("invalid cash", 403)
    
    cash = float(cash)

    # Update user's cash
    db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", cash, session["user_id"])

    # Flash a success message   
    flash(f"Added ${cash:.2f} to your account.")

    # Redirect user to home page
    return redirect("/")

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # Get user_id from session
    user_id = session["user_id"]
    # Get portfolio data for the user
    portfolio = db.execute("SELECT symbol, shares, price, total FROM portfolio WHERE user_id = ?", user_id)
    cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]
    total = cash + sum([row["total"] for row in portfolio])
    return render_template("index.html", portfolio=portfolio, cash=cash, total=total)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # layout.html ensures /register is only visible to users who are not logged in

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)
        
        # Ensure username is not already taken
        db_rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        if len(db_rows) != 0:
            return apology("username already taken", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure confirmation was submitted
        elif not request.form.get("confirmation"):
            return apology("must provide confirmation", 403)

        # Ensure password and confirmation match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords must match", 403)

        # Hash the password
        hash = generate_password_hash(request.form.get("password"), method="pbkdf2:sha256") # default method scrypt errored in macos

        # Insert new user into database
        db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)",
            request.form.get("username"),
            hash,
        )

        # Redirect to login page
        flash("Registered successfully!")
        return redirect("/login")
    
    # User reached route via GET (as by clicking a link or via redirect)
    return render_template("register.html")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    
    if request.method == "POST":
        # Ensure symbol was submitted
        symbol = request.form.get("symbol")
        quote = None 
        try:
            quote = lookup(symbol)
        except:
            return apology("symbol not listed in C$50 finance", 403)
        
        if not symbol or not quote:
            return apology("invalid symbol", 403)
        
        shares = request.form.get("shares")
        if not shares or int(shares) <= 0:
            return apology("invalid shares", 403)
        
        symbol = symbol.upper()
        shares = int(shares)

        required_cash = shares * quote["price"]
        user_id = session["user_id"]
        user_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]

        if user_cash < required_cash:
            return apology("not enough cash", 403)
        
        # Update user's cash
        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", required_cash, user_id)

        # Insert transaction into history
        db.execute(
            "INSERT INTO history (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)",
            user_id, symbol, shares, quote["price"] )

        # Check if the user already owns shares of the stock
        owned_shares = db.execute("SELECT shares FROM portfolio WHERE user_id = ? AND symbol = ?",
                                    user_id, symbol)
        if len(owned_shares) > 0:
            # Update the number of shares owned
            db.execute(
                "UPDATE portfolio SET shares = shares + ? WHERE user_id = ? AND symbol = ?",
                shares, user_id, symbol )
        else:
            # Insert the new stock into the portfolio
            db.execute(
                "INSERT INTO portfolio (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)",
                user_id, symbol, shares, quote["price"] )

        # Flash a success message   
        flash(f"Bought {shares} shares of {quote['name']} ({quote['symbol']}) at ${quote['price']:.2f} each.")

        
        # Redirect user to home page
        return redirect("/")
        
        
    # User reached route via GET (as by clicking a link or via redirect)
    return render_template("buy.html")
        


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    rows = db.execute("SELECT symbol, shares, price, time FROM history WHERE user_id = ?", session["user_id"])
    return render_template("history.html", rows=rows)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide symbol", 403)

        # Lookup quote
        quote = lookup(request.form.get("symbol"))

        # Ensure symbol is valid
        if quote == None:
            return apology("invalid symbol", 403)

        # Render quote
        return render_template("quote.html", quote=quote)
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")
    return apology("TODO")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        # Ensure symbol was submitted
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("must provide symbol", 403)
        
        shares = request.form.get("shares")
        if not shares or int(shares) <= 0:
            return apology("invalid shares", 403)
        
        shares = int(shares)

        row = db.execute("SELECT symbol, shares FROM portfolio WHERE user_id = ? AND symbol = ?", session["user_id"], symbol)
        if len(row) == 0:
            return apology("not owned", 403)
        if row[0]["shares"] < shares:
            return apology("not enough shares", 403)
        


        # Lookup quote
        quote = lookup(symbol)
        if quote == None:
            return apology("invalid symbol", 403)
        # Get user_id from session
        user_id = session["user_id"]
        # Get user's cash
        user_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]
        # Update user's cash
        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", shares * quote["price"], user_id)
        
        # Insert transaction into history
        db.execute(
            "INSERT INTO history (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)",
            user_id, symbol, -shares, quote["price"] )

        # Update the number of shares owned
        db.execute(
            "UPDATE portfolio SET shares = shares - ? WHERE user_id = ? AND symbol = ?",
            shares, user_id, symbol )

        # If the user has no more shares of the stock, remove it from the portfolio
        if row[0]["shares"] == shares:
            db.execute("DELETE FROM portfolio WHERE user_id = ? AND symbol = ?",
                user_id, symbol )

        # Flash a success message   
        flash(f"Sold {shares} shares of {quote['name']} ({quote['symbol']}) at ${quote['price']:.2f} each.")

        
        # Redirect user to home page
        return redirect("/")
    
    # User reached route via GET (as by clicking a link or via redirect)
    user_id = session["user_id"]
    # Get portfolio data for the user
    stocks = db.execute("SELECT symbol FROM portfolio WHERE user_id = ?", user_id)
    stocks = [stock["symbol"] for stock in stocks]
    return render_template("sell.html", stocks=stocks)
