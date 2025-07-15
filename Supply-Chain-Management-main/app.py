# app.py
from flask import Flask, request, jsonify, send_from_directory
from flask import Flask, request, session, redirect, render_template
import bcrypt
from flask_cors import CORS
from functools import wraps
import mysql.connector
from config import DB_CONFIG
from datetime import datetime
import requests
import os
import json
import logging
from decimal import Decimal
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app)

logging.basicConfig(level=logging.INFO)

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect('/login')
            if role and session.get('role') != role:
                return "Access Denied: Not authorized", 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

if not GROQ_API_KEY:
    logging.error("Groq API key is not set. Please set the GROQ_API_KEY environment variable.")
    exit(1)

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        logging.error(f"Error connecting to the database: {str(err)}")
        return None

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

@app.route('/')
def home():
    return redirect('/login')

app.secret_key = 'this_is_a_very_secure_key_1234!@#$'  # Required for sessions

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form['username']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()
    conn.close()

    if user:
        print("👉 Username entered:", username)
        print("👉 Password entered:", password)
        print("👉 Password from DB:", user['password'])
        match = bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8'))
        print("👉 bcrypt match result:", match)

        if match:
            session['user_id'] = user['id']
            session['role'] = user['role']

            # ✅ Update last_login
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
            conn.commit()
            cursor.close()
            conn.close()

            # 🎯 Redirect by role
            if user['role'] == 'admin':
                return redirect('/admin_dashboard')
            elif user['role'] == 'manager':
                return redirect('/manager_dashboard')
            elif user['role'] == 'customer':
                return redirect('/customer_dashboard')


    return "Invalid username or password"



@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/profile')
@login_required()  # Any logged-in user can view their profile
def profile():
    user_id = session.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT username, role, last_login FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("profile.html", user=user)


@app.route('/manager_dashboard')
@login_required(role='manager')
def manager_dashboard():
    return render_template('manager_dashboard.html', role='manager')

@app.route('/customer_dashboard')
@login_required(role='customer')
def customer_dashboard():
    return render_template('customer_dashboard.html', role='customer')

@app.route('/admin_dashboard')
@login_required(role='admin')
def admin_dashboard():
    return render_template('admin_dashboard.html', role='admin')





@app.route('/update_stock', methods=['POST'])
def update_stock():
    data = request.json
    product_id = data['product_id']
    quantity = data['quantity']
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT quantity FROM stocks WHERE product_id = %s", (product_id,))
        result = cursor.fetchone()
        
        if result:
            new_quantity = result[0] + quantity
            cursor.execute("UPDATE stocks SET quantity = %s WHERE product_id = %s", (new_quantity, product_id))
        else:
            cursor.execute("INSERT INTO stocks (product_id, quantity) VALUES (%s, %s)", (product_id, quantity))
        
        conn.commit()
        return jsonify({"message": "Stock updated successfully"})
    except mysql.connector.Error as err:
        logging.error(f"Error updating stock: {str(err)}")
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/update_sales', methods=['POST'])
def update_sales():
    data = request.json
    product_id = data['product_id']
    quantity = data['quantity']
    date = datetime.now().strftime("%Y-%m-%d")
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO sales (product_id, quantity, date) VALUES (%s, %s, %s)", (product_id, quantity, date))
        cursor.execute("UPDATE stocks SET quantity = quantity - %s WHERE product_id = %s", (quantity, product_id))
        conn.commit()
        return jsonify({"message": "Sales data updated and stock reduced successfully"})
    except mysql.connector.Error as err:
        conn.rollback()
        logging.error(f"Error updating sales: {str(err)}")
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/analyze_inventory', methods=['GET'])
def analyze_inventory():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch inventory data
        cursor.execute("""
            SELECT s.product_id, s.quantity AS current_stock,
                   COALESCE(SUM(sa.quantity), 0) AS total_sales,
                   MAX(sa.date) AS last_sale_date
            FROM stocks s
            LEFT JOIN sales sa ON s.product_id = sa.product_id
            GROUP BY s.product_id, s.quantity
        """)
        inventory_data = cursor.fetchall()

        # Prepare chart data
        stock_data = {
            "labels": [item['product_id'] for item in inventory_data],
            "data": [item['current_stock'] for item in inventory_data]
        }

        # Sales trend per date
        cursor.execute("""
            SELECT date, SUM(quantity) as total_quantity
            FROM sales
            GROUP BY date
            ORDER BY date
        """)
        sales_raw = cursor.fetchall()
        sales_data = {
            "labels": [item['date'].strftime('%Y-%m-%d') for item in sales_raw],
            "data": [item['total_quantity'] for item in sales_raw]
        }

        # Get AI analysis from Groq
        for item in inventory_data:
            item['current_stock'] = float(item['current_stock'])
            item['total_sales'] = float(item['total_sales'])
            if item['last_sale_date']:
                item['last_sale_date'] = item['last_sale_date'].strftime('%Y-%m-%d')

        analysis = get_groq_inventory_analysis(inventory_data)

        return jsonify({
            "analysis": analysis['analysis'],
            "stock_data": stock_data,
            "sales_data": sales_data
        })

    except Exception as e:
        logging.error("❌ Error analyzing inventory: %s", e)
        return jsonify({"error": "An error occurred"}), 500
    finally:
        cursor.close()
        conn.close()



