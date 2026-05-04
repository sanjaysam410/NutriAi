from dotenv import load_dotenv
import streamlit as st
import os
import re
import bcrypt
from PIL import Image
from groq import Groq
from datetime import datetime
import psycopg2
from psycopg2.extras import DictCursor

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "openai/gpt-oss-120b"

DATABASE_URL = os.getenv("DATABASE_URL")


def get_db_connection():
    try:
        return psycopg2.connect(DATABASE_URL)
    except psycopg2.OperationalError as e:
        st.error(f"Error connecting to the database: {e}")
        return None


def hash_password(password):
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password, hashed):
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


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



def get_text_response(prompt, system_prompt=None):
    """Get a text response from Groq."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=4096,
    )
    return response.choices[0].message.content


# --- Page Config ---
st.set_page_config(page_title="NutriAi", page_icon="🥘", layout="wide")
st.markdown("<h1 style='text-align: center;'>🥘 NutriAi - AI Meal Analyzer</h1>", unsafe_allow_html=True)


# --- Login Page ---
def login_page():
    st.title("NutriAi Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username and password:
            conn = get_db_connection()
            if conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                    user = cur.fetchone()
                if user and verify_password(password, user["password"]):
                    st.session_state.user_data.update({
                        "logged_in": True, "username": user["username"], "name": user["name"], "age": user["age"],
                        "gender": user["gender"], "height_cm": float(user["height_cm"]),
                        "weight_kg": float(user["weight_kg"]), "goal": user["goal"],
                        "activity_level": float(user["activity_level"]), "tdee": float(user["tdee"]), "user_id": user["id"]
                    })
                    with conn.cursor(cursor_factory=DictCursor) as cur:
                        cur.execute("SELECT * FROM chat_history WHERE user_id = %s ORDER BY timestamp ASC", (user["id"],))
                        st.session_state.messages = [dict(row) for row in cur.fetchall()]
                    conn.close()
                    st.success("Login successful!")
                    st.session_state.page = "main"
                    st.rerun()
                else:
                    if conn:
                        conn.close()
                    st.error("Invalid username or password.")
        else:
            st.warning("Please enter both username and password.")
    if st.button("Go to Signup"):
        st.session_state.page = "signup"
        st.rerun()


# --- Signup Page ---
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
    activity = st.selectbox("Activity Level", [
        "Sedentary (little or no exercise)",
        "Lightly Active (light exercise/sports 1-3 days/week)",
        "Moderately Active (moderate exercise/sports 3-5 days/week)",
        "Very Active (hard exercise/sports 6-7 days/week)",
        "Super Active (very hard exercise/sports & physical job)"
    ])
    if st.button("Signup"):
        if name and username and password and age and height and weight:
            activity_map = {
                "Sedentary (little or no exercise)": 1.2,
                "Lightly Active (light exercise/sports 1-3 days/week)": 1.375,
                "Moderately Active (moderate exercise/sports 3-5 days/week)": 1.55,
                "Very Active (hard exercise/sports 6-7 days/week)": 1.725,
                "Super Active (very hard exercise/sports & physical job)": 1.9
            }
            if gender == "Male":
                bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
            else:
                bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
            tdee = bmr * activity_map[activity]
            hashed_pw = hash_password(password)
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO users (name, username, password, age, gender, height_cm, weight_kg, goal, activity_level, tdee) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (name, username, hashed_pw, age, gender, height, weight, goal, activity_map[activity], tdee)
                        )
                    conn.commit()
                    st.success("Signup successful! Please login.")
                    st.session_state.page = "login"
                    st.rerun()
                except psycopg2.Error as e:
                    st.error(f"Signup failed: {e}")
                finally:
                    conn.close()
        else:
            st.warning("Please fill in all details.")
    if st.button("Go to Login"):
        st.session_state.page = "login"
        st.rerun()


# --- PAGE ROUTING ---
if st.session_state.page == "login":
    login_page()
elif st.session_state.page == "signup":
    signup_page()
elif st.session_state.user_data["logged_in"]:
    # --- Sidebar with Logout ---
    st.sidebar.title(f"Hello, {st.session_state.user_data['name']}!")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.user_data = {
            "logged_in": False,
            "name": "", "username": "", "gender": "", "age": 0, "height_cm": 0,
            "weight_kg": 0, "goal": "", "activity_level": 1.2, "tdee": 0, "user_id": None
        }
        st.session_state.messages = []
        st.session_state.page = "login"
        st.rerun()
    with st.sidebar.expander("Your Health Stats"):
        bmi = st.session_state.user_data["weight_kg"] / ((st.session_state.user_data["height_cm"] / 100)**2)
        st.metric(label="Your BMI", value=f"{bmi:.2f}")
        st.metric(label="Daily Calorie Needs", value=f"{st.session_state.user_data['tdee']:.0f} kcal")

    analyze_tab, plan_tab, chat_tab = st.tabs(["📊 Analyze Meal", "📋 Personalized Meal Plan", "🗣️ Ask NutriAi"])

    # --- Analyze Meal Tab ---
    with analyze_tab:
        col1, col2 = st.columns([2, 1])
        with col1:
            uploaded_file = st.file_uploader("📤 Upload your meal photo (optional, for your records)...", type=["jpg", "jpeg", "png"])
            meal_consumed = st.text_input("What meal did you consume? (e.g., 2 Idli with Sambar and Coconut Chutney)")
            prep_prompt = st.text_input("How was it prepared? (e.g., steamed, deep fried, grilled)")
            analyze_clicked = st.button("🍽️ Analyze My Meal")
        with col2:
            if uploaded_file:
                image = Image.open(uploaded_file)
                st.image(image, caption="📸 Uploaded Meal", output_format="JPEG", width=300)

        if analyze_clicked:
            if not meal_consumed:
                st.warning("Please describe what you ate so NutriAi can analyze it.")
            else:
                with st.spinner("🔍 Analyzing your meal..."):
                    try:
                        user_name = st.session_state.user_data["name"]
                        user_goal = st.session_state.user_data["goal"]
                        user_tdee = st.session_state.user_data["tdee"]
                        analysis_prompt = (
                            f"User Profile:\nName: {user_name}\nHealth Goal: {user_goal}\n"
                            f"Estimated Daily Calorie Needs: {user_tdee:.0f} kcal\n\n"
                            f"The user consumed: {meal_consumed}\n"
                            + (f"Preparation method: {prep_prompt}\n" if prep_prompt else "")
                            + "\nProvide a detailed nutritional analysis with:\n"
                            "1. Item-wise calorie breakdown (each food item separately)\n"
                            "2. Total caloric intake from this meal\n"
                            "3. Macronutrient percentages (protein, carbs, fat)\n"
                            "4. Vitamins and minerals present\n"
                            "5. Health recommendation based on the user's goal"
                        )
                        response = get_text_response(analysis_prompt, "You are NutriAi, an expert nutritionist AI. Provide accurate, detailed nutritional analysis based on the meal description provided. Always include item-wise calorie breakdown, total calories, macronutrient percentages (protein, carbs, fat), and a health recommendation.")
                        st.subheader("🧠 Nutritional Analysis:")
                        st.write(response)
                        calories_match = re.search(r"(\d{2,4})\s*(?:kcal|calories|cal)", response, re.IGNORECASE)
                        calories = calories_match.group(1) if calories_match else "N/A"
                        conn = get_db_connection()
                        if conn:
                            with conn.cursor() as cur:
                                image_bytes = uploaded_file.getvalue() if uploaded_file else None
                                cur.execute(
                                    "INSERT INTO meal_history (user_id, timestamp, image_data, summary, meal_consumed, calories) VALUES (%s, %s, %s, %s, %s, %s)",
                                    (st.session_state.user_data['user_id'], datetime.now(), psycopg2.Binary(image_bytes) if image_bytes else None, response, meal_consumed, calories)
                                )
                            conn.commit()
                            conn.close()
                    except Exception as e:
                        st.error(f"An error occurred during analysis: {e}")

    # --- Meal Plan Tab ---
    with plan_tab:
        st.subheader("🍽️ Generate a Personalized Meal Plan")
        diet_preferences = st.text_input(f"Hello {st.session_state.user_data['name']}, enter your food preferences (e.g., '3 day south indian vegetarian plan')...")
        if st.button("Generate Meal Plan"):
            with st.spinner("Creating your personalized meal plan..."):
                try:
                    # Auto-extract number of days from user input
                    word_to_num = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "single": 1, "a": 1}
                    day_match = re.search(r"(\d+)\s*days?", diet_preferences, re.IGNORECASE)
                    week_match = re.search(r"(\d+)\s*weeks?", diet_preferences, re.IGNORECASE)
                    word_match = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|single|a)\s*days?\b", diet_preferences, re.IGNORECASE)
                    if day_match:
                        plan_days = int(day_match.group(1))
                    elif week_match:
                        plan_days = int(week_match.group(1)) * 7
                    elif word_match:
                        plan_days = word_to_num.get(word_match.group(1).lower(), 7)
                    else:
                        plan_days = 7  # default

                    plan_days = max(1, min(plan_days, 30))  # clamp between 1-30

                    system_prompt = (
                        "You are NutriAi, a certified nutritionist AI. You ONLY provide advice about nutrition, food, diet, and meal planning. "
                        "If the user asks about anything unrelated to nutrition or food, politely decline and redirect them to nutrition topics. "
                        "Always provide accurate calorie counts, macronutrient breakdowns, and portion sizes. "
                        "Tailor your response to the exact number of days requested — never generate more or fewer days than asked."
                    )
                    day_label = f"{plan_days}-day" if plan_days > 1 else "single-day"
                    meal_plan_prompt = (
                        f"Generate a detailed {day_label} personalized meal plan (exactly {plan_days} day{'s' if plan_days > 1 else ''}, no more, no less) "
                        f"for a person with:\n"
                        f"- Health Goal: {st.session_state.user_data['goal']}\n"
                        f"- Daily Calorie Needs: {st.session_state.user_data['tdee']:.0f} kcal\n"
                        f"- Food Preferences: {diet_preferences}\n\n"
                        f"For each day, include Breakfast, Mid-Morning Snack, Lunch, Evening Snack, and Dinner with:\n"
                        f"- Exact portion sizes\n"
                        f"- Calorie count per meal\n"
                        f"- Macronutrient breakdown (protein, carbs, fat)\n\n"
                        f"End with a consolidated grocery list."
                    )
                    meal_plan_text = get_text_response(meal_plan_prompt, system_prompt)
                    st.subheader(f"Your {day_label.title()} Personalized Meal Plan:")
                    st.write(meal_plan_text)
                    conn = get_db_connection()
                    if conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "INSERT INTO diet_plans (user_id, plan, timestamp) VALUES (%s, %s, %s)",
                                (st.session_state.user_data['user_id'], meal_plan_text, datetime.now())
                            )
                        conn.commit()
                        conn.close()
                    st.download_button(label="Download Meal Plan 📄", data=meal_plan_text, file_name="personalized_meal_plan.txt", mime="text/plain")
                except Exception as e:
                    st.error(f"An error occurred while generating the meal plan: {e}")
        if st.button("View Last Generated Meal Plan"):
            conn = get_db_connection()
            if conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT plan FROM diet_plans WHERE user_id = %s ORDER BY timestamp DESC LIMIT 1", (st.session_state.user_data['user_id'],))
                    result = cur.fetchone()
                conn.close()
                if result:
                    st.subheader("Last Generated Meal Plan:")
                    st.write(result['plan'])
                else:
                    st.info("No meal plan found. Generate one to see it here.")

    # --- Chat Tab ---
    with chat_tab:
        st.subheader("🗣️ Ask NutriAi")

        for message in st.session_state.messages:
            if message['role'] == 'user':
                button_key = f"delete_{message['id']}"
                if st.session_state.get(button_key, False):
                    conn = get_db_connection()
                    if conn:
                        with conn.cursor() as cur:
                            cur.execute("DELETE FROM chat_history WHERE id = %s AND user_id = %s", (message['id'], st.session_state.user_data['user_id']))
                        conn.commit()
                        conn.close()
                        st.rerun()

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message["role"] == 'user':
                    col1, col2 = st.columns([10, 1])
                    with col1:
                        st.markdown(message["content"])
                    with col2:
                        st.button("🗑️", key=f"delete_{message['id']}", help="Delete this query")
                else:
                    st.markdown(message["content"])

        if prompt := st.chat_input("What would you like to know about nutrition?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            conn = get_db_connection()
            if conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(
                        "INSERT INTO chat_history (user_id, role, content) VALUES (%s, %s, %s) RETURNING id",
                        (st.session_state.user_data['user_id'], 'user', prompt)
                    )
                    new_msg_id = cur.fetchone()['id']
                    st.session_state.messages[-1]['id'] = new_msg_id
                conn.commit()

                user_info = st.session_state.user_data
                chat_system_prompt = (
                    "You are NutriAi, an expert nutrition assistant. You ONLY answer questions about nutrition, food, diet, calories, "
                    "meal planning, vitamins, minerals, supplements, and healthy eating. "
                    "If the user asks about anything unrelated to nutrition or food (e.g., coding, math, weather, sports scores, etc.), "
                    "politely decline and say: 'I'm NutriAi — I can only help with nutrition and food-related questions! 🥗'"
                    f"\n\nUser Profile:\n- Name: {user_info['name']}\n- Goal: {user_info['goal']}\n- Daily Calorie Needs: {user_info['tdee']:.0f} kcal"
                )
                assistant_response = get_text_response(prompt, chat_system_prompt)

                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO chat_history (user_id, role, content) VALUES (%s, %s, %s)",
                        (st.session_state.user_data['user_id'], 'assistant', assistant_response)
                    )
                conn.commit()
                conn.close()
                st.rerun()