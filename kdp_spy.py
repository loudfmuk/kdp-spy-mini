import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

st.set_page_config(page_title="KDP Spy Mini", layout="wide", page_icon="🎨")
st.title("🎨 KDP Spy Mini - Coloring Books Edition")
st.markdown("**Optimized for Coloring Books & Low Content Books**")

# ====================== Improved Sales Estimator ======================
def bsr_to_sales(bsr_str, low_content_mode=False):
    if not bsr_str or bsr_str == "N/A":
        return "N/A", "N/A"
    
    try:
        bsr = int(re.sub(r'[^\d]', '', bsr_str))
        
        if low_content_mode:
            # Better for coloring books
            if bsr <= 5000:   daily = 12
            elif bsr <= 10000: daily = 8
            elif bsr <= 20000: daily = 5
            elif bsr <= 40000: daily = 3
            elif bsr <= 80000: daily = 1.8
            elif bsr <= 150000: daily = 0.9
            else: daily = 0.4
        else:
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


# ====================== Fetch Book by ISBN ======================
def fetch_book_by_isbn(isbn: str, marketplace: str = "com", low_content_mode=False):
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
        
        monthly, daily = bsr_to_sales(bsr, low_content_mode)
        
        data = {
            "Title": title_text,
            "Price": price_text,
            "BSR": bsr,
            "Est. Monthly Sales": monthly,
            "Est. Daily Sales": daily,
            "Link": url
        }
        return pd.DataFrame([data])
    except:
        return pd.DataFrame()


# ====================== Keyword Search ======================
def search_kindle(keyword: str, pages: int = 2, marketplace: str = "com", low_content_mode=False):
    books = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    for page in range(1, pages + 1):
        url = f"https://www.amazon.{marketplace}/s?k={keyword.replace(' ', '+')}&i=digital-text"
        if page > 1:
            url += f"&page={page}"
        
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
                    
                    price_tag = item.select_one('.a-price .a-offscreen')
                    price = price_tag.get_text(strip=True) if price_tag else "N/A"
                    
                    bsr_match = re.search(r'#([\d,]+)', item.get_text())
                    bsr = bsr_match.group(1) if bsr_match else "N/A"
                    
                    monthly, daily = bsr_to_sales(bsr, low_content_mode)
                    
                    books.append({
                        "Title": title[:75] + "..." if len(title) > 75 else title,
                        "Price": price,
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


# ====================== Main UI ======================
st.sidebar.header("Settings")
marketplace = st.sidebar.selectbox("Marketplace", ["com", "co.uk", "de", "fr", "ca"], index=0)

low_content = st.sidebar.toggle("🎨 Low Content Mode (Recommended for Coloring Books)", value=True)
st.session_state.low_content = low_content

tab1, tab2 = st.tabs(["🔍 Keyword Search", "📖 ISBN / Barcode Lookup"])

with tab1:
    st.subheader("Quick Coloring Book Presets")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("Adult Coloring", use_container_width=True):
            st.session_state.keyword = "adult coloring book"
    with col2:
        if st.button("Mandala", use_container_width=True):
            st.session_state.keyword = "mandala coloring book"
    with col3:
        if st.button("Cat Coloring", use_container_width=True):
            st.session_state.keyword = "cat coloring book"
    with col4:
        if st.button("Christmas Coloring", use_container_width=True):
            st.session_state.keyword = "christmas coloring book"
    with col5:
        if st.button("Animal Coloring", use_container_width=True):
            st.session_state.keyword = "animal coloring book"

    keyword = st.text_input("Or type your own keyword", 
                           value=st.session_state.get('keyword', "adult coloring book"))

    pages = st.slider("Pages to scrape", 1, 5, 2)
    
    if st.button("🔍 Search", type="primary"):
        with st.spinner("Searching Amazon..."):
            df = search_kindle(keyword, pages, marketplace, low_content)
            if df.empty:
                st.warning("No results found.")
            else:
                st.success(f"Found {len(df)} books")
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                csv = df.to_csv(index=False).encode()
                st.download_button("📥 Download CSV", csv, f"{keyword.replace(' ', '_')}.csv", "text/csv")

with tab2:
    st.subheader("Lookup by ISBN or ASIN")
    isbn = st.text_input("Enter ISBN-10, ISBN-13 or ASIN", placeholder="9781234567890")
    if st.button("🔎 Lookup Book", type="primary") and isbn.strip():
        with st.spinner("Fetching book..."):
            df = fetch_book_by_isbn(isbn.strip(), marketplace, low_content)
            if not df.empty and df.iloc[0]["Title"] != "N/A":
                st.success("✅ Book Found!")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.error("Could not find the book. Please check the ISBN.")

st.caption("🎨 Low Content Mode gives more realistic estimates for coloring books.")
