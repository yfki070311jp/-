# coding: utf-8
import os
import json
import pandas as pd
import streamlit as st
from datetime import datetime, time, date, timedelta, timezone

# タイムゾーンの設定（常に日本時間にする）
JST = timezone(timedelta(hours=+9), 'JST')

DATA_DIR = "data"
INVENTORY_FILE = os.path.join(DATA_DIR, "inventory.csv")
HISTORY_FILE = os.path.join(DATA_DIR, "history.csv")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

os.makedirs(DATA_DIR, exist_ok=True)

# 安全に数値変換するヘルパー関数
def safe_int(val, default=0):
    try:
        num = pd.to_numeric(val, errors='coerce')
        return int(num) if pd.notnull(num) else default
    except Exception:
        return default

def save_data():
    st.session_state.inventory.to_csv(INVENTORY_FILE, index=False, encoding="utf-8-sig")
    st.session_state.history.to_csv(HISTORY_FILE, index=False, encoding="utf-8-sig")
    settings = {
        "ticket_counter": st.session_state.ticket_counter,
        "master_prices": st.session_state.master_prices,
        "start_inventory_set": st.session_state.start_inventory_set
    }
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    st.session_state.start_inventory.to_csv(os.path.join(DATA_DIR, "start_inventory.csv"), index=False, encoding="utf-8-sig")

default_inventory = pd.DataFrame([
    {'商品名': 'チュロス（チョコ）', '価格': 200, '在庫数': 400},
    {'商品名': 'チュロス（シナモン）', '価格': 200, '在庫数': 200},
    {'商品名': 'シュー（いちご）', '価格': 100, '在庫数': 180},
    {'商品名': 'シュー（バニラ）', '価格': 100, '在庫数': 180},
    {'商品名': 'シュー（抹茶）', '価格': 100, '在庫数': 90},
    {'商品名': 'シュー（チョコ）', '価格': 100, '在庫数': 90}
])

default_history = pd.DataFrame(columns=['日時', '商品名', '数量', '合計金額', '整理券番号', '受け渡し済'])

# --- 初期化処理 ---
if 'inventory' not in st.session_state:
    if os.path.exists(INVENTORY_FILE):
        try:
            st.session_state.inventory = pd.read_csv(INVENTORY_FILE, encoding="utf-8-sig")
            st.session_state.inventory['価格'] = st.session_state.inventory['価格'].apply(lambda x: safe_int(x, 0))
            st.session_state.inventory['在庫数'] = st.session_state.inventory['在庫数'].apply(lambda x: safe_int(x, 0))
        except Exception:
            st.session_state.inventory = default_inventory.copy()
    else:
        st.session_state.inventory = default_inventory.copy()

if 'history' not in st.session_state:
    if os.path.exists(HISTORY_FILE):
        try:
            st.session_state.history = pd.read_csv(HISTORY_FILE, encoding="utf-8-sig")
            # 数量カラムの型安全確保
            if '数量' in st.session_state.history.columns:
                st.session_state.history['数量'] = st.session_state.history['数量'].apply(lambda x: safe_int(x, 0))
            else:
                st.session_state.history['数量'] = 0

            if '受け渡し済' in st.session_state.history.columns:
                def parse_bool(val):
                    if isinstance(val, bool): return val
                    if pd.isna(val): return False
                    str_val = str(val).strip().lower()
                    return True if str_val in ['true', '1', 'yes', 't', 'y'] else False
                st.session_state.history['受け渡し済'] = st.session_state.history['受け渡し済'].apply(parse_bool)
            else:
                st.session_state.history['受け渡し済'] = False
        except Exception:
            st.session_state.history = default_history.copy()
    else:
        st.session_state.history = default_history.copy()
else:
    # セッション内に既に存在する場合も数量の安全性を担保
    if '数量' in st.session_state.history.columns:
        st.session_state.history['数量'] = st.session_state.history['数量'].apply(lambda x: safe_int(x, 0))

if 'master_prices' not in st.session_state:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
            st.session_state.master_prices = {str(k): int(v) for k, v in settings.get("master_prices", {}).items()}
        except Exception:
            st.session_state.master_prices = {row['商品名']: safe_int(row['価格']) for _, row in st.session_state.inventory.iterrows() if pd.notnull(row['商品名'])}
    else:
        st.session_state.master_prices = {row['商品名']: safe_int(row['価格']) for _, row in st.session_state.inventory.iterrows() if pd.notnull(row['商品名'])}

if 'start_inventory' not in st.session_state:
    start_file = os.path.join(DATA_DIR, "start_inventory.csv")
    if os.path.exists(start_file):
        try:
            st.session_state.start_inventory = pd.read_csv(start_file, encoding="utf-8-sig")
        except Exception:
            st.session_state.start_inventory = st.session_state.inventory.copy()
    else:
        st.session_state.start_inventory = st.session_state.inventory.copy()

