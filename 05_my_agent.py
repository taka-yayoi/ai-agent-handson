# Databricks notebook source
# MAGIC %md
# MAGIC # 05：自分のエージェントを作る
# MAGIC
# MAGIC 01〜04 では、ひかり食堂のエージェントで仕組みを確かめました。ここでは、自分で選んだ題材でエージェントを作ります。
# MAGIC
# MAGIC | 部 | 節 | やること |
# MAGIC |---|---|---|
# MAGIC | 第1部（宿題） | 1〜4 | データを書き、ツールの説明とシステムプロンプトを書いて、質問に答えさせる |
# MAGIC | 第2部（第2回の授業） | 5〜8 | 評価して、1か所だけ直して、もう一度評価して比べる |
# MAGIC
# MAGIC 書き換えるのは、見出しに **【書き換える】** と付いたセルだけです。ほかのセルはそのまま実行します。
# MAGIC
# MAGIC 最初は、架空の大学「みどり大学」の学内イベント案内が例として入っています。まずは書き換えずに「すべてを実行」して、動くことを確かめてください。

# COMMAND ----------

# MAGIC %md
# MAGIC ## 題材の選び方
# MAGIC
# MAGIC 次の3つを満たす題材を選びます。
# MAGIC
# MAGIC - 答えが正しいかどうかを、自分で判定できる
# MAGIC - 今日の日付を調べてからデータを探す、のようにツールを2回以上使う質問が作れる
# MAGIC - 架空のデータで作れる（実在の人の名前や連絡先などの個人情報は入れない）
# MAGIC
# MAGIC | 題材の例 | データの列 |
# MAGIC |---|---|
# MAGIC | 学内イベントの案内（このノートブックの例） | 日付、開始時刻、イベント名、場所 |
# MAGIC | 時間割の案内 | 曜日、時限、授業名、教室 |
# MAGIC | 部室の予約状況 | 日付、時間帯、部屋、予約した団体 |
# MAGIC | ゲームのアイテム図鑑 | アイテム名、種類、効果、入手場所 |

# COMMAND ----------

# MAGIC %pip install -qU databricks-openai "mlflow[databricks]>=3.11.1"
# MAGIC %restart_python

# COMMAND ----------

# MAGIC %run ./00_config

# COMMAND ----------

# MAGIC %md
# MAGIC # 第1部（宿題）

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. データを書く【書き換える】
# MAGIC
# MAGIC 表を、1行目が見出し、2行目からがデータの形で書きます。値はカンマ `,` で区切ります。10〜20行が目安です。
# MAGIC
# MAGIC - カンマは半角で書きます。日本語入力のまま打つと全角の「，」や「、」になり、列が分かれません
# MAGIC - データは手で書いても、Genie Code（画面右上のアシスタント）に「学内イベントの架空のデータを、日付,開始時刻,イベント名,場所 の見出しで15行、カンマ区切りで作って」のように頼んで作ってもかまいません

# COMMAND ----------

THEME = "みどり大学の学内イベント案内"

DATA = """
日付,開始時刻,イベント名,場所
11/26,12:30,昼休みミニコンサート,学生会館ホール
11/26,18:00,プログラミング勉強会,情報棟 301
11/27,13:00,留学説明会,本館 2F 大会議室
11/30,10:00,古本市,図書館前広場
12/01,16:30,キャリア相談会,キャリアセンター
12/02,12:30,昼休みミニコンサート,学生会館ホール
12/03,18:00,プログラミング勉強会,情報棟 301
12/04,14:00,写真部 作品展,図書館 1F ギャラリー
12/07,15:00,ボードゲーム交流会,学生会館 2F
12/09,12:30,献血,本館前
12/10,18:00,プログラミング勉強会,情報棟 301
12/11,13:00,卒業研究ポスター発表,情報棟 1F ロビー
12/15,17:00,クリスマス点灯式,正門前
12/17,12:30,昼休みミニコンサート,学生会館ホール
12/17,16:00,英語スピーチコンテスト,本館 2F 大会議室
12/18,10:00,古本市,図書館前広場
"""

# COMMAND ----------

# MAGIC %md
# MAGIC 下のセルで、データをテーブルにします。読み飛ばしてかまいません。

# COMMAND ----------

import csv
import io

MY_TABLE = f"{CATALOG}.{SCHEMA}.my_data"  # 自分のデータを入れるテーブル

rows = [[v.strip() for v in r] for r in csv.reader(io.StringIO(DATA.strip())) if any(v.strip() for v in r)]
HEADERS, BODY = rows[0], rows[1:]
if len(HEADERS) < 2:
    raise ValueError("列が1つしかありません。カンマが全角（，や、）になっていないか確かめてください")
