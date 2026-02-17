from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_migrate import Migrate
from functools import wraps

app = Flask(__name__)
app.secret_key = 'asdfghjkuytgbnjghfdbvd' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mad.db'

db = SQLAlchemy()
db.init_app(app)
migrate = Migrate(app, db)
app.app_context().push()



class User(db.Model):
   # Our user models the heroes and admins of the parking saga.
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    address = db.Column(db.Text)
    pincode = db.Column(db.String(10))
    is_admin = db.Column(db.Boolean, default=False)

class Booking(db.Model):
    #Each booking is a ticket to park—log it for history and billing.
    
    __tablename__ = 'booking'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'))
    vehicle_no = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime)  # Start time of parking session
    status = db.Column(db.String(20))  # 'Parked' or 'Released'
    slot_id = db.Column(db.Integer, db.ForeignKey('parking_slot.id'))
    cost = db.Column(db.Float)  # Computed cost for session
    release_time = db.Column(db.DateTime)  # When parking ended
    total_cost = db.Column(db.Float)  # Final payable amount

class ParkingLot(db.Model):
    """
    Parking lot info: managed by admins, used by drivers.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    address = db.Column(db.Text)
    pin_code = db.Column(db.String(10))
    price_per_hour = db.Column(db.Float)
    max_spots = db.Column(db.Integer)
    
    # Relationships to slots and bookings
    slots = db.relationship('ParkingSlot', backref='lot', cascade='all, delete-orphan')
    bookings = db.relationship('Booking', backref='lot', lazy=True)
    
    def __repr__(self):
        return f'🅿️({self.id}) {self.name}'

class ParkingSlot(db.Model):
    """
    The individual battlefield spots for cars - may luck be on your side.
    """
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'))
    status = db.Column(db.String(1))  # 'A' = Available, 'O' = Occupied

# Create all tables once
db.create_all()



def login_required(f):
    """
    Decorator for routes needing a logged-in user.
    If missing, will flash a message and redirect.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash("Looks like you've wandered off. Please log in to continue.")
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

#routes

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles the sign-in process.
    GET shows the login form,
    POST verifies user and password, then sends to appropriate dashboard.
    """
    if request.method == 'GET':
        return render_template('login.html')

    user_email = request.form.get('email')
    user_password = request.form.get('pass')
    print(f"[LOGIN] Attempt by {user_email}")

    user = User.query.filter_by(email=user_email).first()
    if user:
        if user.password == user_password:  # TODO: when hashing is done , need to put a check for them instead
            print(f"[LOGIN] Password correct for {user_email}")
            session['user_id'] = user.id
            if user.is_admin:
                return redirect('/admin')
            else:
                return redirect('/user_dashboard')
        else:
            flash("wrong password. Double-check your caps lock")
            return render_template('login.html', error="Incorrect password.")
    else:
        flash("User not found. Wanna register?")
        return redirect('/register')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    New user registration.
    GET renders form; POST validates and adds user if unique.
    """
    if request.method == 'GET':
        return render_template('register.html')

    user_email = request.form.get('email')
    user_password = request.form.get('password')
    user_address = request.form.get('address')
    user_fullname = request.form.get('fullname')
    user_pincode = request.form.get('pincode')

    existing_user = User.query.filter(
        (User.username == user_fullname) | (User.email == user_email)
    ).first()
    if existing_user:
        print(f"[REGISTER] Duplicate attempt for {user_fullname} / {user_email}")
        flash("That username or email is already taken. Try something unique.")
        return render_template('register.html', error="Username or email exists.")

    new_user = User(
        username=user_fullname,
        password=user_password,  # TODO hash passwords again
        email=user_email,
        address=user_address,
        pincode=user_pincode
    )
    db.session.add(new_user)
    db.session.commit()
    print(f"[REGISTER] New user {user_fullname} registered at {datetime.now()}")
    flash("You've registered! Now let's get you logged in.")
    return redirect('/login')

