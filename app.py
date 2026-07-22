import streamlit as st
import os
import sys
import datetime
import subprocess
from dotenv import load_dotenv
load_dotenv(override=True)

from core.pdf_parser import extract_text_from_pdf
from core.ai_analyzer import analyze_resume
import core.database as db

st.set_page_config(page_title="AI Resume Analyzer", page_icon="👔", layout="wide")

# Initialize DB tables on launch
db.init_db()

custom_css = """
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#1e3c72">
    <meta name="application-name" content="AI Resume Analyzer">
    <link rel="manifest" href="data:application/manifest+json,%7B%22name%22%3A%22AI%20Resume%20Analyzer%22%2C%22short_name%22%3A%22ResumeAI%22%2C%22start_url%22%3A%22%2F%22%2C%22display%22%3A%22standalone%22%2C%22background_color%22%3A%22%231e3c72%22%2C%22theme_color%22%3A%22%231e3c72%22%7D">
    <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="collapsedControl"] {display: none;}
        
        .main-header {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 24px;
            border-radius: 12px;
            color: white;
            text-align: center;
            margin-bottom: 24px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .key-badge {
            background-color: #2e7d32;
            color: white;
            padding: 12px 24px;
            font-size: 24px;
            font-weight: bold;
            border-radius: 8px;
            letter-spacing: 2px;
            display: inline-block;
            margin: 10px 0;
            border: 2px dashed #a5d6a7;
        }

        .status-badge-published {
            background-color: #e8f5e9;
            color: #2e7d32;
            padding: 6px 12px;
            border-radius: 20px;
            font-weight: 600;
        }
        
        .status-badge-unpublished {
            background-color: #fff3e0;
            color: #ef6c00;
            padding: 6px 12px;
            border-radius: 20px;
            font-weight: 600;
        }

        /* Mobile Responsive & Native PWA App Enhancements */
        @media only screen and (max-width: 600px) {
            .main-header {
                padding: 16px;
                border-radius: 8px;
            }
            .main-header h1 {
                font-size: 20px !important;
            }
            .key-badge {
                font-size: 16px !important;
                padding: 8px 14px !important;
                word-break: break-all;
            }
            .stButton > button {
                width: 100% !important;
                min-height: 48px !important;
                font-size: 16px !important;
            }
        }
    </style>
"""

def get_base_url():
    env_url = os.environ.get("BASE_URL")
    if env_url:
        return env_url.rstrip("/")
    try:
        if hasattr(st, "context") and hasattr(st.context, "headers"):
            headers = st.context.headers
            host = headers.get("Host") or headers.get("host")
            if host:
                scheme = "https" if ("localhost" not in host and "127.0.0.1" not in host) else "http"
                return f"{scheme}://{host}"
    except Exception:
        pass
    return "http://localhost:8501"


def check_is_published(job_data):
    if not job_data:
        return False
    if job_data.get("is_published"):
        return True
    sched_str = job_data.get("publish_schedule")
    if sched_str:
        try:
            sched_dt = datetime.datetime.fromisoformat(sched_str)
            if datetime.datetime.now() >= sched_dt:
                return True
        except Exception:
            pass
    return False