for i, r in enumerate(BODY, start=2):
    if len(r) != len(HEADERS):
        raise ValueError(f"{i}行目の値の数が {len(r)} 個です。見出しと同じ {len(HEADERS)} 個にしてください：{r}")

# 列の名前は c1, c2, … とし、見出しは 2. のツールが返す文字列の中で使う
COLS = [f"c{i}" for i in range(1, len(HEADERS) + 1)]
(spark.createDataFrame(BODY, ", ".join(f"{c} STRING" for c in COLS))
    .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(MY_TABLE))

display(spark.table(MY_TABLE).toDF(*HEADERS))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. ツールの説明を書く【書き換える】
# MAGIC
# MAGIC このノートブックのツールは、「データの中から、言葉を含む行を探す」`search_data` の1つだけです。中身は用意してあるので、書くのは **ツールの説明** だけです。
# MAGIC
# MAGIC 03 で確かめたとおり、LLM はツールの説明を読んで、ツールを使うかどうかと、何を渡すかを決めます。データに何が入っているかを、1〜2文で書きます。
# MAGIC
# MAGIC ツールはもう1つ、今日の日付と曜日を返す `get_today` を持たせてあります。

# COMMAND ----------

TOOL_DESCRIPTION = "みどり大学の学内イベントの一覧から、指定した言葉を含むイベントを探します。日付、開始時刻、イベント名、場所が分かります。"

# COMMAND ----------

# MAGIC %md
# MAGIC 下のセルで、ツールを Unity Catalog に登録します。読み飛ばしてかまいません。中身を見たい場合は、03 と同じく左のメニューの **カタログ** → **workspace** → **agent_handson** → **機能** → **search_data** を開くと、「説明」と「定義」が見られます。

# COMMAND ----------

import mlflow

w = WorkspaceClient()  # Unity Catalog に登録した関数の情報を読み出すために使う
TOOL_NAMES = ["get_today", "search_data"]


def sql_text(s):
    """SQL の文字列の中に入れられるように、引用符（'）とバックスラッシュの前にバックスラッシュを付ける"""
    return str(s).replace("\\", "\\\\").replace("'", "\\'")


def register_get_today():
    """今日の日付と曜日を返すツール（03 と同じ）"""
    spark.sql(f"""
    CREATE OR REPLACE FUNCTION {CATALOG}.{SCHEMA}.get_today()
    RETURNS STRING
    LANGUAGE PYTHON
    COMMENT '今日の日付と曜日を返します（日本時間）。例：2026-12-14（月）'
    AS $$
from datetime import datetime, timedelta, timezone
now = datetime.now(timezone(timedelta(hours=9)))
return f"{{now:%Y-%m-%d}}（{{'月火水木金土日'[now.weekday()]}}）"
    $$
    """)


def register_search_data(description):
    """データの中から、言葉を含む行を探すツール。description がツールの説明として LLM に渡る"""
    # 1行を「日付：12/04、開始時刻：14:00、…」の形の文字列にする
    row_text = ", ".join(f"concat('{sql_text(h)}：', {c})" for h, c in zip(HEADERS, COLS))
    spark.sql(f"""
    CREATE OR REPLACE FUNCTION {CATALOG}.{SCHEMA}.search_data(
      keyword STRING COMMENT '探す言葉'
    )
    RETURNS STRING
    COMMENT '{sql_text(description)}'
    RETURN (
      SELECT concat_ws('\\n', collect_list(t.row_text))
      FROM (SELECT concat_ws('、', {row_text}) AS row_text FROM {MY_TABLE}) t
      WHERE t.row_text LIKE concat('%', search_data.keyword, '%')
    )
    """)


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
    """Unity Catalog に登録した関数を、SQL から実行する（03 とほぼ同じ）"""
    placeholders = ", ".join(f":{k}" for k in args)
    try:
        row = spark.sql(f"SELECT {CATALOG}.{SCHEMA}.{name}({placeholders}) AS r", args=args).first()
    except Exception as e:
        # エラーでも止めずに、エラーの内容を LLM に返す（トレースにも残る）
        return f"ツールの実行でエラーになりました：{str(e).splitlines()[0]}"
    return row.r if row.r else "該当するデータはありません"


register_get_today()
register_search_data(TOOL_DESCRIPTION)

# 動作確認：LLM に渡すツールの説明を表示する
print(json.dumps([tool_spec_from_uc(n) for n in TOOL_NAMES], ensure_ascii=False, indent=2))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. システムプロンプトを書く【書き換える】
# MAGIC
# MAGIC エージェントの役割を、LLM に伝える文章です。最初は1〜2文でかまいません。

