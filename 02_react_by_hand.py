# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC # 02：あなたがループになる（問い②）
# MAGIC
# MAGIC 01 では、人が「何を調べるか」を決め、調べて、プロンプトに貼りました。ここでは役割を分けます。
# MAGIC
# MAGIC | 役割 | 担当 |
# MAGIC |---|---|
# MAGIC | 何を調べるかを決める | LLM |
# MAGIC | 実際に調べる（ツールを実行する） | あなた（このあと、プログラムに置き換える） |
# MAGIC
# MAGIC エージェントは、下の図の部品でできています。赤枠が、このノートブックであなたと LLM が担当する部分です。各節の先頭の図では、その節で扱う部分を赤枠で示します。
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1fr 0.5fr 1.3fr 1fr 1.3fr 0.5fr 1.3fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:2 / 4;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">システムプロンプト</div><div style="font-size:18px;margin-top:4px">役割とルール</div></div></div><div style="grid-column:4 / 6;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツールの説明</div><div style="font-size:18px;margin-top:4px">名前・説明・引数</div></div></div><div style="grid-column:2 / 6;grid-row:2;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">LLM が読む</div>↓</div></div><div style="grid-column:1;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">質問</div><div style="font-size:18px;margin-top:4px">利用者</div></div></div><div style="grid-column:2;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">LLM</div><div style="font-size:18px;margin-top:4px">何をするか決める</div></div></div><div style="grid-column:4;grid-row:3;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼 → / ← 結果</div>⇄</div></div><div style="grid-column:5;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">実行役</div><div style="font-size:18px;margin-top:4px">ツールを実行する<br>（あなた）</div></div></div><div style="grid-column:6;grid-row:3;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツール</div><div style="font-size:18px;margin-top:4px">get_today / get_menu</div></div></div><div style="grid-column:3;grid-row:4;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼が<br>なければ</div>↓</div></div><div style="grid-column:4 / 8;grid-row:4;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">会話の記録 messages</div><div style="font-size:18px;margin-top:4px">質問・LLM の返事・ツールの結果を積み上げる</div></div></div><div style="grid-column:3;grid-row:5;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">最終回答</div></div></div></div>
# MAGIC
# MAGIC **「すべてを実行」は使わず、上から1セルずつ実行してください。**

# COMMAND ----------

# MAGIC %pip install -qU databricks-openai
# MAGIC %restart_python

# COMMAND ----------

# MAGIC %run ./00_config

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## 1. ツールを用意する
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1fr 0.5fr 1.3fr 1fr 1.3fr 0.5fr 1.3fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:2 / 4;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">システムプロンプト</div><div style="font-size:18px;margin-top:4px">役割とルール</div></div></div><div style="grid-column:4 / 6;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツールの説明</div><div style="font-size:18px;margin-top:4px">名前・説明・引数</div></div></div><div style="grid-column:2 / 6;grid-row:2;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">LLM が読む</div>↓</div></div><div style="grid-column:1;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">質問</div><div style="font-size:18px;margin-top:4px">利用者</div></div></div><div style="grid-column:2;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">LLM</div><div style="font-size:18px;margin-top:4px">何をするか決める</div></div></div><div style="grid-column:4;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼 → / ← 結果</div>⇄</div></div><div style="grid-column:5;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">実行役</div><div style="font-size:18px;margin-top:4px">ツールを実行する<br>（あなた）</div></div></div><div style="grid-column:6;grid-row:3;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツール</div><div style="font-size:18px;margin-top:4px">get_today / get_menu</div></div></div><div style="grid-column:3;grid-row:4;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼が<br>なければ</div>↓</div></div><div style="grid-column:4 / 8;grid-row:4;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">会話の記録 messages</div><div style="font-size:18px;margin-top:4px">質問・LLM の返事・ツールの結果を積み上げる</div></div></div><div style="grid-column:3;grid-row:5;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">最終回答</div></div></div></div>
# MAGIC
# MAGIC ツールは、ふつうの Python の関数です。

# COMMAND ----------

def get_today():
    """今日の日付と曜日を返す（日本時間）"""
    now = datetime.now(timezone(timedelta(hours=9)))
    # weekday() は月曜=0 〜 日曜=6 を返すので、曜日の文字に置き換える
    return f"{now:%Y-%m-%d}（{'月火水木金土日'[now.weekday()]}）"


def get_menu(weekday):
    """指定した曜日のメニューを返す"""
    # :w の部分に、引数 weekday の値が入る（文字列を SQL に直接つなげないので、安全に値を渡せる）
    rows = spark.sql(
        f"SELECT category, item, price FROM {MENU_TABLE} WHERE weekday = :w", args={"w": weekday}
    ).collect()
    if not rows:  # 土日や、「月曜日」のような1文字でない値では行が見つからない
        return "該当するメニューはありません"
    return "\n".join(f"{r.category}：{r.item} {r.price}円" for r in rows)


