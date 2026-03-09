from flask import Flask, jsonify, request
from model import run_model
from flask_cors import CORS
from vectordb import retrieveEvents
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route("/chat", methods=["POST"])

def chat():
    user_message = request.json["message"]

    ai_result = run_model(user_message)

    similar_events = retrieveEvents(user_message, k=5)

    events = []
    for doc in similar_events:
        events.append({
            "title": doc.metadata.get("title"),
            "location": doc.metadata.get("location"),
            "date": doc.metadata.get("date"),
            "distance": doc.metadata.get("distance"),
            "url": doc.metadata.get("url"),
            "type": doc.metadata.get("type")
        })

    return jsonify({
        "reply": ai_result,
        "events": events
    })

if __name__ == "__main__":
    app.run(debug=True)