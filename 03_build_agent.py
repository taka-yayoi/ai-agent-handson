# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC # 03：ツールを登録して、エージェントを作る（問い③）
# MAGIC
# MAGIC 02 ではツールをノートブックの中の関数として書きました。ここでは、ツールを Unity Catalog に登録します。
# MAGIC
# MAGIC - **Unity Catalog**：Databricks でデータや関数をまとめて管理し、誰が使えるかを決める仕組み
# MAGIC - 登録すると、ほかのノートブックやほかのエージェントからも同じツールを使えます
# MAGIC - 関数に付けた説明（`COMMENT`）が、そのまま LLM に渡るツールの説明になります
# MAGIC
# MAGIC 02 から変わるのは、図の赤枠の部分です。実行役は、02 の最後に作ったプログラムのループです。
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1fr 0.5fr 1.3fr 1fr 1.3fr 0.5fr 1.3fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:2 / 4;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">システムプロンプト</div><div style="font-size:18px;margin-top:4px">役割とルール</div></div></div><div style="grid-column:4 / 6;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツールの説明</div><div style="font-size:18px;margin-top:4px">Unity Catalog の COMMENT から作る</div></div></div><div style="grid-column:2 / 6;grid-row:2;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1"><div style="font-size:18px">LLM が読む</div>↓</div></div><div style="grid-column:1;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">質問</div><div style="font-size:18px;margin-top:4px">利用者</div></div></div><div style="grid-column:2;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">LLM</div><div style="font-size:18px;margin-top:4px">何をするか決める</div></div></div><div style="grid-column:4;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼 → / ← 結果</div>⇄</div></div><div style="grid-column:5;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">実行役</div><div style="font-size:18px;margin-top:4px">ツールを実行する<br>（プログラム）</div></div></div><div style="grid-column:6;grid-row:3;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツール</div><div style="font-size:18px;margin-top:4px">Unity Catalog の関数</div></div></div><div style="grid-column:3;grid-row:4;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼が<br>なければ</div>↓</div></div><div style="grid-column:4 / 8;grid-row:4;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">会話の記録 messages</div><div style="font-size:18px;margin-top:4px">質問・LLM の返事・ツールの結果を積み上げる</div></div></div><div style="grid-column:3;grid-row:5;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">最終回答</div></div></div><div style="grid-column:4 / 8;grid-row:5;align-self:center"><div style="position:relative;border:3px dashed #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">MLflow トレース</div><div style="font-size:18px;margin-top:4px">LLM の呼び出しとツールの実行を、順番どおりに記録する</div></div></div></div>

# COMMAND ----------

# MAGIC %pip install -qU databricks-openai "mlflow[databricks]>=3.4"
# MAGIC %restart_python

# COMMAND ----------

# MAGIC %run ./00_config

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## 1. ツールを Unity Catalog に登録する
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1fr 0.5fr 1.3fr 1fr 1.3fr 0.5fr 1.3fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:2 / 4;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">システムプロンプト</div><div style="font-size:18px;margin-top:4px">役割とルール</div></div></div><div style="grid-column:4 / 6;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツールの説明</div><div style="font-size:18px;margin-top:4px">Unity Catalog の COMMENT から作る</div></div></div><div style="grid-column:2 / 6;grid-row:2;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">LLM が読む</div>↓</div></div><div style="grid-column:1;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">質問</div><div style="font-size:18px;margin-top:4px">利用者</div></div></div><div style="grid-column:2;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">LLM</div><div style="font-size:18px;margin-top:4px">何をするか決める</div></div></div><div style="grid-column:4;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼 → / ← 結果</div>⇄</div></div><div style="grid-column:5;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">実行役</div><div style="font-size:18px;margin-top:4px">ツールを実行する<br>（プログラム）</div></div></div><div style="grid-column:6;grid-row:3;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツール</div><div style="font-size:18px;margin-top:4px">Unity Catalog の関数</div></div></div><div style="grid-column:3;grid-row:4;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼が<br>なければ</div>↓</div></div><div style="grid-column:4 / 8;grid-row:4;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">会話の記録 messages</div><div style="font-size:18px;margin-top:4px">質問・LLM の返事・ツールの結果を積み上げる</div></div></div><div style="grid-column:3;grid-row:5;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">最終回答</div></div></div><div style="grid-column:4 / 8;grid-row:5;align-self:center"><div style="position:relative;border:3px dashed #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">MLflow トレース</div><div style="font-size:18px;margin-top:4px">LLM の呼び出しとツールの実行を、順番どおりに記録する</div></div></div></div>

# COMMAND ----------