# ツールの名前から関数を引けるようにしておく（LLM は名前で依頼してくるため）
TOOLS = {"get_today": get_today, "get_menu": get_menu}

# 動作確認：ツールを直接呼んでみる
print(get_today())
print(get_menu("月"))

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## 2. ツールの説明を書く
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1fr 0.5fr 1.3fr 1fr 1.3fr 0.5fr 1.3fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:2 / 4;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">システムプロンプト</div><div style="font-size:18px;margin-top:4px">役割とルール</div></div></div><div style="grid-column:4 / 6;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツールの説明</div><div style="font-size:18px;margin-top:4px">名前・説明・引数</div></div></div><div style="grid-column:2 / 6;grid-row:2;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1"><div style="font-size:18px">LLM が読む</div>↓</div></div><div style="grid-column:1;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">質問</div><div style="font-size:18px;margin-top:4px">利用者</div></div></div><div style="grid-column:2;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">LLM</div><div style="font-size:18px;margin-top:4px">何をするか決める</div></div></div><div style="grid-column:4;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼 → / ← 結果</div>⇄</div></div><div style="grid-column:5;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">実行役</div><div style="font-size:18px;margin-top:4px">ツールを実行する<br>（あなた）</div></div></div><div style="grid-column:6;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツール</div><div style="font-size:18px;margin-top:4px">get_today / get_menu</div></div></div><div style="grid-column:3;grid-row:4;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼が<br>なければ</div>↓</div></div><div style="grid-column:4 / 8;grid-row:4;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">会話の記録 messages</div><div style="font-size:18px;margin-top:4px">質問・LLM の返事・ツールの結果を積み上げる</div></div></div><div style="grid-column:3;grid-row:5;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">最終回答</div></div></div></div>
# MAGIC
# MAGIC LLM は関数の中身を読めません。読むのは、名前・説明・引数（関数に渡す値）の説明だけです。
# MAGIC これを JSON（プログラム同士がデータをやり取りするときの書式）で書いて LLM に渡します。

# COMMAND ----------

tool_specs = [
    {
        "type": "function",
        "function": {
            "name": "get_today",  # LLM はこの名前で実行を依頼してくる
            "description": "今日の日付と曜日を返します。",  # LLM はこの説明を読んで、使うかどうかを決める
            "parameters": {"type": "object", "properties": {}},  # 引数なし
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_menu",
            "description": "ひかり食堂の、指定した曜日のメニューと値段を返します。土日は休業です。",
            "parameters": {
                "type": "object",
                "properties": {
                    # 引数 weekday の型と説明。LLM はこの説明を読んで、渡す値を決める
                    "weekday": {"type": "string", "description": "曜日を1文字で。月, 火, 水, 木, 金, 土, 日 のいずれか"}
                },
                "required": ["weekday"],  # 必ず渡す引数
            },
        },
    },
]

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## 3. 会話を始める
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1fr 0.5fr 1.3fr 1fr 1.3fr 0.5fr 1.3fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:2 / 4;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">システムプロンプト</div><div style="font-size:18px;margin-top:4px">役割とルール</div></div></div><div style="grid-column:4 / 6;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツールの説明</div><div style="font-size:18px;margin-top:4px">名前・説明・引数</div></div></div><div style="grid-column:2 / 6;grid-row:2;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1"><div style="font-size:18px">LLM が読む</div>↓</div></div><div style="grid-column:1;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">質問</div><div style="font-size:18px;margin-top:4px">利用者</div></div></div><div style="grid-column:2;grid-row:3;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">LLM</div><div style="font-size:18px;margin-top:4px">何をするか決める</div></div></div><div style="grid-column:4;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼 → / ← 結果</div>⇄</div></div><div style="grid-column:5;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">実行役</div><div style="font-size:18px;margin-top:4px">ツールを実行する<br>（あなた）</div></div></div><div style="grid-column:6;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツール</div><div style="font-size:18px;margin-top:4px">get_today / get_menu</div></div></div><div style="grid-column:3;grid-row:4;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼が<br>なければ</div>↓</div></div><div style="grid-column:4 / 8;grid-row:4;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">会話の記録 messages</div><div style="font-size:18px;margin-top:4px">質問・LLM の返事・ツールの結果を積み上げる</div></div></div><div style="grid-column:3;grid-row:5;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">最終回答</div></div></div></div>
# MAGIC
# MAGIC `messages` は、LLM に渡す会話の記録です。`role` は発言者を表します。
# MAGIC
# MAGIC - `system`：LLM への役割やルールの指示（システムプロンプト）
# MAGIC - `user`：利用者の質問
# MAGIC - `assistant`：LLM の返事
# MAGIC - `tool`：ツールの実行結果

