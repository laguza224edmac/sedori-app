import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import statistics
import urllib.parse
from pyzbar.pyzbar import decode
from PIL import Image

# --- ページ設定 ---
st.set_page_config(page_title="プロ・ハンター v9.0", layout="wide")

st.title("🏹 プロ・ハンター v9.0")
st.write("利益アラート ＆ 複数市場リサーチモード")

# --- サイドバー設定 ---
st.sidebar.header("⚙️ ハンター設定")
input_mode = st.sidebar.radio("検索モード", ["バーコード読み取り", "キーワード入力"])
alert_threshold = st.sidebar.number_input("利益アラートの基準（円）", value=2000, step=500)
shipping_cost = st.sidebar.number_input("送料（円）", value=750, step=50)

keyword = ""

# --- カメラでバーコード読み取り ---
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

# --- 価格取得のための裏方ツール ---
def get_yahoo_price(kw):
    url = f"https://auctions.yahoo.co.jp/closedsearch/closedsearch?p={kw}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        prices = [int(p.text.replace("円", "").replace(",", "").strip()) for p in soup.find_all(class_="Product__priceValue") if p.text.replace("円", "").replace(",", "").strip().isdigit()]
        return int(statistics.mean(prices)) if prices else 0
    except:
        return 0

def get_rakuten_price(kw):
    url = f"https://search.rakuten.co.jp/search/mall/{kw}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        prices = [int(p.text.replace(",", "").strip()) for p in soup.find_all(class_="_price") if p.text.replace(",", "").strip().isdigit()]
        return min(prices) if prices else 0
    except:
        return 0

# --- メインのリサーチ処理 ---
if keyword:
    st.divider()
    if st.button("🚀 全市場一斉リサーチ開始！"):
        with st.spinner('各市場のデータを全力で計算中...'):
            yahoo_avg = get_yahoo_price(keyword)
            rakuten_min = get_rakuten_price(keyword)
            
            # --- 画面表示：相場比較 ---
            st.markdown("### 📊 市場の相場チェック")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("ヤフオク落札相場", f"{yahoo_avg:,}円")
            with col2:
                st.metric("楽天最安値(新品目安)", f"{rakuten_min:,}円")

            st.divider()

            # --- ヤフオクで現在出品中の利益商品をチェック ---
            st.info("現在出品中のお宝を探しています...")
            url_current = f"https://auctions.yahoo.co.jp/search/search?p={keyword}"
            res_curr = requests.get(url_current, headers={"User-Agent": "Mozilla/5.0"})
            soup_curr = BeautifulSoup(res_curr.text, 'html.parser')
            
            current_items = []
            for item in soup_curr.find_all("li", class_="Product")[:10]: # 上位10件を素早くチェック
                t = item.find("a", class_="Product__titleLink")
                p = item.find("span", class_="Product__priceValue")
                if t and p:
                    price = int(p.text.replace("円", "").replace(",", "").strip())
                    profit = int((yahoo_avg * 0.9) - shipping_cost - price) # 利益計算
                    current_items.append({"商品名": t.text.strip(), "価格": price, "利益": profit, "URL": t.get("href")})
            
            if current_items:
                df = pd.DataFrame(current_items).sort_values(by="利益", ascending=False)
                best = df.iloc[0]

                # === ★新機能：利益アラート★ ===
                if best["利益"] >= alert_threshold:
                    st.balloons() # 風船でお祝い！
                    st.toast("お宝発見！基準をクリアしました！", icon="💰") # スマホ用ポップアップ
                    st.error(f"🚨 【激アツ】予想利益 +{best['利益']:,}円 の商品があります！")
                    st.markdown(f"**狙い目商品:** [{best['商品名']}]({best['URL']})")
                else:
                    st.info(f"現在の最高利益：+{best['利益']:,}円（設定した基準まであと {alert_threshold - best['利益']}円）")

                # リスト表示
                st.write("### 📋 簡易リサーチリスト")
                st.table(df[["商品名", "価格", "利益"]])
            else:
                st.warning("現在出品中のアイテムが見つかりませんでした。")