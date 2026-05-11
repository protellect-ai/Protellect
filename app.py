import streamlit as st

st.set_page_config(page_title="Protellect v32", page_icon="🧬", layout="wide")

st.markdown("""
<style>
body { background: #02060d; color: #dde9f5; }
.stApp { background: linear-gradient(135deg, #04101e 0%, #02060d 100%); }
</style>
""", unsafe_allow_html=True)

st.title("🧬 Protellect v32 - Test Version")
st.write("If you see this message, the app deployed successfully!")

gene = st.text_input("Enter a human gene symbol", placeholder="TP53")

if gene:
    st.success(f"✓ You entered: {gene}")
    st.info("Full app is working! This is the minimal test version.")
    
st.markdown("---")
st.caption("Protellect v32 - Genetics-first protein intelligence platform")
