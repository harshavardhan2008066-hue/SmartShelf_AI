# MAJOR PROJECT GENERATIVE AI LAYER - FILE: ai_chef.py
import json
import time
from typing import Callable
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from database_backend import get_connection

# Initialize the Gemini Client
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

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY environment variable")

client = genai.Client(api_key=GOOGLE_API_KEY)


# ==============================================================================
# VISION LAYER SCHEMA STRUCTURE (FOR OBJECT DETECTION)
# ==============================================================================
class GroceryItem(BaseModel):
    name: str = Field(description="The name of the food item or ingredient found.")
    quantity: float = Field(description="Estimated numerical quantity or count.")
    category: str = Field(description="Must be exactly one of: Proteins, Dairy, Vegetables, Fruits, Grains, Other")
    life: int = Field(description="Estimated shelf life remaining in days as a plain integer.")

class InventoryExtraction(BaseModel):
    items: list[GroceryItem]

# ==============================================================================
# ENGINE PIPELINE FUNCTIONS
# ==============================================================================
def _retry_call(callable_fn: Callable, max_attempts: int = 3, initial_delay: float = 2.0):
    last_exception = None
    for attempt in range(1, max_attempts + 1):
        try:
            return callable_fn()
        except Exception as exc:
            last_exception = exc
            wait = initial_delay * (2 ** (attempt - 1))
            print(f"⚠️ Gemini API temporary failure, attempt {attempt}/{max_attempts}: {exc}")
            if attempt == max_attempts:
                raise
            time.sleep(wait)


def analyze_shelf_image(uploaded_file):
    """Passes the raw image asset to Gemini's computer vision core to parse actual items as structured data."""
    if uploaded_file is None:
        return []
        
    try:
        print("\n📸 Processing raw image bytes through Gemini Structured Vision Core...")
        
        # 1. Read the uploaded file stream directly into raw binary bytes
        image_bytes = uploaded_file.getvalue()
        image_mime_type = uploaded_file.type
        
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=image_mime_type)

        # 2. Prompt that forces strict JSON output using the InventoryExtraction schema
        vision_prompt = """
        Analyze the uploaded food image and return only valid JSON matching the schema below.
        Do not include any explanation, markdown, or text outside the JSON object.

        Output schema:
        {
          "items": [
            {
              "name": "string",
              "quantity": 0.0,
              "category": "Proteins|Dairy|Vegetables|Fruits|Grains|Other",
              "life": 0
            }
          ]
        }

        Identify all visible grocery items, estimate their quantity, category, and remaining shelf life days.
        """

        def _call():
            return client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[types.Part.from_text(text=vision_prompt), image_part],
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': InventoryExtraction,
                },
            )

        response = _retry_call(_call)

        data_clean = None
        parsed = getattr(response, 'parsed', None)
        if parsed:
            try:
                if isinstance(parsed, dict):
                    data_clean = parsed
                elif hasattr(parsed, 'dict'):
                    data_clean = parsed.dict()
                else:
                    data_clean = json.loads(str(parsed))
            except Exception:
                data_clean = None

        if data_clean is None:
            # 4. Safe programmatic loading of the resulting clean data array
            # The model may return JSON wrapped in markdown fences; extract the first JSON object/array.
            raw_text = getattr(response, 'text', None) or ""
            if not raw_text and hasattr(response, 'output'):
                raw_text = str(response.output)

            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                # Remove ```json / ``` wrappers
                cleaned = cleaned.strip("`")
                cleaned = cleaned.replace("json", "", 1).strip()
            start_obj = cleaned.find("{")
            start_arr = cleaned.find("[")
            if start_obj == -1 and start_arr == -1:
                raise ValueError(f"Model did not return JSON: {cleaned[:320]}")
            start = start_obj if start_obj != -1 else start_arr
            end_obj = cleaned.rfind("}")
            end_arr = cleaned.rfind("]")
            end = end_obj if end_obj != -1 else end_arr
            json_blob = cleaned[start : end + 1]
            data_clean = json.loads(json_blob)

        parsed_assets = []
        
        for item in data_clean.get("items", []):
            parsed_assets.append({
                "name": item["name"],
                "quantity": float(item["quantity"]),
                "category": item["category"] if item["category"] in ["Proteins", "Dairy", "Vegetables", "Fruits", "Grains", "Other"] else "Other",
                "life": int(item["life"])
            })
            
        print(f"🤖 Successfully parsed {len(parsed_assets)} items natively via JSON mode.")
        return parsed_assets
        
    except Exception as e:
        print(f"❌ Critical AI Vision Analytics Pipeline Failure: {e}")
        return []


