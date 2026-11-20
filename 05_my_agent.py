# Databricks notebook source
# MAGIC %md
# MAGIC # 05：自分のエージェントを作る
# MAGIC
# MAGIC 01〜04 では、ひかり食堂のエージェントを使って仕組みを確かめました。ここでは、自分で選んだ題材でエージェントを作ります。
# MAGIC
# MAGIC このノートブックは2部に分かれています。
# MAGIC
# MAGIC | 部 | 節 | やること |
# MAGIC |---|---|---|
# MAGIC | 第1部（宿題） | 1〜4 | 題材を決め、データ・ツール・システムプロンプトを書いて、質問に答えさせる |
# MAGIC | 第2部（第2回の授業） | 5〜8 | 評価データを書いて評価し、1か所だけ直して、もう一度評価して比べる |
# MAGIC
# MAGIC 書き換えるのは、見出しに **【書き換える】** と付いた節のセルだけです。ほかのセルはそのまま実行します。
# MAGIC
# MAGIC 最初は、架空の大学「みどり大学」の学内イベント案内が例として入っています。書き換えずに上から実行すれば、そのまま動きます。動くことを確かめてから、自分の題材に書き換えてください。

# COMMAND ----------

# MAGIC %md
# MAGIC ## 題材の選び方
# MAGIC
# MAGIC 次の3つを満たす題材を選びます。
# MAGIC
# MAGIC - 答えが正しいかどうかを、自分で判定できる
# MAGIC - ツールを2回以上使わないと答えられない質問が作れる（例：今日の日付を調べてから、その日のイベントを調べる）
# MAGIC - 架空のデータで作れる（実在の人の名前や連絡先などの個人情報は入れない）
# MAGIC
# MAGIC | 題材の例 | データの1行 | ツールの例 |
# MAGIC |---|---|---|
# MAGIC | 学内イベントの案内（このノートブックの例） | 日付・時間・イベント名・場所 | 日付で探す、場所で探す |
# MAGIC | 時間割の案内 | 曜日・時限・授業名・教室 | 曜日で探す、授業名で探す |
# MAGIC | 部室の予約状況 | 日付・時間帯・部屋・予約した団体 | 日付で探す、部屋で探す |
# MAGIC | ゲームのアイテム図鑑 | アイテム名・種類・効果・入手場所 | 種類で探す、名前で探す |
# MAGIC
# MAGIC データは手で書いても、Genie Code（画面右上のアシスタント）に「学内イベントの架空のデータを15行作って」のように日本語で頼んで作ってもかまいません。

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
# MAGIC ## 1. 題材を決めて、データを書く【書き換える】
# MAGIC
# MAGIC - `THEME`：題材の名前。システムプロンプトの例で使います
# MAGIC - `COLUMNS`：列の一覧。1つの列を `("列の名前", "列の意味")` の組で書きます。列の名前は半角の英小文字で、意味は日本語で書きます
# MAGIC - `ROWS`：データ。1行を `( )` で囲み、`COLUMNS` と同じ順番・同じ数の値を書きます。値はすべて `" "` で囲みます
# MAGIC
# MAGIC カンマ `,` と引用符 `"` は、半角で書きます。日本語入力のまま打つと全角になり、エラーになります。

# COMMAND ----------

THEME = "みどり大学の学内イベント案内"

COLUMNS = [
    ("date", "日付"),
    ("time", "開始時刻"),
    ("event", "イベント名"),
    ("place", "場所"),
]

ROWS = [
    ("2026-11-26", "12:30", "昼休みミニコンサート", "学生会館ホール"),
    ("2026-11-26", "18:00", "プログラミング勉強会", "情報棟 301"),
    ("2026-11-27", "13:00", "留学説明会", "本館 2F 大会議室"),
    ("2026-11-30", "10:00", "古本市", "図書館前広場"),
    ("2026-12-01", "16:30", "キャリア相談会", "キャリアセンター"),
    ("2026-12-02", "12:30", "昼休みミニコンサート", "学生会館ホール"),
    ("2026-12-03", "18:00", "プログラミング勉強会", "情報棟 301"),
    ("2026-12-04", "14:00", "写真部 作品展", "図書館 1F ギャラリー"),
    ("2026-12-07", "15:00", "ボードゲーム交流会", "学生会館 2F"),
    ("2026-12-09", "12:30", "献血", "本館前"),
    ("2026-12-10", "18:00", "プログラミング勉強会", "情報棟 301"),
    ("2026-12-11", "13:00", "卒業研究ポスター発表", "情報棟 1F ロビー"),
    ("2026-12-15", "17:00", "クリスマス点灯式", "正門前"),
    ("2026-12-17", "12:30", "昼休みミニコンサート", "学生会館ホール"),
    ("2026-12-17", "16:00", "英語スピーチコンテスト", "本館 2F 大会議室"),
    ("2026-12-18", "10:00", "古本市", "図書館前広場"),
]

