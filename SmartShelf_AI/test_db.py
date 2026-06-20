import sys
from database_backend import (
    initialize_dummy_user, insert_pantry_item, get_connection,
    add_meal_log, get_calories_for_today, get_daily_meal_logs
)
from ai_chef import generate_waste_free_recipe, estimate_meal_calories

# Ensure output encoding is robust on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

print("[*] Starting SmartShelf AI Full-Pipeline Test...")

# 1. Connect to our existing test profile user (Harsha Vardhan)
uid = initialize_dummy_user()

if not uid:
    print("[-] Setup stopped. Check your database connection parameters.")
    raise SystemExit(1)

print(f"[+] Test Profile Loaded. User ID: {uid}")

# Clean any existing inventory for test user to start fresh
conn = get_connection()
if conn:
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM inventory WHERE user_id = %s;", (uid,))
        conn.commit()
    except Exception as e:
        print(f"[-] Warning: could not clear test inventory: {e}")
    finally:
        conn.close()

# Insert dummy pantry items for recipe generation testing
print("[*] Inserting mock ingredients for testing...")
insert_pantry_item(uid, "Rice", 2.0, "Grains", 30)
insert_pantry_item(uid, "Eggs", 6.0, "Proteins", 7)
insert_pantry_item(uid, "Spinach", 1.0, "Vegetables", 3)

# 2. Basic smoke test: ensure recipe generation returns a non-empty string
print("[*] Calling Gemini AI Chef API for recipe generation...")
recipe_output = generate_waste_free_recipe(uid)
assert isinstance(recipe_output, str) and recipe_output.strip(), "Recipe output should be a non-empty string"

# Verify it generated a real recipe rather than the empty kitchen warning
assert "Your kitchen inventory is currently empty" not in recipe_output, "Recipe test failed: Inventory was reported as empty"

print("\n=================== AI GENERATED CHEF REPORT ===================")
print(recipe_output)
print("================================================================")
print("\n[+] PIPELINE SUCCESSFUL: Relational Data successfully orchestrated into AI output!")

# 3. Calorie Persistence and AI Estimation Smoke Tests
print("\n[*] Starting Calorie Persistence and AI Estimation Smoke Tests...")

# Clean any existing meal logs for today
conn = get_connection()
if conn:
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM meal_logs WHERE user_id = %s;", (uid,))
        conn.commit()
    except Exception as e:
        print(f"[-] Warning: could not clear test meal logs: {e}")
    finally:
        conn.close()

# Test AI Calorie Estimation
print("[*] Testing AI calorie estimation for 'two slices of cheese pizza'...")
estimated_cal = estimate_meal_calories("two slices of cheese pizza")
print(f"[+] AI Estimated: ~{estimated_cal} kcal")
assert estimated_cal > 0, "AI calorie estimation failed"

# Test Meal Log Addition
print("[*] Logging meal...")
add_meal_log(uid, estimated_cal, "Two Slices of Cheese Pizza")
today_cal = get_calories_for_today(uid)
print(f"[+] Today's total logged calories: {today_cal} kcal")
assert abs(today_cal - estimated_cal) < 0.1, "Calorie total mismatch"

# Test Daily Logs fetching
daily_logs = get_daily_meal_logs(uid)
print(f"[+] Today's logs: {daily_logs}")
assert len(daily_logs) == 1, "Log count mismatch"
assert daily_logs[0]['food_item'] == "Two Slices of Cheese Pizza", "Log food item mismatch"

print("\n[+] CALORIE PIPELINE SUCCESSFUL: Persistent daily logs with time and AI calorie estimation verified!")

# 4. Vision smoke test intentionally skipped here because it requires an actual uploaded file object.
print("[i] Vision test skipped (requires uploaded file object).")
