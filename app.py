import streamlit as st
import cv2
import numpy as np
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import av
from PIL import Image
import pandas as pd
import datetime
import time
import hashlib
import pickle
import mysql.connector
import os

# Page config
st.set_page_config(page_title="TCGC Attendance System", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

# Enhanced CSS with better user-friendly design
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.08);
        text-align: center;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 15px rgba(0,0,0,0.12);
    }
    .metric-value {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-label {
        font-size: 1.1rem;
        color: #666;
        margin-top: 0.5rem;
        font-weight: 500;
    }
    .event-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin: 1rem 0;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }
    .student-card {
        background: linear-gradient(to right, #f8f9fa 0%, #e9ecef 100%);
        padding: 1.2rem;
        border-radius: 12px;
        margin: 0.7rem 0;
        border-left: 5px solid #667eea;
        color: #333;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        transition: all 0.2s;
    }
    .student-card:hover {
        transform: translateX(5px);
        box-shadow: 0 3px 8px rgba(0,0,0,0.1);
    }
    .success-box {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border: 2px solid #28a745;
        color: #155724;
        padding: 1.2rem;
        border-radius: 12px;
        margin: 1rem 0;
        font-weight: 500;
    }
    .warning-box {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        border: 2px solid #ffc107;
        color: #856404;
        padding: 1.2rem;
        border-radius: 12px;
        margin: 1rem 0;
        font-weight: 500;
    }
    .info-box {
        background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
        border: 2px solid #17a2b8;
        color: #0c5460;
        padding: 1.2rem;
        border-radius: 12px;
        margin: 1rem 0;
        font-weight: 500;
    }
    .section-header {
        color: #667eea;
        font-size: 1.8rem;
        margin-bottom: 1.5rem;
        font-weight: bold;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #667eea;
    }
    .event-list-item {
        background: white;
        color: #333;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 0.7rem 0;
        border: 2px solid #e9ecef;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        transition: all 0.2s;
    }
    .event-list-item:hover {
        border-color: #667eea;
        box-shadow: 0 4px 10px rgba(102,126,234,0.2);
    }
    .attendance-record {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        color: #333;
        border-left: 4px solid #28a745;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .time-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0.2rem;
    }
    .time-in-badge {
        background: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    .time-out-badge {
        background: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
    }
    .count-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.4rem 0.9rem;
        border-radius: 25px;
        font-size: 0.9rem;
        font-weight: bold;
        margin-left: 0.5rem;
        display: inline-block;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)

# Database connection
def get_db_connection():
    try:
        if st.secrets.get("database", {}).get("host"):
            return mysql.connector.connect(
                host=st.secrets["database"]["host"],
                user=st.secrets["database"]["user"],
                password=st.secrets["database"]["password"],
                database=st.secrets["database"]["name"],
                port=st.secrets["database"].get("port", 3306)
            )
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "attendance_system"),
            port=int(os.getenv("DB_PORT", 3306))
        )
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        return None