# COMMAND ----------

# MAGIC %md
# MAGIC 下のセルで、データをテーブルにします。データを書き換えたら、このセルから 4. までを順に実行し直してください（ツールもデータに合わせて登録し直すため）。

# COMMAND ----------

import re

MY_TABLE = f"{CATALOG}.{SCHEMA}.my_data"  # 自分のデータを入れるテーブル

# 書き方の間違いを、分かりやすいメッセージで知らせる
for col in COLUMNS:
    if not (isinstance(col, tuple) and len(col) == 2):
        raise ValueError(f'COLUMNS の1つの列は ("列の名前", "列の意味") の組で書いてください：{col}')
COLUMN_NAMES = [c for c, _ in COLUMNS]
for c in COLUMN_NAMES:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", c):
        raise ValueError(f"列の名前「{c}」は、半角の英小文字で始め、英小文字・数字・_ だけで書いてください")
for i, r in enumerate(ROWS, start=1):
    if len(r) != len(COLUMNS):
        raise ValueError(f"{i}行目の値の数が {len(r)} 個です。COLUMNS と同じ {len(COLUMNS)} 個にしてください：{r}")

# すべての列を文字列として、テーブルを作り直す（前に作ったものは置き換える）
schema = ", ".join(f"`{c}` STRING" for c in COLUMN_NAMES)
(spark.createDataFrame([tuple(str(v) for v in r) for r in ROWS], schema)
    .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(MY_TABLE))

display(spark.table(MY_TABLE))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. ツールを決める【書き換える】
# MAGIC
# MAGIC ここで作るツールは、「データのある列で絞り込んで、当てはまる行を返す」ものです。1つのツールを、次の5つの項目で書きます。
# MAGIC
# MAGIC | 項目 | 書くこと |
# MAGIC |---|---|
# MAGIC | `name` | ツールの名前。半角の英小文字・数字・`_` で、何をするツールか分かる名前にする |
# MAGIC | `description` | ツールの説明。何を返すツールかを日本語で書く |
# MAGIC | `column` | 絞り込みに使う列の名前（`COLUMNS` に書いたもの） |
# MAGIC | `match` | `"equal"`（値がぴったり同じ行）か `"contains"`（値を含む行）のどちらか |
# MAGIC | `arg_description` | LLM がツールに渡す値（引数）の説明。どんな形で渡せばよいかを書く |
# MAGIC
# MAGIC 03 で確かめたとおり、LLM が読むのは名前と説明だけです。中身が正しくても、名前と説明が分かりにくいとツールは使われません。
# MAGIC
# MAGIC 今日の日付と曜日を返す `get_today` は、最初から持たせてあります。ここに書く必要はありません。

# COMMAND ----------

TOOLS = [
    {
        "name": "find_events_by_date",
        "description": "みどり大学で、指定した日付に開かれるイベントを返します。",
        "column": "date",
        "match": "equal",
        "arg_description": "日付",
    },
    {
        "name": "find_events_by_place",
        "description": "みどり大学で、指定した場所で開かれるイベントを返します。場所の名前の一部でも探せます。",
        "column": "place",
        "match": "contains",
        "arg_description": "場所の名前（例：図書館）",
    },
]

# COMMAND ----------

# MAGIC %md
# MAGIC 下のセルで、ツールを Unity Catalog に登録します。03 と同じく、関数の説明（`COMMENT`）が LLM に渡るツールの説明になります。読み飛ばしてかまいません。

# COMMAND ----------

import mlflow

w = WorkspaceClient()  # Unity Catalog に登録した関数の情報を読み出すために使う


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


