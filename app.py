# coding: utf-8
import os
import json
import pandas as pd
import streamlit as st
from datetime import datetime, time, date, timedelta

DATA_DIR = "data"
INVENTORY_FILE = os.path.join(DATA_DIR, "inventory.csv")
HISTORY_FILE = os.path.join(DATA_DIR, "history.csv")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

os.makedirs(DATA_DIR, exist_ok=True)

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

if 'inventory' not in st.session_state:
    if os.path.exists(INVENTORY_FILE):
        try:
            st.session_state.inventory = pd.read_csv(INVENTORY_FILE, encoding="utf-8-sig")
        except Exception:
            st.session_state.inventory = default_inventory.copy()
    else:
        st.session_state.inventory = default_inventory.copy()

if 'history' not in st.session_state:
    if os.path.exists(HISTORY_FILE):
        try:
            st.session_state.history = pd.read_csv(HISTORY_FILE, encoding="utf-8-sig")
            if '受け渡し済' in st.session_state.history.columns:
                def parse_bool(val):
                    if isinstance(val, bool):
                        return val
                    if pd.isna(val):
                        return False
                    str_val = str(val).strip().lower()
                    if str_val in ['true', '1', 'yes', 't', 'y']:
                        return True
                    return False
                st.session_state.history['受け渡し済'] = st.session_state.history['受け渡し済'].apply(parse_bool)
            else:
                st.session_state.history['受け渡し済'] = False
        except Exception:
            st.session_state.history = default_history.copy()
    else:
        st.session_state.history = default_history.copy()

if 'master_prices' not in st.session_state:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
            st.session_state.master_prices = {str(k): int(v) for k, v in settings.get("master_prices", {}).items()}
        except Exception:
            st.session_state.master_prices = {row['商品名']: int(row['価格']) for _, row in st.session_state.inventory.iterrows() if pd.notnull(row['商品名']) and pd.notnull(row['価格'])}
    else:
        st.session_state.master_prices = {row['商品名']: int(row['価格']) for _, row in st.session_state.inventory.iterrows() if pd.notnull(row['商品名']) and pd.notnull(row['価格'])}

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

# --- モード切替（権限設定） ---
st.sidebar.header("🔐 モード切替")
passcode = st.sidebar.text_input("管理者パスワード（編集用）", type="password")
ADMIN_PASSWORD = "1234"  # 好きなパスワードに変更可能

is_admin = (passcode == ADMIN_PASSWORD)
if is_admin:
    st.sidebar.success("🟢 編集モード（PC操作中）")
else:
    st.sidebar.warning("🔒 閲覧専用モード")

st.sidebar.header("🕒 営業日時の設定")
today = date.today()
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

now = datetime.now()
elapsed_sales = {}
if not st.session_state.history.empty:
    hist_df = st.session_state.history.copy()
    hist_df['dt'] = pd.to_datetime(hist_df['日時'], errors='coerce')
    target_end = min(e_dt, now)
    target_hist = hist_df[(hist_df['dt'] >= s_dt) & (hist_df['dt'] <= target_end)]
    if not target_hist.empty:
        elapsed_sales = target_hist.groupby('商品名')['数量'].sum().to_dict()

total_minutes = max(1, int((e_dt - s_dt).total_seconds() / 60))
elapsed_weight = 0.0
total_weight = 0.0
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

