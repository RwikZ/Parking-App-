from flask import Flask, render_template, request, redirect,session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime



app =Flask(__name__)
app.secret_key = 'asdfghjkuytgbnjghfdbvd' 
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///mad.db'

db=SQLAlchemy()

db.init_app(app)

app.app_context().push()

class User(db.Model):
    __tablename__='users'
    id=db.Column(db.Integer, primary_key=True, auto_increment=True)
    username=db.Column(db.String(80), unique=True,nullable=False)
    password=db.Column(db.String(120),nullable=False)
    email=db.Column(db.String(120),unique=True,nullable=False)
    address=db.Column(db.Text)
    pincode=db.Column(db.String(10))
    is_admin=db.Column(db.Boolean,default=False)


class Booking(db.Model):
    __tablename__ = 'booking'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'))
    vehicle_no = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime)
    status = db.Column(db.String(20)) 


class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))             
    address = db.Column(db.Text)                    
    pin_code = db.Column(db.String(10))
    price_per_hour = db.Column(db.Float)
    max_spots = db.Column(db.Integer)

    # Relationship to parking slots
    slots = db.relationship("ParkingSlot", backref="lot", cascade="all, delete")
    def __repr__(self):
        return f'<ParkingLot {self.id} - {self.name}>'

class ParkingSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'))
    status = db.Column(db.String(1))  # 'A' = Available, 'O' = Occupied
    


db.create_all()




@app.route('/')
def default():
    return render_template("login.html")



@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='GET':
        return render_template("login.html")
    if request.method=='POST':
        username=request.form.get('email')
        password=request.form.get('pass')
        print(username,password)
        user_exist=User.query.filter_by(email=username).first()

        if user_exist:
            if user_exist.password == password:
                print('Password is correct!')
                if user_exist.is_admin:
                    return redirect('/admin')
                else:
                    session['user_id'] = user_exist.id
                    print('User logged in successfully')
                    return render_template('user_dashboard.html', user=user_exist, parking_history=[], results=[], query=None)
            else:
                print("Password is incorrect")
                return render_template('login.html',error='Password is wrong')
        else:
            print("User doesnt exist")
            return redirect('/register')





@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='GET':
        return render_template("register.html")
    if request.method=='POST':
        formemail=request.form.get('email')
        formpass=request.form.get('password')
        formadd=request.form.get('address')
        formname=request.form.get('fullname')
        formpin=request.form.get('pincode')
        user_exist=User.query.filter_by(username=formemail).first()
        if user_exist:
            print("Username already exists")
            return render_template('register.html',error='Username already exists')
        else:
            new_user=User(username=formname,password=formpass,email=formemail,address=formadd,pincode=formpin)
            db.session.add(new_user)
            db.session.commit()
            print('User added')
            return redirect('/login')


@app.route('/user_dashboard', methods=['GET', 'POST'])
def user_dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    user = User.query.get(user_id)

    # Recent parking history
    parking_history = Booking.query.filter_by(user_id=user_id).order_by(Booking.timestamp.desc()).all()

    search_results = []
    query = None
    if request.method == 'POST':
        query = request.form.get('search')
        search_results = ParkingLot.query.filter(
            (ParkingLot.address.ilike(f'%{query}%')) | (ParkingLot.pin_code.like(f'%{query}%'))
        ).all()

    return render_template('user_dashboard.html', user=user, parking_history=parking_history, results=search_results, query=query)

@app.route('/user_edit_profile', methods=['GET', 'POST'])
def user_edit_profile():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    user = User.query.get(user_id)
    if not user or user.is_admin:
        return redirect('/login')  # Prevent admin from using this route

    if request.method == 'POST':
        user.email = request.form.get('email')
        user.username = request.form.get('username')
        user.password = request.form.get('password')
        user.address = request.form.get('address')
        user.pincode = request.form.get('pincode')
        db.session.commit()
        return redirect('/user_dashboard')

    return render_template('user_edit_profile.html', user=user)





