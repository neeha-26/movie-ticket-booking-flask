from flask import Flask, render_template, request, url_for, redirect, flash
from werkzeug.security import generate_password_hash, check_password_hash  # handles password security
from flask_sqlalchemy import SQLAlchemy #connects flask with database
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
import smtplib
import os
import random

app = Flask(__name__)
TICKET_PRICE = 150
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")



# =========================
# DATABASE
# =========================
class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movie_file_storage.db' #connect your app to sql database
db = SQLAlchemy(model_class=Base)
db.init_app(app)



# =========================
# LOGIN MANAGER
# =========================
login_manager = LoginManager()  #initializes login system
login_manager.init_app(app)

login_manager.login_view = "login"
login_manager.login_message = "Please login to continue."

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ======
#
# ===================
# MODELS
# =========================
class User(UserMixin , db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(1000))
    is_admin = db.Column(db.Boolean, default=False)

class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False , unique=True)
    poster: Mapped[str] = mapped_column(String(300) , nullable=False)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    movie_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)

    seat_number = db.Column(db.String(10))
    show_date = db.Column(db.String(20))
    show_time = db.Column(db.String(20))

    booking_id = db.Column(db.String(30))
    payment_id = db.Column(db.String(30))

    payment_method = db.Column(db.String(30))
    payment_status = db.Column(db.String(20), default="Pending")


#database creation
with app.app_context():
    db.create_all()

    # Add movies only if the table is empty
    # if Movie.query.count() == 0:
    #     db.session.add_all([
    #         Movie(title="RRR", poster="images/RRR.jpeg"),
    #         Movie(title="KGF", poster="images/KGF.jpeg"),
    #         Movie(title="Bahubali", poster="images/Bahubali.jpeg"),
    #         Movie(title="Kantara", poster="images/Kantara.jpeg"),
    #         Movie(title="Salaar", poster="images/salaar.jpeg"),
    #     ])
    #     db.session.commit()
    #
    # # Create admin only if it doesn't already exist
    # existing_admin = User.query.filter_by(email="admin@gmail.com").first()
    #
    # if not existing_admin:
    #     admin = User(
    #         email="admin@gmail.com",
    #         name="Admin",
    #         password=generate_password_hash("1234"),
    #         is_admin=True
    #     )
    #
    #     db.session.add(admin)
    #     db.session.commit()













# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return redirect(url_for("login"))






# -------------------------
# REGISTER
# -------------------------
@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get('email')

        user = db.session.execute(
            db.select(User).where(User.email == email)
        ).scalar()

        if user:
            flash("Email already exists. Login instead.")
            return redirect(url_for('login'))

        new_user = User(
            email=email,
            password=generate_password_hash(request.form.get('password')),
            name=request.form.get('name'),
        )

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user) # logs user in immediately after registration
        return redirect(url_for("open_home_page"))

    return render_template("register.html", logged_in=current_user.is_authenticated)









# -------------------------
# Admin
# -------------------------

@app.route('/admin')
@login_required
def admin_panel():

    if not current_user.is_admin:
        return "Access Denied ❌"

    movies = Movie.query.all()
    return render_template(
        "admin.html",
        movies=movies,
        logged_in=current_user.is_authenticated
    )






# -------------------------
# LOGIN
# -------------------------
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        user = db.session.execute(
            db.select(User).where(User.email == email)
        ).scalar()

        if not user:
            flash("Email not found")
            return redirect(url_for('login'))

        if not check_password_hash(user.password, password):
            flash("Wrong password")
            return redirect(url_for('login'))

        login_user(user)
        return redirect(url_for('open_home_page'))

    return render_template("login.html", logged_in=current_user.is_authenticated)





def send_email(to_email, name, movie, seats, date, time):

    with open("file.txt", "r") as file:
        content = file.read()

    message = content.format(
        name=name,
        movie=movie,
        seats=seats,
        date=date,
        time=time
    )



    # my_email = "shuzukashaik@gmail.com"
    # app_password = "ixjbdudpwntvwxzf"

    my_email = os.environ.get("EMAIL_ADDRESS")
    app_password = os.environ.get("EMAIL_PASSWORD")

    if not my_email or not app_password:
        flash("Email service not configured")
        return

    with smtplib.SMTP("smtp.gmail.com", 587) as connection:
        connection.starttls()
        connection.login(my_email, app_password)

        connection.sendmail(
            from_addr=my_email,
            to_addrs=to_email,
            msg="Subject:Booking Confirmed\n\n" + message
        )





