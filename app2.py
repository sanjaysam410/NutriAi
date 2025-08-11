from dotenv import load_dotenv
import streamlit as st
import os
from PIL import Image
import google.generativeai as genai
from datetime import datetime
import psycopg2
from psycopg2.extras import DictCursor

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# --- PostgreSQL Connection Setup ---
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError as e:
        st.error(f"Error connecting to the database: {e}")
        return None

# --- Session State Initialization ---
if "user_data" not in st.session_state:
    st.session_state.user_data = {
        "logged_in": False,
        "name": "", "username": "", "gender": "", "age": 0, "height_cm": 0,
        "weight_kg": 0, "goal": "", "activity_level": 1.2, "tdee": 0, "user_id": None
    }
if "messages" not in st.session_state:
    st.session_state.messages = []
if "page" not in st.session_state:
    st.session_state.page = "login"

# --- Gemini and Image Functions (No change) ---
def get_gemini_response(image_parts, prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([prompt, image_parts[0]])
    return response.text

def input_image_setup(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        image_parts = [{"mime_type": uploaded_file.type, "data": bytes_data}]
        return image_parts
    else:
        raise FileNotFoundError("No image uploaded.")

st.set_page_config(page_title="NutriAi", page_icon="🥘", layout="wide")
st.markdown("<h1 style='text-align: center;'>🥘 NutriAi - AI Meal Analyzer</h1>", unsafe_allow_html=True)

# --- LOGIN/SIGNUP PAGE LOGIC ---
def login_page():
    st.title("NutriAi Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username and password:
            conn = get_db_connection()
            if conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
                    user = cur.fetchone()
                
                if user:
                    # (MODIFIED) - Load user data and chat history
                    st.session_state.user_data.update({
                        "logged_in": True, "username": user["username"], "name": user["name"], "age": user["age"],
                        "gender": user["gender"], "height_cm": float(user["height_cm"]),
                        "weight_kg": float(user["weight_kg"]), "goal": user["goal"],
                        "activity_level": float(user["activity_level"]), "tdee": float(user["tdee"]), "user_id": user["id"]
                    })
                    
                    # (NEW) - Load chat history from the database
                    with conn.cursor(cursor_factory=DictCursor) as cur:
                        cur.execute("SELECT * FROM chat_history WHERE user_id = %s ORDER BY timestamp ASC", (user["id"],))
                        history = cur.fetchall()
                        st.session_state.messages = [dict(row) for row in history]
                    
                    conn.close()
                    st.success("Login successful!")
                    st.session_state.page = "main"
                    st.rerun()
                else:
                    conn.close()
                    st.error("Invalid username or password.")
        else:
            st.warning("Please enter both username and password.")
    if st.button("Go to Signup"):
        st.session_state.page = "signup"
        st.rerun()

# --- (signup_page function remains the same) ---
def signup_page():
    st.title("NutriAi Signup")
    name = st.text_input("Name")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    age = st.number_input("Age", min_value=1, max_value=120, value=25)
    gender = st.selectbox("Gender", ["Male", "Female"])
    height = st.number_input("Height (in cm)", min_value=50, max_value=250, value=170)
    weight = st.number_input("Weight (in kg)", min_value=20, max_value=300, value=70)
    goal = st.selectbox("Health Goal", ["Lose Weight", "Maintain Weight", "Gain Muscle"])
    activity = st.selectbox("Activity Level", ["Sedentary (little or no exercise)", "Lightly Active (light exercise/sports 1-3 days/week)", "Moderately Active (moderate exercise/sports 3-5 days/week)", "Very Active (hard exercise/sports 6-7 days/week)", "Super Active (very hard exercise/sports & physical job)"])
    if st.button("Signup"):
        if name and username and password and age and height and weight:
            activity_map = {"Sedentary (little or no exercise)": 1.2, "Lightly Active (light exercise/sports 1-3 days/week)": 1.375, "Moderately Active (moderate exercise/sports 3-5 days/week)": 1.55, "Very Active (hard exercise/sports 6-7 days/week)": 1.725, "Super Active (very hard exercise/sports & physical job)": 1.9}
            if gender == "Male": bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
            else: bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
            tdee = bmr * activity_map[activity]
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO users (name, username, password, age, gender, height_cm, weight_kg, goal, activity_level, tdee) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",(name, username, password, age, gender, height, weight, goal, activity_map[activity], tdee))
                    conn.commit()
                    st.success("Signup successful! Please login.")
                    st.session_state.page = "login"
                    st.rerun()
                except psycopg2.Error as e: st.error(f"Signup failed: {e}")
                finally: conn.close()
        else: st.warning("Please fill in all details.")
    if st.button("Go to Login"):
        st.session_state.page = "login"
        st.rerun()

# --- PAGE ROUTING ---
if st.session_state.page == "login":
    login_page()
elif st.session_state.page == "signup":
    signup_page()
elif st.session_state.user_data["logged_in"]:
    st.sidebar.title(f"Hello, {st.session_state.user_data['name']}!")
    with st.sidebar.expander("Your Health Stats"):
        bmi = st.session_state.user_data["weight_kg"] / ((st.session_state.user_data["height_cm"] / 100)**2)
        st.metric(label="Your BMI", value=f"{bmi:.2f}")
        st.metric(label="Daily Calorie Needs", value=f"{st.session_state.user_data['tdee']:.0f} kcal")
    
    analyze_tab, plan_tab, chat_tab = st.tabs(["📊 Analyze Meal", "📋 Personalized Meal Plan", "🗣️ Ask NutriAi"])

    # --- (analyze_tab and plan_tab remain the same) ---
    with analyze_tab:
        col1, col2 = st.columns([2, 1])
        with col1:
            uploaded_file = st.file_uploader("📤 Upload your delicious meal photo...", type=["jpg", "jpeg", "png"])
            meal_consumed = st.text_input("What meal did you consume? (e.g., Idli, Sambar, Rice, etc.)")
            prep_prompt = st.text_input("Tell us how your meal was prepared (e.g., grilled, fried, steamed) for a more detailed analysis:")
            analyze_clicked = st.button("🍽️ Analyze My Meal")
        with col2:
            if uploaded_file:
                image = Image.open(uploaded_file)
                st.image(image, caption="📸 Uploaded Meal", output_format="JPEG", width=300)
                st.markdown("<style>img {height: 200px !important; object-fit: contain;}</style>", unsafe_allow_html=True)
        user_name = st.session_state.user_data["name"]
        user_goal = st.session_state.user_data["goal"]
        user_tdee = st.session_state.user_data["tdee"]
        base_prompt = f"User Profile:\nName: {user_name}\nHealth Goal: {user_goal}\nEstimated Daily Calorie Needs: {user_tdee:.0f} kcal\n\nYou are an expert nutritionist..."
        input_prompt = base_prompt + ("\nMeal Preparation Details: " + prep_prompt if prep_prompt else "")
        if uploaded_file and analyze_clicked:
            with st.spinner("🔍 Analyzing your meal..."):
                try:
                    image_data = input_image_setup(uploaded_file)
                    response = get_gemini_response(image_data, input_prompt)
                    st.subheader("🧠 Nutritional Analysis:")
                    st.write(response)
                    import re
                    calories_match = re.search(r"total caloric intake from this meal is ([\d]+) calories", response, re.IGNORECASE)
                    calories = calories_match.group(1) if calories_match else "N/A"
                    conn = get_db_connection()
                    if conn:
                        with conn.cursor() as cur:
                            image_bytes = uploaded_file.getvalue()
                            cur.execute("INSERT INTO meal_history (user_id, timestamp, image_data, summary, meal_consumed, calories) VALUES (%s, %s, %s, %s, %s, %s)",(st.session_state.user_data['user_id'], datetime.now(), psycopg2.Binary(image_bytes), response, meal_consumed, calories))
                        conn.commit()
                        conn.close()
                except Exception as e: st.error(f"An error occurred during analysis: {e}")
    with plan_tab:
        st.subheader("🍽️ Generate a Personalized Meal Plan")
        diet_preferences = st.text_input(f"Hello {st.session_state.user_data['name']}, enter your food preferences...")
        if st.button("Generate Meal Plan"):
            with st.spinner("Creating your personalized meal plan..."):
                try:
                    meal_plan_prompt = f"Generate a detailed 7-day personalized meal plan..."
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    meal_plan_response = model.generate_content(meal_plan_prompt)
                    st.subheader("Your 7-Day Personalized Meal Plan:")
                    st.write(meal_plan_response.text)
                    conn = get_db_connection()
                    if conn:
                        with conn.cursor() as cur:
                            cur.execute("INSERT INTO diet_plans (user_id, plan, timestamp) VALUES (%s, %s, %s)", (st.session_state.user_data['user_id'], meal_plan_response.text, datetime.now()))
                        conn.commit()
                        conn.close()
                    st.download_button(label="Download Meal Plan 📄", data=meal_plan_response.text, file_name="personalized_meal_plan.txt", mime="text/plain")
                except Exception as e: st.error(f"An error occurred while generating the meal plan: {e}")
        if st.button("View Last Generated Meal Plan"):
            conn = get_db_connection()
            if conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT plan FROM diet_plans WHERE user_id = %s ORDER BY timestamp DESC LIMIT 1",(st.session_state.user_data['user_id'],))
                    result = cur.fetchone()
                conn.close()
                if result:
                    st.subheader("Last Generated Meal Plan:")
                    st.write(result['plan'])
                else: st.info("No meal plan found. Generate one to see it here.")
    
    # --- CHAT TAB (MODIFIED) ---
    with chat_tab:
        st.subheader("🗣️ Ask NutriAi")

        # (NEW) - Process delete requests first
        for message in st.session_state.messages:
            if message['role'] == 'user':
                # Generate a unique key for each delete button
                button_key = f"delete_{message['id']}"
                if st.session_state.get(button_key, False):
                    conn = get_db_connection()
                    if conn:
                        with conn.cursor() as cur:
                            # User can only delete their own messages
                            cur.execute("DELETE FROM chat_history WHERE id = %s AND user_id = %s", (message['id'], st.session_state.user_data['user_id']))
                        conn.commit()
                        conn.close()
                        # Refresh the page to reflect the deletion
                        st.rerun()

        # Display chat messages from history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                # Use columns to place delete button next to user messages
                if message["role"] == 'user':
                    col1, col2 = st.columns([10, 1])
                    with col1:
                        st.markdown(message["content"])
                    with col2:
                        # Add a delete button with a unique key
                        st.button("🗑️", key=f"delete_{message['id']}", help="Delete this query")
                else:
                    st.markdown(message["content"])

        # Accept user input
        if prompt := st.chat_input("What would you like to know about nutrition?"):
            # Add user message to state and DB
            st.session_state.messages.append({"role": "user", "content": prompt})
            conn = get_db_connection()
            if conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("INSERT INTO chat_history (user_id, role, content) VALUES (%s, %s, %s) RETURNING id",
                                (st.session_state.user_data['user_id'], 'user', prompt))
                    user_message_id = cur.fetchone()['id']
                conn.commit()
            
                # Prepare prompt and get assistant response
                user_info = st.session_state.user_data
                context_prompt = f"User Profile:\nName: {user_info['name']}...\nQuestion: {prompt}"
                model = genai.GenerativeModel('gemini-1.5-flash')
                response_obj = model.generate_content(context_prompt)
                assistant_response = response_obj.text

                # Add assistant response to state and DB
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO chat_history (user_id, role, content) VALUES (%s, %s, %s)",
                                (st.session_state.user_data['user_id'], 'assistant', assistant_response))
                conn.commit()
                conn.close()
                # Rerun to display new messages and delete buttons
                st.rerun()