if 'start_inventory_set' not in st.session_state:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
            st.session_state.start_inventory_set = settings.get("start_inventory_set", False)
        except Exception:
            st.session_state.start_inventory_set = False
    else:
        st.session_state.start_inventory_set = False

if 'ticket_counter' not in st.session_state:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
            st.session_state.ticket_counter = int(settings.get("ticket_counter", 1))
        except Exception:
            st.session_state.ticket_counter = 1
    else:
        st.session_state.ticket_counter = 1

st.title("簡易レジ＆在庫管理アプリ")

# --- モード切替 ---
st.sidebar.header("🔐 モード切替")
passcode = st.sidebar.text_input("管理者パスワード（編集用）", type="password")
ADMIN_PASSWORD = "1234"

is_admin = (passcode == ADMIN_PASSWORD)
if is_admin:
    st.sidebar.success("🟢 編集モード（PC操作中）")
else:
    st.sidebar.warning("🔒 閲覧専用モード")

# --- 営業日時の設定 ---
st.sidebar.header("🕒 営業日時の設定")
today = datetime.now(JST).date()
start_date_input = st.sidebar.date_input("開始日", value=today, key="s_date")
start_time_input = st.sidebar.time_input("開始時間", value=time(9, 30), key="s_time")
s_dt = datetime.combine(start_date_input, start_time_input)

end_date_input = st.sidebar.date_input("終了日", value=today, key="e_date")
end_time_input = st.sidebar.time_input("終了時間", value=time(14, 0), key="e_time")
e_dt = datetime.combine(end_date_input, end_time_input)

if e_dt <= s_dt:
    e_dt += timedelta(days=1)

def is_peak_time(dt_slot):
    current_minutes = dt_slot.hour * 60 + dt_slot.minute
    return (11 * 60) <= current_minutes < (13 * 60)

now = datetime.now(JST).replace(tzinfo=None)

elapsed_sales = {}
if not st.session_state.history.empty:
    hist_df = st.session_state.history.copy()
    hist_df['dt'] = pd.to_datetime(hist_df['日時'], errors='coerce')
    hist_df = hist_df.dropna(subset=['dt'])
    # 数量を確実に数値化して集計
    hist_df['数量'] = hist_df['数量'].apply(lambda x: safe_int(x, 0))
    target_end = min(e_dt, now)
    target_hist = hist_df[(hist_df['dt'] >= s_dt) & (hist_df['dt'] <= target_end)]
    if not target_hist.empty:
        elapsed_sales = target_hist.groupby('商品名')['数量'].sum().to_dict()

total_minutes = max(1, int((e_dt - s_dt).total_seconds() / 60))
elapsed_weight = 0.0
total_weight = 0.0

if total_minutes > 60 * 24 * 3:
    st.sidebar.error("⚠️ 営業期間が長すぎます（最大3日まで）。予測計算を簡易モードに切り替えます。")
    total_weight = float(total_minutes)
    if now > s_dt:
        actual_end = min(now, e_dt)
        elapsed_weight = max(0.1, (actual_end - s_dt).total_seconds() / 60)
else:
    curr = s_dt
    while curr < e_dt:
        next_minute = curr + timedelta(minutes=1)
        if next_minute > e_dt:
            next_minute = e_dt
        minute_length = (next_minute - curr).total_seconds() / 60
        middle = curr + (next_minute - curr) / 2
        weight = 1.5 if is_peak_time(middle) else 1.0
        total_weight += weight * minute_length
        if curr < now:
            actual_end = min(next_minute, now)
            actual_minutes = (actual_end - curr).total_seconds() / 60
            if actual_minutes > 0:
                elapsed_weight += weight * actual_minutes
        curr = next_minute

if elapsed_weight <= 0:
    elapsed_weight = 0.1

total_duration = (e_dt - s_dt).total_seconds()
remaining_duration = (e_dt - now).total_seconds()
time_progress = max(0.0, min(1.0, remaining_duration / total_duration)) if total_duration > 0 else 0.5

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["レジ（会計）", "在庫管理", "販売履歴", "整理券確認", "販売予測", "価格提案"])

