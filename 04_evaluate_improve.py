# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC # 04：評価して、直して、もう一度評価する（問い④）
# MAGIC
# MAGIC 03 のエージェントは、数回試した範囲ではうまく動きました。では、質問を増やしても正しく答えられるでしょうか。
# MAGIC
# MAGIC 1. 質問と正解の組（評価データ）を用意する
# MAGIC 2. LLM ジャッジ（回答を採点する役の LLM）で、全部の回答を採点する
# MAGIC 3. 点の低い質問のトレースを見て、原因を探す
# MAGIC 4. 1か所だけ直して、同じ評価データでもう一度採点し、比べる
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1.2fr 0.3fr 1.4fr 0.3fr 1.2fr 0.3fr 1.2fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:1;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#FF3621;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">1</div><div style="font-weight:bold">評価データ</div><div style="font-size:18px;margin-top:4px">質問と正解の組</div></div></div><div style="grid-column:2;grid-row:1;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#FF3621;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">2</div><div style="font-weight:bold">エージェントが答え、<br>LLM ジャッジが採点</div><div style="font-size:18px;margin-top:4px">Correctness など</div></div></div><div style="grid-column:4;grid-row:1;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:5;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#FF3621;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">3</div><div style="font-weight:bold">トレースで<br>原因を探す</div><div style="font-size:18px;margin-top:4px">点の低い質問</div></div></div><div style="grid-column:6;grid-row:1;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#FF3621;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">4</div><div style="font-weight:bold">1か所だけ直す</div><div style="font-size:18px;margin-top:4px">A または B</div></div></div><div style="grid-column:3 / 8;grid-row:2;align-self:start"><div style="border:3px solid #FF3621;border-top:none;height:34px;border-radius:0 0 12px 12px;margin:0 60px"></div><div style="text-align:center;color:#1B1B1B;font-size:20px;font-weight:bold"><span style="background:#FF3621;color:#fff;border-radius:12px;padding:0 10px;margin-right:6px">5</span>同じ評価データで、もう一度採点して比べる（2 に戻る）</div></div></div>
# MAGIC
# MAGIC 先に `03_build_agent` を最後まで実行しておいてください（ツールの登録が必要です）。

# COMMAND ----------

# MAGIC %pip install -qU databricks-openai "mlflow[databricks]>=3.11.1"
# MAGIC %restart_python

# COMMAND ----------

# MAGIC %run ./00_config

# COMMAND ----------

# MAGIC %md
# MAGIC ### 評価の同時実行数を抑える
# MAGIC
# MAGIC `mlflow.genai.evaluate` は、既定では評価データの複数の質問を同時にエージェントに実行させます。
# MAGIC Databricks Free Edition の基盤モデルには1秒あたりの呼び出し回数に上限があり、超えると
# MAGIC `429 REQUEST_LIMIT_EXCEEDED` のエラーになります。評価を始める前に、環境変数で同時実行数を1にし、
# MAGIC 429 が返ったときの再試行の回数を増やしておきます。
# MAGIC
# MAGIC - [環境変数の一覧（Databricks ドキュメント）](https://docs.databricks.com/aws/ja/mlflow3/genai/eval-monitor/concepts/eval-harness)

# COMMAND ----------

import os

# 評価データの質問を、1問ずつ順番にエージェントに実行させる（既定では複数の質問を同時に実行する）
os.environ["MLFLOW_GENAI_EVAL_MAX_WORKERS"] = "1"
# 429（呼び出し回数の上限を超えた）エラーが返ったときに、再試行する回数（既定は 3）
os.environ["MLFLOW_GENAI_EVAL_MAX_RETRIES"] = "5"

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## 0. 03 と同じエージェントを用意する（中身は 03 と同じなので、読み飛ばして構いません）
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:0.9fr 0.7fr 7fr;gap:8px;max-width:1150px;margin:18px 0 8px;align-items:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">利用者</div></div><div><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1"><div style="font-size:18px">質問</div>→</div><div style="height:28px"></div><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">←<div style="font-size:18px">最終回答</div></div></div><div style="border:3px solid #5B6470;border-radius:16px;padding:26px 14px 14px;position:relative"><div style="position:absolute;top:-16px;left:16px;background:#fff;padding:0 8px;font-size:20px;font-weight:bold;color:#1B1B1B">エージェント</div><div style="display:grid;grid-template-columns:1.2fr 0.9fr 1.2fr 0.4fr 1.2fr;gap:6px;align-items:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">LLM</div><div style="font-size:18px;margin-top:4px">何をするか決める</div></div><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1"><div style="font-size:18px">依頼 → / ← 結果</div>⇄</div><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">実行役</div><div style="font-size:18px;margin-top:4px">ツールを実行する<br>（プログラム）</div></div><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">ツール</div><div style="font-size:18px;margin-top:4px">Unity Catalog の関数</div></div></div><div style="margin-top:14px"><div style="position:relative;border:3px dashed #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">MLflow トレース</div><div style="font-size:18px;margin-top:4px">エージェントの中で実行したことを、順番どおりに記録する</div></div></div></div></div>

