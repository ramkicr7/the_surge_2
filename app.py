from flask import Flask, render_template
from config import Config
from extensions import db, login_manager
from routes.auth import auth
from routes.dashboard import dashboard
from routes.trade import trade
from models import User

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager.init_app(app)

app.register_blueprint(auth)
app.register_blueprint(dashboard)
app.register_blueprint(trade)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def splash():
    return render_template("splash.html")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)