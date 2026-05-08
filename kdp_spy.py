import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from datetime import datetime

st.set_page_config(page_title="KDP Spy Mini", layout="wide", page_icon="🎨")
st.title("🎨 KDP Spy Mini - Coloring Books Edition")
st.markdown("**Optimized for Coloring Books & Low Content Books**")

# ====================== Improved BSR Sales Estimator ======================
def bsr_to_sales(bsr_str, low_content_mode=False):
    if not bsr_str or bsr_str == "N/A":
        return "N/A", "N/A"
    
    try:
        bsr = int(re.sub(r'[^\d]', '', bsr_str))
        
        if low_content_mode:
            # More realistic for coloring / low-content books
            if bsr <= 5000:   daily = 12
            elif bsr <= 10000: daily = 8
            elif bsr <= 20000: daily = 5
            elif bsr <= 40000: daily = 3
            elif bsr <= 80000: daily = 1.8
            elif bsr <= 150000: daily = 0.9
            else: daily = 0.4
        else:
            # Standard mode
            if bsr <= 100: daily = 150
            elif bsr <= 500: daily = 45
            elif bsr <= 1000: daily = 25
            elif bsr <= 5000: daily = 8
            elif bsr <= 10000: daily = 5
            elif bsr <= 30000: daily = 2.5
            elif bsr <= 100000: daily = 1.0
            else: daily = 0.3
            
        monthly = round(daily * 30.4)
        return f"{monthly:,}", f"~{daily:.1f}/day"
    except:
        return "N/A", "N/A"


# ====================== Fetch by ISBN ======================
def fetch_book_by_isbn(isbn: str, marketplace: str = "com"):
    # ... (same as previous version - keeping it short)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    url = f"https://www.amazon.{marketplace}/dp/{isbn}"
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        title = soup.select_one('#productTitle, h1')
        title_text = title.get_text(strip=True)[:120] if title else "N/A"
        
        price = soup.select_one('.a-price .a-offscreen')
        price_text = price.get_text(strip=True) if price else "N/A"
        
        bsr_match = re.search(r'#([\d,]+)', soup.get_text())
        bsr = bsr_match.group(1) if bsr_match else "N/A"
        
        monthly, daily = bsr_to_sales(bsr, st.session_state.get('low_content', False))
        
        data = {
            "Title": title_text, "Price": price_text, "BSR": bsr,
            "Est. Monthly Sales": monthly, "Est. Daily Sales": daily,
            "Link": url
        }
        return pd.DataFrame([data])
    except:
        return pd.DataFrame()


# ====================== Keyword Search ======================
def search_kindle(keyword: str, pages: int = 2, marketplace: str = "com"):
    # ... (same logic as before)
    books = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    for page in range(1, pages + 1):
        url = f"https://www.amazon.{marketplace}/s?k={keyword.replace(' ', '+')}&i=digital-text"
        if page > 1: url += f"&page={page}"
        
        try:
            r = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            items = soup.select('[data-component-type="s-search-result"]')
            
            for item in items:
                try:
                    title_tag = item.select_one('h2 a')
                    if not title_tag: continue
                    title = title_tag.get_text(strip=True)
                    link = "https://www.amazon." + marketplace + title_tag['href']
                    
                    price = item.select_one('.a-price .a-offscreen')
                    price_text = price.get_text(strip=True) if price else "N/A"
                    
                    bsr_match = re.search(r'#([\d,]+)', item.get_text())
                    bsr = bsr_match.group(1) if bsr_match else "N/A"
                    
                    monthly, daily = bsr_to_sales(bsr, st.session_state.get('low_content', False))
                    
                    books.append({
                        "Title": title[:75] + "..." if len(title) > 75 else title,
                        "Price": price_text,
                        "BSR": bsr,
                        "Est. Monthly Sales": monthly,
                        "Est. Daily Sales": daily,
                        "Link": link
                    })
                except:
                    continue
            time.sleep(1.1)
        except:
            continue
    return pd.DataFrame(books)


# ====================== UI ======================
st.sidebar.header("Settings")
marketplace = st.sidebar.selectbox("Marketplace", ["com", "co.uk", "de", "fr", "ca"], index=0)

low_content = st.sidebar.toggle("🎨 Low Content Mode (Coloring Books)", value=True, 
                               help="Better estimates for coloring books, journals, etc.")
st.session_state.low_content = low_content

tab1, tab2 = st.tabs(["🔍 Keyword Search", "📖 ISBN / Barcode Lookup"])

# ====================== TAB 1: Keyword Search ======================
with tab1:
    st.subheader("Quick Coloring Book Presets")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("Adult Coloring Book", use_container_width=True):
            st.session_state.keyword = "adult coloring book"
    with col2:
        if st.button("Mandala Coloring", use_container_width=True):
            st.session_state.keyword = "mandala coloring book"
    with col3:
        if st.button("Cat Coloring Book", use_container_width=True):
            st.session_state.keyword = "cat coloring book"
    with col4:
        if st.button("Christmas Coloring", use_container_width=True):
            st.session_state.keyword = "christmas coloring book"

    keyword = st.text_input("Or type your own keyword", 
                           value=st.session_state.get('keyword', "adult coloring book"))

    pages = st.slider("Pages to scrape", 1, 5, 2)
    
    if st.button("🔍 Search", type="primary"):
        with st.spinner("Searching..."):
            df = search_kindle(keyword, pages, marketplace)
            if df.empty:
                st.warning("No results.")
            else:
                st.success(f"Found {len(df)} books")
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                csv = df.to_csv(index=False).encode()
                st.download_button("📥 Download CSV", csv, f"{keyword}_coloring_books.csv", "text/csv")

# ====================== TAB 2: ISBN Lookup ======================
with tab2:
    st.subheader("Lookup Single Book")
    isbn = st.text_input("Enter ISBN or ASIN", placeholder="9781234567890")
    if st.button("🔎 Lookup", type="primary") and isbn:
        with st.spinner("Fetching..."):
            df = fetch_book_by_isbn(isbn, marketplace)
            if not df.empty and df.iloc[0]["Title"] != "N/A":
                st.success("Book Found!")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.error("Book not found.")

st.caption("🎨 Low Content Mode is ON by default — optimized for coloring books.")
Updated with Coloring Books presets and improved low-content estimator
