import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import statistics
import urllib.parse
from pyzbar.pyzbar import decode
from PIL import Image
import re

st.set_page_config(page_title="プロ・ハンター v9.2", layout="wide")

st.title("👑 プロ・ハンター v9.2 (精度向上版)")
st.write("アクセサリーや異常な安値を弾いて、正確な相場を計算します！")

# --- サイドバー設定 ---
st.sidebar.header("⚙️ ハンター設定")
input_mode = st.sidebar.radio("検索モード", ["バーコード読み取り", "キーワード入力"])
alert_threshold = st.sidebar.number_input("利益アラートの基準（円）", value=2000, step=500)
shipping_cost = st.sidebar.number_input("送料（円）", value=750, step=50)
exclude_junk = st.sidebar.checkbox("「ジャンク・ケース等」を除外", value=True)
min_price_filter = st.sidebar.number_input("最低価格フィルター（円）", value=3000, step=1000, help="この金額以下の商品はアクセサリーとみなして計算から除外します")

keyword = ""

if input_mode == "バーコード読み取り":
    st.info("👇 バーコードの写真を撮ってください")
    img_file_buffer = st.camera_input("バーコードをスキャン")
    if img_file_buffer:
        image = Image.open(img_file_buffer)
        decoded = decode(image)
        if decoded:
            keyword = decoded[0].data.decode("utf-8")
            st.success(f"🎯 読み取り成功: {keyword}")
        else:
            st.error("読み取り失敗... 明るい場所でもう一度試して！")
else:
    keyword = st.sidebar.text_input("検索ワード入力", "iPhone 12")

# --- ゴミ＆アクセサリー弾く強力なフィルター ---
def is_junk(title):
    if not exclude_junk:
        return False
    # フィルムやカバーなどのアクセサリーも追加！
    junk_words = ["ジャンク", "JUNK", "訳あり", "難あり", "ケース", "空箱", "フィルム", "カバー", "ガラス", "保護", "モック"]
    for word in junk_words:
        if word in title:
            return True
    return False

# --- 価格取得（ヤフオク） ---
def get_yahoo_price(kw):
    url = f"https://auctions.yahoo.co.jp/closedsearch/closedsearch?p={kw}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        prices = []
        for item in soup.find_all("li", class_="Product"):
            t = item.find("a", class_="Product__titleLink")
            p = item.find("span", class_="Product__priceValue")
            if t and p:
                if is_junk(t.text):
                    continue
                price_text = p.text.replace("円", "").replace(",", "").strip()
                if price_text.isdigit():
                    price_val = int(price_text)
                    # ★最低価格フィルター（安すぎるものはアクセサリーとみなして無視）
                    if price_val >= min_price_filter:
                        prices.append(price_val)
        return int(statistics.mean(prices)) if prices else 0
    except:
        return 0

# --- メインリサーチ ---
if keyword:
    st.divider()
    if st.button("🚀 リサーチ開始！"):
        with st.spinner('データを全力で計算中...'):
            yahoo_avg = get_yahoo_price(keyword)
            
            st.markdown("### 📊 市場の相場チェック")
            # 楽天は一旦ブロックされやすいのでヤフオクの相場に集中！
            st.metric("ヤフオク落札相場 (過去の実績)", f"{yahoo_avg:,}円")

            st.divider()

            st.info("現在出品中のお宝を探しています...")
            url_current = f"https://auctions.yahoo.co.jp/search/search?p={keyword}"
            res_curr = requests.get(url_current, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            soup_curr = BeautifulSoup(res_curr.text, 'html.parser')
            
            current_items = []
            for item in soup_curr.find_all("li", class_="Product")[:20]: 
                t = item.find("a", class_="Product__titleLink")
                p = item.find("span", class_="Product__priceValue")
                if t and p:
                    title_text = t.text.strip()
                    if is_junk(title_text):
                        continue
                    
                    price = int(p.text.replace("円", "").replace(",", "").strip())
                    profit = int((yahoo_avg * 0.9) - shipping_cost - price)
                    current_items.append({"商品名": title_text, "価格": price, "利益": profit, "URL": t.get("href")})
            
            if current_items:
                df = pd.DataFrame(current_items).sort_values(by="利益", ascending=False)
                best = df.iloc[0]

                # === ★表示のバグを修正★ ===
                if best["利益"] >= alert_threshold:
                    st.balloons()
                    st.error(f"🚨 【激アツ】予想利益 +{best['利益']:,}円 の商品があります！")
                    st.markdown(f"**狙い目商品:** [{best['商品名']}]({best['URL']})")
                else:
                    # マイナスの時は「+」をつけないように分岐！
                    profit_text = f"+{best['利益']:,}円" if best['利益'] > 0 else f"{best['利益']:,}円"
                    st.info(f"現在の最高利益：{profit_text} （設定した基準まであと {alert_threshold - best['利益']:,}円）")

                st.write("### 📋 リサーチリスト")
                st.dataframe(
                    df,
                    column_config={
                        "URL": st.column_config.LinkColumn("商品ページ"),
                        "価格": st.column_config.NumberColumn(format="%d円"),
                        "利益": st.column_config.NumberColumn(format="%d円"),
                    },
                    hide_index=True
                )
            else:
                st.warning("条件に合う出品が見つかりませんでした。")