# COMMAND ----------

import mlflow

mlflow.openai.autolog()  # LLM の呼び出しを自動で記録する
w = WorkspaceClient()  # Unity Catalog に登録した関数の情報を読み出すために使う
TOOL_NAMES = ["get_today", "get_menu"]  # エージェントに持たせるツール


def tool_spec_from_uc(name):
    """Unity Catalog に登録した関数の名前・説明・引数から、ツールの説明（JSON）を作る（03 と同じ）"""
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
    """Unity Catalog に登録した関数を、SQL から実行する（03 と同じ）"""
    placeholders = ", ".join(f":{k}" for k in args)
    row = spark.sql(f"SELECT {CATALOG}.{SCHEMA}.{name}({placeholders}) AS r", args=args).first()
    return row.r if row.r else "該当するデータはありません"


SYSTEM_PROMPT = "あなたはひかり食堂の案内係です。必要に応じてツールを使って答えてください。"


def register_get_menu(param_comment):
    """get_menu を、引数 weekday の説明（param_comment）だけ変えて登録し直す。4. の候補 A で使う"""
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
    # 03 と違い、実行のたびに Unity Catalog からツールの説明を読み直す。
    # こうしておくと、4. で get_menu の説明を登録し直したときに、そのまま反映される
    specs = [tool_spec_from_uc(n) for n in TOOL_NAMES]
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": question}]
    for _ in range(max_steps):
        # LLM が考える
        reply = client.chat.completions.create(model=MODEL, messages=messages, tools=specs).choices[0].message
        if not reply.tool_calls:  # 依頼がなければ、それが最終回答
            return reply.content
        # 依頼されたツールを実行して、結果を会話の記録に足す
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

# MAGIC %md-sandbox
# MAGIC ## 1. 評価データを用意する
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1.2fr 0.3fr 1.4fr 0.3fr 1.2fr 0.3fr 1.2fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:1;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#FF3621;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">1</div><div style="font-weight:bold">評価データ</div><div style="font-size:18px;margin-top:4px">質問と正解の組</div></div></div><div style="grid-column:2;grid-row:1;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#C9CED6;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">2</div><div style="font-weight:bold">エージェントが答え、<br>LLM ジャッジが採点</div><div style="font-size:18px;margin-top:4px">Correctness など</div></div></div><div style="grid-column:4;grid-row:1;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:5;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#C9CED6;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">3</div><div style="font-weight:bold">トレースで<br>原因を探す</div><div style="font-size:18px;margin-top:4px">点の低い質問</div></div></div><div style="grid-column:6;grid-row:1;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#C9CED6;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">4</div><div style="font-weight:bold">1か所だけ直す</div><div style="font-size:18px;margin-top:4px">A または B</div></div></div><div style="grid-column:3 / 8;grid-row:2;align-self:start"><div style="border:3px solid #C9CED6;border-top:none;height:34px;border-radius:0 0 12px 12px;margin:0 60px"></div><div style="text-align:center;color:#8A929E;font-size:20px;font-weight:normal"><span style="background:#C9CED6;color:#fff;border-radius:12px;padding:0 10px;margin-right:6px">5</span>同じ評価データで、もう一度採点して比べる（2 に戻る）</div></div></div>
# MAGIC
# MAGIC 質問と、期待する答え（正解）の組です。正解はメニュー表から計算して作ります。
# MAGIC 「今日」「明日」の正解は実行した日によって変わるので、実行のたびに作り直します。

# COMMAND ----------

WEEK = "月火水木金土日"
now = datetime.now(timezone(timedelta(hours=9)))  # 日本時間


