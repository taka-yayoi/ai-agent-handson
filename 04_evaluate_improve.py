# Databricks notebook source
# MAGIC %md
# MAGIC # 04：評価して、直して、もう一度評価する（問い④）
# MAGIC
# MAGIC 03 のエージェントは、数回試した範囲ではうまく動きました。では、質問を増やしても正しく答えられるでしょうか。
# MAGIC
# MAGIC 1. 質問と正解の組（評価データ）を用意する
# MAGIC 2. LLM ジャッジ（回答を採点する役の LLM）で、全部の回答を採点する
# MAGIC 3. 点の低い質問のトレースを見て、原因を探す
# MAGIC 4. 1か所だけ直して、同じ評価データでもう一度採点し、比べる
# MAGIC
# MAGIC 先に `03_build_agent` を最後まで実行しておいてください（ツールの登録が必要です）。

# COMMAND ----------

# MAGIC %pip install -qU databricks-openai "mlflow[databricks]>=3.4"
# MAGIC %restart_python

# COMMAND ----------

# MAGIC %run ./00_config

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0. 03 と同じエージェントを用意する（中身は 03 と同じなので、読み飛ばして構いません）

# COMMAND ----------

import mlflow

mlflow.openai.autolog()
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
    placeholders = ", ".join(f":{k}" for k in args)
    row = spark.sql(f"SELECT {CATALOG}.{SCHEMA}.{name}({placeholders}) AS r", args=args).first()
    return row.r if row.r else "該当するデータはありません"


SYSTEM_PROMPT = "あなたはひかり食堂の案内係です。必要に応じてツールを使って答えてください。"


def register_get_menu(param_comment):
    spark.sql(f"""
    CREATE OR REPLACE FUNCTION {CATALOG}.{SCHEMA}.get_menu(
      weekday STRING COMMENT '{param_comment}'
    )
    RETURNS STRING
    COMMENT 'ひかり食堂の、指定した曜日のメニューと値段を返します。土日は休業です。'
    RETURN (
      SELECT concat_ws('\\n', collect_list(concat(category, '：', item, ' ', price, '円')))
      FROM {MENU_TABLE} m
      WHERE m.weekday = get_menu.weekday
    )
    """)


# 直す前（v1）の状態にそろえる：get_menu の引数の説明は 03 と同じ「曜日」
register_get_menu("曜日")


@mlflow.trace(name="エージェントの実行")
def run_agent(question, system_prompt=SYSTEM_PROMPT, max_steps=6, verbose=True):
    specs = [tool_spec_from_uc(n) for n in TOOL_NAMES]
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": question}]
    for _ in range(max_steps):
        reply = client.chat.completions.create(model=MODEL, messages=messages, tools=specs).choices[0].message
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
# MAGIC ## 1. 評価データを用意する
# MAGIC
# MAGIC 質問と、期待する答え（正解）の組です。正解はメニュー表から計算して作ります。
# MAGIC 「今日」「明日」の正解は実行した日によって変わるので、実行のたびに作り直します。

# COMMAND ----------

WEEK = "月火水木金土日"
now = datetime.now(timezone(timedelta(hours=9)))


def day(offset):
    return WEEK[(now.weekday() + offset) % 7]


def menu_of(wd):
    items = [f"{c}：{i} {p}円" for d, c, i, p in MENU if d == wd]
    return "、".join(items) if items else "休業日のためメニューはない"


def item_of(wd, category):
    hit = [f"{i}（{p}円）" for d, c, i, p in MENU if d == wd and c == category]
    return hit[0] if hit else "休業日、または該当するメニューはない"


cheap_today = [f"{i}（{p}円）" for d, c, i, p in MENU if d == day(0) and p <= 500]

