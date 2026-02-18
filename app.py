import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import statistics
import urllib.parse # URLを作るための道具

# --- ページ設定 ---
st.set_page_config(page_title="最強せどりツールv7.0", layout="wide")

st.title("🤖 完全自動せどりマシーン v7.0 (神の目モード)")
st.write("メルカリのライバル価格を一瞬でチェック＆相場トレンドをグラフ化！")

# --- サイドバー ---
st.sidebar.header("🔍 検索設定")
keyword = st.sidebar.text_input("検索ワード", "iPhone 12 64GB")
exclude_junk = st.sidebar.checkbox("「ジャンク」を除外", value=True)
shipping_cost = st.sidebar.number_input("送料（円）", value=750, step=50)

# --- 関数 ---
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
                
                # ジャンク除外
                if exclude_junk:
                    if "ジャンク" in title or "JUNK" in title or "訳あり" in title or "難あり" in title:
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
if st.button("🚀 全自動リサーチ開始！"):
    
    st.info(f"1️⃣ 「{keyword}」の過去相場とトレンドを分析中...")
    
    sold_url = f"https://auctions.yahoo.co.jp/closedsearch/closedsearch?p={keyword}&n=50"
    sold_items = get_yahoo_data(sold_url)
    
    if len(sold_items) > 0:
        sold_prices = [item["price"] for item in sold_items]
        market_price = int(statistics.mean(sold_prices))
        
        # === ★新機能1：トレンドグラフの表示 ===
        st.success(f"📈 データ分析完了！ 平均相場: {market_price:,}円")
        
        # グラフ用にデータを加工
        chart_data = pd.DataFrame({"落札価格": sold_prices})
        st.bar_chart(chart_data, color="#FF4B4B") # 赤い棒グラフで表示
        st.caption("👆 左側が高い値段、右側が安い値段の分布です。山がどこにあるか見てみよう！")

        # === ★新機能2：メルカリ＆Amazonへのリンク生成 ===
        # キーワードをURL用に変換（日本語→%E3%81...みたいな記号にする）
        safe_keyword = urllib.parse.quote(keyword)
        mercari_link = f"https://www.mercari.com/jp/search/?keyword={safe_keyword}&status_on_sale=1"
        amazon_link = f"https://www.amazon.co.jp/s?k={safe_keyword}"
        
        st.markdown("### 🌏 ライバル市場をチェック（答え合わせ）")
        col_link1, col_link2 = st.columns(2)
        col_link1.link_button("メルカリで今の相場を見る", mercari_link, type="primary")
        col_link2.link_button("Amazonで新品価格を見る", amazon_link)

        st.divider() # 区切り線
        
        # === 現在価格の調査 ===
        st.info(f"2️⃣ ヤフオクで出品中のお宝を探しています...")
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
            
            st.markdown("### 🎯 お宝商品リスト")
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
            
            # ベスト商品表示
            best_item = df.iloc[0]
            if best_item["予想利益"] > 0:
                st.balloons()
                col_best1, col_best2 = st.columns([1, 3])
                with col_best1:
                    st.image(best_item["画像"], width=150)
                with col_best2:
                    st.markdown(f"### 👑 キング・オブ・お宝")
                    st.write(f"**{best_item['商品名']}**")
                    st.error(f"現在価格: {best_item['現在価格']:,}円")
                    st.metric("予想利益", f"+{best_item['予想利益']:,}円")
                    st.write(f"👉 [商品ページへGO!]({best_item['リンク']})")
            else:
                st.warning("今は利益が出る商品はなさそうです。")
        else:
            st.error("出品中の商品が見つかりませんでした。")
    else:
        st.error("過去データが見つかりませんでした。")