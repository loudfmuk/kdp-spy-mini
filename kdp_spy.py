import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

st.set_page_config(page_title="KDP Spy Mini", layout="wide", page_icon="🎨")
st.title("🎨 KDP Spy Mini - Coloring Books Edition")
st.markdown("**Optimized for Coloring Books**")

# ====================== Sales Estimator ======================
def bsr_to_sales(bsr_str, low_content_mode=True):
    if not bsr_str or bsr_str == "N/A":
        return "N/A", "N/A"
    try:
        bsr = int(re.sub(r'[^\d]', '', bsr_str))
        if low_content_mode:
            if bsr <= 5000: daily = 12
            elif bsr <= 15000: daily = 6
            elif bsr <= 30000: daily = 3.5
            elif bsr <= 60000: daily = 2
            elif bsr <= 120000: daily = 1
            else: daily = 0.5
        else:
            if bsr <= 5000: daily = 8
            elif bsr <= 10000: daily = 5
            else: daily = 1
        monthly = round(daily * 30.4)
        return f"{monthly:,}", f"~{daily:.1f}/day"
    except:
        return "N/A", "N/A"


# ====================== Search Function (Improved) ======================
def search_kindle(keyword: str, pages: int = 2, marketplace: str = "com"):
    books = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    }
    
    for page in range(1, pages + 1):
        url = f"https://www.amazon.{marketplace}/s?k={keyword.replace(' ', '+')}&i=digital-text"
        if page > 1:
            url += f"&page={page}"
        
        try:
            r = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Multiple possible selectors (Amazon changes often)
            items = soup.select('[data-component-type="s-search-result"], .s-result-item')
            
            for item in items:
                try:
                    title_tag = item.select_one('h2 a, .a-link-normal')
                    if not title_tag or not title_tag.get_text(strip=True):
                        continue
                        
                    title = title_tag.get_text(strip=True)
                    link = "https://www.amazon." + marketplace + title_tag.get('href', '')
                    
                    price_tag = item.select_one('.a-price .a-offscreen')
                    price = price_tag.get_text(strip=True) if price_tag else "N/A"
                    
                    # BSR
                    bsr_match = re.search(r'#([\d,]+)', item.get_text())
                    bsr = bsr_match.group(1) if bsr_match else "N/A"
                    
                    monthly, daily = bsr_to_sales(bsr)
                    
                    books.append({
                        "Title": title[:80] + "..." if len(title) > 80 else title,
                        "Price": price,
                        "BSR": bsr,
                        "Est. Monthly Sales": monthly,
                        "Est. Daily Sales": daily,
                        "Link": link
                    })
                except:
                    continue
                    
            time.sleep(1.5)
        except Exception as e:
            st.warning(f"Page {page} failed")
            continue
            
    return pd.DataFrame(books)


# ====================== UI ======================
st.sidebar.header("Settings")
marketplace = st.sidebar.selectbox("Marketplace", ["com", "co.uk"], index=0)

tab1, tab2 = st.tabs(["🔍 Keyword Search", "📖 ISBN Lookup"])

with tab1:
    st.subheader("Quick Presets")
    cols = st.columns(5)
    presets = ["adult coloring book", "mandala coloring book", "cat coloring book", 
               "christmas coloring book", "animal coloring book"]
    
    for i, preset in enumerate(presets):
        with cols[i]:
            if st.button(preset.replace(" coloring book", "").title(), use_container_width=True):
                st.session_state.keyword = preset

    keyword = st.text_input("Keyword", value=st.session_state.get('keyword', "adult coloring book"))
    pages = st.slider("Pages", 1, 5, 2)

    if st.button("🔍 Search", type="primary"):
        with st.spinner("Searching Amazon... This may take a few seconds"):
            df = search_kindle(keyword, pages, marketplace)
            
            if df.empty:
                st.error("❌ No results found. Try a broader keyword or different marketplace.")
                st.info("Tip: Try 'coloring book' or 'adult coloring'")
            else:
                st.success(f"✅ Found {len(df)} books")
                st.dataframe(df, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("ISBN / ASIN Lookup")
    isbn = st.text_input("Enter ISBN or ASIN")
    if st.button("Lookup") and isbn:
        st.info("ISBN lookup coming in next update...")

st.caption("If you still get no results, Amazon might be blocking the request. Try again in 10-15 minutes.")