# ツール1：今日の日付と曜日を返す（Python で書いた関数）
# 5. で名前と説明を変えて登録し直すので、説明（comment）と名前（name）を引数で受け取れるようにしておく
def register_get_today(comment, name="get_today"):
    # CREATE OR REPLACE FUNCTION：Unity Catalog に関数を登録する（同じ名前があれば置き換える）
    # $$ と $$ の間が関数の中身。f 文字列の中なので、Python の { } は {{ }} と2重に書いている
    spark.sql(f"""
    CREATE OR REPLACE FUNCTION {CATALOG}.{SCHEMA}.{name}()
    RETURNS STRING
    LANGUAGE PYTHON
    COMMENT '{comment}'
    AS $$
from datetime import datetime, timedelta, timezone
now = datetime.now(timezone(timedelta(hours=9)))
return f"{{now:%Y-%m-%d}}（{{'月火水木金土日'[now.weekday()]}}）"
    $$
    """)


register_get_today("今日の日付と曜日を返します（日本時間）。例：2026-12-14（月）")

# ツール2：曜日を受け取り、その日のメニューを返す（SQL で書いた関数）
# 引数の COMMENT が引数の説明、関数の COMMENT が関数の説明になり、どちらも LLM に渡る
spark.sql(f"""
CREATE OR REPLACE FUNCTION {CATALOG}.{SCHEMA}.get_menu(
  weekday STRING COMMENT '曜日'
)
RETURNS STRING
COMMENT 'ひかり食堂の、指定した曜日のメニューと値段を返します。土日は休業です。'
RETURN (
  -- 指定した曜日の行を「種類：料理名 値段円」の形にして、改行でつないで1つの文字列にする
  SELECT concat_ws('\\n', collect_list(concat(category, '：', item, ' ', price, '円')))
  FROM {MENU_TABLE} m
  WHERE m.weekday = get_menu.weekday
)
""")

# 動作確認：登録した関数を SQL から呼んでみる
display(spark.sql(f"SELECT {CATALOG}.{SCHEMA}.get_today() AS today, {CATALOG}.{SCHEMA}.get_menu('月') AS menu"))

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## 2. 登録した説明から、LLM に渡すツールの説明を作る
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1fr 0.5fr 1.3fr 1fr 1.3fr 0.5fr 1.3fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:2 / 4;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">システムプロンプト</div><div style="font-size:18px;margin-top:4px">役割とルール</div></div></div><div style="grid-column:4 / 6;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツールの説明</div><div style="font-size:18px;margin-top:4px">Unity Catalog の COMMENT から作る</div></div></div><div style="grid-column:2 / 6;grid-row:2;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1"><div style="font-size:18px">LLM が読む</div>↓</div></div><div style="grid-column:1;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">質問</div><div style="font-size:18px;margin-top:4px">利用者</div></div></div><div style="grid-column:2;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">LLM</div><div style="font-size:18px;margin-top:4px">何をするか決める</div></div></div><div style="grid-column:4;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼 → / ← 結果</div>⇄</div></div><div style="grid-column:5;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">実行役</div><div style="font-size:18px;margin-top:4px">ツールを実行する<br>（プログラム）</div></div></div><div style="grid-column:6;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツール</div><div style="font-size:18px;margin-top:4px">Unity Catalog の関数</div></div></div><div style="grid-column:3;grid-row:4;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼が<br>なければ</div>↓</div></div><div style="grid-column:4 / 8;grid-row:4;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">会話の記録 messages</div><div style="font-size:18px;margin-top:4px">質問・LLM の返事・ツールの結果を積み上げる</div></div></div><div style="grid-column:3;grid-row:5;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">最終回答</div></div></div><div style="grid-column:4 / 8;grid-row:5;align-self:center"><div style="position:relative;border:3px dashed #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">MLflow トレース</div><div style="font-size:18px;margin-top:4px">LLM の呼び出しとツールの実行を、順番どおりに記録する</div></div></div></div>
# MAGIC
# MAGIC 02 では JSON を手で書きました。ここでは Unity Catalog に登録した名前・説明・引数を読み出して作ります。

# COMMAND ----------

w = WorkspaceClient()  # Unity Catalog に登録した関数の情報を読み出すために使う
TOOL_NAMES = ["get_today", "get_menu"]  # エージェントに持たせるツール


def tool_spec_from_uc(name):
    """Unity Catalog に登録した関数の名前・説明・引数から、02 と同じ形のツールの説明（JSON）を作る"""
    f = w.functions.get(f"{CATALOG}.{SCHEMA}.{name}")  # 登録した関数の情報
    params = (f.input_params.parameters if f.input_params else None) or []  # 引数の一覧（引数なしなら空）
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f.comment,  # 関数の COMMENT
            "parameters": {
                "type": "object",
                # 引数ごとの説明（引数の COMMENT）。このハンズオンの引数はすべて文字列なので string にしている
                "properties": {p.name: {"type": "string", "description": p.comment or ""} for p in params},
                "required": [p.name for p in params],
            },
        },
    }