@app.route('/user_dashboard', methods=['GET', 'POST'])
@login_required
def user_dashboard():
    """
    User's control panel: see history, search for parking lots.
    """
    user_id = session['user_id']
    user = User.query.get(user_id)

    parking_history = Booking.query.filter_by(user_id=user_id).order_by(Booking.timestamp.desc()).all()
    available_lots = []
    search_query = None

    if request.method == 'POST':
        search_query = request.form.get('search')
        matched_lots = ParkingLot.query.filter(
            (ParkingLot.address.ilike(f'%{search_query}%')) | (ParkingLot.pin_code.like(f'%{search_query}%'))
        ).all()

        for lot in matched_lots:
            active_bookings = Booking.query.filter_by(lot_id=lot.id, status='Parked').count()
            available_spots = lot.max_spots - active_bookings
            available_lots.append({
                'id': lot.id,
                'address': lot.address,
                'available': available_spots,
                'max_spots': lot.max_spots
            })

    return render_template(
        'user_dashboard.html',
        user=user,
        parking_history=parking_history,
        results=available_lots,
        query=search_query
    )

@app.route('/user_edit_profile', methods=['GET', 'POST'])
@login_required
def user_edit_profile():
    """
    Not an admin? Perfect spot to update your info when life changes happen.
    """
    user = User.query.get(session['user_id'])
    if user.is_admin:
        flash("Admins, your throne awaits elsewhere.")
        return redirect('/login')

    if request.method == 'POST':
        user.email = request.form.get('email')
        user.username = request.form.get('username')
        user.password = request.form.get('password')  #TODO can also hash passwords here , should actually
        user.address = request.form.get('address')
        user.pincode = request.form.get('pincode')
        db.session.commit()
        flash("Profile updated! You're all set.")
        return redirect('/user_dashboard')

    return render_template('user_edit_profile.html', user=user)

@app.route('/user_summary')
@login_required
def user_summary():
    """
    Show aggregated parking statistics per lot for the logged-in user.
    """
    user_id = session['user_id']
    user = User.query.get(user_id)

    from sqlalchemy import func
    data = db.session.query(
        ParkingLot.name,
        func.count(Booking.id)
    ).join(Booking).filter(Booking.user_id == user_id).group_by(ParkingLot.id).all()

    labels = [row[0] for row in data]
    counts = [row[1] for row in data]

    return render_template('user_summary.html', user=user, labels=labels, counts=counts)

@app.route('/book_parking/<int:lot_id>', methods=['GET', 'POST'])
@login_required
def book_parking(lot_id):
    """
    User reserves an available slot in the given parking lot.
    """
    user_id = session['user_id']
    user = User.query.get(user_id)

    available_slot = ParkingSlot.query.filter_by(lot_id=lot_id, status='A').first()
    if not available_slot:
        flash("no free spots here right now — try another lot!")
        return redirect('/user_dashboard')

    if request.method == 'POST':
        vehicle_no = request.form.get('vehicle_no')

        booking = Booking(
            user_id=user_id,
            lot_id=lot_id,
            slot_id=available_slot.id,
            vehicle_no=vehicle_no,
            status='Parked',
            timestamp=datetime.now()
        )
        db.session.add(booking)

        # Mark the slot as occupied, so no double-booking problem arises
        available_slot.status = 'O'
        db.session.commit()

        flash("Success! Your spot is reserved.")
        return redirect('/user_dashboard')

    return render_template('book_parking.html', user=user, lot_id=lot_id, slot_id=available_slot.id)