def render_hr_auth_page():
    st.markdown("""
        <div class="main-header">
            <h1>👔 HR & Recruiter Portal</h1>
            <p>Sign in or create an HR account to manage job listings and evaluate candidate resumes.</p>
        </div>
    """, unsafe_allow_html=True)
    
    tab_login, tab_register = st.tabs(["🔑 HR Login", "📝 Register HR Account"])
    
    with tab_login:
        st.subheader("Log in to your HR Dashboard")
        with st.form("hr_login_form"):
            email = st.text_input("HR Email Address *")
            password = st.text_input("Password *", type="password")
            login_btn = st.form_submit_button("Log In", use_container_width=True)
            
            if login_btn:
                if not email or not password:
                    st.error("Please fill in both email and password.")
                else:
                    user = db.authenticate_user(email, password)
                    if user:
                        st.session_state["hr_user"] = user
                        st.success(f"Welcome back, {user['hr_name']}!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid Email or Password. Please check your credentials or register.")

    with tab_register:
        st.subheader("Create a New HR Account")
        with st.form("hr_register_form"):
            company_name = st.text_input("Company / Organization Name *")
            hr_name = st.text_input("Full Name (HR Recruiter) *")
            reg_email = st.text_input("Work Email Address *")
            reg_pass = st.text_input("Password *", type="password")
            confirm_pass = st.text_input("Confirm Password *", type="password")
            
            register_btn = st.form_submit_button("Register Account", use_container_width=True)
            
            if register_btn:
                if not company_name or not hr_name or not reg_email or not reg_pass:
                    st.error("Please fill in all required fields.")
                elif reg_pass != confirm_pass:
                    st.error("Passwords do not match!")
                elif len(reg_pass) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    success, res = db.register_user(company_name, hr_name, reg_email, reg_pass)
                    if success:
                        st.session_state["hr_user"] = res
                        st.success("🎉 Account created successfully! Logging you in...")
                        st.rerun()
                    else:
                        st.error(f"❌ {res}")