def day(offset):
    """今日から offset 日後の曜日（0 なら今日、1 なら明日）"""
    return WEEK[(now.weekday() + offset) % 7]  # % 7 で、日曜の次は月曜に戻る


def menu_of(wd):
    """曜日 wd のメニュー全部を、1つの文章にする"""
    items = [f"{c}：{i} {p}円" for d, c, i, p in MENU if d == wd]
    return "、".join(items) if items else "休業日のためメニューはない"


def item_of(wd, category):
    """曜日 wd の、種類 category の料理名と値段"""
    hit = [f"{i}（{p}円）" for d, c, i, p in MENU if d == wd and c == category]
    return hit[0] if hit else "休業日、または該当するメニューはない"


# 今日のメニューのうち、500円以下のもの
cheap_today = [f"{i}（{p}円）" for d, c, i, p in MENU if d == day(0) and p <= 500]

# (質問, 期待する答え) の組
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

# MLflow の評価で使う形にする
# inputs の中身が predict_fn の引数（question）として渡り、expectations が正解として採点に使われる
data = [{"inputs": {"question": q}, "expectations": {"expected_response": a}} for q, a in eval_data]
for d in data:
    print(d["inputs"]["question"], "→", d["expectations"]["expected_response"])

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## 2. 採点の観点（スコアラー）を決めて、評価する
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1.2fr 0.3fr 1.4fr 0.3fr 1.2fr 0.3fr 1.2fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:1;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#C9CED6;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">1</div><div style="font-weight:bold">評価データ</div><div style="font-size:18px;margin-top:4px">質問と正解の組</div></div></div><div style="grid-column:2;grid-row:1;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#FF3621;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">2</div><div style="font-weight:bold">エージェントが答え、<br>LLM ジャッジが採点</div><div style="font-size:18px;margin-top:4px">Correctness など</div></div></div><div style="grid-column:4;grid-row:1;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:5;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#C9CED6;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">3</div><div style="font-weight:bold">トレースで<br>原因を探す</div><div style="font-size:18px;margin-top:4px">点の低い質問</div></div></div><div style="grid-column:6;grid-row:1;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#C9CED6;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">4</div><div style="font-weight:bold">1か所だけ直す</div><div style="font-size:18px;margin-top:4px">A または B</div></div></div><div style="grid-column:3 / 8;grid-row:2;align-self:start"><div style="border:3px solid #C9CED6;border-top:none;height:34px;border-radius:0 0 12px 12px;margin:0 60px"></div><div style="text-align:center;color:#8A929E;font-size:20px;font-weight:normal"><span style="background:#C9CED6;color:#fff;border-radius:12px;padding:0 10px;margin-right:6px">5</span>同じ評価データで、もう一度採点して比べる（2 に戻る）</div></div></div>
# MAGIC
# MAGIC - `Correctness`：期待する答えと比べて正しいか（正解データが必要）
# MAGIC - `ToolCallEfficiency`：ツールを無駄に呼んでいないか

# COMMAND ----------

from mlflow.genai.scorers import Correctness, ToolCallEfficiency

# 採点の観点。どちらも LLM ジャッジが採点する
scorers = [Correctness(), ToolCallEfficiency()]


def predict_fn(question):
    """評価データの質問1つに対して、エージェントの回答を返す（評価では表示を省く）"""
    return run_agent(question, verbose=False)


# 評価の結果を、MLflow の実行（run）として名前を付けて残す。v2 と比べるときに使う
with mlflow.start_run(run_name="v1：直す前"):
    # 評価データの質問ごとに predict_fn を実行し、その回答とトレースをスコアラーで採点する
    result_v1 = mlflow.genai.evaluate(data=data, predict_fn=predict_fn, scorers=scorers)

