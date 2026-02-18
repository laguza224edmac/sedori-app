import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import statistics
import urllib.parse
from pyzbar.pyzbar import decode
from PIL import Image

# --- ページ設定 ---
st.set_page_config(page_title="最強せどりツールv9.0", layout="wide")

st.title("📱 最強せどりツール v9.0")
st.write("ノイズ除去フィルター搭載！純粋な「本体価格」だけを狙い撃ちします。")

# --- サイドバー設定 ---
st.sidebar.header("🔍 検索・フィルタ設定")
input_mode = st.sidebar.radio("モード", ["キーワード入力", "バーコード読み取り"])

# 【追加】価格下限フィルター：安すぎる「ケース」などを排除
min_price_filter = st.sidebar.number_input("最低価格フィルター（これ未満は無視）", value=5000, step=500)

# 【追加】即決のみ設定
buy_now_only = st.sidebar.checkbox("即決価格（今すぐ買える商品）のみ", value=True)

shipping_cost = st.sidebar.number_input("送料（円）", value=750, step=50)
exclude_junk = st.sidebar.checkbox("「ジャンク・ケース・箱」を除外", value=True)

keyword = ""
if input_mode == "キーワード入力":
    keyword = st.sidebar.text_input("検索ワード", "iPhone 12")

# --- 高感度バーコード読み取り ---
if input_mode == "バーコード読み取り":
    img_file_buffer = st.camera_input("バーコードを撮影")
    if img_file_buffer:
        image = Image.open(img_file_buffer)
        # 白黒加工で感度アップ
        gray_image = image.convert('L')
        decoded_objects = decode(image) or decode(gray_image)
        
        if decoded_objects:
            keyword = decoded_objects[0].data.decode("utf-8")
            st.success(f"✅ 読み取り成功: {keyword}")
        else:
            st.error("❌ 読み取れません。もう少し離してピントを合わせてみて！")

# --- 検索関数 ---
def get_yahoo_data(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = []
        product_list = soup.find_all("li", class_="Product")
        
        for product in product_list:
            title_tag = product.find("a", class_="Product__titleLink")
            # 即決価格を探す。なければ通常価格。
            price_tag = product.find("span", class_="Product__priceValue")
            buynow_tag = product.find("span", class_="Product__label--buynow") # 即決アイコン
            
            if title_tag and price_tag:
                title = title_tag.text.strip()
                link = title_tag.get("href")
                price_text = price_tag.text.replace("円", "").replace(",", "").strip()
                
                if price_text.isdigit():
                    price = int(price_text)
                    
                    # --- 鉄壁のフィルター群 ---
                    # 1. 価格下限チェック
                    if price < min_price_filter:
                        continue
                    
                    # 2. 即決のみチェック（即決設定ONで、即決アイコンがない場合は飛ばす）
                    # ヤフオクの仕様上、検索URL側で制御するのが確実なので後述のURL生成も修正
                    
                    # 3. キーワード除外（ケース、フィルム、箱、などのノイズ）
                    if exclude_junk:
                        noise_keywords = ["ジャンク", "JUNK", "訳あり", "ケース", "フィルム", "カバー", "空箱", "写真", "のみ"]
                        if any(nw in title for nw in noise_keywords):
                            continue

                    image_tag = product.find("img")
                    image_url = image_tag.get("src") if image_tag else ""
                    
                    items.append({"画像": image_url, "商品名": title, "price": price, "link": link})
        return items
    except: return []

# --- 実行セクション ---
if keyword:
    st.divider()
    if st.button("🚀 精密リサーチ開始"):
        # URL生成時に「即決」や「価格下限」をヤフオク側にも伝える（より正確になります）
        # istatus=2 が即決のみ、min=価格下限
        yahoo_base = "https://auctions.yahoo.co.jp/search/search?"
        params = {
            "p": keyword,
            "n": 50,
            "min": min_price_filter,
            "istatus": 2 if buy_now_only else 0, # 2は即決、0はすべて
        }
        
        # 過去相場用（過去データは即決に限らず全体を見るのが一般的）
        sold_url = f"https://auctions.yahoo.co.jp/closedsearch/closedsearch?p={keyword}&n=50"
        # 現在出品用
        current_url = f"{yahoo_base}{urllib.parse.urlencode(params)}"
        
        # 相場調査
        sold_items = get_yahoo_data(sold_url)
        if sold_items:
            market_price = int(statistics.mean([item["price"] for item in sold_items]))
            st.success(f"📈 過去相場（ノイズ除去後）: {market_price:,}円")
            
            # 出品中調査
            current_items = get_yahoo_data(current_url)
            if current_items:
                results = []
                for item in current_items:
                    te_dori = market_price * 0.9
                    profit = int(te_dori - shipping_cost - item["price"])
                    results.append({"画像": item["画像"], "商品名": item["商品名"], "現在価格": item["price"], "予想利益": profit, "リンク": item["link"]})
                
                df = pd.DataFrame(results).sort_values(by="予想利益", ascending=False)
                st.dataframe(df, column_config={"画像": st.column_config.ImageColumn(), "リンク": st.column_config.LinkColumn()}, hide_index=True)
                
                # お宝判定
                if df.iloc[0]["予想利益"] > 0:
                    st.balloons()
                    st.error(f"🔥 お宝発見！ 利益: {df.iloc[0]['予想利益']:,}円")
            else: st.warning("条件に合う出品はありません。フィルターを緩めてみて！")
        else: st.error("過去データが見つかりません。")