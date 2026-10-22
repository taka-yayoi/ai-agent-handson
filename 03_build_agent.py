# Databricks notebook source
# MAGIC %md
# MAGIC # 03：ツールを登録して、エージェントを作る（問い③）
# MAGIC
# MAGIC 02 ではツールをノートブックの中の関数として書きました。ここでは、ツールを Unity Catalog に登録します。
# MAGIC
# MAGIC - **Unity Catalog**：Databricks でデータや関数をまとめて管理し、誰が使えるかを決める仕組み
# MAGIC - 登録すると、ほかのノートブックやほかのエージェントからも同じツールを使えます
# MAGIC - 関数に付けた説明（`COMMENT`）が、そのまま LLM に渡るツールの説明になります

# COMMAND ----------

# MAGIC %pip install -qU databricks-openai "mlflow[databricks]>=3.4"
# MAGIC %restart_python

# COMMAND ----------

# MAGIC %run ./00_config

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. ツールを Unity Catalog に登録する

# COMMAND ----------

# ツール1：今日の日付と曜日を返す（Python で書いた関数）
def register_get_today(comment, name="get_today"):
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
spark.sql(f"""
CREATE OR REPLACE FUNCTION {CATALOG}.{SCHEMA}.get_menu(
  weekday STRING COMMENT '曜日'
)
RETURNS STRING
COMMENT 'ひかり食堂の、指定した曜日のメニューと値段を返します。土日は休業です。'
RETURN (
  SELECT concat_ws('\\n', collect_list(concat(category, '：', item, ' ', price, '円')))
  FROM {MENU_TABLE} m
  WHERE m.weekday = get_menu.weekday
)
""")

display(spark.sql(f"SELECT {CATALOG}.{SCHEMA}.get_today() AS today, {CATALOG}.{SCHEMA}.get_menu('月') AS menu"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. 登録した説明から、LLM に渡すツールの説明を作る
# MAGIC
# MAGIC 02 では JSON を手で書きました。ここでは Unity Catalog に登録した名前・説明・引数を読み出して作ります。

# COMMAND ----------

w = WorkspaceClient()
TOOL_NAMES = ["get_today", "get_menu"]


def tool_spec_from_uc(name):
    f = w.functions.get(f"{CATALOG}.{SCHEMA}.{name}")
    params = (f.input_params.parameters if f.input_params else None) or []
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f.comment,
            "parameters": {
                "type": "object",
                "properties": {p.name: {"type": "string", "description": p.comment or ""} for p in params},
                "required": [p.name for p in params],
            },
        },
    }


def run_tool(name, args):
    """Unity Catalog に登録した関数を、SQL から実行する"""
    placeholders = ", ".join(f":{k}" for k in args)
    row = spark.sql(f"SELECT {CATALOG}.{SCHEMA}.{name}({placeholders}) AS r", args=args).first()
    return row.r if row.r else "該当するデータはありません"


tool_specs = [tool_spec_from_uc(n) for n in TOOL_NAMES]
print(json.dumps(tool_specs, ensure_ascii=False, indent=2))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. エージェントを作る
# MAGIC
# MAGIC ループは 02 の最後に作ったものと同じです。`mlflow.trace` を付けると、MLflow が実行の記録（トレース）を残します。
# MAGIC
# MAGIC - **MLflow**：生成AIや機械学習の開発で、実行の記録・評価・管理を行うオープンソースのツール
# MAGIC - **トレース**：エージェントの中で、いつ、何が、どの順番で実行されたかの記録

# COMMAND ----------

import mlflow

mlflow.openai.autolog()  # LLM の呼び出しを自動で記録する

SYSTEM_PROMPT = "あなたはひかり食堂の案内係です。必要に応じてツールを使って答えてください。"


@mlflow.trace(name="エージェントの実行")
def run_agent(question, system_prompt=SYSTEM_PROMPT, max_steps=6, verbose=True):
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": question}]
    for _ in range(max_steps):
        reply = client.chat.completions.create(model=MODEL, messages=messages, tools=tool_specs).choices[0].message
        if not reply.tool_calls:
            return reply.content
        messages.append(reply.to_dict())
        for call in reply.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            with mlflow.start_span(name=f"ツール：{call.function.name}", span_type="TOOL") as span:
                span.set_inputs(args)
                result = run_tool(call.function.name, args)
                span.set_outputs(result)
            if verbose:
                print(f"  [ツール] {call.function.name}({args}) → {result.splitlines()[0]} …")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    return "（繰り返しの上限に達しました）"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. 動かして、トレースを見る
# MAGIC
# MAGIC 実行すると、セルの下にトレースが表示されます。「ツール：get_today」「ツール：get_menu」を開いて、入力と出力を確かめてください。

# COMMAND ----------

print(run_agent("今日の日替わり定食は何？"))

# COMMAND ----------

print(run_agent("明日のデザートは何？"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. 名前と説明を、用途が分からないものにしてみる
# MAGIC
# MAGIC LLM が読むのは名前と説明だけです。中身は get_today と同じ関数を、名前 `tool_a`、説明「データを返します。」で登録し、
# MAGIC get_today の代わりにエージェントに持たせます。LLM はこのツールを使うでしょうか。

# COMMAND ----------

register_get_today("データを返します。", name="tool_a")
TOOL_NAMES = ["tool_a", "get_menu"]
tool_specs = [tool_spec_from_uc(n) for n in TOOL_NAMES]
print(run_agent("今日の日替わり定食は何？"))

# COMMAND ----------

# MAGIC %md
# MAGIC 結果を確かめたら、元に戻します。

# COMMAND ----------

TOOL_NAMES = ["get_today", "get_menu"]
tool_specs = [tool_spec_from_uc(n) for n in TOOL_NAMES]
