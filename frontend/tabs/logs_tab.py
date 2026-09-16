import streamlit as st
from config.settings import LOG_FILE

def render_logs_tab():
    st.markdown("## 📋 System Logs")
    st.markdown("Live view of `aegisforge.log`. Use this to troubleshoot runtime issues.")
    
    col_log1, col_log2 = st.columns([1, 4])
    with col_log1:
        if st.button("🔄 Refresh Logs", use_container_width=True):
            pass # Reruns app naturally
            
    with col_log2:
        num_lines = st.slider("Lines to display", min_value=50, max_value=500, value=100, step=50)
        
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