def register_lookup_tool(tool):
    """TOOLS に書いた1つのツールを、「列で絞り込んで行を返す」関数として登録する"""
    missing = [k for k in ("name", "description", "column", "match", "arg_description") if k not in tool]
    if missing:
        raise ValueError(f"ツールに {missing} の項目がありません。名前の綴りも確かめてください：{tool}")
    name, column, match = tool["name"], tool["column"], tool["match"]
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise ValueError(f"ツールの名前「{name}」は、半角の英小文字で始め、英小文字・数字・_ だけで書いてください")
    if name in ("get_today", "get_menu", "tool_a"):  # 01〜04 で使っている名前は使えない
        raise ValueError(f"ツールの名前「{name}」は 01〜04 で使っているので、別の名前にしてください")
    if column not in COLUMN_NAMES:
        raise ValueError(f"ツール「{name}」の column「{column}」が、COLUMNS にありません。使える列：{COLUMN_NAMES}")
    if match == "equal":
        condition = f"t.`{column}` = {name}.search_value"  # 値がぴったり同じ行
    elif match == "contains":
        condition = f"t.`{column}` LIKE concat('%', {name}.search_value, '%')"  # 値を含む行
    else:
        raise ValueError(f'ツール「{name}」の match は "equal" か "contains" にしてください')
    # 1行を「日付：2026-11-26、開始時刻：12:30、…」の形にする
    row_text = ", ".join(f"concat('{sql_text(label)}：', t.`{c}`)" for c, label in COLUMNS)
    arg_comment = sql_text(tool["arg_description"])  # 引数の説明（LLM に渡る）
    tool_comment = sql_text(tool["description"])  # ツールの説明（LLM に渡る）
    spark.sql(f"""
    CREATE OR REPLACE FUNCTION {CATALOG}.{SCHEMA}.{name}(
      search_value STRING COMMENT '{arg_comment}'
    )
    RETURNS STRING
    COMMENT '{tool_comment}'
    RETURN (
      SELECT concat_ws('\\n', collect_list(concat_ws('、', {row_text})))
      FROM {MY_TABLE} t
      WHERE {condition}
    )
    """)


def register_tools(tools):
    """get_today と、TOOLS に書いたツールをまとめて登録し、エージェントに持たせる"""
    global TOOL_NAMES
    register_get_today()
    for tool in tools:
        register_lookup_tool(tool)
    TOOL_NAMES = ["get_today"] + [t["name"] for t in tools]
    print("エージェントに持たせるツール：", TOOL_NAMES)


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
        # 03 と違い、エラーでも止めずに、エラーの内容を LLM に返す（トレースにも残る）
        return f"ツールの実行でエラーになりました：{str(e).splitlines()[0]}"
    return row.r if row.r else "該当するデータはありません"


register_tools(TOOLS)

# 動作確認：LLM に渡すツールの説明を表示する
print(json.dumps([tool_spec_from_uc(n) for n in TOOL_NAMES], ensure_ascii=False, indent=2))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. システムプロンプトを書く【書き換える】
# MAGIC
# MAGIC エージェントの役割を、LLM に伝える文章です。最初は短くてかまいません。

# COMMAND ----------

SYSTEM_PROMPT = f"あなたは{THEME}の案内係です。必要に応じてツールを使って答えてください。"

# COMMAND ----------

# MAGIC %md
# MAGIC 下のセルで、エージェントを用意します。ループは 04 とほぼ同じです。

# COMMAND ----------

mlflow.openai.autolog()  # LLM の呼び出しを自動で記録する


@mlflow.trace(name="エージェントの実行")
def run_agent(question, system_prompt=None, max_steps=8, verbose=True):
    # 実行のたびに Unity Catalog からツールの説明を読み直す（7. でツールを直したときに、そのまま反映される）
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
# MAGIC ## 4. 質問して、答えを確かめる【書き換える】
# MAGIC
# MAGIC 自分の題材で、エージェントに聞いてみたい質問を書きます。ツールを2回以上使う質問を、1つは入れてください。
# MAGIC
# MAGIC 実行すると、質問ごとにトレースが表示されます。どのツールが、どの値で呼ばれたかを確かめてください。
# MAGIC うまく答えられない質問があってもかまいません。第2回で、原因を調べて直します。
# MAGIC
# MAGIC **宿題はここまでです。** 第2回までに、1〜4 を自分の題材に書き換えて、最後まで実行しておいてください。
# MAGIC
# MAGIC 「すべてを実行」すると、5. のセルで「評価データを自分の題材に書き換えてから…」というエラーが出て止まります。これは第2部の前で止めるためのもので、正常です。

# COMMAND ----------

QUESTIONS = [
    "今日はどんなイベントがある？",
    "明日、図書館で何かある？",
    "情報棟で開かれるイベントは？",
]

for q in QUESTIONS:
    print(f"Q：{q}")
    print(f"A：{run_agent(q)}\n")

# COMMAND ----------

