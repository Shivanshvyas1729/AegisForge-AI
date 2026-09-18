import streamlit as st
from config.settings import LOG_FILE

@st.fragment(run_every=2)
def live_log_reader(num_lines: int):
    try:
        if LOG_FILE.exists():
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            display_lines = lines[-num_lines:] if len(lines) > num_lines else lines
            log_text = "".join(display_lines)
            
            st.code(log_text, language="log")
        else:
            st.info("Log file is currently empty or does not exist.")
    except Exception as e:
        st.error(f"Could not read log file: {e}")

def render_logs_tab():
    st.markdown("## 📋 System Logs")
    st.markdown("Live view of `aegisforge.log`. Use this to troubleshoot runtime issues.")
    
    col_log1, col_log2, col_log3 = st.columns([1, 1, 3])
    with col_log1:
        if st.button("🔄 Refresh Logs", use_container_width=True):
            pass # Reruns app naturally
            
    with col_log2:
        if st.button("🗑️ Clear Logs", use_container_width=True):
            if LOG_FILE.exists():
                with open(LOG_FILE, "w", encoding="utf-8") as f:
                    f.write("")
                st.rerun()
            
    with col_log3:
        num_lines = st.slider("Lines to display", min_value=50, max_value=500, value=100, step=50)
        
    live_log_reader(num_lines)
