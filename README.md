![dashboard](https://github.com/piyanshi009/ADS_PROJECT/blob/354fd23a30ef68872daf1b6b22c65ccce27975c6/Screenshot%202025-11-11%20152348.png)
![graph](https://github.com/piyanshi009/ADS_PROJECT/blob/329724e1ea98baff84783b9e8b2deed37daff0c8/Screenshot%202025-11-11%20145756.png)
![comapre](https://github.com/piyanshi009/ADS_PROJECT/blob/c04611a51d7fe488d19c15b771a096e75e6d8610/Screenshot%202025-11-11%20145702.png)
![review](https://github.com/piyanshi009/ADS_PROJECT/blob/a623fe62e6813b0500c214bf80974fc22e272d86/Screenshot%202025-11-11%20145602.png)
![login](https://github.com/piyanshi009/ADS_PROJECT/blob/48bf74a44a39821e73733055ab285afb83b336b7/Screenshot%202025-11-11%20145514.png)
A complete web-based sentiment analysis platform for movie reviews using Python, Flask, Selenium, BeautifulSoup, NLTK, and Power BI.

🧾 Project Overview

The Movies Review Scraping and Analysis project aims to analyze audience opinions about movies by collecting real-world reviews from Letterboxd.
The system performs web scraping, text cleaning, and sentiment analysis using NLP techniques.
Finally, it visualizes results in a clean web dashboard and Power BI reports, helping users understand audience mood trends for different films.

This project demonstrates a practical blend of data science, machine learning, and web development — turning unstructured movie reviews into structured, interpretable insights.

💡 Key Features
Feature	Description
🎬 Automated Review Scraping	Scrapes reviews directly from Letterboxd using Selenium and BeautifulSoup
💬 Sentiment Analysis (NLP)	Uses NLTK’s VADER model for polarity detection
📊 Interactive Dashboard	Displays sentiment summary and top reviews
🔐 User Authentication	Secure login/signup system with Flask-Login
🔁 Movie Comparison	Compare sentiment of two movies side-by-side
💾 SQLite Database	Stores user credentials and Power BI link
⚙ Caching System	Reuses fetched data for faster access
☁ Power BI Integration	Displays advanced sentiment visualizations
🖥 Responsive UI	Clean dark-mode dashboard design using Bootstrap
🧠 Objectives

To automatically collect and analyze public movie reviews.

To categorize user sentiment as Positive, Negative, or Neutral.

To provide visual insights into audience opinions using Power BI.

To design an interactive, user-friendly web interface.
+----------------------------+
         |      User Interface        |
         | (Flask Frontend - HTML/CSS)|
         +-------------+--------------+
                       |
                       v
         +-------------+--------------+
         |      Flask Server (app)    |
         |   Handles login, routes,   |
         |   dashboard, and compare   |
         +-------------+--------------+
                       |
                       v
         +-------------+--------------+
         |   Web Scraping Module      |
         | (Selenium + BeautifulSoup) |
         +-------------+--------------+
                       |
                       v
         +-------------+--------------+
         |  NLP Sentiment Analyzer    |
         | (VADER + Custom Lexicon)   |
         +-------------+--------------+
                       |
                       v
         +-------------+--------------+
         |  Data Storage & Export     |
         | (Pandas + CSV + SQLite)    |
         +-------------+--------------+
                       |
                       v
         +-------------+--------------+
         |   Power BI Visualization   |
         +----------------------------+
STEPS OF INSTALLATION....

1️⃣ Clone the Repository
git clone https://github.com/yourusername/movie-review-analysis.git
cd movie-review-analysis
2️⃣ Create Virtual Environment
python -m venv venv
venv\Scripts\activate     # (Windows)
source venv/bin/activate  # (Mac/Linux)
3️⃣ Install Dependencies
pip install -r requirements.txt
4️⃣ Run the Flask App
python server.py
5️⃣ Open in your browser:
http://127.0.0.1:5000/
6️⃣ Login using demo credentials:
Username: demo
Password: demo123