# COMMAND ----------

SYSTEM_PROMPT = f"あなたは{THEME}の案内係です。必要に応じてツールを使って答えてください。"

# COMMAND ----------

# MAGIC %md
# MAGIC 下のセルで、エージェントのループを用意します。04 と同じです。読み飛ばしてかまいません。

# COMMAND ----------

mlflow.openai.autolog()  # LLM の呼び出しを自動で記録する


@mlflow.trace(name="エージェントの実行")
def run_agent(question, system_prompt=None, max_steps=8, verbose=True):
    # 実行のたびに Unity Catalog からツールの説明を読み直す（7. でツールの説明を直したときに、そのまま反映される）
    specs = [tool_spec_from_uc(n) for n in TOOL_NAMES]
    messages = [{"role": "system", "content": system_prompt or SYSTEM_PROMPT}, {"role": "user", "content": question}]
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
            if verbose:  # 結果の1行目だけを表示する
                print(f"  [ツール] {call.function.name}({args}) → {result.splitlines()[0]} …")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    return "（繰り返しの上限に達しました）"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. 質問して、トレースで確かめる【書き換える】
# MAGIC
# MAGIC 自分の題材で、エージェントに聞いてみたい質問を書きます。ツールを2回以上使う質問を、1つは入れてください。
# MAGIC
# MAGIC 実行すると、質問ごとにトレースが表示されます。どのツールが、どの値で呼ばれ、何が返ったかを確かめてください。
# MAGIC 正しく答えられない質問があってもかまいません。第2回で、原因を調べて直します。
# MAGIC
# MAGIC **宿題はここまでです。** 第2回までに、1〜4 を自分の題材に書き換えて、ここまで実行しておいてください。
# MAGIC
# MAGIC 「すべてを実行」すると、5. のセルで「評価データを自分の題材に書き換えてから…」というエラーが出て止まります。第2部の前で止めるためのもので、正常です。

# COMMAND ----------

QUESTIONS = [
    "今日はどんなイベントがある？",
    "明日、図書館で何かある？",
    "古本市はいつ？",
]

for q in QUESTIONS:
    print(f"Q：{q}")
    print(f"A：{run_agent(q)}\n")

# COMMAND ----------

# MAGIC %md
# MAGIC # 第2部（第2回の授業）
# MAGIC
# MAGIC 第2回は、ノートブックの一番上から「すべてを実行」で 4. までを実行し直してから始めます（第1部の実行結果は残っていないため）。
# MAGIC 5. のセルでエラーが出て止まるので、そこから続けます。

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. 評価データを書く【書き換える】
# MAGIC
# MAGIC 質問と、期待する答え（正解）の組を5〜10問書きます。04 と同じ形です。
# MAGIC
# MAGIC - 正解は、データを見て自分で書きます
# MAGIC - 4. で試した質問のほかに、書き方を変えた質問も入れます（例：「12/4」と「12月4日」）
# MAGIC - 「今日」「明日」を含む質問は、実行する日によって正解が変わるので、入れません
# MAGIC
# MAGIC 書き終えたら、`READY = True` に変えてから実行します。

# COMMAND ----------

READY = False

EVAL_DATA = [
    ("12月4日はどんなイベントがある？", "写真部 作品展（14:00、図書館 1F ギャラリー）"),
    ("12月17日の昼休みには何がある？", "昼休みミニコンサート（12:30、学生会館ホール）"),
    ("図書館で開かれるイベントは？", "古本市（11月30日と12月18日、図書館前広場）と、写真部 作品展（12月4日、図書館 1F ギャラリー）"),
    ("プログラミング勉強会はどこで開かれる？", "情報棟 301"),
    ("12月25日にイベントはある？", "ない"),
]

if not READY:
    raise ValueError("評価データを自分の題材に書き換えてから、READY = True にして実行してください")

# MLflow の評価で使う形にする（04 と同じ）
data = [{"inputs": {"question": q}, "expectations": {"expected_response": a}} for q, a in EVAL_DATA]
for q, a in EVAL_DATA:
    print(q, "→", a)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. 評価する
# MAGIC
# MAGIC 04 と同じ2つの観点で採点します。
# MAGIC
# MAGIC - `Correctness`：期待する答えと比べて正しいか
# MAGIC - `ToolCallEfficiency`：ツールを無駄に呼んでいないか
# MAGIC
# MAGIC 1問ずつ順番に実行するので、数分かかります。

# COMMAND ----------

import os
from mlflow.genai.scorers import Correctness, ToolCallEfficiency