eval_data = [
    ("今日の日替わり定食は何？", f"今日（{day(0)}曜日）の日替わり定食は {item_of(day(0), '日替わり定食')}"),
    ("明日のデザートは何？", f"明日（{day(1)}曜日）のデザートは {item_of(day(1), 'デザート')}"),
    ("明後日の麺は何？", f"明後日（{day(2)}曜日）の麺は {item_of(day(2), '麺')}"),
    ("月曜日のカレーは何？", "月曜日のカレーはビーフカレー（480円）"),
    ("水曜日の麺は何？", "水曜日の麺は冷やし中華（470円）"),
    ("木曜日の丼はいくら？", "木曜日の丼は牛丼で420円"),
    ("金曜日の日替わり定食の値段は？", "金曜日の日替わり定食は白身魚フライ定食で510円"),
    ("土曜日は営業していますか？", "土曜日は休業"),
    ("カレーがあるのは何曜日？", "月曜日（ビーフカレー）、水曜日（カツカレー）、金曜日（シーフードカレー）"),
    ("今日、500円以下で食べられるものは？",
     "、".join(cheap_today) if cheap_today else f"今日（{day(0)}曜日）は休業日"),
]

data = [{"inputs": {"question": q}, "expectations": {"expected_response": a}} for q, a in eval_data]
for d in data:
    print(d["inputs"]["question"], "→", d["expectations"]["expected_response"])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. 採点の観点（スコアラー）を決めて、評価する
# MAGIC
# MAGIC - `Correctness`：期待する答えと比べて正しいか（正解データが必要）
# MAGIC - `ToolCallEfficiency`：ツールを無駄に呼んでいないか

# COMMAND ----------

from mlflow.genai.scorers import Correctness, ToolCallEfficiency

scorers = [Correctness(), ToolCallEfficiency()]


def predict_fn(question):
    return run_agent(question, verbose=False)


with mlflow.start_run(run_name="v1：直す前"):
    result_v1 = mlflow.genai.evaluate(data=data, predict_fn=predict_fn, scorers=scorers)

result_v1.metrics

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. 点の低い質問を調べる
# MAGIC
# MAGIC 上のセルの出力にある評価結果のリンクを開き、`Correctness` が「no」の質問を選びます。
# MAGIC トレースを開いて、次を確かめてください。
# MAGIC
# MAGIC - どのツールが、どの引数で呼ばれたか
# MAGIC - ツールは何を返したか（「該当するデータはありません」になっていないか）
# MAGIC - LLM は、ツールの結果どおりに答えたか

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. 1か所だけ直す
# MAGIC
# MAGIC 原因に合わせて、**次のどれか1つだけ**を変えます。2か所以上を同時に変えると、何が効いたのか分からなくなります。
# MAGIC
# MAGIC | 候補 | 変えるもの |
# MAGIC |---|---|
# MAGIC | A | `get_menu` の引数 `weekday` の説明（下のセル） |
# MAGIC | B | システムプロンプト（`SYSTEM_PROMPT_V2`） |
# MAGIC
# MAGIC 使わないほうのセルは実行しないでください。

# COMMAND ----------

# 候補 A：get_menu の引数の説明を変える
register_get_menu("曜日を1文字で。月, 火, 水, 木, 金, 土, 日 のいずれか")
SYSTEM_PROMPT_V2 = SYSTEM_PROMPT

# COMMAND ----------

# 候補 B：システムプロンプトを変える（A を実行した場合は、このセルは実行しない）
SYSTEM_PROMPT_V2 = """あなたはひかり食堂の案内係です。
- 日付や曜日が関係する質問では、必ず最初に get_today で今日を確かめてください。
- メニューはツールの結果だけを使って答え、推測で答えないでください。"""

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. 同じ評価データで、もう一度評価して比べる

# COMMAND ----------

def predict_fn_v2(question):
    return run_agent(question, system_prompt=SYSTEM_PROMPT_V2, verbose=False)


with mlflow.start_run(run_name="v2：直した後"):
    result_v2 = mlflow.genai.evaluate(data=data, predict_fn=predict_fn_v2, scorers=scorers)

import pandas as pd

pd.DataFrame({"v1：直す前": result_v1.metrics, "v2：直した後": result_v2.metrics})

# COMMAND ----------

# MAGIC %md
# MAGIC ### ふりかえり
# MAGIC
# MAGIC - 何を変えたか、なぜそこを変えたか
# MAGIC - スコアは上がったか、下がったか、変わらなかったか
# MAGIC - 点が上がった質問と、下がった質問はあったか