# COMMAND ----------

# 会話の記録の最初は、システムプロンプトと利用者の質問の2つ。このあと、LLM の返事とツールの結果が足されていく
messages = [
    {"role": "system", "content": "あなたはひかり食堂の案内係です。必要に応じてツールを使って答えてください。"},
    {"role": "user", "content": "今日の日替わり定食は何？"},
]

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## 4. ループを手で回す
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1fr 0.5fr 1.3fr 1fr 1.3fr 0.5fr 1.3fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:2 / 4;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">システムプロンプト</div><div style="font-size:18px;margin-top:4px">役割とルール</div></div></div><div style="grid-column:4 / 6;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツールの説明</div><div style="font-size:18px;margin-top:4px">名前・説明・引数</div></div></div><div style="grid-column:2 / 6;grid-row:2;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">LLM が読む</div>↓</div></div><div style="grid-column:1;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">質問</div><div style="font-size:18px;margin-top:4px">利用者</div></div></div><div style="grid-column:2;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#FF3621;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">セル A</div><div style="font-weight:bold">LLM</div><div style="font-size:18px;margin-top:4px">何をするか決める</div></div></div><div style="grid-column:4;grid-row:3;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼 → / ← 結果</div>⇄</div></div><div style="grid-column:5;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#FF3621;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">セル B</div><div style="font-weight:bold">実行役</div><div style="font-size:18px;margin-top:4px">ツールを実行する<br>（あなた）</div></div></div><div style="grid-column:6;grid-row:3;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツール</div><div style="font-size:18px;margin-top:4px">get_today / get_menu</div></div></div><div style="grid-column:3;grid-row:4;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼が<br>なければ</div>↓</div></div><div style="grid-column:4 / 8;grid-row:4;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">会話の記録 messages</div><div style="font-size:18px;margin-top:4px">質問・LLM の返事・ツールの結果を積み上げる</div></div></div><div style="grid-column:3;grid-row:5;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">最終回答</div></div></div></div>
# MAGIC
# MAGIC 次の2つのセルを、**A → B → A → B …** の順に、A が「最終回答」を出すまで繰り返し実行してください。
# MAGIC
# MAGIC - **セル A（LLM が考える）**：LLM に会話の記録を渡し、次に何をするかを決めさせます
# MAGIC - **セル B（あなたが行動する）**：LLM が依頼したツールを実行し、結果を会話の記録に足します

# COMMAND ----------

# セル A：LLM が考える
# 会話の記録とツールの説明を渡す。LLM はツールを実行せず、「どのツールを、どの引数で実行してほしいか」を返すだけ
resp = client.chat.completions.create(model=MODEL, messages=messages, tools=tool_specs)
reply = resp.choices[0].message  # LLM の返事

print("【LLM の返事（そのまま）】")
print(json.dumps(reply.to_dict(), ensure_ascii=False, indent=2))  # 返事の中身を、そのまま見やすく表示する
print("=" * 60)
if reply.tool_calls:  # tool_calls に依頼が入っていれば、まだ答えずにツールの実行を頼んでいる
    for call in reply.tool_calls:
        print(f"LLM の依頼：{call.function.name} を 引数 {call.function.arguments} で実行してほしい")
    print("→ セル B を実行してください")
else:  # 依頼がなければ、content に入っている文章が最終回答
    print("【最終回答】")
    print(reply.content)

# COMMAND ----------

# セル B：あなたが行動する（LLM の依頼どおりにツールを実行する）
if not reply.tool_calls:
    print("依頼はありません。セル A で最終回答が出ています。次の「確かめること」に進んでください")
else:
    messages.append(reply.to_dict())  # LLM の返事（依頼）を会話の記録に足す
    for call in reply.tool_calls:  # 依頼が複数あれば、1つずつ実行する
        args = json.loads(call.function.arguments or "{}")  # 引数は JSON の文字列で届くので、Python の辞書に変換する
        result = TOOLS[call.function.name](**args)  # ← ツールを実行しているのは、LLM ではなくこの行
        print(f"{call.function.name}({args}) の結果：\n{result}\n")
        # ツールの結果を会話の記録に足す。tool_call_id で、どの依頼への結果かを LLM に伝える
        messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    print("→ セル A をもう一度実行してください")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 確かめること