# 呼び出し回数の上限（429 エラー）を超えないように、1問ずつ順番に実行する（04 と同じ）
os.environ["MLFLOW_GENAI_EVAL_MAX_WORKERS"] = "1"
os.environ["MLFLOW_GENAI_EVAL_MAX_RETRIES"] = "5"

scorers = [Correctness(), ToolCallEfficiency()]


def predict_fn(question):
    """評価データの質問1つに対して、エージェントの回答を返す"""
    return run_agent(question, verbose=False)


with mlflow.start_run(run_name="v1：直す前"):
    result_v1 = mlflow.genai.evaluate(data=data, predict_fn=predict_fn, scorers=scorers)

result_v1.metrics

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. 原因を調べて、1か所だけ直す【書き換える】
# MAGIC
# MAGIC 上のセルの出力にある評価結果のリンクを開き、`Correctness` が「Fail」の質問のトレースを開いて、次を確かめます。
# MAGIC
# MAGIC - `search_data` に、どんな言葉が渡されたか
# MAGIC - それはデータの書き方と合っているか（例：データは「12/04」なのに「12月4日」が渡されていないか）
# MAGIC - LLM は、ツールの結果どおりに答えたか
# MAGIC
# MAGIC 原因が分かったら、下のセルで A か B の **どちらか1つだけ** を直します。2つを同時に変えると、どちらが効いたのか分からなくなります。
# MAGIC
# MAGIC | 候補 | 直すもの | こういう原因なら |
# MAGIC |---|---|---|
# MAGIC | A | ツールの説明 | ツールに渡す言葉の書き方が、データと合っていない |
# MAGIC | B | システムプロンプト | ツールを使わずに推測で答えている、ツールの結果と違うことを答えている |
# MAGIC
# MAGIC A か B のどちらか1つの `#` を外して、自分の題材に合わせて書き換えます。

# COMMAND ----------

# v1 をコピーして v2 を作る（v1 は比べるために残す）
TOOL_DESCRIPTION_V2 = TOOL_DESCRIPTION
SYSTEM_PROMPT_V2 = SYSTEM_PROMPT

# A：ツールの説明を直す（例の題材では、データの日付の書き方を伝える）
# TOOL_DESCRIPTION_V2 = TOOL_DESCRIPTION + "日付は 12/04 のように、月と日を2桁の数字にして / でつないで書いています。"

# B：システムプロンプトを直す
# SYSTEM_PROMPT_V2 = SYSTEM_PROMPT + "ツールの結果だけを使って答え、推測で答えないでください。"

# COMMAND ----------

changed_tool = TOOL_DESCRIPTION_V2 != TOOL_DESCRIPTION
changed_prompt = SYSTEM_PROMPT_V2 != SYSTEM_PROMPT
if changed_tool and changed_prompt:
    raise ValueError("A と B の両方が変わっています。どちらか1つだけにしてください")
if not (changed_tool or changed_prompt):
    raise ValueError("まだ何も直していません。上のセルで A か B の # を外してから実行してください")

register_search_data(TOOL_DESCRIPTION_V2)  # A の場合は、直した説明でツールを登録し直す
print("直したもの：", "A（ツールの説明）" if changed_tool else "B（システムプロンプト）")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. もう一度評価して比べる
# MAGIC
# MAGIC 評価データと採点の観点は、6. と同じです。違うのは、7. で直した1か所だけです。
# MAGIC
# MAGIC 質問ごとの結果は、v1 と v2 の評価結果のリンクをそれぞれ開いて見比べます。直したかった質問が、v2 で「Pass」になったかを確かめてください。

# COMMAND ----------

import pandas as pd


def predict_fn_v2(question):
    """直した後のエージェントで回答する"""
    return run_agent(question, system_prompt=SYSTEM_PROMPT_V2, verbose=False)


with mlflow.start_run(run_name="v2：直した後"):
    result_v2 = mlflow.genai.evaluate(data=data, predict_fn=predict_fn_v2, scorers=scorers)

pd.DataFrame({"v1：直す前": result_v1.metrics, "v2：直した後": result_v2.metrics})

# COMMAND ----------

# MAGIC %md
# MAGIC ## ふりかえり（発表で聞かれること）
# MAGIC
# MAGIC - どんな題材のエージェントを作ったか
# MAGIC - どの質問で、なぜ正しく答えられなかったか（トレースで分かったこと）
# MAGIC - A と B のどちらを、なぜ直したか
# MAGIC - 点数はどう変わったか。直したかった質問が、トレースの上で直ったか
# MAGIC
# MAGIC 同じ設定でも、評価のたびに点数は少し変わります。点数だけで判断せず、直したかった質問がトレースの上で直っているかも確かめてください。