@app.route('/release_parking/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def release_parking(booking_id):
    """
    Ends parking session, calculates fees, and frees the slot.
    """
    booking = Booking.query.get(booking_id)
    if not booking or booking.status != 'Parked':
        flash("invalid booking or already released.")
        return redirect('/user_dashboard')

    now = datetime.now()
    duration_hours = (now - booking.timestamp).total_seconds() / 3600

    # Use the lot's price per hour if available; else default to 50
    lot = ParkingLot.query.get(booking.lot_id)
    rate_per_hour = lot.price_per_hour if lot else 50
    total_cost = round(duration_hours * rate_per_hour, 2)

    if request.method == 'POST':
        booking.status = 'Released'
        booking.release_time = now
        booking.cost = total_cost

        slot = ParkingSlot.query.get(booking.slot_id)
        if slot:
            slot.status = 'A'  # Mark slot as free

        db.session.commit()
        flash(f"Parking released. Total charge: ₹{total_cost}")
        return redirect('/user_dashboard')

    return render_template('release_parking.html', booking=booking, now=now, total_cost=total_cost)

#admin routes

@app.route('/admin')
@login_required
def admin():
    """
    Main admin page - view all lots and their slot statuses.
    """
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash("Admins only! You shall not pass.")
        return redirect('/login')

    lots = ParkingLot.query.all()
    summary = []

    for lot in lots:
        slots = ParkingSlot.query.filter_by(lot_id=lot.id).all()
        occupied = sum(1 for s in slots if s.status == 'O')
        summary.append({
            'id': lot.id,
            'capacity': len(slots),
            'occupied': occupied,
            'slots': slots
        })

    return render_template('admin.html', lots=summary)

@app.route('/users')
@login_required
def users():
    """
    Admin-only page: list of registered users (excluding admins).
    """
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash("Admins only! You shall not pass.")
        return redirect('/login')

    user_list = User.query.filter_by(is_admin=False).all()
    return render_template('users.html', users=user_list)

@app.route('/add_lot', methods=['GET', 'POST'])
@login_required
def add_lot():
    """
    Admin action: add new parking lot and create all its slots.
    """
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash("Admins only! No sneaking in here.")
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        pin_code = request.form['pin_code']
        price_per_hour = float(request.form['price_per_hour'])
        max_spots = int(request.form['max_spots'])

        new_lot = ParkingLot(
            name=name,
            address=address,
            pin_code=pin_code,
            price_per_hour=price_per_hour,
            max_spots=max_spots
        )
        db.session.add(new_lot)
        db.session.commit()

        for _ in range(max_spots):
            slot = ParkingSlot(lot_id=new_lot.id, status='A')
            db.session.add(slot)
        db.session.commit()

        flash(f"Lot '{name}' added with {max_spots} spots!")
        return redirect('/admin')

    return render_template('add_lot.html')

@app.route('/view_slot/<int:slot_id>', methods=['GET', 'POST'])
@login_required
def view_slot(slot_id):
    """
    Show details of a specific parking slot, including current booking if occupied.
    Allows deletion if free.
    """
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash("Admins only, sorry!")
        return redirect('/login')

    slot = ParkingSlot.query.get_or_404(slot_id)
    lot = ParkingLot.query.get(slot.lot_id)
    estimated_cost = None
    current_booking = None

    if slot.status == 'O':
        current_booking = Booking.query.filter_by(slot_id=slot.id, status='Parked').order_by(Booking.timestamp.desc()).first()
        if current_booking:
            now = datetime.now()
            duration = (now - current_booking.timestamp).total_seconds() / 3600
            estimated_cost = round(duration * lot.price_per_hour, 2)

    if request.method == 'POST':
        if slot.status == 'O':
            flash("Cannot delete an occupied slot!")
            return redirect('/view_slot/' + str(slot_id))
        db.session.delete(slot)
        db.session.commit()
        flash("Slot deleted.")
        return redirect('/admin')

    return render_template('view_slot.html', slot=slot, lot=lot, booking=current_booking, estimate=estimated_cost)

@app.route('/delete_lot/<int:lot_id>')
@login_required
def delete_lot(lot_id):
    """
    Admin can delete a whole parking lot and its slots.
    """
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash("Admins only!")
        return redirect('/login')

    ParkingSlot.query.filter_by(lot_id=lot_id).delete()
    ParkingLot.query.filter_by(id=lot_id).delete()
    db.session.commit()
    flash("Lot and associated slots deleted.")
    return redirect('/admin')

@app.route('/edit_lot/<int:lot_id>', methods=['GET', 'POST'])
@login_required
def edit_lot(lot_id):
    """
    Admin edits parking lot info.
    """
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash("Admins only!")
        return redirect('/login')

    lot = ParkingLot.query.get_or_404(lot_id)
    if request.method == 'POST':
        lot.name = request.form['name']
        lot.address = request.form['address']
        lot.pin_code = request.form['pin_code']
        lot.price_per_hour = float(request.form['price_per_hour'])
        lot.max_spots = int(request.form['max_spots'])
        db.session.commit()
        flash(f"Lot '{lot.name}' updated.")
        return redirect('/admin')
    
    return render_template('edit_lot.html', lot=lot)

@app.route('/admin_edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """
    Admin updates their own profile. Separate from user edit.
    """
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash("Admins only!")
        return redirect('/login')

    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        address = request.form.get('address')
        pincode = request.form.get('pincode')

        existing = User.query.filter(
            ((User.email == email) | (User.username == username)) & (User.id != user.id)
        ).first()

        if existing:
            flash("Email or username already taken by another user.")
            return render_template('edit_profile.html', admin=user, error="Conflicting user info.")

        user.email = email
        user.username = username
        user.password = password  # TODO: can create hashed password with given time 
        user.address = address
        user.pincode = pincode
        db.session.commit()

        flash("Admin profile updated successfully.")
        return redirect('/admin')

    return render_template('admin_edit_profile.html', admin=user)

@app.route('/summary')
@login_required
def summary():
    """
    Admin gets a stats dashboard for revenue and slot usage across all lots.
    """
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash("Admins only!")
        return redirect('/login')

    lots = ParkingLot.query.all()
    lot_revenue = {}
    slot_summary = []
    
    for lot in lots:
        revenue = sum([b.cost for b in lot.bookings if b.cost])
        lot_revenue[lot.name] = revenue

        occupied = ParkingSlot.query.filter_by(lot_id=lot.id, status='O').count()
        available = lot.max_spots - occupied
        slot_summary.append({
            'name': lot.name,
            'occupied': occupied,
            'available': available
        })

    return render_template('summary.html', lot_revenue=lot_revenue, slot_summary=slot_summary)

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """
    Search users or parking lots.
    Query param: user_id, location, or pincode.
    """
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash("Admins only!")
        return redirect('/login')

    results = []
    query = ''
    category = ''
    
    if request.method == 'POST':
        category = request.form['category']
        query = request.form['search']

        if category == 'user_id':
            results = User.query.filter(User.id == query).all()
        elif category == 'location':
            results = ParkingLot.query.filter(ParkingLot.name.ilike(f"%{query}%")).all()
        elif category == 'pincode':
            results = ParkingLot.query.filter(ParkingLot.pin_code.ilike(f"%{query}%")).all()

        for lot in results:
            lot.occupied_spots = ParkingSlot.query.filter_by(lot_id=lot.id, status='O').count()
            lot.max_spots = ParkingSlot.query.filter_by(lot_id=lot.id).count() 

    return render_template('search.html', results=results, category=category, query=query)



def create_auto_admin():
    """
    Creates a default admin upon first launch.
    Please change the admin password post-launch for security.
    """
    if not User.query.filter_by(is_admin=True).first():
        admin = User(
            username='admin',
            password='admin', #cant be putting such easy password in actual app but only for testing
            email='admin@example.com',
            address='Top Floor, Parking HQ',
            pincode='0000',
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print(" Admin created!")
    else:
        print("Admin’s already made , dont make another")

if __name__ == '__main__':
    create_auto_admin()
    app.run(debug=True)
