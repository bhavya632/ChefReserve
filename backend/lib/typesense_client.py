import typesense
import os
from dotenv import load_dotenv

load_dotenv()

client = typesense.Client({
    "nodes": [{
        "host": os.getenv("TYPESENSE_HOST"),
        "port": os.getenv("TYPESENSE_PORT", "443"),
        "protocol": os.getenv("TYPESENSE_PROTOCOL", "https"),
    }],
    "api_key": os.getenv("TYPESENSE_API_KEY"),
    "connection_timeout_seconds": 5,
})

COLLECTION_NAME = "recipes"