with tab1:
    st.header("高速お会計（数量調整ボタン）")
    if not is_admin:
        st.info("💡 閲覧モード中のため、レジ操作は無効化されています。")
    inv = st.session_state.inventory.dropna(subset=['商品名'])
    
    if 'temp_cart' not in st.session_state:
        st.session_state.temp_cart = {}
    current_product_names = [str(name) for name in inv['商品名'] if pd.notnull(name)]
    st.session_state.temp_cart = {name: st.session_state.temp_cart.get(name, 0) for name in current_product_names}

    for index, row in inv.iterrows():
        p_name = row['商品名']
        if pd.isnull(p_name):
            continue
        p_name = str(p_name)
        p_price = int(row['価格']) if pd.notnull(row['価格']) else 0
        p_stock = int(row['在庫数']) if pd.notnull(row['在庫数']) else 0

        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        if p_stock <= 0:
            c1.write(f"**{p_name}** (¥{p_price} / 🔴 売り切れ)")
        else:
            c1.write(f"**{p_name}** (¥{p_price} / 在庫:{p_stock})")

        if c2.button("－", key=f"sub_{index}", disabled=not is_admin):
            if st.session_state.temp_cart.get(p_name, 0) > 0:
                st.session_state.temp_cart[p_name] -= 1
                st.rerun()

        c3.write(f"### {st.session_state.temp_cart.get(p_name, 0)}")

        if c4.button("＋", key=f"add_{index}", disabled=(p_stock <= 0 or not is_admin)):
            if st.session_state.temp_cart.get(p_name, 0) < p_stock:
                st.session_state.temp_cart[p_name] += 1
                st.rerun()

    st.divider()
    total_price = 0
    for name, qty in st.session_state.temp_cart.items():
        if qty > 0 and name in inv['商品名'].values:
            match_row = inv[inv['商品名'] == name]
            if not match_row.empty and pd.notnull(match_row['価格'].iloc[0]):
                price = int(match_row['価格'].iloc[0])
                total_price += price * qty

    st.info(f"合計金額: **¥{total_price}**")
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        if st.button("整理券なしで会計", disabled=not is_admin):
            has_item = any(q > 0 for q in st.session_state.temp_cart.values())
            if not has_item:
                st.error("商品が選択されていません。")
            else:
                insufficient = []
                for name, qty in st.session_state.temp_cart.items():
                    if qty <= 0:
                        continue
                    match = st.session_state.inventory[st.session_state.inventory['商品名'] == name]
                    if match.empty:
                        continue
                    current_stock = int(match['在庫数'].iloc[0])
                    if qty > current_stock:
                        insufficient.append(f"{name}（在庫{current_stock}個）")
                if insufficient:
                    st.error("在庫不足です：" + "、".join(insufficient))
                else:
                    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    for name, qty in st.session_state.temp_cart.items():
                        if qty > 0:
                            idx = st.session_state.inventory.index[st.session_state.inventory['商品名'] == name][0]
                            price = int(st.session_state.inventory.at[idx, '価格'])
                            st.session_state.inventory.at[idx, '在庫数'] -= qty
                            new_hist = pd.DataFrame([{'日時': now_str, '商品名': name, '数量': qty, '合計金額': price * qty, '整理券番号': "なし", '受け渡し済': True}])
                            st.session_state.history = pd.concat([st.session_state.history, new_hist], ignore_index=True)
                    save_data()
                    st.success("会計完了！（整理券なし）")
                    st.session_state.temp_cart = {name: 0 for name in current_product_names}
                    st.rerun()

    with col_btn2:
        if st.button("整理券を発行して会計", disabled=not is_admin):
            has_item = any(q > 0 for q in st.session_state.temp_cart.values())
            if not has_item:
                st.error("商品が選択されていません。")
            else:
                insufficient = []
                for name, qty in st.session_state.temp_cart.items():
                    if qty <= 0:
                        continue
                    match = st.session_state.inventory[st.session_state.inventory['商品名'] == name]
                    if match.empty:
                        continue
                    current_stock = int(match['在庫数'].iloc[0])
                    if qty > current_stock:
                        insufficient.append(f"{name}（在庫{current_stock}個）")
                if insufficient:
                    st.error("在庫不足です：" + "、".join(insufficient))
                else:
                    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ticket_num = st.session_state.ticket_counter
                    for name, qty in st.session_state.temp_cart.items():
                        if qty > 0:
                            idx = st.session_state.inventory.index[st.session_state.inventory['商品名'] == name][0]
                            price = int(st.session_state.inventory.at[idx, '価格'])
                            st.session_state.inventory.at[idx, '在庫数'] -= qty
                            new_hist = pd.DataFrame([{'日時': now_str, '商品名': name, '数量': qty, '合計金額': price * qty, '整理券番号': ticket_num, '受け渡し済': False}])
                            st.session_state.history = pd.concat([st.session_state.history, new_hist], ignore_index=True)
                    st.session_state.ticket_counter += 1
                    save_data()
                    st.success(f"会計完了！整理券番号: **{ticket_num}**")
                    st.session_state.temp_cart = {name: 0 for name in current_product_names}
                    st.rerun()

    with col_btn3:
        if st.button("かごを空にする", disabled=not is_admin):
            st.session_state.temp_cart = {name: 0 for name in current_product_names}
            st.rerun()

with tab2:
    st.header("在庫管理")
    if is_admin:
        st.write("・表の内容（商品名、価格、在庫数）を変更すると自動で保存されます。")
        edited_inventory = st.data_editor(
            st.session_state.inventory,
            use_container_width=True,
            num_rows="dynamic",
            key="inventory_editor"
        )
        if not edited_inventory.equals(st.session_state.inventory):
            st.session_state.inventory = edited_inventory
            save_data()
            st.rerun()
    else:
        st.write("・現在の在庫状況です（閲覧専用）。")
        st.dataframe(st.session_state.inventory, use_container_width=True)

    for _, row in st.session_state.inventory.iterrows():
        p_name = row['商品名']
        p_price = row['価格']
        if pd.notnull(p_name) and pd.notnull(p_price):
            if p_name not in st.session_state.master_prices:
                st.session_state.master_prices[p_name] = int(p_price)
                if is_admin:
                    save_data()

    if is_admin:
        st.divider()
        if not st.session_state.start_inventory_set:
            if st.button("現在の在庫を開始時在庫として更新"):
                st.session_state.start_inventory = st.session_state.inventory.copy()
                st.session_state.start_inventory_set = True
                save_data()
                st.success("営業開始時の在庫基準を更新しました！")
                st.rerun()
        else:
            st.info("✅ 開始時在庫はすでに設定済みです。")
            if st.button("ロックを解除して再設定できるようにする"):
                st.session_state.start_inventory_set = False
                save_data()
                st.rerun()

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
                    p_qty = row['数量']
                    if p_name in st.session_state.inventory['商品名'].values:
                        idx = st.session_state.inventory.index[st.session_state.inventory['商品名'] == p_name][0]
                        st.session_state.inventory.at[idx, '在庫数'] = int(st.session_state.inventory.at[idx, '在庫数']) + p_qty
                    st.session_state.history = st.session_state.history.drop(i).reset_index(drop=True)
                    save_data()
                    st.rerun()
    else:
        st.write("履歴はありません。")

