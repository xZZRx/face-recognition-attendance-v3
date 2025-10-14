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
import json
import os

# Page config
st.set_page_config(
    page_title="TCGC Event Attendance System",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #667eea;
    }
    .metric-label {
        font-size: 1rem;
        color: #666;
        margin-top: 0.5rem;
    }
    .event-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }
    .student-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
        color: #333;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .warning-box {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .section-header {
        color: white;
        font-size: 1.5rem;
        margin-bottom: 1rem;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    .sidebar-button {
        width: 100%;
        margin: 0.5rem 0;
    }
    .event-list-item {
        background: #f8f9fa;
        color: #333;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .event-list-item h4 {
        color: #333 !important;
    }
    .attendance-record {
        background: #e9ecef;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.3rem 0;
        color: #333;
    }
</style>
""", unsafe_allow_html=True)

# Data file paths
DATA_DIR = "tcgc_data"
STUDENTS_FILE = os.path.join(DATA_DIR, "students.json")
EVENTS_FILE = os.path.join(DATA_DIR, "events.json")
ATTENDANCE_FILE = os.path.join(DATA_DIR, "attendance.json")

# Ensure data directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Initialize session state
def initialize_session_state():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "students" not in st.session_state:
        st.session_state.students = load_data(STUDENTS_FILE, {})
    if "events" not in st.session_state:
        st.session_state.events = load_data(EVENTS_FILE, [])
    if "current_event" not in st.session_state:
        st.session_state.current_event = ""
    if "attendance_records" not in st.session_state:
        st.session_state.attendance_records = load_data(ATTENDANCE_FILE, [])
    if "webcam_key" not in st.session_state:
        st.session_state.webcam_key = 0
    if "attendance_webcam_key" not in st.session_state:
        st.session_state.attendance_webcam_key = 0
    if "attendance_session" not in st.session_state:
        st.session_state.attendance_session = []

# File I/O functions
def save_data(file_path, data):
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        st.error(f"Error saving data: {e}")

def load_data(file_path, default):
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
                if file_path == STUDENTS_FILE:
                    for sid, sdata in data.items():
                        if sdata.get('features'):
                            data[sid]['features'] = np.array(sdata['features'], dtype=np.float32)
                return data
        return default
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return default

# Login functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    admin_credentials = {
        "admin": hash_password("admin123"),
    }
    return admin_credentials.get(username) == hash_password(password)

def login_page():
    st.markdown("""
    <div class="main-header">
        <h1>🎓 TCGC Event Attendance System</h1>
        <p>Face Recognition for Student Attendance</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 Login")
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="admin")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if check_login(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("✅ Login successful!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials!")
        
        st.info("**Default Credentials:**\nUsername: `admin` | Password: `admin123`")

# Face detection functions
@st.cache_resource
def load_face_detector():
    return cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def detect_faces(image, face_cascade):
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    gray = cv2.equalizeHist(gray)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
    valid_faces = []
    for (x, y, w, h) in faces:
        aspect_ratio = w / h
        if 0.6 <= aspect_ratio <= 1.5:
            valid_faces.append((x, y, x+w, y+h))
    return valid_faces

def extract_face_features(image, face_coords):
    x1, y1, x2, y2 = face_coords
    face_roi = image[y1:y2, x1:x2]
    if face_roi.size == 0:
        return None
    face_roi = cv2.resize(face_roi, (100, 100))
    gray_face = cv2.cvtColor(face_roi, cv2.COLOR_RGB2GRAY)
    features = gray_face.flatten().astype(np.float32)
    features = features / 255.0
    return features

def compare_faces(known_features, unknown_features, threshold=0.5):
    if known_features is None or unknown_features is None:
        return False, 0.0
    dot_product = np.dot(known_features, unknown_features)
    norm_a = np.linalg.norm(known_features)
    norm_b = np.linalg.norm(unknown_features)
    if norm_a == 0 or norm_b == 0:
        return False, 0.0
    similarity = dot_product / (norm_a * norm_b)
    return similarity > threshold, similarity

# Event management
def create_event(event_name, event_date, event_description=""):
    event = {
        'id': len(st.session_state.events) + 1,
        'event_name': event_name,
        'event_date': event_date.strftime("%Y-%m-%d"),
        'event_description': event_description,
        'created_at': datetime.datetime.now().isoformat()
    }
    st.session_state.events.append(event)
    save_data(EVENTS_FILE, st.session_state.events)
    return True

def delete_event(event_id):
    st.session_state.events = [e for e in st.session_state.events if e['id'] != event_id]
    st.session_state.attendance_records = [r for r in st.session_state.attendance_records 
                                          if r.get('event_id') != event_id]
    save_data(EVENTS_FILE, st.session_state.events)
    save_data(ATTENDANCE_FILE, st.session_state.attendance_records)
    return True

# Attendance management
def save_attendance_record(student_id, student_name, event_name, attendance_type="time_in"):
    timestamp = datetime.datetime.now()
    date = timestamp.strftime("%Y-%m-%d")
    time_str = timestamp.strftime("%H:%M:%S")
    
    existing_record = None
    for record in st.session_state.attendance_records:
        if (record['student_id'] == student_id and 
            record['event_name'] == event_name and 
            record['date'] == date):
            existing_record = record
            break
    
    if existing_record and attendance_type == "time_out":
        existing_record['time_out'] = time_str
        existing_record['timestamp'] = timestamp.isoformat()
    else:
        record = {
            'id': len(st.session_state.attendance_records) + 1,
            'student_id': student_id,
            'student_name': student_name,
            'event_name': event_name,
            'date': date,
            'time_in': time_str if attendance_type == "time_in" else None,
            'time_out': time_str if attendance_type == "time_out" else None,
            'timestamp': timestamp.isoformat()
        }
        st.session_state.attendance_records.append(record)
    
    save_data(ATTENDANCE_FILE, st.session_state.attendance_records)
    return True

def get_attendance_summary(event_name):
    return [r for r in st.session_state.attendance_records if r['event_name'] == event_name]

def get_student_attendance(student_id):
    return [r for r in st.session_state.attendance_records if r['student_id'] == student_id]

# Student management
def save_student(student_id, student_name, features):
    st.session_state.students[student_id] = {
        'name': student_name,
        'features': features.tolist() if features is not None else None
    }
    save_data(STUDENTS_FILE, st.session_state.students)
    return True

def update_student(old_id, new_id, new_name):
    if old_id in st.session_state.students:
        student_data = st.session_state.students.pop(old_id)
        st.session_state.students[new_id] = {
            'name': new_name,
            'features': student_data['features']
        }
        save_data(STUDENTS_FILE, st.session_state.students)
        for record in st.session_state.attendance_records:
            if record['student_id'] == old_id:
                record['student_id'] = new_id
                record['student_name'] = new_name
        save_data(ATTENDANCE_FILE, st.session_state.attendance_records)
        return True
    return False

def check_duplicate_student(student_id, student_name, exclude_id=None):
    for sid, data in st.session_state.students.items():
        if sid != exclude_id and (sid == student_id or data['name'] == student_name):
            return (sid, data['name'])
    return None

def delete_student(student_id):
    if student_id in st.session_state.students:
        del st.session_state.students[student_id]
        save_data(STUDENTS_FILE, st.session_state.students)
        return True
    return False

# Initialize session state
initialize_session_state()

# Load face detector
try:
    face_cascade = load_face_detector()
except Exception as e:
    st.error(f"❌ Error loading face detection: {e}")
    st.stop()

# Main app
if not st.session_state.logged_in:
    login_page()
    st.stop()

# Header
st.markdown(f"""
<div class="main-header">
    <h1>🎓 TCGC Event Attendance System</h1>
    <p>Welcome, {st.session_state.username}!</p>
</div>
""", unsafe_allow_html=True)

# Sidebar with tabs
with st.sidebar:
    st.markdown(f"""
    <div style='padding: 1rem; text-align: center;'>
        <h3>Navigation</h3>
        <p>Logged in as: <strong>{st.session_state.username}</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    tab_selection = st.radio(
        "Menu",
        ["📊 Dashboard Overview", "📅 Event Management", "👥 Student Registration", "✅ Take Attendance", 
         "📋 Attendance Records", "🔍 Manage Students", "⚙️ Settings"],
        label_visibility="collapsed"
    )
    
    if st.button("🚪 Logout", key="logout_button", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.current_event = ""
        st.session_state.attendance_session = []
        st.rerun()

# Main content based on tab selection
if tab_selection == "📊 Dashboard Overview":
    st.markdown('<div class="section-header">📊 Dashboard Overview</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">{}</div>
            <div class="metric-label">👥 Total Students</div>
        </div>
        """.format(len(st.session_state.students)), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">{}</div>
            <div class="metric-label">📅 Total Events</div>
        </div>
        """.format(len(st.session_state.events)), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">{}</div>
            <div class="metric-label">📝 Total Records</div>
        </div>
        """.format(len(st.session_state.attendance_records)), unsafe_allow_html=True)
    
    with col4:
        active = "Yes ✅" if st.session_state.current_event else "No ❌"
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value" style="font-size: 1.5rem;">{}</div>
            <div class="metric-label">🎯 Active Event</div>
        </div>
        """.format(active), unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.session_state.current_event:
        st.markdown(f"""
        <div class="event-card">
            <h3>📍 Current Active Event</h3>
            <h2>{st.session_state.current_event}</h2>
        </div>
        """, unsafe_allow_html=True)
        
        today = datetime.date.today().strftime("%Y-%m-%d")
        today_attendance = [r for r in st.session_state.attendance_records 
                          if r['event_name'] == st.session_state.current_event and r['date'] == today]
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📊 Today's Attendance Statistics")
            st.metric("Students Attended Today", len(today_attendance))
            
            if today_attendance:
                time_in_count = sum(1 for r in today_attendance if r.get('time_in'))
                time_out_count = sum(1 for r in today_attendance if r.get('time_out'))
                st.metric("Time In Records", time_in_count)
                st.metric("Time Out Records", time_out_count)
        
        with col2:
            st.subheader("🕐 Recent Activity")
            recent = sorted(st.session_state.attendance_session[-5:], 
                          key=lambda x: x[2] if len(x) > 2 else "", reverse=True)
            if recent:
                for sid, name, time_str, att_type in recent:
                    st.markdown(f"""
                    <div class="student-card">
                        <strong>{name}</strong> - {att_type}<br>
                        <small>🕐 {time_str}</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No recent activity")
    else:
        st.info("ℹ️ No active event selected. Please select an event from the Events tab.")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Attendance Trends")
        if st.session_state.attendance_records:
            df = pd.DataFrame(st.session_state.attendance_records)
            attendance_by_date = df.groupby('date').size().reset_index(name='count')
            st.line_chart(attendance_by_date.set_index('date'))
        else:
            st.info("No attendance data available yet")
    
    with col2:
        st.subheader("🎯 Events Overview")
        if st.session_state.events:
            event_data = []
            for event in st.session_state.events:
                count = len([r for r in st.session_state.attendance_records 
                           if r['event_name'] == event['event_name']])
                event_data.append({'Event': event['event_name'], 'Attendance': count})
            
            if event_data:
                df_events = pd.DataFrame(event_data)
                st.bar_chart(df_events.set_index('Event'))
        else:
            st.info("No events created yet")
    
    st.markdown("---")
    st.subheader("👥 Recently Registered Students")
    if st.session_state.students:
        recent_students = list(st.session_state.students.items())[-5:]
        cols = st.columns(5)
        for idx, (sid, data) in enumerate(recent_students):
            with cols[idx]:
                st.markdown(f"""
                <div class="student-card" style="text-align: center;">
                    <div style="font-size: 2rem;">👤</div>
                    <strong>{data['name']}</strong><br>
                    <small>{sid}</small>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No students registered yet")

elif tab_selection == "📅 Event Management":
    st.markdown('<div class="section-header">📅 Event Management</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("➕ Create New Event")
        with st.form("create_event_form"):
            new_event_name = st.text_input("Event Name", placeholder="e.g., Computer Science Seminar 2024")
            new_event_date = st.date_input("Event Date", value=datetime.date.today())
            new_event_desc = st.text_area("Event Description (Optional)")
            
            if st.form_submit_button("➕ Create Event", use_container_width=True):
                if new_event_name:
                    if create_event(new_event_name, new_event_date, new_event_desc):
                        st.success(f"✅ Event '{new_event_name}' created!")
                        st.session_state.current_event = new_event_name
                        st.rerun()
                else:
                    st.error("❌ Please enter an event name!")
    
    with col2:
        st.subheader("📋 Quick Stats")
        st.metric("Total Events", len(st.session_state.events))
        st.metric("Active Event", "Yes" if st.session_state.current_event else "No")
    
    st.markdown("---")
    st.markdown('<div class="section-header">📋 All Events</div>', unsafe_allow_html=True)
    
    if st.session_state.events:
        for event in st.session_state.events:
            is_active = st.session_state.current_event == event['event_name']
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                badge = "🟢 ACTIVE" if is_active else ""
                st.markdown(f"""
                <div class="event-list-item">
                    <h4 style="color: #333;">📅 {event['event_name']} {badge}</h4>
                    <p style="color: #333;">📆 {event['event_date']}</p>
                    <p style="color: #333;"><small>{event.get('event_description', '')}</small></p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                if st.button("📍 Select", key=f"sel_{event['id']}", use_container_width=True):
                    st.session_state.current_event = event['event_name']
                    st.success(f"✅ Event selected!")
                    st.rerun()
            
            with col3:
                if st.button("🗑️ Delete", key=f"del_{event['id']}", use_container_width=True):
                    if delete_event(event['id']):
                        if st.session_state.current_event == event['event_name']:
                            st.session_state.current_event = ""
                        st.success("✅ Event deleted!")
                        st.rerun()
    else:
        st.info("📋 No events created yet")

elif tab_selection == "👥 Student Registration":
    st.markdown('<div class="section-header">👥 Student Registration</div>', unsafe_allow_html=True)
    
    reg_method = st.radio("Registration Method:", ["📸 Upload Photo", "📹 Use Webcam"], horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        student_id = st.text_input("Student ID", placeholder="e.g., CS-2024-001")
    with col2:
        student_name = st.text_input("Student Name", placeholder="e.g., John Doe")
    
    if student_id and student_name:
        duplicate = check_duplicate_student(student_id, student_name)
        if duplicate:
            st.warning(f"⚠️ Student with ID '{duplicate[0]}' or name '{duplicate[1]}' already exists!")
    
    if reg_method == "📸 Upload Photo":
        uploaded_file = st.file_uploader("Upload student photo", type=["jpg", "png", "jpeg"])
        
        if uploaded_file and student_id and student_name:
            if not check_duplicate_student(student_id, student_name):
                try:
                    pil_image = Image.open(uploaded_file).convert("RGB")
                    image_array = np.array(pil_image)
                    faces = detect_faces(image_array, face_cascade)
                    
                    if faces:
                        face_coords = faces[0]
                        features = extract_face_features(image_array, face_coords)
                        
                        if features is not None:
                            if save_student(student_id, student_name, features):
                                st.success(f"✅ {student_name} registered successfully!")
                                
                                result_image = image_array.copy()
                                x1, y1, x2, y2 = face_coords
                                cv2.rectangle(result_image, (x1, y1), (x2, y2), (0, 255, 0), 3)
                                st.image(result_image, caption=f"Registered: {student_name}", width=300)
                        else:
                            st.error("❌ Could not extract face features")
                    else:
                        st.error("❌ No face detected in photo")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
            else:
                st.error("❌ Student already exists!")
    
    else:
        if not student_id or not student_name:
            st.warning("⚠️ Please enter Student ID and Name first!")
        elif check_duplicate_student(student_id, student_name):
            st.error("❌ Student already exists!")
        else:
            st.info("📹 Position your face and click Capture")
            
            class RegistrationProcessor:
                def __init__(self):
                    self.latest_frame = None
                
                def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
                    img = frame.to_ndarray(format="bgr24")
                    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    self.latest_frame = rgb_img.copy()
                    
                    faces = detect_faces(rgb_img, face_cascade)
                    for face_coords in faces:
                        x1, y1, x2, y2 = face_coords
                        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(img, "Ready!", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    return av.VideoFrame.from_ndarray(img, format="bgr24")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                webrtc_ctx = webrtc_streamer(
                    key=f"reg_{st.session_state.webcam_key}",
                    mode=WebRtcMode.SENDRECV,
                    video_processor_factory=RegistrationProcessor,
                    media_stream_constraints={"video": True, "audio": False},
                    async_processing=True
                )
            
            with col2:
                st.markdown("### 📸 Capture")
                if webrtc_ctx and webrtc_ctx.video_processor:
                    if st.button("📸 Capture & Register", type="primary", use_container_width=True):
                        if webrtc_ctx.video_processor.latest_frame is not None:
                            image_array = webrtc_ctx.video_processor.latest_frame
                            faces = detect_faces(image_array, face_cascade)
                            
                            if faces:
                                features = extract_face_features(image_array, faces[0])
                                if features is not None and save_student(student_id, student_name, features):
                                    st.success(f"✅ {student_name} registered!")
                                    st.balloons()
                                    time.sleep(1)
                                    st.rerun()
                            else:
                                st.error("❌ No face detected!")

elif tab_selection == "✅ Take Attendance":
    st.markdown('<div class="section-header">✅ Take Attendance</div>', unsafe_allow_html=True)
    
    if not st.session_state.current_event:
        st.warning("⚠️ Please select an event first!")
    elif not st.session_state.students:
        st.warning("⚠️ Please register students first!")
    else:
        st.markdown(f"""
        <div class="event-card">
            <h4>📅 Event: {st.session_state.current_event}</h4>
        </div>
        """, unsafe_allow_html=True)
        
        attendance_type = st.radio("Type:", ["⏰ Time In", "🚪 Time Out"], horizontal=True)
        att_method = st.radio("Method:", ["📸 Upload Photo", "📹 Live Webcam"], horizontal=True)
        
        if att_method == "📸 Upload Photo":
            uploaded = st.file_uploader("Upload photo", type=["jpg", "png", "jpeg"], key="att")
            
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
                            best_match = None
                            best_sim = 0
                            
                            for sid, data in st.session_state.students.items():
                                is_match, sim = compare_faces(data["features"], features, 0.4)
                                if is_match and sim > best_sim:
                                    best_sim = sim
                                    best_match = (sid, data["name"])
                            
                            x1, y1, x2, y2 = face_coords
                            if best_match:
                                sid, name = best_match
                                recognized.append((sid, name))
                                cv2.rectangle(result_image, (x1, y1), (x2, y2), (0, 255, 0), 3)
                                cv2.putText(result_image, name, (x1, y1-10), 
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    st.image(result_image, width=500)
                    
                    if recognized:
                        att_type = "time_in" if "In" in attendance_type else "time_out"
                        for sid, name in recognized:
                            if save_attendance_record(sid, name, st.session_state.current_event, att_type):
                                st.success(f"✅ {attendance_type} marked for {name}")
                else:
                    st.warning("No faces detected")
        
        else:
            class AttendanceProcessor:
                def __init__(self):
                    self.latest_frame = None
                
                def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
                    img = frame.to_ndarray(format="bgr24")
                    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    self.latest_frame = rgb_img.copy()
                    
                    faces = detect_faces(rgb_img, face_cascade)
                    for face_coords in faces:
                        x1, y1, x2, y2 = face_coords
                        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    return av.VideoFrame.from_ndarray(img, format="bgr24")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                webrtc_ctx = webrtc_streamer(
                    key=f"att_{st.session_state.attendance_webcam_key}",
                    mode=WebRtcMode.SENDRECV,
                    video_processor_factory=AttendanceProcessor,
                    media_stream_constraints={"video": True, "audio": False},
                    async_processing=True
                )
            
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
                                    best_match = None
                                    best_sim = 0
                                    
                                    for sid, data in st.session_state.students.items():
                                        is_match, sim = compare_faces(data["features"], features, 0.3)
                                        if is_match and sim > best_sim:
                                            best_sim = sim
                                            best_match = (sid, data["name"])
                                    
                                    if best_match:
                                        sid, name = best_match
                                        att_type = "time_in" if "In" in attendance_type else "time_out"
                                        
                                        if save_attendance_record(sid, name, st.session_state.current_event, att_type):
                                            current_time = datetime.datetime.now()
                                            st.session_state.attendance_session.append(
                                                (sid, name, current_time.strftime("%H:%M:%S"), attendance_type)
                                            )
                                            st.success(f"✅ {attendance_type} marked for {name}!")
                                            st.balloons()
                                    else:
                                        st.error("❌ Face not recognized!")
                            else:
                                st.error("❌ No face detected!")
                
                st.markdown("### 📋 Recent Marks")
                if st.session_state.attendance_session:
                    for sid, name, time_str, att_type in st.session_state.attendance_session[-5:]:
                        st.markdown(f"""
                        <div class="student-card">
                            ✅ <strong>{name}</strong><br>
                            <small>{att_type} at {time_str}</small>
                        </div>
                        """, unsafe_allow_html=True)

elif tab_selection == "📋 Attendance Records":
    st.markdown('<div class="section-header">📋 Attendance Records</div>', unsafe_allow_html=True)
    
    # Student search section
    st.markdown("### 🔍 Search Student Attendance")
    search_term = st.text_input("Search by Student ID or Name", placeholder="Enter student ID or name...", key="attendance_search")
    
    if search_term:
        results = [(sid, data) for sid, data in st.session_state.students.items() 
                  if search_term.lower() in sid.lower() or search_term.lower() in data['name'].lower()]
        
        if results:
            st.markdown(f"### Search Results ({len(results)} found)")
            for sid, data in results:
                with st.container():
                    st.markdown(f"""
                    <div class="student-card">
                        <strong>{data['name']}</strong> (ID: {sid})
                    </div>
                    """, unsafe_allow_html=True)
                    # Display attendance records for the student
                    attendance_records = get_student_attendance(sid)
                    if attendance_records:
                        st.markdown("**Events Attended:**")
                        for record in attendance_records:
                            time_in = record.get('time_in', 'N/A')
                            time_out = record.get('time_out', 'Not recorded')
                            st.markdown(f"""
                            <div class="attendance-record">
                                <strong>Event:</strong> {record['event_name']}<br>
                                <strong>Date:</strong> {record['date']}<br>
                                <strong>Time In:</strong> {time_in}<br>
                                <strong>Time Out:</strong> {time_out}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="attendance-record">No events attended</div>', unsafe_allow_html=True)
        else:
            st.info("No students found matching the search term.")
    
    st.markdown("---")
    
    # Existing event-based attendance records
    if st.session_state.current_event:
        records = get_attendance_summary(st.session_state.current_event)
        
        if records:
            st.markdown(f"""
            <div class="event-card">
                <h3>📅 {st.session_state.current_event}</h3>
                <p>Total Records: {len(records)}</p>
            </div>
            """, unsafe_allow_html=True)
            
            for record in records:
                time_in = record.get('time_in', 'N/A')
                time_out = record.get('time_out', 'Not recorded')
                
                st.markdown(f"""
                <div class="student-card">
                    🎓 <strong>{record['student_name']}</strong> (ID: {record['student_id']})<br>
                    📅 Date: {record['date']}<br>
                    ⏰ Time In: {time_in}<br>
                    🚪 Time Out: {time_out}
                </div>
                """, unsafe_allow_html=True)
            
            df = pd.DataFrame(records)
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"attendance_{st.session_state.current_event}_{datetime.date.today()}.csv",
                mime="text/csv"
            )
        else:
            st.info("No attendance records for this event")
    else:
        st.warning("Please select an event first")

elif tab_selection == "🔍 Manage Students":
    st.markdown('<div class="section-header">🔍 Manage Students</div>', unsafe_allow_html=True)
    
    search_term = st.text_input("Search by ID or Name", placeholder="Enter student ID or name...", key="manage_students_search")
    
    if search_term:
        results = [(sid, data) for sid, data in st.session_state.students.items() 
                  if search_term.lower() in sid.lower() or search_term.lower() in data['name'].lower()]
        
        if results:
            st.markdown(f"### Search Results ({len(results)} found)")
            for sid, data in results:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"""
                        <div class="student-card">
                            <strong>{data['name']}</strong> (ID: {sid})
                        </div>
                        """, unsafe_allow_html=True)
                        # Display attendance records for the student
                        attendance_records = get_student_attendance(sid)
                        if attendance_records:
                            st.markdown("**Events Attended:**")
                            for record in attendance_records:
                                st.markdown(f"""
                                <div class="attendance-record">
                                    📅 {record['event_name']} on {record['date']}
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.markdown('<div class="attendance-record">No events attended</div>', unsafe_allow_html=True)
                    with col2:
                        if st.button("✏️ Edit", key=f"edit_stu_{sid}", help="Edit student"):
                            st.session_state[f"editing_{sid}"] = True
                    with col3:
                        if st.button("🗑️ Delete", key=f"del_stu_{sid}", help="Delete student"):
                            if delete_student(sid):
                                st.success(f"✅ Deleted {data['name']}")
                                st.rerun()
                
                if st.session_state.get(f"editing_{sid}", False):
                    with st.form(f"edit_form_{sid}"):
                        new_id = st.text_input("New Student ID", value=sid, key=f"new_id_{sid}")
                        new_name = st.text_input("New Student Name", value=data['name'], key=f"new_name_{sid}")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Save"):
                                if new_id and new_name:
                                    if new_id != sid or new_name != data['name']:
                                        duplicate = check_duplicate_student(new_id, new_name, exclude_id=sid)
                                        if not duplicate:
                                            if update_student(sid, new_id, new_name):
                                                st.success(f"✅ Updated student to {new_name} ({new_id})")
                                                st.session_state[f"editing_{sid}"] = False
                                                st.rerun()
                                        else:
                                            st.error(f"❌ ID '{duplicate[0]}' or name '{duplicate[1]}' already exists!")
                                    else:
                                        st.session_state[f"editing_{sid}"] = False
                                        st.rerun()
                                else:
                                    st.error("❌ Please fill in all fields")
                        with col2:
                            if st.form_submit_button("Cancel"):
                                st.session_state[f"editing_{sid}"] = False
                                st.rerun()
    
    st.markdown("---")
    st.markdown('<div class="section-header">👥 All Students</div>', unsafe_allow_html=True)
    
    if st.session_state.students:
        students_per_page = 10
        total_students = len(st.session_state.students)
        total_pages = max(1, (total_students - 1) // students_per_page + 1)
        
        if "current_page" not in st.session_state:
            st.session_state.current_page = 1
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("⬅️ Previous") and st.session_state.current_page > 1:
                st.session_state.current_page -= 1
                st.rerun()
        with col2:
            st.write(f"Page {st.session_state.current_page} of {total_pages}")
        with col3:
            if st.button("Next ➡️") and st.session_state.current_page < total_pages:
                st.session_state.current_page += 1
                st.rerun()
        
        start_idx = (st.session_state.current_page - 1) * students_per_page
        end_idx = min(start_idx + students_per_page, total_students)
        
        students_list = list(st.session_state.students.items())
        for i in range(start_idx, end_idx):
            sid, data = students_list[i]
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"""
                <div class="student-card">
                    🎓 <strong>{data['name']}</strong> (ID: {sid})
                </div>
                """, unsafe_allow_html=True)
            with col2:
                if st.button("✏️", key=f"edit_all_{sid}", help="Edit"):
                    st.session_state[f"editing_{sid}"] = True
            with col3:
                if st.button("🗑️", key=f"del_all_{sid}", help="Delete"):
                    if delete_student(sid):
                        st.success(f"✅ Deleted")
                        st.rerun()
            
            if st.session_state.get(f"editing_{sid}", False):
                with st.form(f"edit_form_all_{sid}"):
                    new_id = st.text_input("New Student ID", value=sid, key=f"new_id_all_{sid}")
                    new_name = st.text_input("New Student Name", value=data['name'], key=f"new_name_all_{sid}")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Save"):
                            if new_id and new_name:
                                if new_id != sid or new_name != data['name']:
                                    duplicate = check_duplicate_student(new_id, new_name, exclude_id=sid)
                                    if not duplicate:
                                        if update_student(sid, new_id, new_name):
                                            st.success(f"✅ Updated student to {new_name} ({new_id})")
                                            st.session_state[f"editing_{sid}"] = False
                                            st.rerun()
                                    else:
                                        st.error(f"❌ ID '{duplicate[0]}' or name '{duplicate[1]}' already exists!")
                                else:
                                    st.session_state[f"editing_{sid}"] = False
                                    st.rerun()
                            else:
                                st.error("❌ Please fill in all fields")
                    with col2:
                        if st.form_submit_button("Cancel"):
                            st.session_state[f"editing_{sid}"] = False
                            st.rerun()

elif tab_selection == "⚙️ Settings":
    st.markdown('<div class="section-header">⚙️ System Settings</div>', unsafe_allow_html=True)
    
    st.subheader("💾 Data Management")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### Backup Data")
        if st.button("📥 Create Backup", use_container_width=True):
            backup_data = {
                'students': {},
                'events': st.session_state.events,
                'attendance_records': st.session_state.attendance_records,
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            for sid, data in st.session_state.students.items():
                backup_data['students'][sid] = {
                    'name': data['name'],
                    'features': data['features'].tolist() if data['features'] is not None else None
                }
            
            backup_json = json.dumps(backup_data, indent=2)
            st.download_button(
                label="📥 Download Backup",
                data=backup_json,
                file_name=f"tcgc_backup_{datetime.date.today()}.json",
                mime="application/json"
            )
            st.success("✅ Backup ready!")
    
    with col2:
        st.markdown("### Restore Data")
        uploaded_backup = st.file_uploader("Upload backup file", type=['json'])
        if uploaded_backup:
            try:
                backup_data = json.load(uploaded_backup)
                
                st.session_state.students = {}
                for sid, data in backup_data.get('students', {}).items():
                    features = np.array(data['features']) if data['features'] else None
                    st.session_state.students[sid] = {
                        'name': data['name'],
                        'features': features
                    }
                
                st.session_state.events = backup_data.get('events', [])
                st.session_state.attendance_records = backup_data.get('attendance_records', [])
                
                save_data(STUDENTS_FILE, st.session_state.students)
                save_data(EVENTS_FILE, st.session_state.events)
                save_data(ATTENDANCE_FILE, st.session_state.attendance_records)
                
                st.success("✅ Data restored successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error restoring backup: {e}")
    
    with col3:
        st.markdown("### Clear All Data")
        if st.button("🗑️ Clear Data", type="secondary", use_container_width=True):
            with st.form("confirm_clear"):
                st.warning("⚠️ This will delete ALL data!")
                confirm = st.text_input("Type 'DELETE' to confirm:")
                
                if st.form_submit_button("Confirm"):
                    if confirm == "DELETE":
                        st.session_state.students = {}
                        st.session_state.events = []
                        st.session_state.attendance_records = []
                        st.session_state.current_event = ""
                        st.session_state.attendance_session = []
                        save_data(STUDENTS_FILE, {})
                        save_data(EVENTS_FILE, [])
                        save_data(ATTENDANCE_FILE, [])
                        st.success("✅ All data cleared!")
                        st.rerun()
                    else:
                        st.error("Please type 'DELETE' to confirm")
    
    st.markdown("---")
    
    st.subheader("📊 System Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Total Students", len(st.session_state.students))
    with col2:
        st.metric("📅 Total Events", len(st.session_state.events))
    with col3:
        st.metric("📝 Total Records", len(st.session_state.attendance_records))
    with col4:
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        st.metric("🕐 Current Time", current_time)
    
    st.markdown("---")
    
    st.subheader("ℹ️ System Information")
    st.info(f"""
    **System Status:** ✅ Running  
    **Storage:** Local JSON Files  
    **Active Event:** {st.session_state.current_event or 'None'}  
    **Logged in as:** {st.session_state.username}
    """)
    
    st.markdown("---")
    st.markdown("### 📖 Quick Guide")
    
    with st.expander("How to use this system"):
        st.markdown("""
        1. **Create an Event** - Go to Events tab and create a new event
        2. **Register Students** - Use the Register Students tab to add students with face recognition
        3. **Take Attendance** - Select an event and use webcam/photo to mark attendance
        4. **View Records** - Check attendance records in the View Records tab
        5. **Manage Students** - Edit or delete students in the Manage Students tab
        6. **Backup Data** - Regularly backup your data from Settings tab
        
        **Tips:**
        - Ensure good lighting for face detection
        - Position face clearly in camera view
        - Use clear, front-facing photos for registration
        - Backup your data regularly to prevent loss
        """)

# Footer
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p>🎓 <strong>TCGC Event Attendance System</strong></p>
    <p>Built with Streamlit • OpenCV • Face Recognition</p>
    <p>Active Event: <strong>{st.session_state.current_event or 'Not Set'}</strong> | 
       Logged in as: <strong>{st.session_state.username}</strong></p>
</div>
""", unsafe_allow_html=True)