def get_groq_inventory_analysis(inventory_data):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Analyze the following inventory data and provide insights and recommendations:
    {json.dumps(inventory_data, indent=2, cls=DecimalEncoder)}
    
    Consider the following aspects:
    1. Current stock levels
    2. Total sales
    3. Last sale date
    4. Potential overstocking or understocking
    5. Sales trends
    6. Recommendations for inventory management
    7. Strategies to boost sales for slow-moving items
    8. Overall business improvement suggestions
    
    Provide a concise analysis and actionable recommendations in markdown format.
    """
    
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "You are an AI assistant specialized in inventory management and business analysis. Provide concise responses in markdown format."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        analysis = response.json()['choices'][0]['message']['content']
        return {"analysis": analysis}
    except requests.exceptions.RequestException as e:
        logging.error(f"Error communicating with Groq AI: {str(e)}")
        return {"error": "Failed to generate inventory analysis"}
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding Groq AI response: {str(e)}")
        return {"error": "Error decoding Groq AI response"}
    except KeyError as e:
        logging.error(f"Unexpected response format from Groq AI: {str(e)}")
        return {"error": "Unexpected response format from Groq AI"}

@app.route('/get_inventory_data', methods=['GET'])
def get_inventory_data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT product_id, quantity FROM stocks")
        stock_data = cursor.fetchall()

        cursor.execute("""
            SELECT date, SUM(quantity) as total_sales
            FROM sales
            GROUP BY date
            ORDER BY date
        """)
        sales_data = cursor.fetchall()

        conn.close()

        return jsonify({
            "stocks": stock_data,
            "sales": sales_data
        })

    except Exception as e:
        logging.error(f"Error fetching inventory chart data: {str(e)}")
        return jsonify({"error": "Failed to load chart data"}), 500

@app.route('/transport_route', methods=['POST'])
def transport_route():
    data = request.json
    start_point = data['start']
    destination = data['destination']
    important_points = data.get('important_points', [])
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Given the starting point '{start_point}' and destination '{destination}', 
    suggest an optimized transportation route passing through important locations: {important_points}. 
    Explain the choice of this route in terms of efficiency, safety, and cost-effectiveness.
    Provide a concise analysis and actionable recommendations in markdown format.
    """
    
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "You are an AI assistant specialized in transportation management. Provide optimized routes with justifications.Provide concise responses in markdown format."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        route_info = response.json()['choices'][0]['message']['content']
        return jsonify({"route": route_info})
    except requests.exceptions.RequestException as e:
        print("❌ Error talking to Groq API:", e)
        logging.error(f"Error communicating with Groq AI: {str(e)}")
        return jsonify({"error": "Failed to get transport route"}), 500

@app.route('/active_sessions')
@login_required(role='admin')
def active_sessions():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT username, role FROM users WHERE role IN ('manager', 'customer')")
        users = cursor.fetchall()
        sessions = []
        for user in users:
            sessions.append({
                "username": user['username'],
                "role": user['role'],
                "status": "Logged In (simulated)"  # You can replace with real session status
            })
        return jsonify({"sessions": sessions})
    except Exception as e:
        logging.error(f"Error in active_sessions: {str(e)}")
        return jsonify({"error": "Failed to load active sessions"}), 500

@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.json
    user_message = data['message']
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", 
             "content": "You are a concise assistant focused on supply chain, sales, inventory. "
             "Answer questions clearly in **2–4 lines max**, using markdown formatting."
             "Avoid long explanations. Go straight to the point with short tips or steps."},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 300,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        ai_response = response.json()['choices'][0]['message']['content']
        return jsonify({"response": ai_response})
    except requests.exceptions.RequestException as e:
        error_message = f"Error communicating with Groq AI: {str(e)}"
        logging.error(error_message)
        return jsonify({"error": error_message}), 500
    except json.JSONDecodeError as e:
        error_message = f"Error decoding Groq AI response: {str(e)}"
        logging.error(error_message)
        return jsonify({"error": error_message}), 500
    except KeyError as e:
        error_message = f"Unexpected response format from Groq AI: {str(e)}"
        logging.error(error_message)
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    app.run(debug=True)