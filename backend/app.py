from flask import Flask
from flask_cors import CORS
from routes.search import search_bp
from routes.rerank import rerank_bp
from routes.scraper import scraper_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(search_bp, url_prefix="/api")
app.register_blueprint(rerank_bp, url_prefix="/api")
app.register_blueprint(scraper_bp, url_prefix="/api")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