def run_tool(name, args):
    """Unity Catalog に登録した関数を、SQL から実行する"""
    # 例：get_menu に {"weekday": "月"} を渡すと SELECT workspace.agent_handson.get_menu(:weekday) を実行する
    placeholders = ", ".join(f":{k}" for k in args)
    row = spark.sql(f"SELECT {CATALOG}.{SCHEMA}.{name}({placeholders}) AS r", args=args).first()
    # 該当する行がないと空（NULL）が返るので、LLM に分かる文章に置き換える
    return row.r if row.r else "該当するデータはありません"


tool_specs = [tool_spec_from_uc(n) for n in TOOL_NAMES]
print(json.dumps(tool_specs, ensure_ascii=False, indent=2))  # 02 で手で書いた JSON と見比べる

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## 3. エージェントを作る
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1fr 0.5fr 1.3fr 1fr 1.3fr 0.5fr 1.3fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:2 / 4;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">システムプロンプト</div><div style="font-size:18px;margin-top:4px">役割とルール</div></div></div><div style="grid-column:4 / 6;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツールの説明</div><div style="font-size:18px;margin-top:4px">Unity Catalog の COMMENT から作る</div></div></div><div style="grid-column:2 / 6;grid-row:2;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">LLM が読む</div>↓</div></div><div style="grid-column:1;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">質問</div><div style="font-size:18px;margin-top:4px">利用者</div></div></div><div style="grid-column:2;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">LLM</div><div style="font-size:18px;margin-top:4px">何をするか決める</div></div></div><div style="grid-column:4;grid-row:3;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼 → / ← 結果</div>⇄</div></div><div style="grid-column:5;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#FF3621;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">run_agent</div><div style="font-weight:bold">実行役</div><div style="font-size:18px;margin-top:4px">ツールを実行する<br>（プログラム）</div></div></div><div style="grid-column:6;grid-row:3;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツール</div><div style="font-size:18px;margin-top:4px">Unity Catalog の関数</div></div></div><div style="grid-column:3;grid-row:4;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼が<br>なければ</div>↓</div></div><div style="grid-column:4 / 8;grid-row:4;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">会話の記録 messages</div><div style="font-size:18px;margin-top:4px">質問・LLM の返事・ツールの結果を積み上げる</div></div></div><div style="grid-column:3;grid-row:5;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">最終回答</div></div></div><div style="grid-column:4 / 8;grid-row:5;align-self:center"><div style="position:relative;border:3px dashed #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">MLflow トレース</div><div style="font-size:18px;margin-top:4px">LLM の呼び出しとツールの実行を、順番どおりに記録する</div></div></div></div>
# MAGIC
# MAGIC ループは 02 の最後に作ったものと同じです。`mlflow.trace` を付けると、MLflow が実行の記録（トレース）を残します。
# MAGIC
# MAGIC - **MLflow**：生成AIや機械学習の開発で、実行の記録・評価・管理を行うオープンソースのツール
# MAGIC - **トレース**：エージェントの中で、いつ、何が、どの順番で実行されたかの記録

# COMMAND ----------

import mlflow

mlflow.openai.autolog()  # LLM の呼び出しを自動で記録する

SYSTEM_PROMPT = "あなたはひかり食堂の案内係です。必要に応じてツールを使って答えてください。"


