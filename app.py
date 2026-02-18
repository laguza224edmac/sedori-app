import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import statistics
import urllib.parse
from pyzbar.pyzbar import decode
from PIL import Image

# --- ページ設定 ---
st.set_page_config(page_title="最強せどりツールv8.0", layout="wide")

st.title("📱 最強せどりツール v8.0 (カメラ搭載版)")
st.write("バーコードを読み取って、一瞬で相場を特定します！")

# --- サイドバー設定 ---
st.sidebar.header("🔍 検索設定")
input_mode = st.sidebar.radio("検索モード", ["キーワード入力", "バーコード読み取り"])
keyword = "" # 初期化

if input_mode == "キーワード入力":
    keyword = st.sidebar.text_input("検索ワード", "iPhone 12")
    
shipping_cost = st.sidebar.number_input("送料（円）", value=750, step=50)
exclude_junk = st.sidebar.checkbox("「ジャンク」を除外", value=True)

# --- カメラでバーコードを読み取る機能 ---
if input_mode == "バーコード読み取り":
    st.info("👇 下のボタンを押して、バーコードの写真を撮ってください")
    img_file_buffer = st.camera_input("バーコードを撮影")
    
    if img_file_buffer is not None:
        # 写真を読み込む
        image = Image.open(img_file_buffer)
        
        # バーコードを解析する
        decoded_objects = decode(image)
        
        if decoded_objects:
            # 読み取れた最初のバーコードを使う
            barcode_data = decoded_objects[0].data.decode("utf-8")
            st.success(f"✅ バーコード読み取り成功: {barcode_data}")
            
            # バーコード番号をそのまま検索ワードにする
            keyword = barcode_data
        else:
            st.error("❌ バーコードが読み取れませんでした。明るい場所でもう一度試して！")

# --- 関数：Yahooデータを取得 ---
def get_yahoo_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = []
        product_list = soup.find_all("li", class_="Product")
        
        for product in product_list:
            title_tag = product.find("a", class_="Product__titleLink")
            price_tag = product.find("span", class_="Product__priceValue")
            image_tag = product.find("img")
            
            if title_tag and price_tag:
                title = title_tag.text.strip()
                link = title_tag.get("href")
                price_text = price_tag.text.replace("円", "").replace(",", "").strip()
                image_url = image_tag.get("src") if image_tag else "https://via.placeholder.com/150"
                
                if exclude_junk:
                    if "ジャンク" in title or "JUNK" in title or "訳あり" in title:
                        continue

                if price_text.isdigit():
                    items.append({
                        "商品画像": image_url,
                        "商品名": title,
                        "price": int(price_text),
                        "link": link
                    })
        return items
    except Exception as e:
        return []

# --- メイン処理 ---
# キーワードがある（入力された or バーコードで読み取れた）場合のみ実行
if keyword:
    st.divider()
    st.markdown(f"### 🔍 検索ワード: **{keyword}**")
    
    if st.button("🚀 このキーワードでリサーチ開始！"):
        st.info("過去相場とトレンドを分析中...")
        
        sold_url = f"https://auctions.yahoo.co.jp/closedsearch/closedsearch?p={keyword}&n=50"
        sold_items = get_yahoo_data(sold_url)
        
        if len(sold_items) > 0:
            sold_prices = [item["price"] for item in sold_items]
            market_price = int(statistics.mean(sold_prices))
            
            st.success(f"📈 平均相場: {market_price:,}円")
            
            # グラフ表示
            chart_data = pd.DataFrame({"落札価格": sold_prices})
            st.bar_chart(chart_data, color="#FF4B4B")

            # リンク生成
            safe_keyword = urllib.parse.quote(keyword)
            mercari_link = f"https://www.mercari.com/jp/search/?keyword={safe_keyword}&status_on_sale=1"
            amazon_link = f"https://www.amazon.co.jp/s?k={safe_keyword}"
            
            col_link1, col_link2 = st.columns(2)
            col_link1.link_button("メルカリで相場を見る", mercari_link, type="primary")
            col_link2.link_button("Amazonで新品価格を見る", amazon_link)

            st.divider()
            
            st.info("出品中のお宝を探しています...")
            current_url = f"https://auctions.yahoo.co.jp/search/search?p={keyword}&n=50"
            current_items = get_yahoo_data(current_url)
            
            if len(current_items) > 0:
                results = []
                for item in current_items:
                    shiire = item["price"]
                    te_dori = market_price * 0.9
                    expected_profit = int(te_dori - shipping_cost - shiire)
                    
                    results.append({
                        "画像": item["商品画像"],
                        "商品名": item["商品名"],
                        "現在価格": shiire,
                        "予想利益": expected_profit,
                        "リンク": item["link"]
                    })
                
                df = pd.DataFrame(results)
                df = df.sort_values(by="予想利益", ascending=False)
                
                st.dataframe(
                    df,
                    column_config={
                        "画像": st.column_config.ImageColumn("商品画像"),
                        "リンク": st.column_config.LinkColumn("商品ページへ"),
                        "現在価格": st.column_config.NumberColumn(format="%d円"),
                        "予想利益": st.column_config.NumberColumn(format="%d円"),
                    },
                    hide_index=True,
                    row_height=100
                )
                
                best_item = df.iloc[0]
                if best_item["予想利益"] > 0:
                    st.balloons()
                    st.markdown(f"### 👑 キング・オブ・お宝")
                    col1, col2 = st.columns([1,3])
                    with col1:
                        st.image(best_item["画像"])
                    with col2:
                        st.error(f"価格: {best_item['現在価格']:,}円")
                        st.metric("予想利益", f"+{best_item['予想利益']:,}円")
                        st.write(f"[商品ページへ]({best_item['リンク']})")
                else:
                    st.warning("今は利益が出る商品はなさそうです。")
            else:
                st.error("出品中の商品が見つかりませんでした。")
        else:
            st.error("過去データが見つかりませんでした。")