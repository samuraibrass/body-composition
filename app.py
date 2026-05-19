import io
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import anthropic
from urllib.request import urlopen

SPREADSHEET_ID = "12pLQ_HQCuQgUdoivIkCytFZkqLtP2olT27TgsmtqUrk"


def _api_key() -> str:
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except (KeyError, FileNotFoundError):
        return os.environ.get("ANTHROPIC_API_KEY", "")


@st.cache_data(ttl=300)
def load_sheet():
    """Load body composition data and basic profile info from one sheet."""
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv"
    with urlopen(url) as resp:
        content = resp.read().decode("utf-8")

    lines = content.strip().split("\n")

    # Find the blank separator row between main data and profile info
    blank_idx = None
    for i, line in enumerate(lines):
        if all(v.strip() == "" for v in line.split(",")):
            blank_idx = i
            break

    main_csv = "\n".join(lines[:blank_idx]) if blank_idx else content
    extra_csv = "\n".join(lines[blank_idx + 1 :]) if blank_idx else ""

    # ── Main body composition data ──────────────────────────────────────────
    df = pd.read_csv(io.StringIO(main_csv))
    df = df.dropna(how="all")
    df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
    df = df.dropna(subset=["日付"])
    df["体重(kg)"] = pd.to_numeric(df["体重(kg)"], errors="coerce")
    df = df.dropna(subset=["体重(kg)"])
    for col in ["前週比(kg)", "体脂肪率(%)", "骨格筋量(%)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.sort_values("日付").reset_index(drop=True)

    # ── Basic profile info (below blank row) ────────────────────────────────
    basic_info: dict = {}
    if extra_csv.strip():
        try:
            basic_df = pd.read_csv(io.StringIO(extra_csv))
            basic_df = basic_df.dropna(how="all").dropna(axis=1, how="all")
            if not basic_df.empty:
                basic_info = {
                    k: str(v).strip()
                    for k, v in basic_df.iloc[0].items()
                    if pd.notna(v)
                }
        except Exception:
            pass

    return df, basic_info


def calc_ideal(basic_info: dict) -> dict:
    """Calculate ideal body composition targets from height and gender."""
    height_str = str(basic_info.get("身長", "170cm"))
    height_cm = float("".join(c for c in height_str if c.isdigit() or c == "."))
    h = height_cm / 100
    female = "女" in str(basic_info.get("性別", "男"))

    return {
        "weight": round(h ** 2 * 22, 1),
        "fat": 25.0 if female else 20.0,
        "muscle": 28.0 if female else 33.0,
    }


def _build_prompt(df: pd.DataFrame, basic_info: dict, ideal: dict) -> str:
    latest = df.iloc[-1]
    trend = df.tail(4)[["日付", "体重(kg)", "体脂肪率(%)", "骨格筋量(%)"]].copy()
    trend["日付"] = trend["日付"].dt.strftime("%Y/%m/%d")

    return f"""以下の体組成データをもとに、今週の変化のポイントと具体的なアドバイスを含む日本語コメントを100字程度で生成してください。

【基礎情報】
{', '.join(f'{k}: {v}' for k, v in basic_info.items())}

【最新データ（{latest['日付'].strftime('%Y/%m/%d')}）】
体重: {latest['体重(kg)']} kg（前週比: {latest['前週比(kg)']} kg）
体脂肪率: {latest['体脂肪率(%)']}%
骨格筋量: {latest['骨格筋量(%)']}%

【理想値】
目標体重: {ideal['weight']} kg（BMI 22）
目標体脂肪率: {ideal['fat']}% 以下
目標骨格筋量: {ideal['muscle']}% 以上

【直近4週のトレンド】
{trend.to_string(index=False)}

コメントのみ出力してください（ラベルや記号は不要）。"""


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ai_comment(prompt: str, api_key: str) -> str:
    if not api_key:
        return ""
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


# ── Helpers ──────────────────────────────────────────────────────────────────
def _fmt(val, suffix="", fallback="---"):
    return fallback if pd.isna(val) else f"{val:.1f}{suffix}"


def _signed(val, suffix=""):
    return None if pd.isna(val) else f"{val:+.1f}{suffix}"


def _line_chart(df, col, title, y_label, ref_val=None, ref_label=None):
    data = df.dropna(subset=[col])
    if data.empty:
        st.info(f"{title}のデータがありません")
        return
    fig = px.line(
        data, x="日付", y=col, title=title, markers=True,
        labels={"日付": "日付", col: y_label},
    )
    if ref_val is not None:
        fig.add_hline(
            y=ref_val, line_dash="dash", line_color="mediumseagreen",
            annotation_text=ref_label or "目標",
            annotation_position="bottom right",
        )
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), height=300)
    st.plotly_chart(fig, use_container_width=True)


# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="週次ボディダッシュボード", layout="wide")
st.title("週次ボディダッシュボード")

# ── Load data ────────────────────────────────────────────────────────────────
try:
    df, basic_info = load_sheet()
except Exception as e:
    st.error(f"データの読み込みに失敗しました: {e}")
    st.stop()

if df.empty:
    st.info("表示できるデータがありません")
    st.stop()

latest = df.iloc[-1]
ideal = calc_ideal(basic_info) if basic_info else {}

# ── Latest data cards ────────────────────────────────────────────────────────
st.subheader("最新データ")
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric("最新日付", latest["日付"].strftime("%Y/%m/%d"))
with c2:
    st.metric(
        "体重",
        _fmt(latest["体重(kg)"], " kg"),
        delta=_signed(latest["前週比(kg)"], " kg"),
        delta_color="inverse",
    )
with c3:
    st.metric("前週比", _fmt(latest["前週比(kg)"], " kg"))
with c4:
    st.metric("体脂肪率", _fmt(latest["体脂肪率(%)"], " %"))
with c5:
    st.metric("骨格筋量", _fmt(latest["骨格筋量(%)"], " %"))

# ── AI comment ───────────────────────────────────────────────────────────────
key = _api_key()
if basic_info and key:
    with st.spinner("AIコメントを生成中..."):
        try:
            comment = fetch_ai_comment(_build_prompt(df, basic_info, ideal), key)
            if comment:
                st.info(f"💬  {comment}")
        except Exception as e:
            st.warning(f"AIコメントの生成に失敗しました: {e}")
elif not key:
    st.caption("AIコメントを表示するには ANTHROPIC_API_KEY を設定してください。")

st.divider()

# ── Ideal values ─────────────────────────────────────────────────────────────
if ideal:
    st.subheader("理想値との現在地")
    d1, d2, d3 = st.columns(3)

    with d1:
        gap = latest["体重(kg)"] - ideal["weight"]
        st.metric(
            f"目標体重（BMI 22）",
            f"{ideal['weight']:.1f} kg",
            delta=f"{gap:+.1f} kg",
            delta_color="inverse",
        )
    with d2:
        fat = latest["体脂肪率(%)"]
        if pd.notna(fat):
            st.metric(
                f"目標体脂肪率（{ideal['fat']:.0f}% 以下）",
                _fmt(fat, " %"),
                delta=f"{fat - ideal['fat']:+.1f} %",
                delta_color="inverse",
            )
    with d3:
        muscle = latest["骨格筋量(%)"]
        if pd.notna(muscle):
            st.metric(
                f"目標骨格筋量（{ideal['muscle']:.0f}% 以上）",
                _fmt(muscle, " %"),
                delta=f"{muscle - ideal['muscle']:+.1f} %",
                delta_color="normal",
            )

    st.divider()

# ── Charts ───────────────────────────────────────────────────────────────────
w, f, m = ideal.get("weight"), ideal.get("fat"), ideal.get("muscle")

_line_chart(df, "体重(kg)", "体重の推移", "体重 (kg)",
            ref_val=w, ref_label=f"目標 {w} kg" if w else None)
_line_chart(df, "体脂肪率(%)", "体脂肪率の推移", "体脂肪率 (%)",
            ref_val=f, ref_label=f"目標 {f}%" if f else None)
_line_chart(df, "骨格筋量(%)", "骨格筋量の推移", "骨格筋量 (%)",
            ref_val=m, ref_label=f"目標 {m}%" if m else None)

st.divider()

# ── Data table ───────────────────────────────────────────────────────────────
st.subheader("記録一覧")
cols = ["日付", "体重(kg)", "前週比(kg)", "体脂肪率(%)", "骨格筋量(%)"]
table = df[[c for c in cols if c in df.columns]].copy()
table = table.sort_values("日付", ascending=False)
table["日付"] = table["日付"].dt.strftime("%Y/%m/%d")
st.dataframe(table, use_container_width=True, hide_index=True)
