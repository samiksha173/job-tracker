from app import create_app
from extensions import db

app = create_app()

with app.app_context():
    db.drop_all()       # drops old wrong-schema tables
    db.create_all()     # recreates all tables fresh
    print("✅ All tables created successfully!")
    
    # List created tables
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"Tables created: {tables}")
    
    # Show columns in users table
    cols = [c['name'] for c in inspector.get_columns('users')]
    print(f"Users columns: {cols}")