def render_admin_dashboard():
    user = st.session_state["hr_user"]
    
    col_user, col_logout = st.columns([4, 1])
    with col_user:
        st.markdown(f"👤 Logged in as **{user['hr_name']}** ({user['company_name']}) | `{user['email']}`")
    with col_logout:
        if st.button("🚪 Logout", use_container_width=True):
            del st.session_state["hr_user"]
            st.rerun()

    st.markdown(f"""
        <div class="main-header">
            <h1>👔 {user['company_name']} - HR Dashboard</h1>
            <p>Create jobs, track applicants, and manage AI evaluation publishing.</p>
        </div>
    """, unsafe_allow_html=True)
    
    if not os.environ.get("NVIDIA_API_KEY"):
        st.error("⚠️ NVIDIA_API_KEY is not set in environment variables. AI analysis will fail until it is configured!")

    user_jobs = db.get_user_jobs(user["id"])
    
    st.sidebar.subheader("Job Listings")
    
    job_options = {"➕ Create New Job Posting": "NEW"}
    for j in user_jobs:
        job_options[f"📋 {j['job_title']} (ID: {j['id']})"] = j["id"]
        
    selected_job_label = st.selectbox("Select Job Listing:", list(job_options.keys()))
    selected_job_id = job_options[selected_job_label]
    
    if selected_job_id == "NEW":
        st.subheader("Create a New Job Posting")
        with st.form("create_job_form"):
            new_title = st.text_input("Job Title *", placeholder="e.g. Senior Python Developer")
            new_qual = st.text_area("Detailed Requirements & Qualifications *", height=200, 
                                     placeholder="List key technical skills, experience required, education, responsibilities, etc.")
            
            create_btn = st.form_submit_button("Publish Job Posting", use_container_width=True)
            if create_btn:
                if not new_title or not new_qual:
                    st.error("Please fill in Job Title and Qualifications.")
                else:
                    new_id = db.create_job(user["id"], new_title, new_qual)
                    st.success(f"✅ Job '{new_title}' created successfully! (Job ID: {new_id})")
                    st.rerun()
    else:
        current_job = db.get_job_by_id(selected_job_id)
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "📝 Job Qualifications", 
            "🔗 Application Link & Publishing", 
            "📊 Candidate Applications",
            "🚀 Public Hosting & Mobile App Guide"
        ])
        
        with tab1:
            st.subheader(f"Edit Qualifications for: {current_job['job_title']}")
            with st.form("edit_job_form"):
                job_title = st.text_input("Job Title", value=current_job["job_title"])
                qualifications = st.text_area("Detailed Requirements", value=current_job["qualifications"], height=220)
                
                saved = st.form_submit_button("Save Changes", use_container_width=True)
                if saved:
                    db.update_job_details(selected_job_id, job_title, qualifications)
                    st.success("✅ Job details updated!")
                    st.rerun()

        with tab2:
            st.subheader("Shareable Application Link & Publishing")
            base_url = get_base_url()
            application_link = f"{base_url}/?job_id={current_job['id']}"
            
            st.success("**Candidate Application Link:**")
            st.code(application_link, language="text")
            st.info("💡 Share this link with candidates to allow them to apply specifically for this job.")
            
            st.markdown("---")
            st.subheader("📢 Result Announcement & Schedule Control")
            
            sched_val = current_job.get("publish_schedule")
            default_date = datetime.date.today()
            default_time = datetime.time(10, 0)
            if sched_val:
                try:
                    dt_obj = datetime.datetime.fromisoformat(sched_val)
                    default_date = dt_obj.date()
                    default_time = dt_obj.time()
                except Exception:
                    pass

            st.markdown("#### 📅 Schedule Result Announcement Date & Time")
            col_d, col_t = st.columns(2)
            with col_d:
                sched_date = st.date_input("Announcement Date", value=default_date)
            with col_t:
                sched_time = st.time_input("Announcement Time", value=default_time)
                
            if st.button("Save Announcement Schedule", use_container_width=True):
                combined_dt = datetime.datetime.combine(sched_date, sched_time)
                db.update_job_publishing(selected_job_id, current_job.get("is_published", False), combined_dt.isoformat())
                st.success(f"✅ Result Announcement Schedule set to: **{combined_dt.strftime('%B %d, %Y at %I:%M %p')}**")
                st.rerun()

            st.markdown("---")
            st.markdown("#### ⚙️ Publishing Status & Manual Override")
            
            is_auto_published = check_is_published(current_job)
            manual_status = bool(current_job.get("is_published", 0))
            
            if is_auto_published:
                st.markdown("Current Status: <span class='status-badge-published'>🟢 PUBLISHED</span>", unsafe_allow_html=True)
                st.write("Candidates can now check their evaluation status using their Unique Candidate Key.")
            else:
                st.markdown("Current Status: <span class='status-badge-unpublished'>🟠 UNPUBLISHED</span>", unsafe_allow_html=True)
                if sched_val:
                    try:
                        dt_fmt = datetime.datetime.fromisoformat(sched_val).strftime('%B %d, %Y at %I:%M %p')
                        st.write(f"Results are scheduled to automatically publish on **{dt_fmt}**.")
                    except Exception:
                        pass
                else:
                    st.write("Results are currently hidden from candidates.")
                
            new_status = st.toggle("Publish Immediately (Manual Override)", value=manual_status)
            if new_status != manual_status:
                db.update_job_publishing(selected_job_id, new_status, sched_val)
                st.success(f"Status changed to {'PUBLISHED' if new_status else 'UNPUBLISHED'}")
                st.rerun()

        with tab3:
            st.subheader(f"Applications Management ({current_job['job_title']})")
            applications = db.get_job_applications(selected_job_id)
            
            if not applications:
                st.info("No applications submitted for this job yet.")
            else:
                shortlisted = [app for app in applications if app.get("approved") == 1]
                rejected = [app for app in applications if app.get("approved") == 0]
                resubmit_requests = [app for app in applications if app.get("resubmit_status") == "requested"]
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Applicants", len(applications))
                c2.metric("🟢 Shortlisted", len(shortlisted))
                c3.metric("🔴 Not Shortlisted", len(rejected))
                c4.metric("🔄 Re-submission Requests", len(resubmit_requests))
                
                st.markdown("---")
                sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
                    f"🟢 Shortlisted ({len(shortlisted)})", 
                    f"🔴 Not Shortlisted ({len(rejected)})",
                    f"🔄 Re-submission Requests ({len(resubmit_requests)})",
                    f"📋 All Submissions ({len(applications)})"
                ])
                
                def render_app_list(app_list):
                    if not app_list:
                        st.info("No applications in this category.")
                        return
                    for app in app_list:
                        key = app.get("candidate_key")
                        is_approved = app.get("approved") == 1
                        status_badge = "🟢 Shortlisted" if is_approved else "🔴 Not Shortlisted"
                        resubmit_badge = ""
                        if app.get("resubmit_status") == "requested":
                            resubmit_badge = " | 🔄 Re-submission Requested"
                        elif app.get("resubmit_status") == "allowed":
                            resubmit_badge = " | ✅ Re-submission Allowed"
                            
                        with st.expander(f"👤 {app.get('candidate_name')} | Key: `{key}` | Status: {status_badge}{resubmit_badge}"):
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.write(f"**Candidate Name:** {app.get('candidate_name')}")
                                st.write(f"**Email/Phone:** {app.get('candidate_contact')}")
                                st.write(f"**Submitted At:** {app.get('submitted_at')}")
                            with col_b:
                                st.write(f"**Unique Key:** `{key}`")
                                st.write(f"**AI Decision:** {status_badge}")
                            
                            st.markdown("**AI Evaluation Reason:**")
                            st.info(app.get("ai_reason", "No details available."))

                with sub_tab1:
                    render_app_list(shortlisted)
                with sub_tab2:
                    render_app_list(rejected)
                with sub_tab3:
                    if not resubmit_requests:
                        st.info("No candidate re-submission requests currently pending.")
                    else:
                        st.write("Review candidate requests to replace/re-upload their resume:")
                        for app in resubmit_requests:
                            key = app.get("candidate_key")
                            st.markdown(f"### 👤 {app.get('candidate_name')} (`{key}`)")
                            st.write(f"**Contact:** `{app.get('candidate_contact')}` | **Submitted At:** {app.get('submitted_at')}")
                            st.warning(f"**Candidate's Reason:** {app.get('resubmit_reason', 'No reason provided.')}")
                            
                            btn_col1, btn_col2 = st.columns(2)
                            with btn_col1:
                                if st.button(f"✅ Allow Re-submission for {key}", key=f"approve_{key}"):
                                    db.update_resubmit_status(key, "allowed")
                                    st.success(f"Approved re-submission for {app.get('candidate_name')}!")
                                    st.rerun()
                            with btn_col2:
                                if st.button(f"🔴 Reject Request for {key}", key=f"reject_{key}"):
                                    db.update_resubmit_status(key, "rejected")
                                    st.info(f"Rejected re-submission request for {app.get('candidate_name')}.")
                                    st.rerun()
                            st.markdown("---")

                with sub_tab4:
                    render_app_list(applications)

        with tab4:
            st.subheader("🚀 How to Deploy Publicly & Use on Mobile (Android & iPhone)")
            st.markdown("""
            ### 🌐 1. Deploy Publicly for FREE (Streamlit Community Cloud)
            You can deploy this application publicly online with a secure `https://` domain for **100% Free**:
            1. Push your project code to a **GitHub Repository**.
            2. Visit **[share.streamlit.io](https://share.streamlit.io)** and log in with your GitHub account.
            3. Click **"New App"**, select your repository and main file (`app.py`).
            4. In **Advanced Settings -> Secrets**, add your API key:
               ```toml
               NVIDIA_API_KEY = "nvapi-xxxxxxxxxxxx"
               ```
            5. Click **Deploy!** Your app will instantly be live at `https://your-app-name.streamlit.app`.

            ---
            ### 📱 2. Mobile App Installation (Android & iPhone PWA)
            Both HR recruiters and candidates can install this app directly on their mobile home screen **without needing Google Play Store or Apple App Store**:
            
            * **🤖 Android (Google Chrome)**:
              1. Open the public app link in Chrome on Android.
              2. Tap the **3-Dots Menu (⋮)** at the top right.
              3. Tap **"Add to Home Screen"** or **"Install App"**.
              
            * **🍎 iPhone / iPad (Safari)**:
              1. Open the public app link in Safari on iPhone.
              2. Tap the **Share Button (square with arrow)** at the bottom.
              3. Scroll down and tap **"Add to Home Screen"**.
            """)

