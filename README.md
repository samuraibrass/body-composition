# 週次ボディダッシュボード

オムロンコネクトで計測した体組成データ（体重・体脂肪率・骨格筋量）の推移を  
Googleスプレッドシートから読み込んで表示するStreamlitダッシュボードです。

## 画面構成

1. 最新データカード（最新日付・体重＋前週比・前週比・体脂肪率・骨格筋量）
2. 体重推移グラフ
3. 体脂肪率推移グラフ
4. 骨格筋量推移グラフ
5. 記録一覧テーブル

---

## ローカルでの起動方法

### 前提

- Python 3.9 以上
- pip

### 手順

```bash
# 1. このディレクトリに移動
cd body-composition

# 2. 依存ライブラリをインストール
pip install -r requirements.txt

# 3. アプリを起動
streamlit run app.py
```

ブラウザで `http://localhost:8501` が自動的に開きます。

---

## Streamlit Community Cloud で公開する手順

1. このディレクトリを GitHub リポジトリに push する
   ```bash
   git init
   git add app.py requirements.txt README.md
   git commit -m "initial commit"
   git remote add origin https://github.com/<ユーザー名>/<リポジトリ名>.git
   git push -u origin main
   ```

2. [Streamlit Community Cloud](https://streamlit.io/cloud) に GitHub アカウントでサインイン

3. 「New app」をクリック

4. リポジトリ・ブランチ（`main`）・メインファイル（`app.py`）を指定

5. 「Deploy!」をクリック → URLが発行されてデプロイ完了

> **注意**: スプレッドシートの共有設定を「リンクを知っている全員が閲覧可能」にしておく必要があります。

---

## スプレッドシートの URL を変更したい場合

`app.py` の冒頭にある `SPREADSHEET_ID` を書き換えてください。

```python
# app.py 4行目
SPREADSHEET_ID = "12pLQ_HQCuQgUdoivIkCytFZkqLtP2olT27TgsmtqUrk"
```

スプレッドシートの URL が  
`https://docs.google.com/spreadsheets/d/XXXX/edit`  
の場合、`XXXX` の部分が `SPREADSHEET_ID` です。

---

## シート名を変更した場合

`app.py` の冒頭にある `SHEET_NAME` を書き換えてください。

```python
# app.py 5行目
SHEET_NAME = "体組成推移"
```

---

## スプレッドシートの列仕様

| 列名 | 型 | 備考 |
|---|---|---|
| 日付 | 日付 | |
| 体重(kg) | 数値 | 空の行はスキップされます |
| 前週比(kg) | 数値 | |
| 体脂肪率(%) | 数値 | |
| 骨格筋量(%) | 数値 | |
