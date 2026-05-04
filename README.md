# 🥘 NutriAi - AI Meal Analyzer

An AI-powered nutrition assistant built with Streamlit that analyzes meal photos, generates personalized meal plans, and answers nutrition questions using Groq's LLM APIs.

## Features

- **📊 Meal Analysis** — Upload a photo of your meal and get an AI-powered nutritional breakdown (calories, macros, health recommendations)
- **📋 Personalized Meal Plans** — Generate 7-day meal plans tailored to your health goals, calorie needs, and food preferences
- **🗣️ Ask NutriAi** — Chat with an AI nutrition assistant that knows your health profile
- **👤 User Accounts** — Signup/login with health stats (BMI, TDEE auto-calculated)
- **💾 History** — All analyses, meal plans, and chat conversations are saved to your account

## Tech Stack

- **Frontend:** Streamlit
- **AI Backend:** Groq API (LLaMA 4 Scout for vision, GPT-OSS-120B for text)
- **Database:** PostgreSQL
- **Auth:** bcrypt password hashing

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up PostgreSQL

Make sure PostgreSQL is running locally. Create a database called `nutridb`:

```sql
CREATE DATABASE nutridb;
```

Then create the required tables:

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR, username VARCHAR UNIQUE, password VARCHAR,
    age INTEGER, gender VARCHAR, height_cm NUMERIC, weight_kg NUMERIC,
    goal VARCHAR, activity_level NUMERIC, tdee NUMERIC
);

CREATE TABLE meal_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    timestamp TIMESTAMP, image_data BYTEA, summary TEXT,
    meal_consumed VARCHAR, calories VARCHAR
);

CREATE TABLE diet_plans (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    plan TEXT, timestamp TIMESTAMP
);

CREATE TABLE chat_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    role VARCHAR, content TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3. Configure environment variables

Create a `.env` file:

```
DATABASE_URL="postgresql://postgres:yourpassword@localhost:5432/nutridb"
GROQ_API_KEY=your_groq_api_key_here
```

Get a Groq API key at [console.groq.com/keys](https://console.groq.com/keys).

### 4. Run the app

```bash
streamlit run app2.py
```

The app will be available at `http://localhost:8501`.