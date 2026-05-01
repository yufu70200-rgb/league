import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# 設定標題
st.set_page_config(page_title="LoL 對策助手", layout="wide")
st.title("🎮 我的英雄聯盟對敵大數據")

def get_data():
    # 注意：資料庫檔案是在 league 資料夾內
    conn = sqlite3.connect('my_lol_stats.db')
    df = pd.read_sql_query("SELECT * FROM matches", conn)
    conn.close()
    return df

try:
    df = get_data()
    if df.empty:
        st.warning("資料庫裡還沒有比賽紀錄，請先執行 lol_track.py！")
    else:
        # 側邊欄選單
        all_enemies = sorted(df['enemy_hero'].unique())
        selected_enemy = st.sidebar.selectbox("🎯 選擇敵方英雄", all_enemies)

        enemy_stats = df[df['enemy_hero'] == selected_enemy]
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"對戰 {selected_enemy} 勝率")
            win_count = enemy_stats['result'].sum()
            loss_count = len(enemy_stats) - win_count
            fig = px.pie(values=[win_count, loss_count], names=['勝', '敗'], hole=0.4)
            st.plotly_chart(fig)

        with col2:
            st.subheader("我方最佳選角")
            hero_analysis = enemy_stats.groupby('my_hero')['result'].mean().reset_index()
            hero_analysis['勝率'] = hero_analysis['result'] * 100
            fig_bar = px.bar(hero_analysis, x='my_hero', y='勝率', text='勝率')
            st.plotly_chart(fig_bar)

        st.subheader("📋 詳細對戰歷史")
        st.dataframe(enemy_stats)

except Exception as e:
    st.error(f"目前還沒抓到資料庫：{e}")