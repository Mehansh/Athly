from flask import Flask, jsonify, request
from model import run_model
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]
    result = run_model(user_message)
    return jsonify({"reply": result})

if __name__ == "__main__":
    app.run(debug=True)