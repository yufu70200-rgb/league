import requests
import sqlite3
import time

# ==========================================
# 1. 你的個人金鑰與身分 ID
# ==========================================
API_KEY = "RGAPI-ba494fe4-b324-4cf9-b96c-1a8e08682e2a"
MY_PUUID = "HwK2Dc6FQP-k0uiZnKnmbwt3GkZ2S0mIbY7A9ZdeMahIT8pid-lyEDO03I_TMpP0fVE4pGh2hIUyQ"
REGION = "asia" # 台灣伺服器區域

def init_db():
    """初始化 SQLite 資料庫"""
    conn = sqlite3.connect('my_lol_stats.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            match_id TEXT PRIMARY KEY,
            my_hero TEXT,
            enemy_hero TEXT,
            result INTEGER,
            kills INTEGER,
            deaths INTEGER,
            assists INTEGER,
            position TEXT
        )
    ''')
    conn.commit()
    return conn

def sync_data(count=20):
    """從 Riot API 同步戰績到本地資料庫"""
    conn = init_db()
    cursor = conn.cursor()
    headers = {"X-Riot-Token": API_KEY}
    
    # 步驟 A: 抓取比賽 ID 列表
    match_list_url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{MY_PUUID}/ids?start=0&count={count}"
    
    try:
        res = requests.get(match_list_url, headers=headers)
        if res.status_code != 200:
            print(f"❌ 無法獲取比賽列表: {res.status_code}")
            return
        
        match_ids = res.json()
        print(f"📡 找到 {len(match_ids)} 場比賽，準備檢查更新...")

        for m_id in match_ids:
            # 檢查是否已經抓過這場了
            cursor.execute("SELECT match_id FROM matches WHERE match_id=?", (m_id,))
            if cursor.fetchone():
                continue

            # 步驟 B: 抓取單場詳細資料
            detail_url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{m_id}"
            detail = requests.get(detail_url, headers=headers).json()
            
            try:
                participants = detail['info']['participants']
                # 找到我自己的數據
                me = next(p for p in participants if p['puuid'] == MY_PUUID)
                my_pos = me['teamPosition']
                
                # 找到對位對手 (同位置、不同隊)
                # 注意：如果打 ARAM 或特殊模式，可能找不到對位，會跳過
                enemy = next(p for p in participants if p['teamPosition'] == my_pos and p['teamId'] != me['teamId'])
                
                cursor.execute('''
                    INSERT INTO matches (match_id, my_hero, enemy_hero, result, kills, deaths, assists, position)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (m_id, me['championName'], enemy['championName'], 1 if me['win'] else 0, me['kills'], me['deaths'], me['assists'], my_pos))
                
                print(f"📝 成功記錄: {me['championName']} vs {enemy['championName']} ({'勝' if me['win'] else '敗'})")
                
            except StopIteration:
                print(f"⏩ 跳過非對稱對位場次 (如 ARAM): {m_id}")
            
            # 頻率限制保護 (1.2秒抓一場)
            time.sleep(1.2)

        conn.commit()
        print("\n✅ 資料庫同步完成！")
        
    except Exception as e:
        print(f"💥 發生錯誤: {e}")
    finally:
        conn.close()

def query_counter(enemy_name):
    """查詢對付特定英雄的最佳選擇"""
    conn = sqlite3.connect('my_lol_stats.db')
    cursor = conn.cursor()
    
    # 搜尋 enemy_hero (不分大小寫)
    cursor.execute('''
        SELECT my_hero, 
               COUNT(*) as games, 
               SUM(result)*100.0/COUNT(*) as win_rate,
               AVG(kills) as avg_k, AVG(deaths) as avg_d, AVG(assists) as avg_a
        FROM matches 
        WHERE enemy_hero LIKE ?
        GROUP BY my_hero
        ORDER BY win_rate DESC
    ''', (enemy_name,))
    
    rows = cursor.fetchall()
    
    print(f"\n--- 💡 針對 {enemy_name} 的歷史戰績 ---")
    if not rows:
        print("目前資料庫還沒有對戰這隻英雄的紀錄喔！多打幾場再來查。")
    else:
        for row in rows:
            print(f"🔹 選「{row[0]}」: 勝率 {row[2]:.1f}% (共 {row[1]} 場)")
            print(f"   平均 KDA: {row[3]:.1}/{row[4]:.1}/{row[5]:.1}")
    conn.close()

if __name__ == "__main__":
    # 1. 先同步戰績 (第一次跑會比較久)
    sync_data(count=20)
    
    # 2. 進行查詢 (範例：查詢對付 Yasuo 的勝率)
    # 你可以把 Yasuo 換成任何你想查詢的英雄名稱
    print("\n[查詢測試]")
    target = input("請輸入你想查詢的敵方英雄名稱 (例如 Yasuo, Aatrox): ")
    if target:
        query_counter(target)