# -------------------------
# HOME PAGE
# -------------------------
@app.route("/open_home_page")
@login_required
def open_home_page():

    search = request.args.get("search")

    if search:
        movies = Movie.query.filter(Movie.title.contains(search)).all()
    else:
        movies = Movie.query.all()

    return render_template(
        "open_home_page.html",
        movies=movies,
        logged_in=current_user.is_authenticated
    )








# -------------------------
# MOVIE DETAILS (SHOW SELECTION)
# -------------------------
@app.route('/movie/<int:movie_id>')
@login_required
def movie_detail(movie_id):
    movie = db.get_or_404(Movie, movie_id)
    return render_template("movie_detail.html", movie=movie , logged_in = current_user.is_authenticated)




# -------------------------
# SELECT SHOW
# -------------------------
@app.route("/select_show/<int:movie_id>", methods=["GET", "POST"])
@login_required
def select_show(movie_id):

    movie = db.get_or_404(Movie, movie_id)

    if request.method == "POST":

        show_date = request.form.get("show_date")
        show_time = request.form.get("show_time")

        return redirect(url_for(
            "select_seat",
            movie_id=movie.id,
            date=show_date,
            time=show_time
        ))

    return render_template(
        "select_show.html",
        movie=movie,
        logged_in=current_user.is_authenticated
    )










# -------------------------
# Add Movies
# -------------------------
@app.route('/add_movie', methods=["POST"])
@login_required
def add_movie():

    if not current_user.is_admin:
        return "Access Denied ❌"

    title = request.form.get("title")
    poster = request.form.get("poster")

    existing = Movie.query.filter_by(title=title).first()

    if existing:
        flash("Movie already exists!")
        return redirect(url_for('admin_panel'))

    new_movie = Movie(title=title, poster=poster)

    db.session.add(new_movie)
    db.session.commit()

    flash("Movie added successfully!")

    return redirect(url_for('admin_panel'))








# -------------------------
# Delete movies
# -------------------------
@app.route('/delete_movie/<int:movie_id>')
@login_required
def delete_movie(movie_id):

    if not current_user.is_admin:
        return "Access Denied ❌"

    movie = db.get_or_404(Movie, movie_id)

    db.session.delete(movie)
    db.session.commit()

    flash("Movie deleted!")

    return redirect(url_for('admin_panel'))










# -------------------------
# SEAT SELECTION
# -------------------------
@app.route('/select_seat/<int:movie_id>', methods=["GET", "POST"])
@login_required
def select_seat(movie_id):

    movie = db.get_or_404(Movie, movie_id)

    # =========================
    # POST → Go to Payment Page
    # =========================
    if request.method == "POST":

        seats = request.form.get("selected_seats")
        show_date = request.form.get("show_date")
        show_time = request.form.get("show_time")

        if not seats:
            flash("Please select at least one seat!")
            return redirect(url_for(
                "select_seat",
                movie_id=movie.id,
                date=show_date,
                time=show_time
            ))

        # ✅ FIX: clean seat list properly
        seat_list = [s.strip() for s in seats.split(",") if s.strip()]

        # remove duplicates
        seat_list = list(set(seat_list))

        # =========================
        # CHECK ALREADY BOOKED SEATS
        # =========================
        for seat in seat_list:
            existing = Booking.query.filter_by(
                movie_id=movie.id,
                seat_number=seat,
                show_date=show_date,
                show_time=show_time
            ).first()

            if existing:
                flash(f"Seat {seat} already booked!")
                return redirect(url_for(
                    "select_seat",
                    movie_id=movie.id,
                    date=show_date,
                    time=show_time
                ))

        # =========================
        # GO TO PAYMENT PAGE
        # =========================
        return render_template(
            "payment.html",
            movie=movie,
            seats=seat_list,
            total=len(seat_list) * TICKET_PRICE,
            show_date=show_date,
            show_time=show_time,
            logged_in=current_user.is_authenticated
        )

    # =========================
    # GET → Show Seat Layout
    # =========================
    show_date = request.args.get("date")
    show_time = request.args.get("time")

    booked_seats = Booking.query.filter_by(
        movie_id=movie_id,
        show_date=show_date,
        show_time=show_time
    ).all()

    booked = [b.seat_number for b in booked_seats]

    return render_template(
        "select_seat.html",
        movie=movie,
        booked=booked,
        show_date=show_date,
        show_time=show_time,
        logged_in=current_user.is_authenticated
    )