# MAGIC %md
# MAGIC # 第2部（第2回の授業）
# MAGIC
# MAGIC 第2回は、ノートブックの一番上から「すべてを実行」で 4. までを実行し直してから始めます（第1部の結果は残っていないため）。
# MAGIC 5. のセルでエラーが出て止まるので、そこから続けます。

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. 評価データを書く【書き換える】
# MAGIC
# MAGIC 質問と、期待する答え（正解）の組を5〜10問書きます。04 と同じ形です。
# MAGIC
# MAGIC - 正解は、データを見て自分で書きます
# MAGIC - 4. で試した質問のほかに、聞き方を変えた質問も入れます（例：「12月4日」「12/4」「2026-12-04」）
# MAGIC - 「今日」「明日」を含む質問は、実行する日によって正解が変わります。入れる場合は、授業の当日の正解を書いてください
# MAGIC
# MAGIC 書き終えたら、`READY = True` に変えてから実行します。

# COMMAND ----------

READY = False

EVAL_DATA = [
    ("12月4日はどんなイベントがある？", "写真部 作品展（14:00、図書館 1F ギャラリー）"),
    ("12/17 の昼休みには何がある？", "昼休みミニコンサート（12:30、学生会館ホール）"),
    ("図書館で開かれるイベントは？", "古本市（11月30日と12月18日、図書館前広場）と、写真部 作品展（12月4日、図書館 1F ギャラリー）"),
    ("学生会館ホールのイベントはいつ？", "11月26日、12月2日、12月17日の昼休みミニコンサート（12:30）"),
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
# MAGIC 1問ずつ順番に実行するので、10問で1〜2分かかります。

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
# MAGIC ## 7. 点の低い質問を調べて、1か所だけ直す【書き換える】
# MAGIC
# MAGIC 上のセルの出力にある評価結果のリンクを開き、`Correctness` が「no」の質問のトレースを開きます。04 と同じく、次を確かめます。
# MAGIC
# MAGIC - どのツールが、どの値で呼ばれたか
# MAGIC - ツールは何を返したか（「該当するデータはありません」になっていないか）
# MAGIC - LLM は、ツールの結果どおりに答えたか
# MAGIC
# MAGIC 原因が分かったら、下のセルで **ツールかシステムプロンプトのどちらか1つだけ** を直します。2つを同時に変えると、どちらが効いたのか分からなくなります。
# MAGIC
# MAGIC | 直すもの | こういう原因なら |
# MAGIC |---|---|
# MAGIC | ツールの説明・引数の説明 | ツールに渡す値の形が、データと合っていない（例：「12月4日」が渡され、データは「2026-12-04」） |
# MAGIC | ツールを足す | 質問に答えるためのツールがない（例：イベント名で探すツールがない） |
# MAGIC | システムプロンプト | ツールを使わずに推測で答えている、ツールの結果と違うことを答えている |
# MAGIC
# MAGIC 下のセルには、例の題材の直し方を1つだけ入れてあります。`#` を外すと使えます。自分の題材では、上の表から原因に合うものを選んで書き換えます。

# COMMAND ----------

import copy

# 直す前のものをそのまま写す。このあとに、直したいところだけを書き換える
TOOLS_V2 = copy.deepcopy(TOOLS)
SYSTEM_PROMPT_V2 = SYSTEM_PROMPT

# 例：1つ目のツールの、引数の説明を変える（例の題材で「12月4日」の質問が失敗した場合）
# TOOLS_V2[0]["arg_description"] = "日付。2026-12-04 の形で、年・月・日を - でつなぐ"


# COMMAND ----------

changed_tools = TOOLS_V2 != TOOLS
changed_prompt = SYSTEM_PROMPT_V2 != SYSTEM_PROMPT
if changed_tools and changed_prompt:
    raise ValueError("ツールとシステムプロンプトの両方が変わっています。どちらか1つだけにしてください")
if not (changed_tools or changed_prompt):
    raise ValueError("まだ何も直していません。上のセルで1か所直してから実行してください")

register_tools(TOOLS_V2)  # ツールを直した場合は、ここで登録し直す
print("直したもの：", "ツール" if changed_tools else "システムプロンプト")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. もう一度評価して比べる
# MAGIC
# MAGIC 評価データと採点の観点は、6. と同じです。違うのは、7. で直した1か所だけです。

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
# MAGIC ## ふりかえり（発表で話すこと）
# MAGIC
# MAGIC - どんな題材のエージェントを作ったか
# MAGIC - どの質問で、なぜうまく答えられなかったか（トレースで分かったこと）
# MAGIC - 何を直したか、点数はどう変わったか
# MAGIC
# MAGIC 同じ設定でも、評価のたびに点数は少し変わります。点数だけで判断せず、直したかった質問がトレースの上で直っているかも確かめてください。