# Initialize session state
def initialize_session_state():
    defaults = {
        "logged_in": False,
        "username": "",
        "students": {},
        "current_event": "",
        "webcam_key": 0,
        "attendance_webcam_key": 0,
        "attendance_session": [],
        "current_page": 1
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if "students" in st.session_state and not st.session_state.students:
        st.session_state.students = load_students()

# Login
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    return {"admin": hash_password("admin123")}.get(username) == hash_password(password)

def login_page():
    st.markdown('<div class="main-header"><h1>🎓 TCGC Event Attendance System</h1><p style="font-size: 1.2rem; margin-top: 1rem;">Intelligent Face Recognition Attendance Solution</p></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 Admin Login")
        with st.form("login_form"):
            username = st.text_input("👤 Username", placeholder="Enter username")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter password")
            if st.form_submit_button("🚀 Login", use_container_width=True):
                if check_login(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("✅ Login successful!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials!")
        st.markdown('<div class="info-box">💡 <strong>Default Login:</strong><br>Username: <code>admin</code><br>Password: <code>admin123</code></div>', unsafe_allow_html=True)

# Face detection
@st.cache_resource
def load_face_detector():
    return cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def detect_faces(image, face_cascade):
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    gray = cv2.equalizeHist(gray)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
    return [(x, y, x+w, y+h) for (x, y, w, h) in faces if 0.6 <= w/h <= 1.5]

def extract_face_features(image, face_coords):
    x1, y1, x2, y2 = face_coords
    face_roi = image[y1:y2, x1:x2]
    if face_roi.size == 0:
        return None
    face_roi = cv2.resize(face_roi, (100, 100))
    gray_face = cv2.cvtColor(face_roi, cv2.COLOR_RGB2GRAY)
    return gray_face.flatten().astype(np.float32) / 255.0

def compare_faces(known_features, unknown_features, threshold=0.5):
    if known_features is None or unknown_features is None:
        return False, 0.0
    dot_product = np.dot(known_features, unknown_features)
    norm_a, norm_b = np.linalg.norm(known_features), np.linalg.norm(unknown_features)
    if norm_a == 0 or norm_b == 0:
        return False, 0.0
    similarity = dot_product / (norm_a * norm_b)
    return similarity > threshold, similarity

# Student management
def load_students():
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT student_id, student_name, face_features FROM students")
            students = {}
            for row in cursor.fetchall():
                students[row['student_id']] = {
                    'name': row['student_name'],
                    'features': pickle.loads(row['face_features']) if row['face_features'] else None
                }
            cursor.close()
            conn.close()
            return students
    except Exception as err:
        st.error(f"Error loading students: {err}")
        return {}

def save_student(student_id, student_name, features):
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            features_blob = pickle.dumps(features)
            cursor.execute(
                "INSERT INTO students (student_id, student_name, face_features) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE student_name = %s, face_features = %s",
                (student_id, student_name, features_blob, student_name, features_blob)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return True
    except Exception as err:
        st.error(f"Error saving student: {err}")
        return False

def check_duplicate_student(student_id, student_name, exclude_id=None):
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            if exclude_id:
                cursor.execute("SELECT student_id, student_name FROM students WHERE (student_id = %s OR student_name = %s) AND student_id != %s", (student_id, student_name, exclude_id))
            else:
                cursor.execute("SELECT student_id, student_name FROM students WHERE student_id = %s OR student_name = %s", (student_id, student_name))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result
    except:
        return None

def update_student(old_id, new_id, new_name):
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT face_features FROM students WHERE student_id = %s", (old_id,))
            result = cursor.fetchone()
            if result:
                features = result[0]
                cursor.execute("DELETE FROM students WHERE student_id = %s", (old_id,))
                cursor.execute("INSERT INTO students (student_id, student_name, face_features) VALUES (%s, %s, %s)", (new_id, new_name, features))
                cursor.execute("UPDATE attendance_records SET student_id = %s, student_name = %s WHERE student_id = %s", (new_id, new_name, old_id))
                conn.commit()
                cursor.close()
                conn.close()
                return True
            return False
    except Exception as err:
        st.error(f"Error updating student: {err}")
        return False

def delete_student(student_id):
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM students WHERE student_id = %s", (student_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return True
    except:
        return False

def search_students(search_term):
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            search_pattern = f"%{search_term}%"
            cursor.execute("SELECT student_id, student_name FROM students WHERE student_id LIKE %s OR student_name LIKE %s", (search_pattern, search_pattern))
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
    except:
        return []

# Event management
def create_event(event_name, event_description="", start_datetime=None, end_datetime=None):
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO events (event_name, event_description, start_datetime, end_datetime, created_at) VALUES (%s, %s, %s, %s, %s)",
                (event_name, event_description, start_datetime, end_datetime, datetime.datetime.now())
            )
            conn.commit()
            cursor.close()
            conn.close()
            return True
    except Exception as err:
        st.error(f"Error creating event: {err}")
        return False

def get_all_events():
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM events ORDER BY start_datetime DESC")
            events = cursor.fetchall()
            cursor.close()
            conn.close()
            return events
    except:
        return []

def is_event_active(event):
    """Check if event is currently within its date/time range"""
    if not event.get('start_datetime') or not event.get('end_datetime'):
        return True  # No time limit set
    
    current_datetime = datetime.datetime.now()
    
    start_dt = event['start_datetime']
    end_dt = event['end_datetime']
    
    # Convert to datetime if string
    if isinstance(start_dt, str):
        start_dt = datetime.datetime.strptime(start_dt, "%Y-%m-%d %H:%M:%S")
    if isinstance(end_dt, str):
        end_dt = datetime.datetime.strptime(end_dt, "%Y-%m-%d %H:%M:%S")
    
    return start_dt <= current_datetime <= end_dt

def format_datetime_display(dt):
    """Format datetime for display"""
    if isinstance(dt, str):
        dt = datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
    return dt.strftime("%b %d, %Y %I:%M %p")

def delete_event(event_id):
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT event_name FROM events WHERE id = %s", (event_id,))
            event = cursor.fetchone()
            if event:
                cursor.execute("DELETE FROM attendance_records WHERE event_name = %s", (event[0],))
                cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
                conn.commit()
            cursor.close()
            conn.close()
            return True
    except:
        return False

# Enhanced Attendance management with multiple Time In/Out tracking and custom time
def save_attendance_record(student_id, student_name, event_name, attendance_type="time_in", custom_time=None):
    if custom_time:
        timestamp = custom_time
    else:
        timestamp = datetime.datetime.now()
    
    date, time_str = timestamp.strftime("%Y-%m-%d"), timestamp.strftime("%H:%M:%S")
    
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            # Always create new record for each attendance mark
            cursor.execute(
                "INSERT INTO attendance_records (student_id, student_name, event_name, timestamp, date, time_in, time_out, attendance_type) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (student_id, student_name, event_name, timestamp, date, 
                 time_str if attendance_type == "time_in" else None,
                 time_str if attendance_type == "time_out" else None,
                 attendance_type)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return True
    except Exception as err:
        st.error(f"Error saving attendance: {err}")
        return False

def get_attendance_summary(event_name):
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM attendance_records WHERE event_name = %s ORDER BY timestamp DESC", (event_name,))
            records = cursor.fetchall()
            cursor.close()
            conn.close()
            return records
    except:
        return []

def get_student_attendance(student_id):
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM attendance_records WHERE student_id = %s ORDER BY date DESC, timestamp DESC", (student_id,))
            records = cursor.fetchall()
            cursor.close()
            conn.close()
            return records
    except:
        return []

def get_all_attendance_records():
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM attendance_records ORDER BY timestamp DESC")
            records = cursor.fetchall()
            cursor.close()
            conn.close()
            return records
    except:
        return []

def get_attendance_counts(student_id, event_name, date):
    """Get count of Time In and Time Out for a student on specific date"""
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM attendance_records WHERE student_id = %s AND event_name = %s AND date = %s AND attendance_type = 'time_in'",
                (student_id, event_name, date)
            )
            time_in_count = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(*) FROM attendance_records WHERE student_id = %s AND event_name = %s AND date = %s AND attendance_type = 'time_out'",
                (student_id, event_name, date)
            )
            time_out_count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return time_in_count, time_out_count
    except:
        return 0, 0

# Initialize
initialize_session_state()
try:
    face_cascade = load_face_detector()
except Exception as e:
    st.error(f"❌ Error loading face detection: {e}")
    st.stop()

# Login check
if not st.session_state.logged_in:
    login_page()
    st.stop()

# Header
st.markdown(f'<div class="main-header"><h1>🎓 TCGC Event Attendance System</h1><p style="font-size: 1.1rem; margin-top: 0.8rem;">Welcome back, <strong>{st.session_state.username}</strong>! 👋</p></div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown(f"""
    <div style='padding: 1.5rem; text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; color: white; margin-bottom: 1rem;'>
        <h3 style='margin: 0;'>🧭 Navigation</h3>
        <p style='margin: 0.5rem 0 0 0; opacity: 0.9;'>Logged in as: <strong>{st.session_state.username}</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    tab_selection = st.radio("Menu", ["📊 Dashboard", "📅 Events", "👥 Register", "✅ Attendance", "📋 Records", "🔍 Manage", "📈 Reports", "⚙️ Settings"], label_visibility="collapsed")
    
    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True, type="primary"):
        st.session_state.logged_in = False
        st.session_state.clear()
        st.rerun()

# Dashboard Tab
if tab_selection == "📊 Dashboard":
    st.markdown('<div class="section-header">📊 Dashboard Overview</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{len(st.session_state.students)}</div><div class="metric-label">👥 Total Students</div></div>', unsafe_allow_html=True)
    with col2:
        events = get_all_events()
        st.markdown(f'<div class="metric-card"><div class="metric-value">{len(events)}</div><div class="metric-label">📅 Total Events</div></div>', unsafe_allow_html=True)
    with col3:
        all_records = get_all_attendance_records()
        st.markdown(f'<div class="metric-card"><div class="metric-value">{len(all_records)}</div><div class="metric-label">📝 Total Records</div></div>', unsafe_allow_html=True)
    with col4:
        active = "✅" if st.session_state.current_event else "❌"
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="font-size: 2.5rem;">{active}</div><div class="metric-label">🎯 Active Event</div></div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.session_state.current_event:
        st.markdown(f'<div class="event-card"><h2 style="margin: 0;">📍 {st.session_state.current_event}</h2><p style="margin: 0.5rem 0 0 0; font-size: 1.1rem; opacity: 0.95;">Currently Active Event</p></div>', unsafe_allow_html=True)
        
        today = datetime.date.today().strftime("%Y-%m-%d")
        today_records = [r for r in get_attendance_summary(st.session_state.current_event) if str(r.get('date')) == today]
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 📊 Today's Attendance Statistics")
            unique_students_today = len(set(r['student_id'] for r in today_records))
            time_in_today = sum(1 for r in today_records if r.get('attendance_type') == 'time_in')
            time_out_today = sum(1 for r in today_records if r.get('attendance_type') == 'time_out')
            
            st.metric("Unique Students Attended", unique_students_today, help="Number of unique students who marked attendance today")
            st.metric("⏰ Total Time In Marks", time_in_today, help="Total number of Time In records today")
            st.metric("🚪 Total Time Out Marks", time_out_today, help="Total number of Time Out records today")
        
        with col2:
            st.markdown("#### 🕐 Recent Activity (Last 5)")
            recent = sorted(st.session_state.attendance_session[-5:], key=lambda x: x[2] if len(x) > 2 else "", reverse=True)
            if recent:
                for sid, name, time_str, att_type in recent:
                    badge_class = "time-in-badge" if "In" in att_type else "time-out-badge"
                    st.markdown(f'<div class="student-card"><strong>🎓 {name}</strong><br><span class="time-badge {badge_class}">{att_type}</span> <small>🕐 {time_str}</small></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="info-box">ℹ️ No recent activity yet. Start marking attendance!</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="warning-box">⚠️ <strong>No Active Event Selected</strong><br>Please go to the <strong>Events</strong> tab and select an event to start marking attendance.</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📈 Attendance Trends (Last 30 Days)")
        all_records = get_all_attendance_records()
        if all_records:
            df = pd.DataFrame(all_records)
            df['date'] = pd.to_datetime(df['date'])
            thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
            df = df[df['date'] >= thirty_days_ago]
            attendance_by_date = df.groupby('date').size().reset_index(name='count')
            st.line_chart(attendance_by_date.set_index('date'), height=300)
        else:
            st.markdown('<div class="info-box">📊 No attendance data available yet</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown("#### 🎯 Events Overview")
        events = get_all_events()
        if events:
            event_data = []
            for event in events[:10]:  # Top 10 events
                count = len(get_attendance_summary(event['event_name']))
                event_data.append({'Event': event['event_name'][:30], 'Records': count})
            if event_data:
                df_events = pd.DataFrame(event_data)
                st.bar_chart(df_events.set_index('Event'), height=300)
        else:
            st.markdown('<div class="info-box">📅 No events created yet</div>', unsafe_allow_html=True)

# Events Tab
elif tab_selection == "📅 Events":
    st.markdown('<div class="section-header">📅 Event Management</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### ➕ Create New Event")
        with st.form("create_event_form"):
            new_event_name = st.text_input("📝 Event Name", placeholder="e.g., Computer Science Seminar 2024")
            new_event_desc = st.text_area("📋 Event Description (Optional)", placeholder="Brief description of the event...")
            
            st.markdown("**📅 Event Schedule**")
            
            col_date1, col_time1 = st.columns(2)
            with col_date1:
                start_date = st.date_input("🗓️ Start Date", value=datetime.date.today(), help="Event start date")
            with col_time1:
                start_time = st.time_input("🕐 Start Time", value=datetime.time(8, 0), help="Event start time")
            
            col_date2, col_time2 = st.columns(2)
            with col_date2:
                end_date = st.date_input("🗓️ End Date", value=datetime.date.today(), help="Event end date")
            with col_time2:
                end_time = st.time_input("🕐 End Time", value=datetime.time(17, 0), help="Event end time")
            
            # Validation
            start_datetime = datetime.datetime.combine(start_date, start_time)
            end_datetime = datetime.datetime.combine(end_date, end_time)
            
            if start_datetime >= end_datetime:
                st.markdown('<div class="warning-box">⚠️ End date/time must be after start date/time!</div>', unsafe_allow_html=True)
            
            # Show duration
            duration = end_datetime - start_datetime
            days = duration.days
            hours = duration.seconds // 3600
            minutes = (duration.seconds % 3600) // 60
            
            duration_text = []
            if days > 0:
                duration_text.append(f"{days} day{'s' if days > 1 else ''}")
            if hours > 0:
                duration_text.append(f"{hours} hour{'s' if hours > 1 else ''}")
            if minutes > 0:
                duration_text.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
            
            st.markdown(f'<div class="info-box">⏱️ <strong>Event Duration:</strong> {", ".join(duration_text) if duration_text else "0 minutes"}</div>', unsafe_allow_html=True)
            
            if st.form_submit_button("✅ Create Event", use_container_width=True, type="primary"):
                if new_event_name:
                    if start_datetime >= end_datetime:
                        st.markdown('<div class="warning-box">⚠️ Please set valid date/time range!</div>', unsafe_allow_html=True)
                    else:
                        if create_event(new_event_name, new_event_desc, start_datetime, end_datetime):
                            st.markdown(f'<div class="success-box">✅ <strong>Event "{new_event_name}" created successfully!</strong><br>From: {format_datetime_display(start_datetime)}<br>To: {format_datetime_display(end_datetime)}</div>', unsafe_allow_html=True)
                            st.session_state.current_event = new_event_name
                            time.sleep(1.5)
                            st.rerun()
                else:
                    st.markdown('<div class="warning-box">⚠️ Please enter an event name!</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 📊 Quick Stats")
        all_events = get_all_events()
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="font-size: 2.5rem;">{len(all_events)}</div><div class="metric-label">Total Events</div></div>', unsafe_allow_html=True)
        st.write("")
        
        # Count active events
        active_events = sum(1 for e in all_events if is_event_active(e))
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="font-size: 2.5rem;">{active_events}</div><div class="metric-label">Active Events</div></div>', unsafe_allow_html=True)
        st.write("")
        
        selected_text = "✅ Yes" if st.session_state.current_event else "❌ No"
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="font-size: 1.8rem;">{selected_text}</div><div class="metric-label">Selected Event</div></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown('<div class="section-header">📋 All Events</div>', unsafe_allow_html=True)
    
    if all_events:
        for event in all_events:
            is_selected = st.session_state.current_event == event['event_name']
            event_time_active = is_event_active(event)
            
            col1, col2, col3 = st.columns([4, 1, 1])
            
            with col1:
                # Selected badge
                if is_selected:
                    badge = '<span class="count-badge" style="background: #28a745; margin-left: 0.5rem;">✓ SELECTED</span>'
                else:
                    badge = ''
                
                # Active status badge
                if event_time_active:
                    status_badge = '<span class="time-badge time-in-badge">🟢 ACTIVE NOW</span>'
                else:
                    current_dt = datetime.datetime.now()
                    start_dt = event.get('start_datetime')
                    if isinstance(start_dt, str):
                        start_dt = datetime.datetime.strptime(start_dt, "%Y-%m-%d %H:%M:%S")
                    
                    if current_dt < start_dt:
                        status_badge = '<span class="time-badge" style="background: #fff3cd; color: #856404;">⏳ UPCOMING</span>'
                    else:
                        status_badge = '<span class="time-badge" style="background: #f8d7da; color: #721c24;">🔴 ENDED</span>'
                
                # Format dates
                if event.get('start_datetime') and event.get('end_datetime'):
                    start_display = format_datetime_display(event['start_datetime'])
                    end_display = format_datetime_display(event['end_datetime'])
                    time_display = f'<p style="color: #666; margin: 0.3rem 0;"><strong>📅 Start:</strong> {start_display}<br><strong>📅 End:</strong> {end_display}</p>'
                else:
                    time_display = '<p style="color: #999; margin: 0.3rem 0;"><em>No schedule set</em></p>'
                
                attendance_count = len(get_attendance_summary(event['event_name']))
                
                st.markdown(f'''
                <div class="event-list-item">
                    <h4 style="color: #333; margin: 0; display: flex; align-items: center; gap: 0.5rem;">
                        📅 {event["event_name"]} {badge} {status_badge}
                    </h4>
                    {time_display}
                    <p style="color: #666; margin: 0.3rem 0;">
                        <strong>📝 Attendance Records:</strong> <span class="count-badge" style="font-size: 0.75rem;">{attendance_count}</span>
                    </p>
                    <p style="color: #666; margin: 0.5rem 0 0 0; font-size: 0.9rem;">{event.get("event_description", "No description")}</p>
                </div>
                ''', unsafe_allow_html=True)
            
            with col2:
                button_type = "secondary" if is_selected else "primary"
                button_text = "✓ Selected" if is_selected else "📍 Select"
                button_disabled = is_selected
                
                if st.button(button_text, key=f"sel_{event['id']}", use_container_width=True, type=button_type, disabled=button_disabled):
                    st.session_state.current_event = event['event_name']
                    st.markdown('<div class="success-box">✅ Event selected!</div>', unsafe_allow_html=True)
                    time.sleep(0.5)
                    st.rerun()
            
            with col3:
                if st.button("🗑️ Delete", key=f"del_{event['id']}", use_container_width=True):
                    if delete_event(event['id']):
                        if st.session_state.current_event == event['event_name']:
                            st.session_state.current_event = ""
                        st.markdown('<div class="success-box">✅ Event deleted!</div>', unsafe_allow_html=True)
                        time.sleep(0.5)
                        st.rerun()
    else:
        st.markdown('<div class="info-box">📋 No events created yet. Create your first event above!</div>', unsafe_allow_html=True)

# Register Tab
elif tab_selection == "👥 Register":
    st.markdown('<div class="section-header">👥 Student Registration</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        student_id = st.text_input("🆔 Student ID", placeholder="e.g., CS-2024-001")
    with col2:
        student_name = st.text_input("👤 Student Name", placeholder="e.g., John Doe")
    
    if student_id and student_name:
        duplicate = check_duplicate_student(student_id, student_name)
        if duplicate:
            st.markdown(f'<div class="warning-box">⚠️ <strong>Duplicate Detected!</strong><br>Student with ID "{duplicate[0]}" or name "{duplicate[1]}" already exists!</div>', unsafe_allow_html=True)
    
    # Webcam registration only
    if not student_id or not student_name:
        st.markdown('<div class="info-box">ℹ️ Please enter Student ID and Name first before using webcam.</div>', unsafe_allow_html=True)
    elif check_duplicate_student(student_id, student_name):
        st.markdown('<div class="warning-box">❌ Cannot register: Student already exists!</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="info-box">📹 Position your face clearly in the camera and click the capture button when ready.</div>', unsafe_allow_html=True)
        
        class RegistrationProcessor:
            def __init__(self):
                self.latest_frame = None
            def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
                img = frame.to_ndarray(format="bgr24")
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                self.latest_frame = rgb_img.copy()
                faces = detect_faces(rgb_img, face_cascade)
                for x1, y1, x2, y2 in faces:
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
                    cv2.putText(img, "Face Detected - Ready!", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                if not faces:
                    cv2.putText(img, "Position your face in view", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                return av.VideoFrame.from_ndarray(img, format="bgr24")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            webrtc_ctx = webrtc_streamer(
                key=f"registration_webcam_{st.session_state.webcam_key}",
                mode=WebRtcMode.SENDRECV,
                video_processor_factory=RegistrationProcessor,
                media_stream_constraints={"video": True, "audio": False},
                async_processing=True
            )
        with col2:
            st.markdown("### 📸 Capture Controls")
            if webrtc_ctx and webrtc_ctx.video_processor:
                if st.button("📸 Capture & Register", type="primary", use_container_width=True):
                    if webrtc_ctx.video_processor.latest_frame is not None:
                        image_array = webrtc_ctx.video_processor.latest_frame
                        faces = detect_faces(image_array, face_cascade)
                        if faces:
                            features = extract_face_features(image_array, faces[0])
                            if features is not None and save_student(student_id, student_name, features):
                                st.session_state.students = load_students()
                                st.markdown(f'<div class="success-box">✅ <strong>{student_name}</strong> registered successfully!</div>', unsafe_allow_html=True)
                                st.balloons()
                                time.sleep(1)
                                st.rerun()
                        else:
                            st.markdown('<div class="warning-box">❌ No face detected! Please position your face clearly.</div>', unsafe_allow_html=True)

# Attendance Tab with Enhanced Tracking - WEBCAM ONLY
elif tab_selection == "✅ Attendance":
    st.markdown('<div class="section-header">✅ Take Attendance</div>', unsafe_allow_html=True)
    
    if not st.session_state.current_event:
        st.markdown('<div class="warning-box">⚠️ <strong>No Event Selected!</strong><br>Please go to the <strong>Events</strong> tab and select an active event first.</div>', unsafe_allow_html=True)
    elif not st.session_state.students:
        st.markdown('<div class="warning-box">⚠️ <strong>No Students Registered!</strong><br>Please register students first in the <strong>Register</strong> tab.</div>', unsafe_allow_html=True)
    else:
        # Get current event details
        current_event_details = None
        all_events = get_all_events()
        for event in all_events:
            if event['event_name'] == st.session_state.current_event:
                current_event_details = event
                break
        
        # Check if event has time limit and if it's active
        time_limit_active = True
        time_warning = ""
        
        if current_event_details and current_event_details.get('start_datetime') and current_event_details.get('end_datetime'):
            time_limit_active = is_event_active(current_event_details)
            if not time_limit_active:
                current_dt = datetime.datetime.now()
                start_dt = current_event_details['start_datetime']
                end_dt = current_event_details['end_datetime']
                
                if isinstance(start_dt, str):
                    start_dt = datetime.datetime.strptime(start_dt, "%Y-%m-%d %H:%M:%S")
                if isinstance(end_dt, str):
                    end_dt = datetime.datetime.strptime(end_dt, "%Y-%m-%d %H:%M:%S")
                
                if current_dt < start_dt:
                    time_warning = f'<div class="warning-box">⏰ <strong>Event Not Started!</strong><br>Event starts on: {format_datetime_display(start_dt)}<br>Current time: {current_dt.strftime("%b %d, %Y %I:%M %p")}</div>'
                elif current_dt > end_dt:
                    time_warning = f'<div class="warning-box">⏰ <strong>Event Has Ended!</strong><br>Event ended on: {format_datetime_display(end_dt)}<br>Current time: {current_dt.strftime("%b %d, %Y %I:%M %p")}</div>'
        
        if time_warning:
            st.markdown(time_warning, unsafe_allow_html=True)
        
        # Display event card with time info
        event_time_info = ""
        if current_event_details and current_event_details.get('start_datetime') and current_event_details.get('end_datetime'):
            start_display = format_datetime_display(current_event_details['start_datetime'])
            end_display = format_datetime_display(current_event_details['end_datetime'])
            status = "🟢 Active Now" if time_limit_active else "🔴 Inactive"
            event_time_info = f'<p style="margin: 0.5rem 0 0 0; opacity: 0.95;">📅 From: {start_display}</p><p style="margin: 0.3rem 0 0 0; opacity: 0.95;">📅 To: {end_display}</p><p style="margin: 0.3rem 0 0 0; opacity: 0.95;">Status: {status}</p>'
        
        st.markdown(f'''
        <div class="event-card">
            <h3 style="margin: 0;">📅 Event: {st.session_state.current_event}</h3>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Marking attendance for this event</p>
            {event_time_info}
        </div>
        ''', unsafe_allow_html=True)
        
        # Only allow attendance if time limit is active (or no time limit set)
        if not time_limit_active:
            st.markdown('<div class="warning-box">⚠️ <strong>Attendance Disabled!</strong><br>This event is not currently active. Please wait for the event time or select an active event.</div>', unsafe_allow_html=True)
        else:
            col1, col2 = st.columns(2)
            with col1:
                attendance_type = st.radio("⏰ Attendance Type:", ["⏰ Time In", "🚪 Time Out"], horizontal=True, help="Select whether students are arriving or leaving", key="attendance_type_radio")
            with col2:
                manual_time = st.checkbox("🕐 Manual Time", value=False, help="Set custom time for attendance", key="manual_time_checkbox")
            
            # Manual time input
            custom_time = None
            if manual_time:
                st.markdown("**🕐 Custom Time Entry**")
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    custom_date = st.date_input("📅 Date", value=datetime.date.today(), help="Select attendance date", key="custom_date_input")
                with col_t2:
                    custom_time_input = st.time_input("🕐 Time", value=datetime.datetime.now().time(), help="Select attendance time", key="custom_time_input")
                custom_time = datetime.datetime.combine(custom_date, custom_time_input)
                st.markdown(f'<div class="info-box">📅 Will record as: <strong>{custom_time.strftime("%B %d, %Y at %I:%M %p")}</strong></div>', unsafe_allow_html=True)
            
            st.markdown('<div class="info-box">💡 <strong>Tip:</strong> Each Time In/Out will be recorded separately, allowing multiple entries per day for accurate tracking.</div>', unsafe_allow_html=True)
            
            # WEBCAM ONLY - NO UPLOAD OPTION
            st.markdown("### 📹 Live Webcam Attendance")
            
            class AttendanceProcessor:
                def __init__(self):
                    self.latest_frame = None
                def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
                    img = frame.to_ndarray(format="bgr24")
                    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    self.latest_frame = rgb_img.copy()
                    faces = detect_faces(rgb_img, face_cascade)
                    for x1, y1, x2, y2 in faces:
                        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
                        cv2.putText(img, "Face Detected", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    if not faces:
                        cv2.putText(img, "Position face in view", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    return av.VideoFrame.from_ndarray(img, format="bgr24")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                webrtc_ctx = webrtc_streamer(
                    key=f"attendance_webcam_{st.session_state.current_event}_{st.session_state.attendance_webcam_key}",
                    mode=WebRtcMode.SENDRECV,
                    video_processor_factory=AttendanceProcessor,
                    media_stream_constraints={"video": True, "audio": False},
                    async_processing=True
                )
            
            with col2:
                st.markdown(f"### 📸 Mark {attendance_type}")
                if webrtc_ctx and webrtc_ctx.video_processor:
                    if st.button(f"✅ Mark {attendance_type}", type="primary", use_container_width=True, key="mark_attendance_button"):
                        if webrtc_ctx.video_processor.latest_frame is not None:
                            image_array = webrtc_ctx.video_processor.latest_frame
                            faces = detect_faces(image_array, face_cascade)
                            if faces:
                                features = extract_face_features(image_array, faces[0])
                                if features is not None:
                                    best_match, best_sim = None, 0
                                    for sid, data in st.session_state.students.items():
                                        is_match, sim = compare_faces(data["features"], features, 0.3)
                                        if is_match and sim > best_sim:
                                            best_sim, best_match = sim, (sid, data["name"])
                                    if best_match:
                                        sid, name = best_match
                                        att_type = "time_in" if "In" in attendance_type else "time_out"
                                        if save_attendance_record(sid, name, st.session_state.current_event, att_type, custom_time):
                                            record_time = custom_time if custom_time else datetime.datetime.now()
                                            today = datetime.date.today().strftime("%Y-%m-%d")
                                            time_in_count, time_out_count = get_attendance_counts(sid, st.session_state.current_event, today)
                                            st.session_state.attendance_session.append((sid, name, record_time.strftime("%H:%M:%S"), attendance_type))
                                            st.markdown(f'''
                                            <div class="success-box">
                                                ✅ <strong>{name}</strong> - {attendance_type} marked!<br>
                                                📅 Recorded at: {record_time.strftime("%B %d, %Y at %I:%M %p")}<br>
                                                <span class="count-badge" style="font-size: 0.8rem;">In: {time_in_count}x | Out: {time_out_count}x Today</span>
                                            </div>
                                            ''', unsafe_allow_html=True)
                                            st.balloons()
                                    else:
                                        st.markdown('<div class="warning-box">❌ Face not recognized! Please register first.</div>', unsafe_allow_html=True)
                            else:
                                st.markdown('<div class="warning-box">❌ No face detected! Position face clearly.</div>', unsafe_allow_html=True)
                
                st.markdown("### 📋 Recent Marks (Last 5)")
                if st.session_state.attendance_session:
                    for sid, name, time_str, att_type in st.session_state.attendance_session[-5:]:
                        badge_class = "time-in-badge" if "In" in att_type else "time-out-badge"
                        st.markdown(f'<div class="attendance-record">✅ <strong>{name}</strong><br><span class="time-badge {badge_class}">{att_type}</span> at {time_str}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="info-box">No marks yet</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-header">✅ Take Attendance</div>', unsafe_allow_html=True)
    
    if not st.session_state.current_event:
        st.markdown('<div class="warning-box">⚠️ <strong>No Event Selected!</strong><br>Please go to the <strong>Events</strong> tab and select an active event first.</div>', unsafe_allow_html=True)
    elif not st.session_state.students:
        st.markdown('<div class="warning-box">⚠️ <strong>No Students Registered!</strong><br>Please register students first in the <strong>Register</strong> tab.</div>', unsafe_allow_html=True)
    else:
        # Get current event details
        current_event_details = None
        all_events = get_all_events()
        for event in all_events:
            if event['event_name'] == st.session_state.current_event:
                current_event_details = event
                break
        
        # Check if event has time limit and if it's active
        time_limit_active = True
        time_warning = ""
        
        if current_event_details and current_event_details.get('start_datetime') and current_event_details.get('end_datetime'):
            time_limit_active = is_event_active(current_event_details)
            if not time_limit_active:
                current_dt = datetime.datetime.now()
                start_dt = current_event_details['start_datetime']
                end_dt = current_event_details['end_datetime']
                
                if isinstance(start_dt, str):
                    start_dt = datetime.datetime.strptime(start_dt, "%Y-%m-%d %H:%M:%S")
                if isinstance(end_dt, str):
                    end_dt = datetime.datetime.strptime(end_dt, "%Y-%m-%d %H:%M:%S")
                
                if current_dt < start_dt:
                    time_warning = f'<div class="warning-box">⏰ <strong>Event Not Started!</strong><br>Event starts on: {format_datetime_display(start_dt)}<br>Current time: {current_dt.strftime("%b %d, %Y %I:%M %p")}</div>'
                elif current_dt > end_dt:
                    time_warning = f'<div class="warning-box">⏰ <strong>Event Has Ended!</strong><br>Event ended on: {format_datetime_display(end_dt)}<br>Current time: {current_dt.strftime("%b %d, %Y %I:%M %p")}</div>'
        
        if time_warning:
            st.markdown(time_warning, unsafe_allow_html=True)
        
        # Display event card with time info
        event_time_info = ""
        if current_event_details and current_event_details.get('start_datetime') and current_event_details.get('end_datetime'):
            start_display = format_datetime_display(current_event_details['start_datetime'])
            end_display = format_datetime_display(current_event_details['end_datetime'])
            status = "🟢 Active Now" if time_limit_active else "🔴 Inactive"
            event_time_info = f'<p style="margin: 0.5rem 0 0 0; opacity: 0.95;">📅 From: {start_display}</p><p style="margin: 0.3rem 0 0 0; opacity: 0.95;">📅 To: {end_display}</p><p style="margin: 0.3rem 0 0 0; opacity: 0.95;">Status: {status}</p>'
        
        st.markdown(f'''
        <div class="event-card">
            <h3 style="margin: 0;">📅 Event: {st.session_state.current_event}</h3>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Marking attendance for this event</p>
            {event_time_info}
        </div>
        ''', unsafe_allow_html=True)
        
        # Only allow attendance if time limit is active (or no time limit set)
        if not time_limit_active:
            st.markdown('<div class="warning-box">⚠️ <strong>Attendance Disabled!</strong><br>This event is not currently active. Please wait for the event time or select an active event.</div>', unsafe_allow_html=True)
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                attendance_type = st.radio("⏰ Attendance Type:", ["⏰ Time In", "🚪 Time Out"], horizontal=True, help="Select whether students are arriving or leaving")
            with col2:
                att_method = st.radio("📸 Method:", ["📤 Upload Photo", "📹 Live Webcam"], horizontal=True)
            with col3:
                manual_time = st.checkbox("🕐 Manual Time", value=False, help="Set custom time for attendance")
            
            # Manual time input
            custom_time = None
            if manual_time:
                st.markdown("**🕐 Custom Time Entry**")
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    custom_date = st.date_input("📅 Date", value=datetime.date.today(), help="Select attendance date")
                with col_t2:
                    custom_time_input = st.time_input("🕐 Time", value=datetime.datetime.now().time(), help="Select attendance time")
                custom_time = datetime.datetime.combine(custom_date, custom_time_input)
                st.markdown(f'<div class="info-box">📅 Will record as: <strong>{custom_time.strftime("%B %d, %Y at %I:%M %p")}</strong></div>', unsafe_allow_html=True)
            
            st.markdown('<div class="info-box">💡 <strong>Tip:</strong> Each Time In/Out will be recorded separately, allowing multiple entries per day for accurate tracking.</div>', unsafe_allow_html=True)
            
            if att_method == "📤 Upload Photo":
                uploaded = st.file_uploader("📷 Upload Attendance Photo", type=["jpg", "png", "jpeg"], key="att_photo", help="Upload a photo containing student faces")
            uploaded = st.file_uploader("📷 Upload Attendance Photo", type=["jpg", "png", "jpeg"], key="att", help="Upload a photo containing student faces")
            if uploaded:
                pil_image = Image.open(uploaded).convert("RGB")
                image_array = np.array(pil_image)
                faces = detect_faces(image_array, face_cascade)
                if faces:
                    result_image = image_array.copy()
                    recognized = []
                    for face_coords in faces:
                        features = extract_face_features(image_array, face_coords)
                        if features is not None:
                            best_match, best_sim = None, 0
                            for sid, data in st.session_state.students.items():
                                is_match, sim = compare_faces(data["features"], features, 0.4)
                                if is_match and sim > best_sim:
                                    best_sim, best_match = sim, (sid, data["name"])
                            x1, y1, x2, y2 = face_coords
                            if best_match:
                                sid, name = best_match
                                recognized.append((sid, name))
                                cv2.rectangle(result_image, (x1, y1), (x2, y2), (0, 255, 0), 3)
                                cv2.putText(result_image, f"{name} ({best_sim:.2f})", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    st.image(result_image, caption="Recognition Results", width=600)
                    
                    if recognized:
                        att_type = "time_in" if "In" in attendance_type else "time_out"
                        today = datetime.date.today().strftime("%Y-%m-%d")
                        st.markdown(f'<div class="section-header">✅ {attendance_type} Marked Successfully</div>', unsafe_allow_html=True)
                        for sid, name in recognized:
                            if save_attendance_record(sid, name, st.session_state.current_event, att_type, custom_time):
                                time_in_count, time_out_count = get_attendance_counts(sid, st.session_state.current_event, today)
                                badge_class = "time-in-badge" if att_type == "time_in" else "time-out-badge"
                                recorded_time = custom_time.strftime("%B %d, %Y at %I:%M %p") if custom_time else datetime.datetime.now().strftime("%B %d, %Y at %I:%M %p")
                                st.markdown(f'''
                                <div class="success-box">
                                    ✅ <strong>{name}</strong> (ID: {sid})<br>
                                    <span class="time-badge {badge_class}">{attendance_type}</span> at {recorded_time}<br>
                                    <span class="count-badge" style="font-size: 0.8rem;">Time In: {time_in_count}x | Time Out: {time_out_count}x Today</span>
                                </div>
                                ''', unsafe_allow_html=True)
                        st.balloons()
                    else:
                        st.markdown('<div class="warning-box">⚠️ No registered students recognized in the photo.</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="warning-box">❌ No faces detected in the image.</div>', unsafe_allow_html=True)
        
            else:  # Live Webcam
                class AttendanceProcessor:
                    def __init__(self):
                        self.latest_frame = None
                    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
                        img = frame.to_ndarray(format="bgr24")
                        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        self.latest_frame = rgb_img.copy()
                        faces = detect_faces(rgb_img, face_cascade)
                        for x1, y1, x2, y2 in faces:
                            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
                            cv2.putText(img, "Face Detected", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        if not faces:
                            cv2.putText(img, "Position face in view", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                        return av.VideoFrame.from_ndarray(img, format="bgr24")
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    webrtc_ctx = webrtc_streamer(key=f"att_{st.session_state.attendance_webcam_key}", mode=WebRtcMode.SENDRECV,
                                                video_processor_factory=AttendanceProcessor, media_stream_constraints={"video": True, "audio": False}, async_processing=True)
                with col2:
                    st.markdown(f"### 📸 Mark {attendance_type}")
                    if webrtc_ctx and webrtc_ctx.video_processor:
                        if st.button(f"✅ Mark {attendance_type}", type="primary", use_container_width=True):
                            if webrtc_ctx.video_processor.latest_frame is not None:
                                image_array = webrtc_ctx.video_processor.latest_frame
                                faces = detect_faces(image_array, face_cascade)
                                if faces:
                                    features = extract_face_features(image_array, faces[0])
                                    if features is not None:
                                        best_match, best_sim = None, 0
                                        for sid, data in st.session_state.students.items():
                                            is_match, sim = compare_faces(data["features"], features, 0.3)
                                            if is_match and sim > best_sim:
                                                best_sim, best_match = sim, (sid, data["name"])
                                        if best_match:
                                            sid, name = best_match
                                            att_type = "time_in" if "In" in attendance_type else "time_out"
                                            if save_attendance_record(sid, name, st.session_state.current_event, att_type, custom_time):
                                                record_time = custom_time if custom_time else datetime.datetime.now()
                                                today = datetime.date.today().strftime("%Y-%m-%d")
                                                time_in_count, time_out_count = get_attendance_counts(sid, st.session_state.current_event, today)
                                                st.session_state.attendance_session.append((sid, name, record_time.strftime("%H:%M:%S"), attendance_type))
                                                st.markdown(f'''
                                                <div class="success-box">
                                                    ✅ <strong>{name}</strong> - {attendance_type} marked!<br>
                                                    📅 Recorded at: {record_time.strftime("%B %d, %Y at %I:%M %p")}<br>
                                                    <span class="count-badge" style="font-size: 0.8rem;">In: {time_in_count}x | Out: {time_out_count}x Today</span>
                                                </div>
                                                ''', unsafe_allow_html=True)
                                                st.balloons()
                                        else:
                                            st.markdown('<div class="warning-box">❌ Face not recognized! Please register first.</div>', unsafe_allow_html=True)
                                else:
                                    st.markdown('<div class="warning-box">❌ No face detected! Position face clearly.</div>', unsafe_allow_html=True)
                    
                    st.markdown("### 📋 Recent Marks (Last 5)")
                    if st.session_state.attendance_session:
                        for sid, name, time_str, att_type in st.session_state.attendance_session[-5:]:
                            badge_class = "time-in-badge" if "In" in att_type else "time-out-badge"
                            st.markdown(f'<div class="attendance-record">✅ <strong>{name}</strong><br><span class="time-badge {badge_class}">{att_type}</span> at {time_str}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="info-box">No marks yet</div>', unsafe_allow_html=True)

# Records Tab with Enhanced Display
elif tab_selection == "📋 Records":
    st.markdown('<div class="section-header">📋 Attendance Records</div>', unsafe_allow_html=True)
    
    st.markdown("### 🔍 Search Student Attendance")
    search_term = st.text_input("🔎 Search by Student ID or Name", placeholder="Enter student ID or name...")
    
    if search_term:
        results = search_students(search_term)
        if results:
            st.markdown(f'<div class="info-box">🔍 Found <strong>{len(results)}</strong> student(s)</div>', unsafe_allow_html=True)
            for student in results:
                sid, name = student['student_id'], student['student_name']
                attendance_records = get_student_attendance(sid)
                
                # Group records by date and event
                records_by_date_event = {}
                for record in attendance_records:
                    key = (str(record['date']), record['event_name'])
                    if key not in records_by_date_event:
                        records_by_date_event[key] = {'time_in': [], 'time_out': []}
                    if record.get('attendance_type') == 'time_in' and record.get('time_in'):
                        records_by_date_event[key]['time_in'].append(record['time_in'])
                    if record.get('attendance_type') == 'time_out' and record.get('time_out'):
                        records_by_date_event[key]['time_out'].append(record['time_out'])
                
                st.markdown(f'<div class="student-card"><h4 style="margin: 0; color: #333;">🎓 {name} (ID: {sid})</h4></div>', unsafe_allow_html=True)
                
                if records_by_date_event:
                    st.markdown(f'<div class="info-box">📊 Total Events Attended: <strong>{len(records_by_date_event)}</strong></div>', unsafe_allow_html=True)
                    for (date, event), times in sorted(records_by_date_event.items(), reverse=True):
                        time_in_list = ', '.join(times['time_in']) if times['time_in'] else 'None'
                        time_out_list = ', '.join(times['time_out']) if times['time_out'] else 'None'
                        st.markdown(f'''
                        <div class="attendance-record">
                            <strong>📅 {event}</strong> - {date}<br>
                            <span class="time-badge time-in-badge">⏰ Time In ({len(times['time_in'])}x): {time_in_list}</span>
                            <span class="time-badge time-out-badge">🚪 Time Out ({len(times['time_out'])}x): {time_out_list}</span>
                        </div>
                        ''', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="warning-box">No attendance records found for this student</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="info-box">ℹ️ No students found matching your search.</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.session_state.current_event:
        records = get_attendance_summary(st.session_state.current_event)
        if records:
            # Group by student
            student_records = {}
            for record in records:
                sid = record['student_id']
                if sid not in student_records:
                    student_records[sid] = {
                        'name': record['student_name'],
                        'time_in': [],
                        'time_out': [],
                        'dates': set()
                    }
                student_records[sid]['dates'].add(str(record['date']))
                if record.get('attendance_type') == 'time_in' and record.get('time_in'):
                    student_records[sid]['time_in'].append(f"{record['date']} {record['time_in']}")
                if record.get('attendance_type') == 'time_out' and record.get('time_out'):
                    student_records[sid]['time_out'].append(f"{record['date']} {record['time_out']}")
            
            st.markdown(f'''
            <div class="event-card">
                <h3 style="margin: 0;">📅 {st.session_state.current_event}</h3>
                <p style="margin: 0.5rem 0 0 0;">
                    <span class="count-badge">Total Students: {len(student_records)}</span>
                    <span class="count-badge">Total Records: {len(records)}</span>
                </p>
            </div>
            ''', unsafe_allow_html=True)
            
            for sid, data in student_records.items():
                time_in_count = len(data['time_in'])
                time_out_count = len(data['time_out'])
                days_attended = len(data['dates'])
                
                st.markdown(f'''
                <div class="student-card">
                    <h4 style="margin: 0; color: #333;">🎓 {data['name']} (ID: {sid})</h4>
                    <p style="margin: 0.5rem 0;">
                        <span class="count-badge" style="font-size: 0.8rem;">Days: {days_attended}</span>
                        <span class="time-badge time-in-badge">⏰ Time In: {time_in_count}x</span>
                        <span class="time-badge time-out-badge">🚪 Time Out: {time_out_count}x</span>
                    </p>
                </div>
                ''', unsafe_allow_html=True)
            
            df = pd.DataFrame(records)
            csv = df.to_csv(index=False)
            st.download_button("📥 Download Complete CSV", csv, f"attendance_{st.session_state.current_event}_{datetime.date.today()}.csv", "text/csv", use_container_width=True)
        else:
            st.markdown('<div class="info-box">ℹ️ No attendance records for this event yet.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="warning-box">⚠️ Please select an event from the Events tab first.</div>', unsafe_allow_html=True)

# Manage Tab
elif tab_selection == "🔍 Manage":
    st.markdown('<div class="section-header">🔍 Manage Students</div>', unsafe_allow_html=True)
    
    search_term = st.text_input("🔎 Search by ID or Name", placeholder="Enter student ID or name to manage...")
    
    if search_term:
        results = search_students(search_term)
        if results:
            st.markdown(f'<div class="info-box">🔍 Found <strong>{len(results)}</strong> student(s) matching your search</div>', unsafe_allow_html=True)
            for student in results:
                sid, name = student['student_id'], student['student_name']
                
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        attendance_records = get_student_attendance(sid)
                        total_events = len(set(r['event_name'] for r in attendance_records))
                        total_records = len(attendance_records)
                        
                        st.markdown(f'''
                        <div class="student-card">
                            <h4 style="margin: 0; color: #333;">🎓 {name}</h4>
                            <p style="margin: 0.3rem 0; color: #666;">ID: <strong>{sid}</strong></p>
                            <p style="margin: 0.3rem 0;">
                                <span class="count-badge" style="font-size: 0.75rem;">Events: {total_events}</span>
                                <span class="count-badge" style="font-size: 0.75rem;">Total Records: {total_records}</span>
                            </p>
                        </div>
                        ''', unsafe_allow_html=True)
                    
                    with col2:
                        if st.button("✏️ Edit", key=f"edit_stu_{sid}", help="Edit student information", use_container_width=True):
                            st.session_state[f"editing_{sid}"] = True
                            st.rerun()
                    
                    with col3:
                        if st.button("🗑️ Delete", key=f"del_stu_{sid}", help="Delete student", use_container_width=True):
                            if delete_student(sid):
                                st.session_state.students = load_students()
                                st.markdown(f'<div class="success-box">✅ Student <strong>{name}</strong> deleted successfully!</div>', unsafe_allow_html=True)
                                time.sleep(1)
                                st.rerun()
                
                if st.session_state.get(f"editing_{sid}", False):
                    st.markdown("### ✏️ Edit Student Information")
                    with st.form(f"edit_form_{sid}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            new_id = st.text_input("🆔 Student ID", value=sid, key=f"new_id_{sid}")
                        with col2:
                            new_name = st.text_input("👤 Student Name", value=name, key=f"new_name_{sid}")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary"):
                                if new_id and new_name:
                                    if new_id != sid or new_name != name:
                                        duplicate = check_duplicate_student(new_id, new_name, exclude_id=sid)
                                        if not duplicate:
                                            if update_student(sid, new_id, new_name):
                                                st.session_state.students = load_students()
                                                st.markdown(f'<div class="success-box">✅ Updated to <strong>{new_name}</strong> ({new_id})</div>', unsafe_allow_html=True)
                                                st.session_state[f"editing_{sid}"] = False
                                                time.sleep(1)
                                                st.rerun()
                                        else:
                                            st.markdown('<div class="warning-box">⚠️ ID or name already exists!</div>', unsafe_allow_html=True)
                                    else:
                                        st.session_state[f"editing_{sid}"] = False
                                        st.rerun()
                                else:
                                    st.markdown('<div class="warning-box">⚠️ Please fill in all fields</div>', unsafe_allow_html=True)
                        with col_b:
                            if st.form_submit_button("❌ Cancel", use_container_width=True):
                                st.session_state[f"editing_{sid}"] = False
                                st.rerun()
        else:
            st.markdown('<div class="info-box">ℹ️ No students found matching your search.</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown('<div class="section-header">👥 All Students</div>', unsafe_allow_html=True)
    
    if st.session_state.students:
        students_per_page = 10
        total_students = len(st.session_state.students)
        total_pages = max(1, (total_students - 1) // students_per_page + 1)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("⬅️ Previous", disabled=st.session_state.current_page <= 1, use_container_width=True):
                st.session_state.current_page -= 1
                st.rerun()
        with col2:
            st.markdown(f'<div style="text-align: center; padding: 0.5rem;"><strong>Page {st.session_state.current_page} of {total_pages}</strong></div>', unsafe_allow_html=True)
        with col3:
            if st.button("Next ➡️", disabled=st.session_state.current_page >= total_pages, use_container_width=True):
                st.session_state.current_page += 1
                st.rerun()
        
        start_idx = (st.session_state.current_page - 1) * students_per_page
        end_idx = min(start_idx + students_per_page, total_students)
        students_list = list(st.session_state.students.items())
        
        for i in range(start_idx, end_idx):
            sid, data = students_list[i]
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f'<div class="student-card">🎓 <strong>{data["name"]}</strong> (ID: {sid})</div>', unsafe_allow_html=True)
            with col2:
                if st.button("✏️", key=f"edit_all_{sid}", help="Edit", use_container_width=True):
                    st.session_state[f"editing_{sid}"] = True
                    st.rerun()
            with col3:
                if st.button("🗑️", key=f"del_all_{sid}", help="Delete", use_container_width=True):
                    if delete_student(sid):
                        st.session_state.students = load_students()
                        st.markdown('<div class="success-box">✅ Deleted</div>', unsafe_allow_html=True)
                        time.sleep(1)
                        st.rerun()
    else:
        st.markdown('<div class="info-box">ℹ️ No students registered yet. Register students in the <strong>Register</strong> tab.</div>', unsafe_allow_html=True)

# Reports Tab
elif tab_selection == "📈 Reports":
    st.markdown('<div class="section-header">📈 Comprehensive Reports</div>', unsafe_allow_html=True)
    
    report_type = st.selectbox("📊 Select Report Type", [
        "📊 Attendance Summary by Event",
        "👥 Student Attendance History",
        "📅 Daily Attendance Report",
        "📈 Attendance Trends",
        "🎯 Event Participation Rate",
        "⏰ Time In/Out Analysis",
        "📋 Complete Attendance Log",
        "🔢 Multiple Check-ins Report"
    ])
    
    if report_type == "📊 Attendance Summary by Event":
        events = get_all_events()
        if events:
            selected_event = st.selectbox("Select Event", [e['event_name'] for e in events])
            if selected_event:
                records = get_attendance_summary(selected_event)
                if records:
                    # Group by student
                    student_summary = {}
                    for record in records:
                        sid = record['student_id']
                        if sid not in student_summary:
                            student_summary[sid] = {
                                'name': record['student_name'],
                                'time_in_count': 0,
                                'time_out_count': 0,
                                'dates': set()
                            }
                        if record.get('attendance_type') == 'time_in':
                            student_summary[sid]['time_in_count'] += 1
                        if record.get('attendance_type') == 'time_out':
                            student_summary[sid]['time_out_count'] += 1
                        student_summary[sid]['dates'].add(str(record['date']))
                    
                    summary_data = []
                    for sid, data in student_summary.items():
                        summary_data.append({
                            'Student ID': sid,
                            'Student Name': data['name'],
                            'Days Attended': len(data['dates']),
                            'Total Time In': data['time_in_count'],
                            'Total Time Out': data['time_out_count']
                        })
                    
                    df = pd.DataFrame(summary_data)
                    st.dataframe(df, use_container_width=True)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Students", len(student_summary))
                    with col2:
                        st.metric("Total Records", len(records))
                    with col3:
                        total_time_in = sum(d['time_in_count'] for d in student_summary.values())
                        st.metric("Total Time In", total_time_in)
                    with col4:
                        total_time_out = sum(d['time_out_count'] for d in student_summary.values())
                        st.metric("Total Time Out", total_time_out)
                    
                    st.download_button("📥 Download Report", df.to_csv(index=False), 
                                     f"summary_{selected_event}_{datetime.date.today()}.csv", "text/csv", use_container_width=True)
                else:
                    st.markdown('<div class="info-box">ℹ️ No attendance records for this event</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="info-box">ℹ️ No events available</div>', unsafe_allow_html=True)
    
    elif report_type == "👥 Student Attendance History":
        search = st.text_input("🔎 Search Student", placeholder="Enter ID or name...")
        if search:
            results = search_students(search)
            if results:
                selected = st.selectbox("Select Student", [f"{r['student_name']} ({r['student_id']})" for r in results])
                if selected:
                    student_id = selected.split('(')[1].strip(')')
                    records = get_student_attendance(student_id)
                    if records:
                        # Create detailed report
                        report_data = []
                        for record in records:
                            report_data.append({
                                'Date': str(record['date']),
                                'Event': record['event_name'],
                                'Type': record.get('attendance_type', 'N/A'),
                                'Time In': str(record.get('time_in', 'N/A')),
                                'Time Out': str(record.get('time_out', 'N/A')),
                                'Timestamp': str(record['timestamp'])
                            })
                        
                        df = pd.DataFrame(report_data)
                        st.dataframe(df, use_container_width=True)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Records", len(records))
                        with col2:
                            unique_events = len(set(r['event_name'] for r in records))
                            st.metric("Events Attended", unique_events)
                        with col3:
                            time_in_count = sum(1 for r in records if r.get('attendance_type') == 'time_in')
                            st.metric("Time In Count", time_in_count)
                        
                        st.download_button("📥 Download", df.to_csv(index=False),
                                         f"student_{student_id}_history.csv", "text/csv", use_container_width=True)
                    else:
                        st.markdown('<div class="info-box">ℹ️ No attendance records found</div>', unsafe_allow_html=True)
    
    elif report_type == "📅 Daily Attendance Report":
        selected_date = st.date_input("📅 Select Date", datetime.date.today())
        all_records = get_all_attendance_records()
        date_str = selected_date.strftime("%Y-%m-%d")
        daily_records = [r for r in all_records if str(r.get('date')) == date_str]
        
        if daily_records:
            report_data = []
            for record in daily_records:
                report_data.append({
                    'Student ID': record['student_id'],
                    'Student Name': record['student_name'],
                    'Event': record['event_name'],
                    'Type': record.get('attendance_type', 'N/A'),
                    'Time In': str(record.get('time_in', 'N/A')),
                    'Time Out': str(record.get('time_out', 'N/A'))
                })
            
            df = pd.DataFrame(report_data)
            st.dataframe(df, use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Records", len(daily_records))
            with col2:
                unique_students = len(set(r['student_id'] for r in daily_records))
                st.metric("Unique Students", unique_students)
            with col3:
                events_count = len(set(r['event_name'] for r in daily_records))
                st.metric("Events", events_count)
            
            st.download_button("📥 Download", df.to_csv(index=False),
                             f"daily_{date_str}.csv", "text/csv", use_container_width=True)
        else:
            st.markdown('<div class="info-box">ℹ️ No attendance records for this date</div>', unsafe_allow_html=True)
    
    elif report_type == "📈 Attendance Trends":
        all_records = get_all_attendance_records()
        if all_records:
            df = pd.DataFrame(all_records)
            df['date'] = pd.to_datetime(df['date'])
            
            st.markdown("#### 📊 Daily Attendance Trend")
            trend_df = df.groupby('date').size().reset_index(name='count')
            st.line_chart(trend_df.set_index('date'), height=400)
            
            st.markdown("#### 📊 Attendance by Event")
            event_df = df.groupby('event_name').size().reset_index(name='count')
            st.bar_chart(event_df.set_index('event_name'), height=400)
            
            st.markdown("#### 📊 Time In vs Time Out")
            type_df = df.groupby('attendance_type').size().reset_index(name='count')
            st.bar_chart(type_df.set_index('attendance_type'), height=300)
        else:
            st.markdown('<div class="info-box">ℹ️ No data available for trends</div>', unsafe_allow_html=True)
    
    elif report_type == "🎯 Event Participation Rate":
        events = get_all_events()
        total_students = len(st.session_state.students)
        
        if events and total_students > 0:
            participation_data = []
            for event in events:
                records = get_attendance_summary(event['event_name'])
                unique_students = len(set(r['student_id'] for r in records))
                rate = (unique_students / total_students) * 100
                time_in_count = sum(1 for r in records if r.get('attendance_type') == 'time_in')
                time_out_count = sum(1 for r in records if r.get('attendance_type') == 'time_out')
                
                participation_data.append({
                    'Event': event['event_name'],
                    'Date': str(event['event_date']),
                    'Students Attended': unique_students,
                    'Total Students': total_students,
                    'Participation Rate (%)': round(rate, 2),
                    'Time In Records': time_in_count,
                    'Time Out Records': time_out_count
                })
            
            df = pd.DataFrame(participation_data)
            st.dataframe(df, use_container_width=True)
            st.bar_chart(df.set_index('Event')['Participation Rate (%)'], height=400)
            st.download_button("📥 Download", df.to_csv(index=False),
                             f"participation_{datetime.date.today()}.csv", "text/csv", use_container_width=True)
        else:
            st.markdown('<div class="info-box">ℹ️ No data available</div>', unsafe_allow_html=True)
    
    elif report_type == "⏰ Time In/Out Analysis":
        if st.session_state.current_event:
            records = get_attendance_summary(st.session_state.current_event)
            if records:
                # Group by student
                student_analysis = {}
                for record in records:
                    sid = record['student_id']
                    if sid not in student_analysis:
                        student_analysis[sid] = {
                            'name': record['student_name'],
                            'time_in': [],
                            'time_out': []
                        }
                    if record.get('attendance_type') == 'time_in' and record.get('time_in'):
                        student_analysis[sid]['time_in'].append(f"{record['date']} {record['time_in']}")
                    if record.get('attendance_type') == 'time_out' and record.get('time_out'):
                        student_analysis[sid]['time_out'].append(f"{record['date']} {record['time_out']}")
                
                analysis_data = []
                for sid, data in student_analysis.items():
                    analysis_data.append({
                        'Student ID': sid,
                        'Student Name': data['name'],
                        'Time In Count': len(data['time_in']),
                        'Time Out Count': len(data['time_out']),
                        'Balance': len(data['time_in']) - len(data['time_out'])
                    })
                
                df = pd.DataFrame(analysis_data)
                st.dataframe(df, use_container_width=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    total_in = df['Time In Count'].sum()
                    st.metric("Total Time In", total_in)
                with col2:
                    total_out = df['Time Out Count'].sum()
                    st.metric("Total Time Out", total_out)
                with col3:
                    balanced = len(df[df['Balance'] == 0])
                    st.metric("Balanced Records", balanced)
                
                st.download_button("📥 Download", df.to_csv(index=False),
                                 f"analysis_{st.session_state.current_event}.csv", "text/csv", use_container_width=True)
            else:
                st.markdown('<div class="info-box">ℹ️ No records for current event</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="warning-box">⚠️ Please select an event first</div>', unsafe_allow_html=True)
    
    elif report_type == "📋 Complete Attendance Log":
        all_records = get_all_attendance_records()
        if all_records:
            log_data = []
            for record in all_records:
                log_data.append({
                    'ID': record.get('id', 'N/A'),
                    'Student ID': record['student_id'],
                    'Student Name': record['student_name'],
                    'Event': record['event_name'],
                    'Date': str(record['date']),
                    'Type': record.get('attendance_type', 'N/A'),
                    'Time In': str(record.get('time_in', 'N/A')),
                    'Time Out': str(record.get('time_out', 'N/A')),
                    'Timestamp': str(record['timestamp'])
                })
            
            df = pd.DataFrame(log_data)
            st.dataframe(df, use_container_width=True)
            st.metric("Total Records in System", len(all_records))
            st.download_button("📥 Download Complete Log", df.to_csv(index=False),
                             f"complete_log_{datetime.date.today()}.csv", "text/csv", use_container_width=True)
        else:
            st.markdown('<div class="info-box">ℹ️ No attendance records available</div>', unsafe_allow_html=True)
    
    elif report_type == "🔢 Multiple Check-ins Report":
        st.markdown("### 🔢 Students with Multiple Check-ins")
        all_records = get_all_attendance_records()
        if all_records:
            # Group by student, event, and date
            multi_checkins = {}
            for record in all_records:
                key = (record['student_id'], record['event_name'], str(record['date']))
                if key not in multi_checkins:
                    multi_checkins[key] = {
                        'name': record['student_name'],
                        'time_in': [],
                        'time_out': []
                    }
                if record.get('attendance_type') == 'time_in':
                    multi_checkins[key]['time_in'].append(str(record.get('time_in', '')))
                if record.get('attendance_type') == 'time_out':
                    multi_checkins[key]['time_out'].append(str(record.get('time_out', '')))
            
            # Filter for multiple check-ins
            report_data = []
            for (sid, event, date), data in multi_checkins.items():
                in_count = len(data['time_in'])
                out_count = len(data['time_out'])
                if in_count > 1 or out_count > 1:
                    report_data.append({
                        'Student ID': sid,
                        'Student Name': data['name'],
                        'Event': event,
                        'Date': date,
                        'Time In Count': in_count,
                        'Time Out Count': out_count,
                        'Time In Times': ', '.join(data['time_in']),
                        'Time Out Times': ', '.join(data['time_out'])
                    })
            
            if report_data:
                df = pd.DataFrame(report_data)
                st.dataframe(df, use_container_width=True)
                st.markdown(f'<div class="info-box">📊 Found <strong>{len(report_data)}</strong> instances of multiple check-ins</div>', unsafe_allow_html=True)
                st.download_button("📥 Download Report", df.to_csv(index=False),
                                 f"multiple_checkins_{datetime.date.today()}.csv", "text/csv", use_container_width=True)
            else:
                st.markdown('<div class="info-box">ℹ️ No multiple check-ins found</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="info-box">ℹ️ No attendance data available</div>', unsafe_allow_html=True)

# Settings Tab
elif tab_selection == "⚙️ Settings":
    st.markdown('<div class="section-header">⚙️ System Settings</div>', unsafe_allow_html=True)
    
    st.markdown("### 📊 System Statistics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{len(st.session_state.students)}</div><div class="metric-label">👥 Students</div></div>', unsafe_allow_html=True)
    with col2:
        events = get_all_events()
        st.markdown(f'<div class="metric-card"><div class="metric-value">{len(events)}</div><div class="metric-label">📅 Events</div></div>', unsafe_allow_html=True)
    with col3:
        all_records = get_all_attendance_records()
        st.markdown(f'<div class="metric-card"><div class="metric-value">{len(all_records)}</div><div class="metric-label">📝 Records</div></div>', unsafe_allow_html=True)
    with col4:
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="font-size: 1.8rem;">{current_time}</div><div class="metric-label">🕐 Time</div></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("### ℹ️ System Information")
    st.markdown(f'''
    <div class="info-box">
        <strong>📊 System Status:</strong> ✅ Running<br>
        <strong>💾 Storage:</strong> MySQL Database<br>
        <strong>🎯 Active Event:</strong> {st.session_state.current_event or "None"}<br>
        <strong>👤 Logged in as:</strong> {st.session_state.username}<br>
        <strong>📅 Current Date:</strong> {datetime.date.today().strftime("%B %d, %Y")}
    </div>
    ''', unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("### 📖 System Guide")
    with st.expander("📘 How to Use This System", expanded=False):
        st.markdown("""
        #### 🚀 Getting Started
        
        **1. Create an Event** 📅
        - Navigate to the **Events** tab
        - Click "Create New Event"
        - Fill in event name, date, and description
        - Click "Select" to make it active
        
        **2. Register Students** 👥
        - Go to the **Register** tab
        - Enter Student ID and Name
        - Choose upload photo or use webcam
        - Capture clear front-facing photo
        
        **3. Take Attendance** ✅
        - Ensure an event is active
        - Go to **Attendance** tab
        - Select Time In or Time Out
        - Use photo upload or live webcam
        - Students can check in/out multiple times per day
        
        **4. View Records** 📋
        - Access **Records** tab
        - Search specific students
        - View all attendance for active event
        - Download CSV reports
        
        **5. Manage Students** 🔍
        - Use **Manage** tab
        - Search, edit, or delete students
        - View attendance history per student
        
        **6. Generate Reports** 📈
        - Visit **Reports** tab
        - Choose from 8 report types
        - Analyze attendance patterns
        - Export data for further analysis
        
        #### 💡 Pro Tips
        - 🌟 **Multiple Check-ins**: Students can mark Time In/Out multiple times per day
        - 📸 **Photo Quality**: Use good lighting for better recognition
        - 💾 **Regular Backups**: Download reports regularly
        - 🎯 **Active Event**: Always select an event before marking attendance
        - 📊 **Track Patterns**: Use the Multiple Check-ins Report to see detailed patterns
        """)
    
    with st.expander("🔧 Database Schema Information", expanded=False):
        st.markdown("""
        #### Required MySQL Tables
        
        ```sql
        -- Students Table
        CREATE TABLE students (
            student_id VARCHAR(50) PRIMARY KEY,
            student_name VARCHAR(100) NOT NULL,
            face_features LONGBLOB NOT NULL
        );
        
        -- Events Table
        CREATE TABLE events (
            id INT AUTO_INCREMENT PRIMARY KEY,
            event_name VARCHAR(200) NOT NULL,
            event_date DATE NOT NULL,
            event_description TEXT,
            created_at DATETIME NOT NULL
        );
        
        -- Attendance Records Table
        CREATE TABLE attendance_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id VARCHAR(50) NOT NULL,
            student_name VARCHAR(100) NOT NULL,
            event_name VARCHAR(200) NOT NULL,
            timestamp DATETIME NOT NULL,
            date DATE NOT NULL,
            time_in TIME,
            time_out TIME,
            attendance_type VARCHAR(20)
        );
        ```
        
        #### Database Configuration
        Set environment variables or Streamlit secrets:
        - `DB_HOST`: Database host (default: localhost)
        - `DB_USER`: Database user (default: root)
        - `DB_PASSWORD`: Database password
        - `DB_NAME`: Database name (default: attendance_system)
        - `DB_PORT`: Database port (default: 3306)
        """)
    
    with st.expander("🎨 Features Overview", expanded=False):
        st.markdown("""
        #### ✨ Key Features
        
        - 🎯 **Face Recognition**: Advanced face detection and matching
        - ⏰ **Multiple Check-ins**: Unlimited Time In/Out per day
        - 📊 **Real-time Dashboard**: Live statistics and trends
        - 📈 **8 Report Types**: Comprehensive analytics
        - 🔍 **Smart Search**: Find students and records instantly
        - 💾 **MySQL Storage**: Reliable data persistence
        - 📱 **Responsive Design**: Works on all devices
        - 🎨 **Modern UI**: Beautiful, user-friendly interface
        - 📥 **CSV Export**: Download all reports
        - 🔐 **Secure Login**: Protected admin access
        """)

# Footer
st.markdown("---")
st.markdown(f'''
<div style="text-align: center; color: #666; padding: 2rem; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 12px;">
    <p style="font-size: 1.2rem; font-weight: bold; margin: 0; color: #333;">🎓 TCGC Event Attendance System</p>
    <p style="margin: 0.5rem 0; color: #666;">Powered by Streamlit • OpenCV • MySQL • Face Recognition</p>
    <p style="margin: 0.5rem 0; color: #667eea;"><strong>Active Event:</strong> {st.session_state.current_event or "Not Set"} | <strong>User:</strong> {st.session_state.username}</p>
</div>
''', unsafe_allow_html=True)
