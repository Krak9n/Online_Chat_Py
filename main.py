from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase
import datetime

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///users.sqlite3'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "hjhjsdahhds"
socketio = SocketIO(app)
db = SQLAlchemy(app)
class users(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    username = db.Column("username", db.String(50))
    password = db.Column("password", db.String(50))
    
    def __init__(self, username, password) -> None:
        self.username = username
        self.password = password
        super().__init__()

class file(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    filename = db.Column("filename", db.String(100))
    filedata = db.Column("filedata", db.Text)  # Данные файла в формате base64
    room = db.Column("room", db.String(4))  # Код комнаты, к которой привязан файл

    def __init__(self, filename, filedata, room) -> None:
        self.filename = filename
        self.filedata = filedata
        self.room = room
        super().__init__()

rooms = {}

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code
@app.route("/")
def checkup():
    if not session.get("name"):
        return redirect("/sign-up")
    else:
        return redirect("/find-chat")
    

@app.route("/find-chat", methods=["POST", "GET"])
def home():
    if not session.get("name"):
        return redirect("/sign-up")
    if request.method == "POST":
        name = session["name"]
        session["chatname"] = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)
        
        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": [], "members_name": []}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("home.html")

@app.route("/sign-in", methods=["GET", "POST"])
def sign_in():
    if request.method=="GET":
        if session.get("name"):
            return redirect(url_for("home"))
    if request.method=="POST":
        username = request.form.get("name")
        password = request.form.get("password")
        if username=="" or password =="":
            return render_template("sign_in.html", error="Fill each field!")
        else:
            found_user = users.query.filter_by(username=username, password=password).first()
            if found_user:
                session["name"] = found_user.username
                return redirect("/")
            else:
                return render_template("sign_in.html", error="Username or password is incorrect")
    return render_template("sign_in.html")



@app.route("/sign-up", methods=["GET", "POST"])
# def clear_users():
#     try:
#         db.session.query(users).delete()
#         db.session.commit() 
#         return
#     except Exception as e:
#         db.session.rollback()
#         return
#     finally:
#         return redirect("/")
def sign_up():
    if request.method=="GET":
        if session.get("name"):
            return redirect(url_for("home"))
    if request.method=="POST":
        username = request.form.get("name")
        password = request.form.get("password")
        repeated_password = request.form.get("password_repeat")
        if username=="" or password =="":
            return render_template("sign_in.html", error = "Fill each field!")
        elif password != repeated_password:
            return render_template("sign_in.html", error = "Passwords are not equivalent!")
        else:
            found_user = users.query.filter_by(username=username).first()
            usr = users(username, password)
            if found_user:
                return render_template("sign_up.html", error="User allready exists")
            else:
                db.session.add(usr)
                db.session.commit()
                session["name"] = usr.username
                return redirect("/")
    return render_template("sign_up.html")

@app.route("/database/view")
def view():
    return render_template("view.html", values = users.query.all())
@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))

    return render_template("room.html", code=room, messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return 
    
    content = {
        "name": session.get("chatname"),
        "message": data["data"],
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('chatname')} said: {data['data']}")

@socketio.on("file")
def handle_file(data):
    room = session.get("room")
    if room not in rooms:
        return
    file_name = data["name"]
    file_data = data["data"]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_content = {
        "name": file_name,
        "data": file_data,
        "timestamp": timestamp
    }
    send(data_content, to=room)
    rooms[room]["messages"].append(data_content)  
    print(f"File '{file_name}' sent to room {room} at {timestamp}")

@socketio.on("audioSMS")
def audioSMS(data):
    room = session.get("room")  
    if room not in rooms:
        return
    file_data = data["data"]  
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_content = {
        "name": session.get('chatname'),
        "data": file_data,
        "timestamp": timestamp,
        "ending": "audio"
    }
    send(data_content, to=room)
    rooms[room]["messages"].append(data_content)  
    print(f"Audio message sent to room {room} at {timestamp}")

@socketio.on("connect")
def connect(auth):
    room = session.get("room")    
    name = session.get("chatname")    
    if not room or not name:      
        return                    
    
    if room not in rooms:         
        leave_room(room)          
        return                    
    
    join_room(room)           
    if session["chatname"] not in rooms[room]["members_name"]:
        rooms[room]["members_name"].append(session["chatname"])
        send({"name": name, "message": "has entered the room", "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, to=room)  
    rooms[room]["members"] += 1   
    print(f"{name} joined room {room}")  


@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("chatname")
    leave_room(room)
    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    print(f"{name} has left the room {room}")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, host='0.0.0.0', port=80)