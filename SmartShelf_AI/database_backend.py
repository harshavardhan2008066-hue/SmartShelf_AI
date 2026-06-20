import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

# Local PostgreSQL Connection Configuration
import os
from pathlib import Path


def _load_dotenv_fallback():
    dotenv_path = Path(__file__).resolve().parent / ".env"
    if not dotenv_path.exists():
        return

    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path)
    except ImportError:
        with dotenv_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value


_load_dotenv_fallback()

DB_CONFIG = {
    "dbname": "smartshelf_db",
    "user": "postgres",
    "password": os.getenv("DATABASE_PASSWORD"),
    "host": "localhost",
    "port": "5432",
}

# Allow import without env vars; fail only when a DB connection is actually requested.
# This prevents Streamlit from crashing at import-time.




_schema_verified = False

def verify_or_initialize_schema(conn):
    """Checks if the required tables exist, and if not, runs smartshelf_setup.sql."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'users'
                );
            """)
            exists = cur.fetchone()[0]
            if not exists:
                print("⚠️ Database tables not found. Initializing schema...")
                sql_path = Path(__file__).resolve().parent / "smartshelf_setup.sql"
                if sql_path.exists():
                    with sql_path.open("r", encoding="utf-8") as f:
                        sql_content = f.read()
                    cur.execute(sql_content)
                    conn.commit()
                    print("✅ Schema initialized successfully!")
                else:
                    print("❌ Error: smartshelf_setup.sql not found!")
            else:
                # Ensure the meal_logs table exists if other tables already exist
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS meal_logs (
                        log_id SERIAL PRIMARY KEY,
                        user_id INT NOT NULL,
                        logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        calories DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                        food_item TEXT NOT NULL DEFAULT '',
                        CONSTRAINT fk_meal_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    );
                """)
                conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during schema verification/initialization: {e}")

def get_connection():
    """Establishes and returns a secure pipeline connection to PostgreSQL."""
    global _schema_verified
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        if conn and not _schema_verified:
            _schema_verified = True
            verify_or_initialize_schema(conn)
        return conn
    except Exception as e:
        print(f"❌ DATABASE CONNECTION ERROR: {e}")
        return None

def initialize_dummy_user():
    """Inserts a default profile user to test relational key links."""
    query = """
    INSERT INTO users (name, email, dietary_preference)
    VALUES (%s, %s, %s)
    ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name
    RETURNING user_id;
    """
    conn = get_connection()
    if not conn: return None
    try:
        with conn.cursor() as cur:
            cur.execute(query, ("Harsha Vardhan", "harsha@campus.edu", "High-Protein"))
            user_id = cur.fetchone()[0]
            conn.commit()
            return user_id
    except Exception as e:
        print(f"❌ Error initializing test user: {e}")
        return None
    finally:
        conn.close()

def insert_pantry_item(user_id, item_name, quantity, category, shelf_life_days=7):
    """Saves a tracked food item and schedules its calculated expiration date."""
    query_item = """
    INSERT INTO inventory (user_id, item_name, quantity, category)
    VALUES (%s, %s, %s, %s) RETURNING item_id;
    """
    query_expiry = """
    INSERT INTO expirations (item_id, estimated_expiry)
    VALUES (%s, %s);
    """
    conn = get_connection()
    if not conn: return False
    try:
        with conn.cursor() as cur:
            cur.execute(query_item, (user_id, item_name, quantity, category))
            item_id = cur.fetchone()[0]
            
            expiry_date = (datetime.now() + timedelta(days=shelf_life_days)).date()
            cur.execute(query_expiry, (item_id, expiry_date))
            
            conn.commit()
            print(f"✅ Successfully logged row: {quantity}x {item_name} (Expires: {expiry_date})")
            return True
    except Exception as e:
        conn.rollback()
        print(f"❌ Transaction failed for item {item_name}: {e}")
        return False
    finally:
        conn.close()

def get_active_inventory(user_id):
    """Retrieves current storage items along with computed shelf life metrics from PostgreSQL."""
    query = """
    SELECT i.item_id, i.item_name, i.quantity, i.category, e.estimated_expiry,
           (e.estimated_expiry - CURRENT_DATE) as days_remaining
    FROM inventory i
    JOIN expirations e ON i.item_id = e.item_id
    WHERE i.user_id = %s
    ORDER BY days_remaining ASC;
    """
    conn = get_connection()

    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (user_id,))
            return cur.fetchall()
    except Exception as e:
        print(f"❌ DATABASE FETCH ERROR: Unable to load inventory array. Details: {e}")
        return []
    finally:
        conn.close()

def delete_pantry_item(item_id):
    """Deletes a tracked food item from inventory by ID."""
    conn = get_connection()
    if not conn: return False
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM inventory WHERE item_id = %s;", (item_id,))
            conn.commit()
            print(f"🗑️ Successfully deleted pantry item ID: {item_id}")
            return True
    except Exception as e:
        print(f"❌ Error deleting pantry item {item_id}: {e}")
        return False
    finally:
        conn.close()

# ⬇️ PASTE THE TWO NEW FUNCTIONS RIGHT HERE AT THE VERY BOTTOM ⬇️

def check_login(email):
    """Verifies user credentials by email and returns user data if found."""
    query = "SELECT user_id, name, dietary_preference FROM users WHERE email = %s;"
    conn = get_connection()
    if not conn: return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (email.lower().strip(),))
            return cur.fetchone()  # Returns dict or None
    except Exception as e:
        print(f"❌ Login validation failed: {e}")
        return None
    finally:
        conn.close()

def register_user(name, email, preference):
    """Registers a completely new unique user persona in the database."""
    query = """
    INSERT INTO users (name, email, dietary_preference) 
    VALUES (%s, %s, %s) RETURNING user_id;
    """
    conn = get_connection()
    if not conn: return None
    try:
        with conn.cursor() as cur:
            cur.execute(query, (name.strip(), email.lower().strip(), preference))
            user_id = cur.fetchone()[0]
            conn.commit()
            return user_id
    except psycopg2.errors.UniqueViolation:
        print("❌ Registration failed: Email already exists.")
        return "EXISTS"
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return None
    finally:
        conn.close()
def delete_user_account(user_id):
    """Permanently purges a user profile and cascades down to delete all their inventory rows."""
    query = "DELETE FROM users WHERE user_id = %s;"
    conn = get_connection()
    if not conn: return False
    try:
        with conn.cursor() as cur:
            cur.execute(query, (user_id,))
            conn.commit()
            print(f"🗑️ Account Profile ID {user_id} successfully wiped from server memory grids.")
            return True
    except Exception as e:
        print(f"❌ Critical error during profile deletion sequence: {e}")
        return False
    finally:
        conn.close()

def get_calories_for_today(user_id):
    """Gets the total calorie count logged for today (sum of all meals)."""
    query = """
    SELECT SUM(calories) 
    FROM meal_logs 
    WHERE user_id = %s AND logged_at::date = CURRENT_DATE;
    """
    conn = get_connection()
    if not conn: return 0.0
    try:
        with conn.cursor() as cur:
            cur.execute(query, (user_id,))
            row = cur.fetchone()
            return float(row[0]) if row and row[0] is not None else 0.0
    except Exception as e:
        print(f"❌ Error fetching today's calories: {e}")
        return 0.0
    finally:
        conn.close()

def add_meal_log(user_id, calories, food_item):
    """Logs a single meal entry in the database with current timestamp."""
    query = """
    INSERT INTO meal_logs (user_id, calories, food_item)
    VALUES (%s, %s, %s);
    """
    conn = get_connection()
    if not conn: return False
    try:
        with conn.cursor() as cur:
            cur.execute(query, (user_id, calories, food_item))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        print(f"❌ Error adding meal log: {e}")
        return False
    finally:
        conn.close()

def get_daily_meal_logs(user_id):
    """Retrieves all meal logs for today with their timestamps."""
    query = """
    SELECT log_id, logged_at, calories, food_item
    FROM meal_logs
    WHERE user_id = %s AND logged_at::date = CURRENT_DATE
    ORDER BY logged_at DESC;
    """
    conn = get_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (user_id,))
            return cur.fetchall()
    except Exception as e:
        print(f"❌ Error fetching daily meal logs: {e}")
        return []
    finally:
        conn.close()

def delete_meal_log(log_id):
    """Deletes a specific meal log entry by ID."""
    conn = get_connection()
    if not conn: return False
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM meal_logs WHERE log_id = %s;", (log_id,))
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ Error deleting meal log {log_id}: {e}")
        return False
    finally:
        conn.close()

def get_weekly_calorie_report(user_id):
    """Retrieves daily calorie totals and list of foods eaten for the last 7 days."""
    query = """
    SELECT logged_at::date as log_date, 
           SUM(calories) as calories, 
           STRING_AGG(food_item, ', ') as food_eaten
    FROM meal_logs
    WHERE user_id = %s AND logged_at::date >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY logged_at::date
    ORDER BY log_date DESC;
    """
    conn = get_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (user_id,))
            return cur.fetchall()
    except Exception as e:
        print(f"❌ Error fetching weekly calorie report: {e}")
        return []
    finally:
        conn.close()

def update_pantry_item_details(item_id, quantity, category, shelf_life_days):
    """Updates an ingredient's quantity and category in inventory, and updates its estimated expiry."""
    query_item = """
    UPDATE inventory 
    SET quantity = %s, category = %s, updated_at = CURRENT_TIMESTAMP 
    WHERE item_id = %s;
    """
    query_expiry = "UPDATE expirations SET estimated_expiry = %s WHERE item_id = %s;"
    conn = get_connection()
    if not conn: return False
    try:
        with conn.cursor() as cur:
            cur.execute(query_item, (quantity, category, item_id))
            expiry_date = (datetime.now() + timedelta(days=shelf_life_days)).date()
            cur.execute(query_expiry, (expiry_date, item_id))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        print(f"❌ Error updating pantry item {item_id}: {e}")
        return False
    finally:
        conn.close()

def delete_all_pantry_items(user_id):
    """Deletes all inventory items for a specific user."""
    conn = get_connection()
    if not conn: return False
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM inventory WHERE user_id = %s;", (user_id,))
            conn.commit()
            print(f"🗑️ Successfully cleared all inventory items for user ID: {user_id}")
            return True
    except Exception as e:
        print(f"❌ Error deleting all pantry items for user {user_id}: {e}")
        return False
    finally:
        conn.close()