with tab4:
    st.header("整理券確認・受け渡し管理")
    if not st.session_state.history.empty:
        valid_tickets = [t for t in st.session_state.history['整理券番号'].unique() if t != "なし"]
        if valid_tickets:
            for t_num in sorted(valid_tickets, reverse=True):
                ticket_rows = st.session_state.history[st.session_state.history['整理券番号'] == t_num]
                is_all_delivered = all(ticket_rows['受け渡し済'])
                expander_title = f"整理券番号: {t_num}" + (" ✅ 【受け渡し完了】" if is_all_delivered else " ⏳ 【未】")
                with st.expander(expander_title):
                    new_status = st.checkbox("受け渡しを完了にする", value=is_all_delivered, key=f"check_{t_num}", disabled=not is_admin)
                    if is_admin and (new_status != is_all_delivered):
                        indices = ticket_rows.index
                        st.session_state.history.loc[indices, '受け渡し済'] = new_status
                        save_data()
                        st.rerun()
                    st.table(ticket_rows[['商品名', '数量', '合計金額']])
        else:
            st.write("現在発行されている有効な整理券はありません。")
    else:
        st.write("発行された整理券はありません。")

with tab5:
    st.header("販売予測 ＆ 予想在庫残数")
    res = []
    for _, row in inv.iterrows():
        p_name = row['商品名']
        if pd.isnull(p_name):
            continue
        current_stock = int(row['在庫数']) if pd.notnull(row['在庫数']) else 0
        start_val = st.session_state.start_inventory[st.session_state.start_inventory['商品名'] == p_name]['在庫数']
        start_stock = int(start_val.values[0]) if not start_val.empty and pd.notnull(start_val.values[0]) else current_stock
        sold = elapsed_sales.get(p_name, 0)
        expected_stock_by_sales = start_stock - sold
        manual_loss = max(0, expected_stock_by_sales - current_stock)
        est_total = int((sold / elapsed_weight) * total_weight) + manual_loss
        future_sales_est = int((sold / elapsed_weight) * (total_weight - elapsed_weight))
        expected_remaining = max(0, current_stock - future_sales_est)
        res.append({
            '商品名': p_name,
            '開始時在庫': start_stock,
            '期間内販売数': sold,
            '予測総販売数': est_total,
            '終了時予想残り': expected_remaining
        })
    if res:
        st.table(pd.DataFrame(res))
    else:
        st.write("有効な商品データがありません。")

with tab6:
    st.header("価格提案（強気 vs 弱気）")
    st.write("・**強気提案価格 / 弱気提案価格**: どちらも最大5割引を下限として制限しています。")
    res = []
    for _, row in inv.iterrows():
        p_name = row['商品名']
        if pd.isnull(p_name) or pd.isnull(row['価格']):
            continue
        price = st.session_state.master_prices.get(p_name, int(row['価格']))
        current_stock = int(row['在庫数']) if pd.notnull(row['在庫数']) else 0
        start_val = st.session_state.start_inventory[st.session_state.start_inventory['商品名'] == p_name]['在庫数']
        start_stock = int(start_val.values[0]) if not start_val.empty and pd.notnull(start_val.values[0]) else current_stock
        sold = elapsed_sales.get(p_name, 0)
        expected_stock_by_sales = start_stock - sold
        manual_loss = max(0, expected_stock_by_sales - current_stock)
        status = "現状維持"
        strong_price = "-"
        weak_price = "-"
        future_sales_est = int((sold / elapsed_weight) * (total_weight - elapsed_weight))
        expected_remaining = max(0, current_stock - future_sales_est)
        if expected_remaining > 0 and (sold > 0 or manual_loss > 0):
            status = "要値下げ"
            surplus_ratio = expected_remaining / start_stock if start_stock > 0 else 0
            urgency_factor = (1.0 - time_progress) * surplus_ratio
            strong_rate = max(0.5, 1.0 - (urgency_factor * 0.45))
            strong_price = f"¥{int((price * strong_rate) / 10) * 10}"
            effective_sold = sold + manual_loss
            current_pace_total = (effective_sold / elapsed_weight) * total_weight
            if current_pace_total > 0 and current_pace_total < current_stock:
                needed_multiplier = current_stock / current_pace_total
                raw_weak_rate = 1.0 / needed_multiplier
                weak_rate = max(0.5, min(0.95, raw_weak_rate))
                weak_price = f"¥{int((price * weak_rate) / 10) * 10}"
            else:
                weak_price = f"¥{int(price * 0.5 / 10) * 10}"
        res.append({
            '商品名': p_name,
            'ステータス': status,
            '強気提案価格': strong_price,
            '弱気提案価格': weak_price
        })
    if res:
        st.table(pd.DataFrame(res))
    else:
        st.write("有効な商品データがありません。")