@app.route('/admin')
def admin():
    lots = ParkingLot.query.all()  # Get all lots
    data = []

    for lot in lots:
        slots = ParkingSlot.query.filter_by(lot_id=lot.id).all()
        occupied = sum(1 for slot in slots if slot.status == 'O')

        data.append({
            'id': lot.id,
            'capacity': len(slots),
            'occupied': occupied,
            'slots': slots
        })

    return render_template('admin.html', lots=data)

@app.route('/users')
def users():
    user_list = User.query.filter_by(is_admin=False).all()
    return render_template('users.html', users=user_list)






@app.route('/add_lot', methods=['GET', 'POST'])
def add_lot():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        pin_code = request.form['pin_code']
        price_per_hour = float(request.form['price_per_hour'])
        max_spots = int(request.form['max_spots'])

        # Create the lot
        new_lot = ParkingLot(
            name=name,
            address=address,
            pin_code=pin_code,
            price_per_hour=price_per_hour,
            max_spots=max_spots
        )

        db.session.add(new_lot)
        db.session.commit()

        # Create empty slots (all available 'A')
        for _ in range(max_spots):
            slot = ParkingSlot(lot_id=new_lot.id, status='A')
            db.session.add(slot)

        db.session.commit()
        return redirect('/admin')

    return render_template('add_lot.html')





@app.route('/view_slot/<int:slot_id>', methods=['GET', 'POST'])
def view_slot(slot_id):
    slot = ParkingSlot.query.get_or_404(slot_id)
    lot = ParkingLot.query.get(slot.lot_id)

    if request.method == 'POST':
        if slot.status == 'O':
            return "Cannot delete occupied slot", 400
        db.session.delete(slot)
        db.session.commit()
        return redirect('/admin')

    return render_template('view_slot.html', slot=slot, lot=lot)





@app.route('/delete_lot/<int:lot_id>')
def delete_lot(lot_id):
    ParkingSlot.query.filter_by(lot_id=lot_id).delete()
    ParkingLot.query.filter_by(id=lot_id).delete()
    db.session.commit()
    return redirect('/admin')





@app.route('/edit_lot/<int:lot_id>', methods=['GET', 'POST'])
def edit_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)

    if request.method == 'POST':
        lot.name = request.form['name']
        lot.address = request.form['address']
        lot.pin_code = request.form['pin_code']
        lot.price_per_hour = float(request.form['price_per_hour'])
        lot.max_spots = int(request.form['max_spots'])

        db.session.commit()
        return redirect('/admin')

    return render_template('edit_lot.html', lot=lot)






@app.route('/admin_edit_profile', methods=['GET', 'POST'])
def edit_profile():
    admin = User.query.filter_by(is_admin=True).first()

    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        address = request.form.get('address')
        pincode = request.form.get('pincode')

        # Check for unique email/username (not used by other users)
        existing_user = User.query.filter(
            (User.email == email) | (User.username == username)
        ).filter(User.id != admin.id).first()

        if existing_user:
            return render_template('edit_profile.html', admin=admin, error="Email or username already taken.")

        # Update fields
        admin.email = email
        admin.username = username
        admin.password = password
        admin.address = address
        admin.pincode = pincode
        db.session.commit()

        return redirect('/admin')

    return render_template('admin_edit_profile.html', admin=admin)




@app.route('/search', methods=['GET', 'POST'])
def search():
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
                lot.occupied_spots = ParkingSlot.query.filter_by(lot_id=lot.id, status='occupied').count()
    return render_template('search.html', results=results, category=category, query=query)




def create_auto_admin():
    if_exists=User.query.filter_by(is_admin=True).first()

    if not if_exists:
        admin=User(username='admin',password='admin',email='admin@example.com',address='Admin hq',pincode='0000',is_admin=True)
        db.session.add(admin)
        db.session.commit()
        print('Admin created')
    else:
        print('Admin already present')


if __name__== '__main__':
    create_auto_admin()
    app.run(debug=True)