# --- Tab 1: レジ ---
with tab1:
    st.header("高速お会計")
    if not is_admin:
        st.info("💡 閲覧モード中のため、レジ操作は無効化されています。")
    
    inv = st.session_state.inventory.dropna(subset=['商品名'])
    if 'temp_cart' not in st.session_state:
        st.session_state.temp_cart = {}
    current_product_names = [str(name) for name in inv['商品名']]
    st.session_state.temp_cart = {name: st.session_state.temp_cart.get(name, 0) for name in current_product_names}

    for index, row in inv.iterrows():
        p_name = str(row['商品名'])
        p_price = safe_int(row['価格'])
        p_stock = safe_int(row['在庫数'])

        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        if p_stock <= 0:
            c1.write(f"**{p_name}** (¥{p_price} / 🔴 売り切れ)")
        else:
            c1.write(f"**{p_name}** (¥{p_price} / 在庫:{p_stock})")

        if c2.button("－", key=f"sub_{p_name}", disabled=not is_admin):
            if st.session_state.temp_cart.get(p_name, 0) > 0:
                st.session_state.temp_cart[p_name] -= 1
                st.rerun()

        c3.write(f"### {st.session_state.temp_cart.get(p_name, 0)}")

        if c4.button("＋", key=f"add_{p_name}", disabled=(p_stock <= 0 or not is_admin)):
            if st.session_state.temp_cart.get(p_name, 0) < p_stock:
                st.session_state.temp_cart[p_name] += 1
                st.rerun()

    st.divider()
    total_price = 0
    for name, qty in st.session_state.temp_cart.items():
        if qty > 0 and name in inv['商品名'].values:
            match_row = inv[inv['商品名'] == name]
            if not match_row.empty:
                price = safe_int(match_row['価格'].iloc[0])
                total_price += price * qty

    st.info(f"合計金額: **¥{total_price}**")
    
    now_str = datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')

    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button("整理券なしで会計", disabled=not is_admin):
            if not any(q > 0 for q in st.session_state.temp_cart.values()):
                st.error("商品が選択されていません。")
            else:
                for name, qty in st.session_state.temp_cart.items():
                    if qty > 0:
                        idx = st.session_state.inventory.index[st.session_state.inventory['商品名'] == name][0]
                        price = safe_int(st.session_state.inventory.at[idx, '価格'])
                        st.session_state.inventory.at[idx, '在庫数'] = safe_int(st.session_state.inventory.at[idx, '在庫数']) - qty
                        new_hist = pd.DataFrame([{'日時': now_str, '商品名': name, '数量': qty, '合計金額': price * qty, '整理券番号': "なし", '受け渡し済': True}])
                        st.session_state.history = pd.concat([st.session_state.history, new_hist], ignore_index=True)
                save_data()
                st.session_state.temp_cart = {name: 0 for name in current_product_names}
                st.success("会計完了！")
                st.rerun()

    with col_btn2:
        if st.button("整理券を発行して会計", disabled=not is_admin):
            if not any(q > 0 for q in st.session_state.temp_cart.values()):
                st.error("商品が選択されていません。")
            else:
                ticket_num = st.session_state.ticket_counter
                for name, qty in st.session_state.temp_cart.items():
                    if qty > 0:
                        idx = st.session_state.inventory.index[st.session_state.inventory['商品名'] == name][0]
                        price = safe_int(st.session_state.inventory.at[idx, '価格'])
                        st.session_state.inventory.at[idx, '在庫数'] = safe_int(st.session_state.inventory.at[idx, '在庫数']) - qty
                        new_hist = pd.DataFrame([{'日時': now_str, '商品名': name, '数量': qty, '合計金額': price * qty, '整理券番号': ticket_num, '受け渡し済': False}])
                        st.session_state.history = pd.concat([st.session_state.history, new_hist], ignore_index=True)
                st.session_state.ticket_counter += 1
                save_data()
                st.session_state.temp_cart = {name: 0 for name in current_product_names}
                st.success(f"会計完了！整理券番号: **{ticket_num}**")
                st.rerun()

    with col_btn3:
        if st.button("かごを空にする", disabled=not is_admin):
            st.session_state.temp_cart = {name: 0 for name in current_product_names}
            st.rerun()

# --- Tab 2: 在庫管理 ---
with tab2:
    st.header("在庫管理")
    if is_admin:
        edited_inventory = st.data_editor(
            st.session_state.inventory,
            use_container_width=True,
            num_rows="dynamic",
            key="inventory_editor",
            column_config={
                "価格": st.column_config.NumberColumn("価格", min_value=0, step=10),
                "在庫数": st.column_config.NumberColumn("在庫数", min_value=0, step=1)
            }
        )
        if not edited_inventory.equals(st.session_state.inventory):
            edited_inventory['価格'] = edited_inventory['価格'].apply(lambda x: safe_int(x, 0))
            edited_inventory['在庫数'] = edited_inventory['在庫数'].apply(lambda x: safe_int(x, 0))
            st.session_state.inventory = edited_inventory
            save_data()
            st.rerun()
    else:
        st.dataframe(st.session_state.inventory, use_container_width=True)