# @mlflow.trace：この関数を1回実行するごとに、1つのトレースとして記録する
@mlflow.trace(name="エージェントの実行")
def run_agent(question, system_prompt=SYSTEM_PROMPT, max_steps=6, verbose=True):
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": question}]
    for _ in range(max_steps):
        # LLM が考える（02 のセル A と同じ）
        reply = client.chat.completions.create(model=MODEL, messages=messages, tools=tool_specs).choices[0].message
        if not reply.tool_calls:  # 依頼がなければ、それが最終回答
            return reply.content
        # 依頼されたツールを実行する（02 のセル B と同じ）
        messages.append(reply.to_dict())
        for call in reply.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            # ツールの実行を、トレースの中の1区切り（スパン）として記録する。入力と出力もあわせて残す
            with mlflow.start_span(name=f"ツール：{call.function.name}", span_type="TOOL") as span:
                span.set_inputs(args)
                result = run_tool(call.function.name, args)  # 02 と違い、Unity Catalog の関数を実行する
                span.set_outputs(result)
            if verbose:  # 結果の1行目だけを表示する
                print(f"  [ツール] {call.function.name}({args}) → {result.splitlines()[0]} …")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    return "（繰り返しの上限に達しました）"

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## 4. 動かして、トレースを見る
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1fr 0.5fr 1.3fr 1fr 1.3fr 0.5fr 1.3fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:2 / 4;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">システムプロンプト</div><div style="font-size:18px;margin-top:4px">役割とルール</div></div></div><div style="grid-column:4 / 6;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツールの説明</div><div style="font-size:18px;margin-top:4px">Unity Catalog の COMMENT から作る</div></div></div><div style="grid-column:2 / 6;grid-row:2;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">LLM が読む</div>↓</div></div><div style="grid-column:1;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">質問</div><div style="font-size:18px;margin-top:4px">利用者</div></div></div><div style="grid-column:2;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">LLM</div><div style="font-size:18px;margin-top:4px">何をするか決める</div></div></div><div style="grid-column:4;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼 → / ← 結果</div>⇄</div></div><div style="grid-column:5;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">実行役</div><div style="font-size:18px;margin-top:4px">ツールを実行する<br>（プログラム）</div></div></div><div style="grid-column:6;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツール</div><div style="font-size:18px;margin-top:4px">Unity Catalog の関数</div></div></div><div style="grid-column:3;grid-row:4;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼が<br>なければ</div>↓</div></div><div style="grid-column:4 / 8;grid-row:4;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">会話の記録 messages</div><div style="font-size:18px;margin-top:4px">質問・LLM の返事・ツールの結果を積み上げる</div></div></div><div style="grid-column:3;grid-row:5;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">最終回答</div></div></div><div style="grid-column:4 / 8;grid-row:5;align-self:center"><div style="position:relative;border:3px dashed #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">MLflow トレース</div><div style="font-size:18px;margin-top:4px">LLM の呼び出しとツールの実行を、順番どおりに記録する</div></div></div></div>
# MAGIC
# MAGIC 実行すると、セルの下にトレースが表示されます。「ツール：get_today」「ツール：get_menu」を開いて、入力と出力を確かめてください。

# COMMAND ----------

print(run_agent("今日の日替わり定食は何？"))

# COMMAND ----------

print(run_agent("明日のデザートは何？"))

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## 5. 名前と説明を、用途が分からないものにしてみる
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1fr 0.5fr 1.3fr 1fr 1.3fr 0.5fr 1.3fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:2 / 4;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">システムプロンプト</div><div style="font-size:18px;margin-top:4px">役割とルール</div></div></div><div style="grid-column:4 / 6;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#FF3621;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">ここを変える</div><div style="font-weight:bold">ツールの説明</div><div style="font-size:18px;margin-top:4px">「データを返します。」</div></div></div><div style="grid-column:2 / 6;grid-row:2;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1"><div style="font-size:18px">LLM が読む</div>↓</div></div><div style="grid-column:1;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">質問</div><div style="font-size:18px;margin-top:4px">利用者</div></div></div><div style="grid-column:2;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">LLM</div><div style="font-size:18px;margin-top:4px">何をするか決める</div></div></div><div style="grid-column:4;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼 → / ← 結果</div>⇄</div></div><div style="grid-column:5;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">実行役</div><div style="font-size:18px;margin-top:4px">ツールを実行する<br>（プログラム）</div></div></div><div style="grid-column:6;grid-row:3;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:3;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツール</div><div style="font-size:18px;margin-top:4px">tool_a / get_menu</div></div></div><div style="grid-column:3;grid-row:4;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼が<br>なければ</div>↓</div></div><div style="grid-column:4 / 8;grid-row:4;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">会話の記録 messages</div><div style="font-size:18px;margin-top:4px">質問・LLM の返事・ツールの結果を積み上げる</div></div></div><div style="grid-column:3;grid-row:5;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">最終回答</div></div></div><div style="grid-column:4 / 8;grid-row:5;align-self:center"><div style="position:relative;border:3px dashed #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">MLflow トレース</div><div style="font-size:18px;margin-top:4px">LLM の呼び出しとツールの実行を、順番どおりに記録する</div></div></div></div>
# MAGIC
# MAGIC LLM が読むのは名前と説明だけです。中身は get_today と同じ関数を、名前 `tool_a`、説明「データを返します。」で登録し、
# MAGIC get_today の代わりにエージェントに持たせます。LLM はこのツールを使うでしょうか。

# COMMAND ----------

register_get_today("データを返します。", name="tool_a")  # 中身は get_today と同じ。名前と説明だけが違う
TOOL_NAMES = ["tool_a", "get_menu"]  # get_today の代わりに tool_a を持たせる
tool_specs = [tool_spec_from_uc(n) for n in TOOL_NAMES]  # ツールの説明を作り直す（run_agent はこれを使う）
print(run_agent("今日の日替わり定食は何？"))

# COMMAND ----------

# MAGIC %md
# MAGIC 結果を確かめたら、元に戻します。

# COMMAND ----------

# 持たせるツールを get_today と get_menu に戻し、ツールの説明を作り直す
TOOL_NAMES = ["get_today", "get_menu"]
tool_specs = [tool_spec_from_uc(n) for n in TOOL_NAMES]
