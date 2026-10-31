"""Cấu hình tập trung - đọc từ .env ở thư mục gốc dự án."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/?retryWrites=true&w=majority&wtimeoutMS=5000")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "social_graph_2026")
DB_NAME = "social"

# Timeout ngắn để phát hiện nút chết nhanh, phục vụ demo chịu lỗi
MONGO_TIMEOUT_MS = 5000
NEO4J_TIMEOUT_S = 5