def fetch_user_profile_and_ingredients(user_id):
    """Gathers both user dietary constraints and available ingredients from PostgreSQL."""
    conn = get_connection()
    if not conn: 
        return "None", ""
    
    dietary_preference = "None"
    ingredients_list = []
    
    try:
        with conn.cursor() as cur:
            # 1. Fetch user restriction profiles
            cur.execute("SELECT dietary_preference FROM users WHERE user_id = %s;", (user_id,))
            user_row = cur.fetchone()
            if user_row:
                dietary_preference = user_row[0]
            
            # 2. Fetch inventory rows
            query = """
            SELECT i.item_name, i.quantity, (e.estimated_expiry - CURRENT_DATE) as days_remaining
            FROM inventory i
            JOIN expirations e ON i.item_id = e.item_id
            WHERE i.user_id = %s;
            """
            cur.execute(query, (user_id,))
            rows = cur.fetchall()
            for row in rows:
                item_str = f"{row[0]} (Quantity: {row[1]}, Expiring in: {row[2]} days)"
                ingredients_list.append(item_str)
                
        return dietary_preference, ", ".join(ingredients_list)
    except Exception as e:
        print(f"❌ Error compiling user data profile matrix: {e}")
        return "None", ""
    finally:
        conn.close()


def generate_waste_free_recipe(user_id):
    """Queries Gemini to construct a custom recipe honoring strict user profile filters."""
    
    # Extract data parameters directly from our relational warehouse
    preference, available_ingredients = fetch_user_profile_and_ingredients(user_id)
    
    if not available_ingredients:
        return "⚠️ Your kitchen inventory is currently empty! Scan some items first."

    # Construct dynamic constraint tuning instructions
    system_instruction = f"""
    You are an expert zero-waste chef and professional clinical nutritionist.
    Your mission is to generate a delicious recipe based STRICTLY on the ingredients provided by the user.
    
    CRITICAL HEALTH CONSTRAINT:
    The current user has a strict nutritional profiling filter: "{preference}". 
    You must modify your output to completely obey this rule! For example:
    - If the preference is Vegan, you must NEVER include meat, poultry, fish, dairy milk, cream, butter, or eggs. 
    - If the preference is Vegetarian, you must NEVER include meat, poultry, or fish, but dairy or eggs are acceptable if they are in inventory.
    Omitting hazardous items that violate the user's "{preference}" constraint is your highest technical priority.
    
    Follow these formatting rules:
    1. Prioritize using items that have the fewest 'days_remaining' to prevent food waste.
    2. You may use basic pantry staples (like salt, water, olive oil, simple spices) if needed.
    3. Output your response using clean Markdown with clear sections:
       - 🍳 Recipe Title
       - 📊 Nutritional Value Metrics (Estimated Total Calories, Protein, Carbs, Fats)
       - 🛒 Ingredients Utilized
       - 📝 Step-by-Step Cooking Instructions
       - 💡 Smart Eco-Tip
    """

    user_prompt = f"Here is my current kitchen inventory: {available_ingredients}. Generate a customized recipe!"

    try:
        print(f"\n🧠 Data stream routed. Processing profile: {preference}...")

        def _call():
            return client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_prompt,
                config={'system_instruction': system_instruction}
            )

        response = _retry_call(_call)
        return getattr(response, 'text', None) or str(getattr(response, 'parsed', ''))
    except Exception as e:
        return f"❌ AI Engine failed to generate content. Details: {e}"

def estimate_meal_calories(food_description: str) -> float:
    """Uses Gemini to estimate the calories of a described food/meal."""
    if not food_description:
        return 0.0
        
    prompt = f"""
    You are an expert nutritionist. Estimate the total calorie count (in kcal) for the following food description:
    "{food_description}"
    
    Provide ONLY a single numerical float or integer representing the estimated calorie count. Do not write any other text, explanation, or units.
    For example, if it's 500 kcal, output exactly: 500
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        text = getattr(response, 'text', '').strip()
        # Extract the first number found in the response text
        import re
        match = re.search(r"[-+]?\d*\.\d+|\d+", text)
        if match:
            return float(match.group())
        return 300.0  # fallback
    except Exception as e:
        print(f"❌ Error estimating meal calories: {e}")
        return 300.0  # fallback