file_path = "alembic/env.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

new_imports = """from logging.config import fileConfig

import os
import sys
from dotenv import load_dotenv

# Add the root directory to sys.path so we can import src
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
load_dotenv()

from src.models import Base
from src.db.connector import DATABASE_URL
"""

content = content.replace("from logging.config import fileConfig", new_imports)

content = content.replace(
    "target_metadata = None",
    """target_metadata = Base.metadata

# Override the sqlalchemy.url dynamically using our environment variables
config.set_main_option("sqlalchemy.url", DATABASE_URL)
""",
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