result_v1.metrics  # 観点ごとの集計（正解した割合など）

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## 3. 点の低い質問を調べる
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1.2fr 0.3fr 1.4fr 0.3fr 1.2fr 0.3fr 1.2fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:1;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#C9CED6;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">1</div><div style="font-weight:bold">評価データ</div><div style="font-size:18px;margin-top:4px">質問と正解の組</div></div></div><div style="grid-column:2;grid-row:1;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#C9CED6;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">2</div><div style="font-weight:bold">エージェントが答え、<br>LLM ジャッジが採点</div><div style="font-size:18px;margin-top:4px">Correctness など</div></div></div><div style="grid-column:4;grid-row:1;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:5;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#FF3621;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">3</div><div style="font-weight:bold">トレースで<br>原因を探す</div><div style="font-size:18px;margin-top:4px">点の低い質問</div></div></div><div style="grid-column:6;grid-row:1;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#C9CED6;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">4</div><div style="font-weight:bold">1か所だけ直す</div><div style="font-size:18px;margin-top:4px">A または B</div></div></div><div style="grid-column:3 / 8;grid-row:2;align-self:start"><div style="border:3px solid #C9CED6;border-top:none;height:34px;border-radius:0 0 12px 12px;margin:0 60px"></div><div style="text-align:center;color:#8A929E;font-size:20px;font-weight:normal"><span style="background:#C9CED6;color:#fff;border-radius:12px;padding:0 10px;margin-right:6px">5</span>同じ評価データで、もう一度採点して比べる（2 に戻る）</div></div></div>
# MAGIC
# MAGIC 上のセルの出力にある評価結果のリンクを開き、`Correctness` が「no」の質問を選びます。
# MAGIC トレースを開いて、次を確かめてください。
# MAGIC
# MAGIC - どのツールが、どの引数で呼ばれたか
# MAGIC - ツールは何を返したか（「該当するデータはありません」になっていないか）
# MAGIC - LLM は、ツールの結果どおりに答えたか

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## 4. 1か所だけ直す
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1.2fr 0.3fr 1.4fr 0.3fr 1.2fr 0.3fr 1.2fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:1;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#C9CED6;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">1</div><div style="font-weight:bold">評価データ</div><div style="font-size:18px;margin-top:4px">質問と正解の組</div></div></div><div style="grid-column:2;grid-row:1;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#C9CED6;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">2</div><div style="font-weight:bold">エージェントが答え、<br>LLM ジャッジが採点</div><div style="font-size:18px;margin-top:4px">Correctness など</div></div></div><div style="grid-column:4;grid-row:1;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:5;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#C9CED6;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">3</div><div style="font-weight:bold">トレースで<br>原因を探す</div><div style="font-size:18px;margin-top:4px">点の低い質問</div></div></div><div style="grid-column:6;grid-row:1;align-self:center"><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#FF3621;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">4</div><div style="font-weight:bold">1か所だけ直す</div><div style="font-size:18px;margin-top:4px">A または B</div></div></div><div style="grid-column:3 / 8;grid-row:2;align-self:start"><div style="border:3px solid #C9CED6;border-top:none;height:34px;border-radius:0 0 12px 12px;margin:0 60px"></div><div style="text-align:center;color:#8A929E;font-size:20px;font-weight:normal"><span style="background:#C9CED6;color:#fff;border-radius:12px;padding:0 10px;margin-right:6px">5</span>同じ評価データで、もう一度採点して比べる（2 に戻る）</div></div></div>
# MAGIC
# MAGIC 原因に合わせて、**次のどれか1つだけ**を変えます。2か所以上を同時に変えると、何が効いたのか分からなくなります。
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;max-width:1150px;margin:18px 0 8px"><div style="font-size:20px;font-weight:bold;color:#1B1B1B;margin-bottom:8px">LLM を呼ぶたびに渡すもの</div><div style="display:grid;grid-template-columns:2fr 1fr;gap:12px;align-items:start"><div style="border:3px solid #FF3621;border-radius:12px;padding:10px 12px;background:#fff"><div style="font-size:20px;font-weight:bold;color:#1B1B1B">messages（会話の記録）</div><div style="border:2px solid #FF3621;background:#FFF1EE;color:#1B1B1B;border-radius:8px;padding:6px 12px;margin-top:8px;font-size:20px;text-align:left"><code style="font-weight:bold;margin-right:10px">system</code>役割とルール（システムプロンプト）<span style="background:#FF3621;color:#fff;border-radius:12px;padding:0 10px;margin-left:8px;font-size:18px;font-weight:bold">候補 B</span></div><div style="border:2px solid #C9CED6;background:#F7F8FA;color:#8A929E;border-radius:8px;padding:6px 12px;margin-top:8px;font-size:20px;text-align:left"><code style="font-weight:bold;margin-right:10px">user</code>利用者の質問</div></div><div style="position:relative;border:3px solid #FF3621;border-radius:12px;background:#FFF1EE;color:#1B1B1B;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#FF3621;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">候補 A</div><div style="font-weight:bold">tools（ツールの説明）</div><div style="font-size:18px;margin-top:4px">get_menu の引数 weekday の説明</div></div></div><div style="border:3px solid #FF3621;border-top:none;height:18px;border-radius:0 0 12px 12px;margin:4px 12% 0"></div><div style="text-align:center;color:#FF3621;font-size:28px;line-height:1.1">↓<div style="font-size:18px">messages と tools を渡す</div></div><div style="width:30%;margin:6px auto 0"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="font-weight:bold">LLM</div><div style="font-size:18px;margin-top:4px">何をするか決める</div></div></div></div>
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
SYSTEM_PROMPT_V2 = SYSTEM_PROMPT  # システムプロンプトは変えない

