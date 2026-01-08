from flask import Flask
from handlers import get_users, get_user_followers

app = Flask(__name__)

@app.route('/api/users', methods=['GET'])
def users():
    # In real app, parse request
    # But since in-process, not used
    pass

@app.route('/api/users/<int:user_id>/followers', methods=['GET'])
def followers(user_id):
    pass

if __name__ == '__main__':
    app.run()