# MAGIC
# MAGIC - セル A の返事で、`content`（答えの文章）が空で、`tool_calls` に依頼が入っていたか
# MAGIC - LLM は何回ツールを依頼したか。どの順番だったか
# MAGIC - ツールを実際に実行したのは誰（どのセル）だったか

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## 5. ループをプログラムに任せる
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1fr 0.5fr 1.3fr 1fr 1.3fr 0.5fr 1.3fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:2 / 4;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">システムプロンプト</div><div style="font-size:18px;margin-top:4px">役割とルール</div></div></div><div style="grid-column:4 / 6;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツールの説明</div><div style="font-size:18px;margin-top:4px">名前・説明・引数</div></div></div><div style="grid-column:2 / 6;grid-row:2;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">LLM が読む</div>↓</div></div><div style="grid-column:1;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">質問</div><div style="font-size:18px;margin-top:4px">利用者</div></div></div><div style="grid-column:2;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">LLM</div><div style="font-size:18px;margin-top:4px">何をするか決める</div></div></div><div style="grid-column:4;grid-row:3;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼 → / ← 結果</div>⇄</div></div><div style="grid-column:5;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#FF3621;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">run_agent</div><div style="font-weight:bold">実行役</div><div style="font-size:18px;margin-top:4px">ツールを実行する<br>（プログラム）</div></div></div><div style="grid-column:6;grid-row:3;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツール</div><div style="font-size:18px;margin-top:4px">get_today / get_menu</div></div></div><div style="grid-column:3;grid-row:4;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼が<br>なければ</div>↓</div></div><div style="grid-column:4 / 8;grid-row:4;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">会話の記録 messages</div><div style="font-size:18px;margin-top:4px">質問・LLM の返事・ツールの結果を積み上げる</div></div></div><div style="grid-column:3;grid-row:5;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">最終回答</div></div></div></div>
# MAGIC
# MAGIC あなたが手でやった「A → B → A → B」を、`while` の繰り返しにします。これがエージェントの本体です。
# MAGIC （下のコードでは、回数の上限を決めやすいように `for` で書いています）

# COMMAND ----------

def run_agent(question, max_steps=6):
    # 会話の記録を、システムプロンプトと質問から始める（3. と同じ）
    messages = [
        {"role": "system", "content": "あなたはひかり食堂の案内係です。必要に応じてツールを使って答えてください。"},
        {"role": "user", "content": question},
    ]
    # LLM が依頼を出し続けて終わらない場合に備えて、繰り返しの回数に上限を付ける
    for step in range(max_steps):
        # セル A と同じ：LLM が考える
        reply = client.chat.completions.create(model=MODEL, messages=messages, tools=tool_specs).choices[0].message
        if not reply.tool_calls:  # 依頼がなければ、それが最終回答
            return reply.content
        # セル B と同じ：依頼されたツールを実行して、結果を会話の記録に足す
        messages.append(reply.to_dict())
        for call in reply.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            result = TOOLS[call.function.name](**args)
            print(f"  [ステップ{step + 1}] {call.function.name}({args})")  # 何を実行したかを表示する
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    return "（繰り返しの上限に達しました）"


print(run_agent("今日の日替わり定食は何？"))

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## 6. 質問を変えてみる
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1fr 0.5fr 1.3fr 1fr 1.3fr 0.5fr 1.3fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:2 / 4;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">システムプロンプト</div><div style="font-size:18px;margin-top:4px">役割とルール</div></div></div><div style="grid-column:4 / 6;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツールの説明</div><div style="font-size:18px;margin-top:4px">名前・説明・引数</div></div></div><div style="grid-column:2 / 6;grid-row:2;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">LLM が読む</div>↓</div></div><div style="grid-column:1;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">質問</div><div style="font-size:18px;margin-top:4px">利用者</div></div></div><div style="grid-column:2;grid-row:3;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">LLM</div><div style="font-size:18px;margin-top:4px">何をするか決める</div></div></div><div style="grid-column:4;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼 → / ← 結果</div>⇄</div></div><div style="grid-column:5;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">実行役</div><div style="font-size:18px;margin-top:4px">ツールを実行する<br>（プログラム）</div></div></div><div style="grid-column:6;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツール</div><div style="font-size:18px;margin-top:4px">get_today / get_menu</div></div></div><div style="grid-column:3;grid-row:4;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼が<br>なければ</div>↓</div></div><div style="grid-column:4 / 8;grid-row:4;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">会話の記録 messages</div><div style="font-size:18px;margin-top:4px">質問・LLM の返事・ツールの結果を積み上げる</div></div></div><div style="grid-column:3;grid-row:5;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">最終回答</div></div></div></div>
# MAGIC
# MAGIC 下の質問を書き換えて実行し、LLM がどのツールを何回呼ぶかを見てください。
# MAGIC
# MAGIC - 「こんにちは」
# MAGIC - 「明日のデザートは何？」
# MAGIC - 「カレーがあるのは何曜日？」

# COMMAND ----------

# ここの質問を書き換えて実行する
print(run_agent("カレーがあるのは何曜日？"))