# COMMAND ----------

# 候補 B：システムプロンプトを変える（A を実行した場合は、このセルは実行しない）
# ツールの説明は変えない
SYSTEM_PROMPT_V2 = """あなたはひかり食堂の案内係です。
- 日付や曜日が関係する質問では、必ず最初に get_today で今日を確かめてください。
- メニューはツールの結果だけを使って答え、推測で答えないでください。"""

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## 5. 同じ評価データで、もう一度評価して比べる
# MAGIC
# MAGIC <div style="font-family:'Hiragino Sans','Meiryo',sans-serif;display:grid;grid-template-columns:1.2fr 0.3fr 1.4fr 0.3fr 1.2fr 0.3fr 1.2fr;gap:10px 6px;max-width:1150px;margin:8px 0;align-items:center"><div style="grid-column:1;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#C9CED6;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">1</div><div style="font-weight:bold">評価データ</div><div style="font-size:18px;margin-top:4px">質問と正解の組</div></div></div><div style="grid-column:2;grid-row:1;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:3;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#C9CED6;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">2</div><div style="font-weight:bold">エージェントが答え、<br>LLM ジャッジが採点</div><div style="font-size:18px;margin-top:4px">Correctness など</div></div></div><div style="grid-column:4;grid-row:1;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:5;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#C9CED6;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">3</div><div style="font-weight:bold">トレースで<br>原因を探す</div><div style="font-size:18px;margin-top:4px">点の低い質問</div></div></div><div style="grid-column:6;grid-row:1;align-self:center"><div style="text-align:center;color:#8A929E;font-size:28px;line-height:1.1">→</div></div><div style="grid-column:7;grid-row:1;align-self:center"><div style="position:relative;border:3px solid #C9CED6;border-radius:12px;background:#F7F8FA;color:#8A929E;padding:12px 10px;text-align:center;font-size:20px;line-height:1.35"><div style="position:absolute;top:-14px;left:10px;background:#C9CED6;color:#fff;font-size:18px;font-weight:bold;padding:0 10px;border-radius:12px">4</div><div style="font-weight:bold">1か所だけ直す</div><div style="font-size:18px;margin-top:4px">A または B</div></div></div><div style="grid-column:3 / 8;grid-row:2;align-self:start"><div style="border:3px solid #FF3621;border-top:none;height:34px;border-radius:0 0 12px 12px;margin:0 60px"></div><div style="text-align:center;color:#1B1B1B;font-size:20px;font-weight:bold"><span style="background:#FF3621;color:#fff;border-radius:12px;padding:0 10px;margin-right:6px">5</span>同じ評価データで、もう一度採点して比べる（2 に戻る）</div></div></div>

# COMMAND ----------

def predict_fn_v2(question):
    """直した後のエージェントで回答する（A の場合はツールの説明が、B の場合はシステムプロンプトが変わっている）"""
    return run_agent(question, system_prompt=SYSTEM_PROMPT_V2, verbose=False)


# 評価データとスコアラーは v1 と同じものを使う。変えたのは predict_fn だけ
with mlflow.start_run(run_name="v2：直した後"):
    result_v2 = mlflow.genai.evaluate(data=data, predict_fn=predict_fn_v2, scorers=scorers)

import pandas as pd

# v1 と v2 の集計を横に並べて比べる
pd.DataFrame({"v1：直す前": result_v1.metrics, "v2：直した後": result_v2.metrics})

# COMMAND ----------

# MAGIC %md
# MAGIC ### ふりかえり
# MAGIC
# MAGIC - 何を変えたか、なぜそこを変えたか
# MAGIC - スコアは上がったか、下がったか、変わらなかったか
# MAGIC - 点が上がった質問と、下がった質問はあったか
