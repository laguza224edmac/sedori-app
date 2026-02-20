import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import statistics
import urllib.parse
from pyzbar.pyzbar import decode
from PIL import Image
import re

# --- ページ設定 ---
st.set_page_config(page_title="プロ・ハンター v9.1", layout="wide")

st.title("👑 プロ・ハンター v9.1 (完全版)")
st.write("バーコード × 利益アラート × ジャンク除外 の最強形態！")

# --- サイドバー設定 ---
st.sidebar.header("⚙️ ハンター設定")
input_mode = st.sidebar.radio("検索モード", ["バーコード読み取り", "キーワード入力"])
alert_threshold = st.sidebar.number_input("利益アラートの基準（円）", value=2000, step=500)
shipping_cost = st.sidebar.number_input("送料（円）", value=750, step=50)
exclude_junk = st.sidebar.checkbox("「ジャンク・ケースのみ」を除外", value=True) # ★完全復活！

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

# --- ★新機能：ゴミを弾く強力なフィルター ---
def is_junk(title):
    if not exclude_junk:
        return False
    # ここに書かれた言葉が入っている商品は無視します！
    junk_words = ["ジャンク", "JUNK", "訳あり", "難あり", "ケースのみ", "ケースだけ", "空箱"]
    for word in junk_words:
        if word in title:
            return True
    return False

# --- 価格取得のための裏方ツール ---
def get_yahoo_price(kw):
    url = f"https://auctions.yahoo.co.jp/closedsearch/closedsearch?p={kw}" # 過去の落札データだけを見る！
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        prices = []
        for item in soup.find_all("li", class_="Product"):
            t = item.find("a", class_="Product__titleLink")
            p = item.find("span", class_="Product__priceValue")
            if t and p:
                if is_junk(t.text): # ジャンクやケースを弾く！
                    continue
                price_text = p.text.replace("円", "").replace(",", "").strip()
                if price_text.isdigit():
                    prices.append(int(price_text))
        return int(statistics.mean(prices)) if prices else 0
    except:
        return 0

def get_rakuten_price(kw):
    # 楽天は日本語のURLエンコードが必要
    safe_kw = urllib.parse.quote(kw)
    url = f"https://search.rakuten.co.jp/search/mall/{safe_kw}/"
    # スマホやPCの「普通のブラウザ」のフリをする（怪しまれないように長くする）
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        prices = []
        # 作戦1：名前に「price」が含まれる場所を全部探す
        price_tags = soup.find_all(class_=re.compile("price", re.IGNORECASE))
        
        for tag in price_tags:
            text = tag.get_text()
            # 「1,980円」などから、数字以外の文字を全部消し去る！
            num_str = re.sub(r'\D', '', text) 
            if num_str:
                prices.append(int(num_str))
        
        # 極端に安いもの（送料表示の100円など）を省くため、500円以上の最安値にする
        valid_prices = [p for p in prices if p > 500]
        return min(valid_prices) if valid_prices else 0
        
    except Exception as e:
        print(f"楽天エラー: {e}") # もしエラーが出てもアプリが止まらないようにする
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
                st.metric("ヤフオク落札相場 (過去の実績)", f"{yahoo_avg:,}円")
            with col2:
                st.metric("楽天最安値 (新品目安)", f"{rakuten_min:,}円")

            st.divider()

            # --- ヤフオクで現在出品中の利益商品をチェック ---
            st.info("現在出品中のお宝を探しています...")
            url_current = f"https://auctions.yahoo.co.jp/search/search?p={keyword}" # 現在オークション中から探す
            res_curr = requests.get(url_current, headers={"User-Agent": "Mozilla/5.0"})
            soup_curr = BeautifulSoup(res_curr.text, 'html.parser')
            
            current_items = []
            for item in soup_curr.find_all("li", class_="Product")[:15]: 
                t = item.find("a", class_="Product__titleLink")
                p = item.find("span", class_="Product__priceValue")
                if t and p:
                    title_text = t.text.strip()
                    if is_junk(title_text): # ここでもジャンクやケースを弾く！
                        continue
                    price = int(p.text.replace("円", "").replace(",", "").strip())
                    profit = int((yahoo_avg * 0.9) - shipping_cost - price)
                    current_items.append({"商品名": title_text, "価格": price, "利益": profit, "URL": t.get("href")})
            
            if current_items:
                df = pd.DataFrame(current_items).sort_values(by="利益", ascending=False)
                best = df.iloc[0]

                # === ★利益アラート★ ===
                if best["利益"] >= alert_threshold:
                    st.balloons()
                    st.toast("お宝発見！基準をクリアしました！", icon="💰")
                    st.error(f"🚨 【激アツ】予想利益 +{best['利益']:,}円 の商品があります！")
                    st.markdown(f"**狙い目商品:** [{best['商品名']}]({best['URL']})")
                else:
                    st.info(f"現在の最高利益：+{best['利益']:,}円（設定した基準まであと {alert_threshold - best['利益']}円）")

                # リスト表示（キレイな表にしました！）
                st.write("### 📋 リサーチリスト")
                st.dataframe(
                    df,
                    column_config={
                        "URL": st.column_config.LinkColumn("商品ページへ"),
                        "価格": st.column_config.NumberColumn(format="%d円"),
                        "利益": st.column_config.NumberColumn(format="%d円"),
                    },
                    hide_index=True
                )
            else:
                st.warning("現在出品中のアイテム（ジャンク以外）が見つかりませんでした。")