# --- Tab 3: 販売履歴 ---
with tab3:
    st.header("販売履歴")
    if not st.session_state.history.empty:
        st.metric("総売上金額", f"¥{st.session_state.history['合計金額'].sum()}")
        for i, row in st.session_state.history.iloc[::-1].iterrows():
            c1, c2 = st.columns([4, 1])
            t_label = f"券#{row['整理券番号']}" if row['整理券番号'] != "なし" else "整理券なし"
            status_label = " [受け渡し済]" if row.get('受け渡し済', False) else ""
            c1.write(f"{t_label}{status_label} | {row['日時']} | {row['商品名']} | {row['数量']}個 | ¥{row['合計金額']}")
            if is_admin:
                if c2.button("削除", key=f"del_{i}"):
                    p_name = row['商品名']
                    p_qty = safe_int(row['数量'])
                    if p_name in st.session_state.inventory['商品名'].values:
                        idx = st.session_state.inventory.index[st.session_state.inventory['商品名'] == p_name][0]
                        st.session_state.inventory.at[idx, '在庫数'] = safe_int(st.session_state.inventory.at[idx, '在庫数']) + p_qty
                    st.session_state.history = st.session_state.history.drop(i).reset_index(drop=True)
                    save_data()
                    st.rerun()
    else:
        st.write("履歴はありません。")

# --- Tab 4: 整理券確認 ---
with tab4:
    st.header("整理券確認・受け渡し管理")
    if not st.session_state.history.empty:
        valid_tickets = [t for t in st.session_state.history['整理券番号'].unique() if str(t) != "なし"]
        if valid_tickets:
            # 型混在や辞書順ソートの問題を防ぐため、安全に数値としてソート（失敗時は文字列として安全に処理）
            def safe_sort_key(val):
                try:
                    return (0, int(val))
                except (ValueError, TypeError):
                    return (1, str(val))

            sorted_tickets = sorted(valid_tickets, key=safe_sort_key, reverse=True)

            for t_num in sorted_tickets:
                ticket_rows = st.session_state.history[st.session_state.history['整理券番号'] == t_num]
                is_all_delivered = all(ticket_rows['受け渡し済'])
                expander_title = f"整理券番号: {t_num}" + (" ✅ 【完了】" if is_all_delivered else " ⏳ 【未】")
                with st.expander(expander_title):
                    new_status = st.checkbox("受け渡しを完了にする", value=is_all_delivered, key=f"check_{t_num}", disabled=not is_admin)
                    if is_admin and (new_status != is_all_delivered):
                        st.session_state.history.loc[ticket_rows.index, '受け渡し済'] = new_status
                        save_data()
                        st.rerun()
                    st.table(ticket_rows[['商品名', '数量', '合計金額']])

# --- Tab 5: 販売予測 ---
with tab5:
    st.header("販売予測 ＆ 予想在庫残数")
    res = []
    for _, row in inv.iterrows():
        p_name = row['商品名']
        current_stock = safe_int(row['在庫数'])
        start_val = st.session_state.start_inventory[st.session_state.start_inventory['商品名'] == p_name]['在庫数']
        start_stock = safe_int(start_val.values[0]) if not start_val.empty else current_stock
        sold = safe_int(elapsed_sales.get(p_name, 0))
        manual_loss = max(0, (start_stock - sold) - current_stock)
        est_total = int((sold / elapsed_weight) * total_weight) + manual_loss
        expected_remaining = max(0, current_stock - int((sold / elapsed_weight) * (total_weight - elapsed_weight)))
        res.append({
            '商品名': p_name,
            '開始時在庫': start_stock,
            '期間内販売数': sold,
            '予測総販売数': est_total,
            '終了時予想残り': expected_remaining
        })
    if res: st.table(pd.DataFrame(res))

# --- Tab 6: 価格提案 ---
with tab6:
    st.header("価格提案")
    res = []
    for _, row in inv.iterrows():
        p_name = row['商品名']
        price = st.session_state.master_prices.get(p_name, safe_int(row['価格']))
        current_stock = safe_int(row['在庫数'])
        start_val = st.session_state.start_inventory[st.session_state.start_inventory['商品名'] == p_name]['在庫数']
        start_stock = safe_int(start_val.values[0]) if not start_val.empty else current_stock
        sold = safe_int(elapsed_sales.get(p_name, 0))
        future_sales_est = int((sold / elapsed_weight) * (total_weight - elapsed_weight))
        expected_remaining = max(0, current_stock - future_sales_est)
        
        status, strong_price, weak_price = "現状維持", "-", "-"
        if expected_remaining > 0 and sold > 0:
            status = "要値下げ"
            strong_rate = max(0.5, 1.0 - ((1.0 - time_progress) * (expected_remaining / start_stock) * 0.45))
            strong_price = f"¥{int((price * strong_rate) / 10) * 10}"
            weak_price = f"¥{int(price * max(0.5, min(0.95, 1.0 / (current_stock / ((sold / elapsed_weight) * total_weight)))) / 10) * 10}"
        res.append({'商品名': p_name, 'ステータス': status, '強気提案': strong_price, '弱気提案': weak_price})
    if res: st.table(pd.DataFrame(res))
