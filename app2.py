from dotenv import load_dotenv
import streamlit as st
import os
from PIL import Image
import google.generativeai as genai
import time

# Load environment variables
load_dotenv()
print("GOOGLE_API_KEY:", os.getenv("GOOGLE_API_KEY"))  # Add this line for debugging
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Function to get Gemini Vision API response using the updated model
def get_gemini_response(image_parts, prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([prompt, image_parts[0]])
    return response.text

# Function to process uploaded image
def input_image_setup(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        image_parts = [{
            "mime_type": uploaded_file.type,
            "data": bytes_data
        }]
        return image_parts
    else:
        raise FileNotFoundError("No image uploaded.")

# Set up Streamlit UI
st.set_page_config(page_title="NutriAi", page_icon="🥘", layout="wide")

# Centered Title using HTML
st.markdown("<h1 style='text-align: center;'>🥘 NutriAi - AI Meal Analyzer</h1>", unsafe_allow_html=True)

# Tabs for analysis and meal plan
analyze_tab, plan_tab = st.tabs(["📊 Analyze Meal", "📋 Personalized Meal Plan"])

with analyze_tab:
    col1, col2 = st.columns([2, 1])
    with col1:
        # File uploader
        uploaded_file = st.file_uploader("📤 Upload your delicious meal photo...", type=["jpg", "jpeg", "png"])
        # Additional prompt for food preparation details
        prep_prompt = st.text_input("Tell us how your meal was prepared (e.g., grilled, fried, steamed) for a more detailed analysis:")
        # Analyze Button
        analyze_clicked = st.button("🍽️ Analyze My Meal")

    with col2:
        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="📸 Uploaded Meal", use_column_width=True, output_format="JPEG", width=300)
            st.markdown(
                """
                <style>
                img {
                    height: 200px !important;
                    object-fit: contain;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

    # Base Nutrition prompt
    base_prompt = """
    You are an expert nutritionist. Analyze the food items from the image and calculate total calories.
    Provide the analysis in this format:

    FOOD ITEMS AND CALORIES:
    1. Item 1 - XXX calories
    2. Item 2 - XXX calories
    3. Item 3 - XXX calories

    TOTAL CALORIES:
    Your total caloric intake from this meal is XXX calories.

    NUTRITIONAL ANALYSIS:
    - Carbohydrates: XX%
    - Protein: XX%
    - Fat: XX%

    RECOMMENDATION:
    [Your food is healthy/Your food is not healthy] because [reason].
    Suggested improvements: [suggestions].
    """

    # Append preparation details to the base prompt if provided
    input_prompt = base_prompt + ("\nMeal Preparation Details: " + prep_prompt if prep_prompt else "")

    if uploaded_file and analyze_clicked:
        with st.spinner("🔍 Analyzing your meal..."):
            try:
                start_time = time.time()  # Start timing
                image_data = input_image_setup(uploaded_file)
                response = get_gemini_response(image_data, input_prompt)
                elapsed = time.time() - start_time  # End timing
                st.subheader("🧠 Nutritional Analysis:")
                st.write(response)
                st.info(f"⏱️ Response generated in {elapsed:.2f} seconds.")
            except Exception as e:
                st.error(f"Something went wrong: {e}")

with plan_tab:
    st.subheader("🍽️ Generate a Personalized Meal Plan")
    diet_preferences = st.text_input("Enter your food preferences (e.g., vegetarian, low-carb, gluten-free, etc.):")
    if st.button("Generate Meal Plan"):
        with st.spinner("Creating your personalized meal plan..."):
            try:
                start_time = time.time()  # Start timing
                meal_plan_prompt = f"Generate a detailed 7-day personalized meal plan based on the following preferences: {diet_preferences}. Include recipes, nutritional information, and grocery list."
                model = genai.GenerativeModel('gemini-1.5-flash')
                meal_plan_response = model.generate_content(meal_plan_prompt)
                elapsed = time.time() - start_time  # End timing
                st.subheader("Your 7-Day Personalized Meal Plan:")
                st.write(meal_plan_response.text)
                st.info(f"⏱️ Response generated in {elapsed:.2f} seconds.")

                st.download_button(
                    label="Download Meal Plan 📄",
                    data=meal_plan_response.text,
                    file_name="personalized_meal_plan.txt",
                    mime="text/plain"
                )
            except Exception as e:
                st.error(f"Something went wrong: {e}")

st.markdown("""
    <style>
    :root {
        --x: 50%;
        --y: 50%;
    }
    body, .main {
        min-height: 100vh;
        background: radial-gradient(circle at var(--x, var(--y)), #414345 0%, #232526 100%);
        transition: background 0.5s cubic-bezier(0.4, 0.0, 0.2, 1);
        animation: none !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        background: #33373b;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 18px;
        padding: 10px 20px;
        color: #fff;
    }
    .stButton>button {
        background-color: #4caf50;
        color: white;
        border-radius: 8px;
        font-size: 16px;
        padding: 10px 24px;
        transition: transform 0.2s;
    }
    .stButton>button:hover {
        transform: scale(1.05);
        background-color: #388e3c;
    }
    .stDownloadButton>button {
        background-color: #1976d2;
        color: white;
        border-radius: 8px;
        font-size: 16px;
        padding: 10px 24px;
        transition: transform 0.2s;
    }
    .stDownloadButton>button:hover {
        transform: scale(1.05);
        background-color: #125ea2;
    }
    /* Make text and cards lighter for dark background */
    .stApp, .stMarkdown, .stTextInput, .stSubheader, .stHeader, .stTitle {
        color: #f8fafc !important;
    }
    </style>
    <script>
    document.addEventListener('mousemove', function(e) {
        const x = (e.clientX / window.innerWidth) * 100;
        const y = (e.clientY / window.innerHeight) * 100;
        document.documentElement.style.setProperty('--x', x + '%');
        document.documentElement.style.setProperty('--y', y + '%');
    });
    </script>
""", unsafe_allow_html=True)

st.sidebar.image("https://img.icons8.com/color/96/meal.png", width=80)
st.sidebar.title("NutriAi Menu")
st.sidebar.markdown("Analyze meals and get personalized plans!")