def render_candidate_page(job_id):
    job = db.get_job_by_id(job_id)
    
    if not job:
        st.error("❌ Invalid or Expired Job Link.")
        return
        
    sched_str = job.get("publish_schedule")
    sched_display = None
    if sched_str:
        try:
            sched_dt = datetime.datetime.fromisoformat(sched_str)
            sched_display = sched_dt.strftime("%B %d, %Y at %I:%M %p")
        except Exception:
            pass

    st.markdown(f"""
        <div class="main-header">
            <h1>📋 {job['job_title']}</h1>
            <p>Organization: <b>{job['company_name']}</b> (HR: {job['hr_name']})</p>
        </div>
    """, unsafe_allow_html=True)
    
    if sched_display:
        st.info(f"📢 **Official Result Announcement Date:** Results will be published on **{sched_display}**.")

    tab_apply, tab_check, tab_resubmit, tab_forgot = st.tabs([
        "📝 Apply / Re-upload", 
        "🔍 Check Result", 
        "🔄 Request Re-submission",
        "🔑 Forgot Key?"
    ])
    
    with tab_apply:
        st.subheader(f"Submit Your Application for {job['job_title']}")
        st.markdown(f"**Job Requirements:**\n{job['qualifications']}")
        st.markdown("---")
        
        with st.form("candidate_apply_form"):
            name = st.text_input("Full Name *")
            contact = st.text_input("Email Address or Phone Number *", help="Used to identify your application.")
            resume_file = st.file_uploader("Upload Resume (PDF format) *", type=["pdf"])
            
            submitted = st.form_submit_button("Submit Application", use_container_width=True)
            
            if submitted:
                contact_clean = contact.strip().lower()
                existing_app = db.get_application_by_contact(job_id, contact_clean)

                if not name or not contact or not resume_file:
                    st.error("⚠️ Please fill in all fields and upload your resume.")
                elif existing_app and existing_app.get("resubmit_status") != "allowed":
                    st.warning(f"⚠️ **Duplicate Application Prevented!**\nAn application with contact info `{contact}` was already submitted on **{existing_app.get('submitted_at')}**.\n\n🔑 **Your Existing Candidate Key:** `{existing_app.get('candidate_key')}`\n\n💡 *If you uploaded a wrong resume by mistake, please use the **'🔄 Request Re-submission'** tab to ask HR for permission.*")
                else:
                    with st.spinner("Processing your application and analyzing resume with AI..."):
                        file_bytes = resume_file.read()
                        resume_text = extract_text_from_pdf(file_bytes)
                        
                        if not resume_text:
                            st.error("❌ Could not extract text from the uploaded PDF. Please upload a clear PDF file.")
                        else:
                            qualifications = job.get("qualifications", "")
                            ai_result = analyze_resume(resume_text, qualifications)
                            
                            existing_key = existing_app.get("candidate_key") if (existing_app and existing_app.get("resubmit_status") == "allowed") else None
                            candidate_key = db.save_application(job_id, name, contact_clean, ai_result, existing_key)
                            
                            st.balloons()
                            msg = "🎉 Resume Re-uploaded & Updated Successfully!" if existing_key else "🎉 Application Submitted Successfully!"
                            st.success(msg)
                            st.markdown(f"""
                                <div style='text-align: center; padding: 20px; border: 1px solid #4caf50; border-radius: 10px; background-color: #f1f8e9;'>
                                    <h3>Your Unique Candidate Key:</h3>
                                    <div class="key-badge">{candidate_key}</div>
                                    <p>⚠️ <b>Please save or copy this key!</b> You will need it to check your selection results once published by HR.</p>
                                </div>
                            """, unsafe_allow_html=True)
                            
    with tab_check:
        st.subheader("Check Your Application Result")
        with st.form("check_result_form"):
            entered_key = st.text_input("Enter Your Unique Candidate Key", placeholder="e.g. KEY-A1B2C3").strip().upper()
            check_btn = st.form_submit_button("Check Result", use_container_width=True)
            
            if check_btn:
                if not entered_key:
                    st.error("Please enter your candidate key.")
                else:
                    app_data = db.get_application_by_key(entered_key)
                    if not app_data:
                        st.error("❌ Invalid Key. Please verify your Unique Candidate Key or use 'Forgot Key?' to retrieve it.")
                    else:
                        is_effectively_published = check_is_published(app_data)
                        resubmit_stat = app_data.get("resubmit_status")
                        
                        st.write(f"**Company:** {app_data.get('company_name')}")
                        st.write(f"**Job Title:** {app_data.get('job_title')}")
                        st.write(f"**Applicant:** {app_data.get('candidate_name')}")
                        st.write(f"**Submitted Date:** {app_data.get('submitted_at')}")
                        
                        if resubmit_stat == "allowed":
                            st.success("✅ **HR has approved your re-submission request!**")
                            st.info("Please switch to the **'📝 Apply / Re-upload'** tab to upload your corrected resume.")
                        elif resubmit_stat == "requested":
                            st.info("🔄 **Your Re-submission Request is currently Pending HR Review.**")
                        elif resubmit_stat == "rejected":
                            st.error("🔴 **HR has declined your re-submission request.**")

                        if not is_effectively_published:
                            st.warning("⌛ **Results Have Not Been Published Yet**")
                            if sched_display:
                                st.info(f"📅 **Scheduled Result Announcement:** {sched_display}\nPlease check back on or after this date & time to view your evaluation result!")
                            else:
                                st.info("HR is currently reviewing applications. Results will be published soon. Please check back later!")
                        else:
                            st.markdown("---")
                            is_approved = app_data.get("approved") == 1
                            if is_approved:
                                st.success("🎉 **Congratulations! You have been Shortlisted!**")
                                st.markdown(f"**HR Feedback:** {app_data.get('ai_reason')}")
                                st.info("Next Steps: HR will contact you directly via your registered contact details.")
                            else:
                                st.error("❌ **Application Update: Not Shortlisted**")
                                st.markdown(f"**Evaluation Feedback:** {app_data.get('ai_reason')}")
                                st.write("Thank you for your interest. We encourage you to apply for future positions.")

    with tab_resubmit:
        st.subheader("Request Resume Re-submission")
        st.write("Did you accidentally upload the wrong resume PDF? Request permission from HR to re-submit your resume.")
        
        with st.form("resubmit_request_form"):
            key_for_req = st.text_input("Enter Your Unique Candidate Key *", placeholder="e.g. KEY-A1B2C3").strip().upper()
            reason_text = st.text_area("Reason for Re-submission Request *", placeholder="e.g. I uploaded an outdated version of my resume by mistake.")
            
            req_submitted = st.form_submit_button("Submit Re-submission Request", use_container_width=True)
            
            if req_submitted:
                app = db.get_application_by_key(key_for_req)
                if not key_for_req or not reason_text:
                    st.error("⚠️ Please fill in both your Candidate Key and Reason.")
                elif not app:
                    st.error("❌ Candidate Key not found. Please verify your key.")
                else:
                    db.set_resubmit_request(key_for_req, reason_text)
                    st.success("✅ **Re-submission request submitted to HR!**")
                    st.info("HR will review your request. Check your key status in the '🔍 Check Result' tab for updates.")

    with tab_forgot:
        st.subheader("Recover Your Candidate Key")
        with st.form("forgot_key_form"):
            contact_lookup = st.text_input("Enter your registered Email or Phone Number").strip().lower()
            recover_btn = st.form_submit_button("Find My Key", use_container_width=True)
            
            if recover_btn:
                if not contact_lookup:
                    st.error("Please enter your contact details.")
                else:
                    found_apps = db.get_applications_by_contact_all(contact_lookup)
                    if found_apps:
                        st.success(f"✅ Found {len(found_apps)} application(s) associated with `{contact_lookup}`:")
                        for app in found_apps:
                            st.markdown(f"- **Key:** `{app['candidate_key']}` | **Company:** {app['company_name']} | **Job:** {app['job_title']} (Submitted: {app['submitted_at']})")
                    else:
                        st.error("❌ No applications found matching that email or phone number.")

def main():
    st.markdown(custom_css, unsafe_allow_html=True)
    if "job_id" in st.query_params:
        render_candidate_page(st.query_params["job_id"])
    else:
        if "hr_user" in st.session_state:
            render_admin_dashboard()
        else:
            render_hr_auth_page()

if __name__ == "__main__":
    from streamlit.runtime import exists
    if not exists():
        print("Launching Streamlit app...")
        subprocess.run([sys.executable, "-m", "streamlit", "run", __file__])
    else:
        main()