# -------------------------
# Cancel Booking
# -------------------------
@app.route('/cancel_booking/<string:booking_id>')
@login_required
def cancel_booking(booking_id):

    bookings = Booking.query.filter_by(booking_id=booking_id).all()

    if not bookings:
        flash("Booking not found")
        return redirect(url_for("my_bookings"))

    # check ownership properly
    for b in bookings:
        if b.user_id != current_user.id:
            return "Unauthorized ❌"

    for b in bookings:
        db.session.delete(b)

    db.session.commit()

    flash("Booking cancelled!")
    return redirect(url_for('my_bookings'))




@app.route("/confirm_payment", methods=["POST"])
@login_required
def confirm_payment():

    movie_id = request.form.get("movie_id")
    seats = request.form.get("selected_seats")
    show_date = request.form.get("show_date")
    show_time = request.form.get("show_time")
    payment_method = request.form.get("payment_method")

    movie = db.get_or_404(Movie, int(movie_id))

    seat_list = [s.strip() for s in seats.split(",") if s.strip()]




    booking_id = f"BK{random.randint(100000, 999999)}"
    payment_id = f"PAY{random.randint(100000, 999999)}"

    for seat in seat_list:

        # Check if the seat was booked by someone else
        existing = Booking.query.filter_by(
            movie_id=movie.id,
            seat_number=seat,
            show_date=show_date,
            show_time=show_time
        ).first()

        if existing:
            flash(f"Seat {seat} has just been booked by another user.")
            return redirect(url_for(
                "select_seat",
                movie_id=movie.id,
                date=show_date,
                time=show_time
            ))

        booking = Booking(
            movie_id=movie.id,
            user_id=current_user.id,
            seat_number=seat,
            show_date=show_date,
            show_time=show_time,

            booking_id=booking_id,
            payment_id=payment_id,
            payment_method=payment_method,
            payment_status="Paid"
        )

        db.session.add(booking)

    db.session.commit()

    send_email(
        current_user.email,
        current_user.name,
        movie.title,
        ",".join(seat_list),
        show_date,
        show_time
    )

    return redirect(url_for(
        "success",
        movie_id=movie.id,
        seats=",".join(seat_list),
        date=show_date,
        time=show_time,
        booking_id=booking_id,
        payment_id=payment_id
    ))








# -------------------------
# SUCCESS PAGE
# -------------------------
@app.route('/success')
@login_required
def success():
    movie_id = request.args.get("movie_id", type=int)
    seats = request.args.get("seats")
    date = request.args.get("date")
    time = request.args.get("time")

    booking_id = request.args.get("booking_id")
    payment_id = request.args.get("payment_id")

    if not movie_id or not seats:
        return redirect(url_for("open_home_page"))

    movie = db.get_or_404(Movie, int(movie_id))

    seat_list = seats.split(",")
    total = len(seat_list) * TICKET_PRICE

    return render_template(
        "success.html",
        movie=movie,
        seats=seat_list,
        total=total,
        date=date,
        time=time,
        booking_id=booking_id,
        payment_id=payment_id,
        logged_in=current_user.is_authenticated
    )









# -------------------------
# MY BOOKINGS
# -------------------------
@app.route('/my_bookings')
@login_required
def my_bookings():

    bookings = Booking.query.filter_by(user_id=current_user.id).all()

    booking_data = []

    for b in bookings:
        movie = db.session.get(Movie, b.movie_id)

        booking_data.append({
            "id": b.id,
            "title": movie.title,
            "poster": movie.poster,
            "seat": b.seat_number,
            "date": b.show_date,
            "time": b.show_time,
            "booking_id": b.booking_id,
            "payment_id": b.payment_id,
            "payment_status": b.payment_status
        })

    return render_template("my_bookings.html", bookings=booking_data , logged_in = current_user.is_authenticated)










# -------------------------
# LOGOUT
# -------------------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))






# =========================
# RUN
# =========================

if __name__ == "__main__":
    app.run(debug=True, port=5001)