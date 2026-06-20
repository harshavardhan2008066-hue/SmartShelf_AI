import streamlit as st
from database_backend import (
    check_login, register_user, insert_pantry_item, get_active_inventory, 
    delete_user_account, delete_pantry_item, get_calories_for_today, 
    get_weekly_calorie_report, delete_all_pantry_items,
    update_pantry_item_details, add_meal_log, get_daily_meal_logs, delete_meal_log
)
from ai_chef import generate_waste_free_recipe, analyze_shelf_image, estimate_meal_calories


st.set_page_config(page_title="SmartShelf AI & Gym Tracker", page_icon="🍳", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "consumed_calories" not in st.session_state:
    st.session_state.consumed_calories = 0.0
if "ai_recipe" not in st.session_state:
    st.session_state.ai_recipe = None

# ==============================================================================
# GATEWAY TIER: LOGIN / SIGNUP
# ==============================================================================
if not st.session_state.logged_in:
    st.title("🍳 Welcome to SmartShelf AI")
    st.subheader("Personalized Relational Database & AI-Orchestrated Zero-Waste Kitchen")
    
    auth_mode = st.radio("Choose Access Route", ["Existing User Login", "Create New Account"], horizontal=True)
    st.markdown("---")
    
    if auth_mode == "Existing User Login":
        st.markdown("### 🔑 Secure Account Login")
        login_email = st.text_input("Enter your registered Email Address").strip()
        
        if st.button("Authenticate & Open Shelf", type="primary"):
            if login_email:
                user = check_login(login_email)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_info = user
                    st.success(f"Welcome back, {user['name']}!")
                    st.rerun()
                else:
                    st.error("No account linked to this email.")
            else:
                st.warning("Please input your email address.")
    else:
        st.markdown("### 📝 Register New SmartShelf System Profile")
        new_name = st.text_input("Full Name").strip()
        new_email = st.text_input("Email Address").strip()
        new_pref = st.selectbox("Your Dietary Profiling Constraints", ["None", "Vegetarian", "Vegan", "Keto", "High-Protein"])
        
        if st.button("Deploy Account Profiles", type="primary"):
            if new_name and new_email:
                result = register_user(new_name, new_email, new_pref)
                if result == "EXISTS":
                    st.error("This email is already registered.")
                elif result:
                    st.success("Profile created successfully! Switch to login mode to enter your kitchen.")
            else:
                st.warning("Please fill out both fields.")

# ==============================================================================
# WORKSPACE TIER: USER INSTRUMENTATION & GYM ANALYTICS PANEL
# ==============================================================================
else:
    user = st.session_state.user_info
    
    # Initialize today's calories from DB if not already initialized for this session
    if "calories_initialized" not in st.session_state or st.session_state.calories_initialized != user['user_id']:
        st.session_state.consumed_calories = get_calories_for_today(user['user_id'])
        st.session_state.calories_initialized = user['user_id']
    
    # Header bar layout matrix
    header_left, header_mid, header_right = st.columns([3, 1, 1])
    with header_left:
        st.title(f"🍳 {user['name']}'s SmartShelf Workspace")
        st.caption(f"Dietary Restriction Filter Active: **{user['dietary_preference']}**")
    with header_mid:
        if st.button("Sign Out of Grid", width='stretch'):
            st.session_state.logged_in = False
            st.session_state.user_info = None
            st.session_state.consumed_calories = 0.0
            if "calories_initialized" in st.session_state:
                del st.session_state.calories_initialized
            st.rerun()
    with header_right:
        if st.button("🗑️ Delete Account", width='stretch', type="secondary"):
            with st.spinner("Purging infrastructure record frames..."):
                success = delete_user_account(user['user_id'])
                if success:
                    st.session_state.logged_in = False
                    st.session_state.user_info = None
                    st.session_state.consumed_calories = 0.0
                    if "calories_initialized" in st.session_state:
                        del st.session_state.calories_initialized
                    st.toast("Your account profile has been wiped cleanly.")
                    st.rerun()
            
    st.markdown("---")
    
    # GYM & INTEGRATED NUTRITION CALORIE TRACKER METRIC BAR
    st.header("💪 Gym & Fitness Calorie Instrumentation Matrix")
    gym_col1, gym_col2, gym_col3 = st.columns([1, 1, 2])
    
    with gym_col1:
        calorie_target = st.slider("🎯 Set Daily Calorie Target (kcal)", min_value=1200, max_value=4000, value=2000, step=50)
    
    with gym_col2:
        st.write("Log / Edit Calories:")
        new_cal = st.number_input(
            "Consumed Calories (kcal)", 
            min_value=0.0, 
            value=float(st.session_state.consumed_calories), 
            step=50.0
        )
        if new_cal != st.session_state.consumed_calories:
            diff = new_cal - st.session_state.consumed_calories
            st.session_state.consumed_calories = new_cal
            add_meal_log(user['user_id'], diff, "Manual Adjustment")
            st.rerun()
            
        with st.popover("🍔 Quick Log Outside Meal", use_container_width=True):
            quick_food = st.text_input("What did you eat? (e.g. Pizza slice)").strip()
            manual_cal = st.number_input("Calories (kcal, optional if estimating)", min_value=0, value=0, step=50)
            
            col_log_manual, col_log_auto = st.columns(2)
            with col_log_manual:
                if st.button("Log Manually", use_container_width=True):
                    if quick_food and manual_cal > 0:
                        add_meal_log(user['user_id'], float(manual_cal), quick_food)
                        st.session_state.consumed_calories += manual_cal
                        st.toast(f"Logged {quick_food} ({manual_cal} kcal)!")
                        st.rerun()
            with col_log_auto:
                if st.button("Auto-Estimate & Log", type="primary", use_container_width=True):
                    if quick_food:
                        with st.spinner("AI estimating calories..."):
                            estimated_cal = estimate_meal_calories(quick_food)
                            add_meal_log(user['user_id'], estimated_cal, quick_food)
                            st.session_state.consumed_calories += estimated_cal
                            st.toast(f"AI Estimated & Logged: {quick_food} (~{int(estimated_cal)} kcal)!")
                            st.rerun()
            
    with gym_col3:
        remaining_cal = calorie_target - st.session_state.consumed_calories
        st.metric(
            label="Current Daily Intake Progress Balance", 
            value=f"{st.session_state.consumed_calories} / {calorie_target} kcal",
            delta=f"{remaining_cal} kcal remaining" if remaining_cal >= 0 else f"{abs(remaining_cal)} kcal OVER LIMIT",
            delta_color="normal" if remaining_cal >= 0 else "inverse"
        )
        
    # 🚨 AUDIO ALARM TRIGGER CHANNEL
    if st.session_state.consumed_calories > calorie_target:
        st.error(f"⚠️ **CRITICAL ALARM: OVER-CALORIE ACCUMULATION DETECTED!** You have exceeded your fitness threshold boundary by {abs(remaining_cal)} kcal. Consider balancing with a gym workout!")
        
        # 🔊 INJECTING WEB AUDIO SYNTHESIZER BEEP SOUND EFFECT
        sound_html = """
        <script>
        function playAlarmSound() {
            var context = new (window.AudioContext || window.webkitAudioContext)();
            
            // Generate a solid warning beep tone using oscillators
            var oscillator = context.createOscillator();
            var gainNode = context.createGain();
            
            oscillator.type = 'sawtooth'; // Distinct, clean buzz tone
            oscillator.frequency.value = 523.25; // High C note pitch frequency
            
            gainNode.gain.setValueAtTime(0.3, context.currentTime); // Control volume output comfort
            
            oscillator.connect(gainNode);
            gainNode.connect(context.destination);
            
            // Ring a double pulse beep sequence
            oscillator.start();
            setTimeout(function() { oscillator.stop(); }, 250); // Beep 1 length
            
            setTimeout(function() {
                var osc2 = context.createOscillator();
                var gain2 = context.createGain();
                osc2.type = 'sawtooth';
                osc2.frequency.value = 523.25;
                gain2.gain.setValueAtTime(0.3, context.currentTime);
                osc2.connect(gain2);
                gain2.connect(context.destination);
                osc2.start();
                setTimeout(function() { osc2.stop(); }, 250); // Beep 2 length
            }, 400);
        }
        // Force execution immediately as the block mounts into view
        playAlarmSound();
        </script>
        """
        # Execute the hidden browser macro components seamlessly
        st.components.v1.html(sound_html, height=0, width=0)
        
    # Daily Meal Logs (Today) Section
    st.subheader("🍽️ Today's Detailed Meal Logs")
    daily_meals = get_daily_meal_logs(user['user_id'])
    if daily_meals:
        meals_display = []
        for row in daily_meals:
            time_str = row['logged_at'].strftime("%I:%M %p")
            meals_display.append({
                "Time": time_str,
                "Food/Meal Description": row['food_item'],
                "Calories (kcal)": float(row['calories'])
            })
        st.dataframe(meals_display, use_container_width=True)
        
        with st.expander("🗑️ Delete/Remove Today's Meal Entry"):
            del_options = {
                f"{row['logged_at'].strftime('%I:%M %p')} - {row['food_item']} ({int(row['calories'])} kcal)": row['log_id']
                for row in daily_meals
            }
            selected_del = st.selectbox("Select meal log to delete", list(del_options.keys()))
            if st.button("Delete Meal Log", type="primary", use_container_width=True):
                log_id_to_delete = del_options[selected_del]
                if delete_meal_log(log_id_to_delete):
                    st.session_state.consumed_calories = get_calories_for_today(user['user_id'])
                    st.toast("Deleted meal log entry!")
                    st.rerun()
    else:
        st.info("No meals logged yet today.")

    # Weekly Calorie Report Section
    st.subheader("📊 Weekly Calorie Intake History")
    weekly_report = get_weekly_calorie_report(user['user_id'])
    if weekly_report:
        report_display = [
            {
                "Date": str(row['log_date']), 
                "Consumed Calories (kcal)": float(row['calories']),
                "Food Eaten": row['food_eaten']
            }
            for row in weekly_report
        ]
        st.dataframe(report_display, use_container_width=True)
        
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date", "Consumed Calories (kcal)", "Food Eaten"])
        for row in report_display:
            writer.writerow([row["Date"], row["Consumed Calories (kcal)"], row["Food Eaten"]])
        csv_data = output.getvalue()
        
        st.download_button(
            label="📥 Download Weekly Calorie Report (CSV)",
            data=csv_data,
            file_name=f"calorie_report_{user['name'].replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("No calorie history logged in the last 7 days.")
        
    st.markdown("---")
    
    # Split layout into Inventory vs Recipe Output channels
    left_column, right_column = st.columns([1, 1.2])

    with left_column:
        st.header("📸 Smart Vision Integration")
        uploaded_image = st.file_uploader("Upload Fridge/Shelf Image Asset", type=["jpg", "jpeg", "png"])
        
        if uploaded_image is not None:
            st.image(uploaded_image, caption="Uploaded Shelf Matrix Source", width='stretch')
            
            if st.button("Run Automated AI Vision Extraction", width='stretch', type="secondary"):
                with st.spinner("Processing image properties via Vision Core matrices..."):
                    detected_assets = analyze_shelf_image(uploaded_image)

                    if not detected_assets:
                        st.error("No items were detected in the image. Try a clearer shelf photo with visible food items.")
                    else:
                        inserted = 0
                        for asset in detected_assets:
                            success = insert_pantry_item(
                                user['user_id'],
                                asset['name'],
                                asset['quantity'],
                                asset['category'],
                                asset['life'],
                            )
                            if success:
                                inserted += 1

                        st.success(f"🤖 Vision scan complete! Inserted {inserted} detected item(s) into inventory.")
                        if inserted:
                            st.session_state.ai_recipe = None
                            st.rerun()

        st.markdown("---")
        st.header("🗄️ Database Entry & Storage Records")
        
        with st.form("manual_add_form", clear_on_submit=True):
            m_name = st.text_input("Ingredient Name").strip()
            row_col1, row_col2 = st.columns(2)
            with row_col1:
                m_qty = st.number_input("Quantity Metric Units", min_value=0.1, value=1.0, step=0.5)
                m_cat = st.selectbox("Food Categorization Group", ["Vegetables", "Proteins", "Dairy", "Fruits", "Grains", "Other"])
            with row_col2:
                m_life = st.slider("Expected Shelf Life Boundaries (Days)", min_value=1, max_value=30, value=7)
            
            submit_manual = st.form_submit_button("Log Item into PostgreSQL Engine", width='stretch')
            
            if submit_manual and m_name:
                success = insert_pantry_item(user['user_id'], m_name, m_qty, m_cat, m_life)
                if success:
                    st.session_state.ai_recipe = None
                    st.success(f"Successfully integrated '{m_name}' into database storage!")
                    st.rerun()

        st.subheader("Current Active Fridge Storage Ledger")
        active_items = get_active_inventory(user['user_id'])
        if active_items:
            display_items = [
                {k: v for k, v in item.items() if k != 'item_id'}
                for item in active_items
            ]
            st.dataframe(display_items, width='stretch')
            
            with st.expander("🛠️ Manage Ingredients Ledger"):
                tab_edit, tab_delete, tab_delete_all = st.tabs(["📝 Edit Ingredient", "🗑️ Delete Single", "🚨 Delete All"])
                
                item_options = {
                    f"{item['item_name']} ({item['quantity']} units - {item['category']})": item
                    for item in active_items
                }
                
                with tab_edit:
                    selected_label = st.selectbox("Select ingredient to edit", list(item_options.keys()), key="edit_select")
                    if selected_label:
                        selected_item = item_options[selected_label]
                        
                        new_qty = st.number_input("New Quantity Metric Units", min_value=0.1, value=float(selected_item['quantity']), step=0.5, key="edit_qty")
                        new_cat = st.selectbox("New Food Categorization Group", ["Vegetables", "Proteins", "Dairy", "Fruits", "Grains", "Other"], index=["Vegetables", "Proteins", "Dairy", "Fruits", "Grains", "Other"].index(selected_item['category']) if selected_item['category'] in ["Vegetables", "Proteins", "Dairy", "Fruits", "Grains", "Other"] else 0, key="edit_cat")
                        
                        current_days = max(1, int(selected_item['days_remaining']))
                        new_life = st.slider("New Expected Shelf Life (Days)", min_value=1, max_value=30, value=current_days, key="edit_life")
                        
                        if st.button("Save Changes", type="primary", use_container_width=True):
                            if update_pantry_item_details(selected_item['item_id'], new_qty, new_cat, new_life):
                                st.session_state.ai_recipe = None
                                st.toast("Ingredient updated successfully!")
                                st.rerun()
                                
                with tab_delete:
                    selected_del_label = st.selectbox("Select ingredient to delete", list(item_options.keys()), key="del_select")
                    if selected_del_label:
                        selected_del_item = item_options[selected_del_label]
                        if st.button("Delete Selected Ingredient", type="primary", use_container_width=True):
                            if delete_pantry_item(selected_del_item['item_id']):
                                st.session_state.ai_recipe = None
                                st.toast("Removed selected ingredient!")
                                st.rerun()
                                
                with tab_delete_all:
                    st.warning("⚠️ **WARNING:** This will permanently delete ALL ingredients in your inventory ledger!")
                    if st.button("🗑️ Delete All Ingredients", type="secondary", use_container_width=True):
                        if delete_all_pantry_items(user['user_id']):
                            st.session_state.ai_recipe = None
                            st.toast("Wiped your inventory clean!")
                            st.rerun()
        else:
            st.info("Your storage records matrix is empty. Input items above or run a vision scan mock snapshot.")

    with right_column:
        st.header("🧠 AI Recipe Synthesis Hub")
        st.write(f"Processes your live PostgreSQL rows through Gemini, adhering to your profile: **{user['dietary_preference']}**.")
        
        if st.button("Generate Personalized Waste-Free Recipe", width='stretch', type="primary"):
            with st.spinner("Analyzing inventory deadlines... Formulating meal profiles..."):
                ai_report_output = generate_waste_free_recipe(user['user_id'])
                st.session_state.ai_recipe = ai_report_output
                
                if "frittata" in ai_report_output.lower() or "rice" in ai_report_output.lower():
                    new_val = st.session_state.consumed_calories + 950.0
                    st.session_state.consumed_calories = new_val
                    
                    recipe_title = "AI Recipe"
                    for line in ai_report_output.split('\n'):
                        clean_line = line.strip()
                        if clean_line.startswith("## ") or clean_line.startswith("🍳 ") or clean_line.startswith("# "):
                            recipe_title = clean_line.strip("# 🍳 ")
                            break
                    update_calories_for_today(user['user_id'], new_val, food_item=recipe_title)
                    st.toast("🔥 Logged estimated recipe nutrition counts into your Gym Dashboard tracker panel!")
                    st.rerun()
        
        if st.session_state.ai_recipe:
            st.markdown("### 📋 AI Generation Report Output Matrix")
            st.markdown(st.session_state.ai_recipe)