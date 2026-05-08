import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from datetime import datetime

st.set_page_config(page_title="KDP Spy Mini", layout="wide", page_icon="🔍")
st.title("🔍 KDP Spy Mini")
st.markdown("**Amazon KDP Research Tool** — Keyword Search + ISBN/Barcode Lookup")

# ====================== BSR to Sales Calculator ======================
def bsr_to_sales(bsr_str):
    if not bsr_str or bsr_str == "N/A":
        return "N/A", "N/A"
    try:
        bsr = int(re.sub(r'[^\d]', '', bsr_str))
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


# ====================== ISBN / ASIN Lookup ======================
def fetch_book_by_isbn(isbn: str, marketplace: str = "com"):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    url = f"https://www.amazon.{marketplace}/dp/{isbn}"
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        title = soup.select_one('#productTitle, h1')
        title_text = title.get_text(strip=True)[:120] if title else "N/A"
        
        price = soup.select_one('.a-price .a-offscreen')
        price_text = price.get_text(strip=True) if price else "N/A"
        
        # Extract BSR
        bsr_match = re.search(r'#([\d,]+)', soup.get_text())
        bsr = bsr_match.group(1) if bsr_match else "N/A"
        
        rating = soup.select_one('.a-icon-star')
        rating_text = rating.get_text(strip=True) if rating else "N/A"
        
        reviews = soup.select_one('#acrCustomerReviewLink')
        reviews_text = reviews.get_text(strip=True).replace(',', '') if reviews else "0"
        
        monthly_sales, daily_sales = bsr_to_sales(bsr)
        
        data = {
            "Title": title_text,
            "Price": price_text,
            "BSR": bsr,
            "Est. Monthly Sales": monthly_sales,
            "Est. Daily Sales": daily_sales,
            "Rating": rating_text,
            "Reviews": reviews_text,
            "Link": url
        }
        return pd.DataFrame([data])
    except Exception as e:
        st.error(f"Failed to fetch book: {e}")
        return pd.DataFrame()


# ====================== Keyword Search ======================
def search_kindle(keyword: str, pages: int = 2, marketplace: str = "com"):
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
                    title = title_tag.get_text(strip=True) if title_tag else ""
                    if not title:
                        continue
                    link = "https://www.amazon." + marketplace + title_tag['href']
                    
                    price_tag = item.select_one('.a-price .a-offscreen')
                    price = price_tag.get_text(strip=True) if price_tag else "N/A"
                    
                    bsr_match = re.search(r'#([\d,]+)', item.get_text())
                    bsr = bsr_match.group(1) if bsr_match else "N/A"
                    
                    rating = item.select_one('.a-icon-star-small')
                    rating_text = rating.get_text(strip=True) if rating else "N/A"
                    
                    reviews = item.select_one('.a-size-base.s-underline-text')
                    reviews_text = reviews.get_text(strip=True) if reviews else "0"
                    
                    monthly, daily = bsr_to_sales(bsr)
                    
                    books.append({
                        "Title": title[:80] + "..." if len(title) > 80 else title,
                        "Price": price,
                        "BSR": bsr,
                        "Est. Monthly Sales": monthly,
                        "Est. Daily Sales": daily,
                        "Rating": rating_text,
                        "Reviews": reviews_text,
                        "Link": link
                    })
                except:
                    continue
            time.sleep(1)
        except:
            continue
    return pd.DataFrame(books)


# ====================== Sidebar & Tabs ======================
tab1, tab2 = st.tabs(["🔍 Keyword Search", "📖 ISBN / Barcode Lookup"])

marketplace = st.sidebar.selectbox("Amazon Marketplace", 
                                  ["com", "co.uk", "de", "fr", "ca"], index=0)

# ====================== TAB 1: Keyword Search ======================
with tab1:
    st.subheader("Search by Keyword")
    keyword = st.text_input("Enter keyword or niche", value="bullet journal")
    pages = st.slider("Number of pages to scrape", 1, 5, 2)
    
    if st.button("🔍 Search", type="primary"):
        with st.spinner(f"Searching Amazon {marketplace}..."):
            df = search_kindle(keyword, pages, marketplace)
            
            if df.empty:
                st.warning("No results found.")
            else:
                st.success(f"Found {len(df)} books")
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                csv = df.to_csv(index=False).encode()
                st.download_button("📥 Download CSV", csv, f"{keyword}_kdp_spy.csv", "text/csv")

# ====================== TAB 2: ISBN Lookup ======================
with tab2:
    st.subheader("Lookup by ISBN or ASIN")
    isbn = st.text_input("Enter ISBN-10 / ISBN-13 or ASIN", placeholder="9781234567890 or B0ABC12345")
    
    if st.button("🔎 Lookup Book", type="primary"):
        if isbn.strip():
            with st.spinner("Fetching book data..."):
                df = fetch_book_by_isbn(isbn.strip(), marketplace)
                if not df.empty and df.iloc[0]["Title"] != "N/A":
                    st.success("✅ Book Found")
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.markdown(f"**View on Amazon:** [{df.iloc[0]['Title']}]({df.iloc[0]['Link']})")
                else:
                    st.error("Could not find the book. Try again or check the ISBN.")
        else:
            st.warning("Please enter an ISBN or ASIN")

st.caption("⚠️ This tool scrapes public Amazon data. Use responsibly and avoid heavy usage.")