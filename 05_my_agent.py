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
# MAGIC 下のセルで、書いたデータを読み込みます。読み飛ばしてかまいません。

# COMMAND ----------

import csv
import io

rows = [[v.strip() for v in r] for r in csv.reader(io.StringIO(DATA.strip())) if any(v.strip() for v in r)]
HEADERS, BODY = rows[0], rows[1:]
if len(HEADERS) < 2:
    raise ValueError("列が1つしかありません。カンマが全角（，や、）になっていないか確かめてください")
for i, r in enumerate(BODY, start=2):
    if len(r) != len(HEADERS):
        raise ValueError(f"{i}行目の値の数が {len(r)} 個です。見出しと同じ {len(HEADERS)} 個にしてください：{r}")

# データの1行を、見出しを付けた1つの文章にしておく。例：「日付：12/04、開始時刻：14:00、イベント名：写真部 作品展、場所：図書館 1F ギャラリー」
LINES = ["、".join(f"{h}：{v}" for h, v in zip(HEADERS, r)) for r in BODY]
for line in LINES:
    print(line)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. ツールの説明を書く【書き換える】
# MAGIC
# MAGIC このノートブックのツールは、「データの中から、言葉を含む行を探す」`search_data` の1つだけです。中身は用意してあるので、書くのは **ツールの説明** だけです。
# MAGIC
# MAGIC 下のセルの `" "` の中の文章を書き換えます。
# MAGIC
# MAGIC LLM はデータそのものを見ていません。LLM がデータについて知る手がかりは、このツールの説明だけです。LLM は説明を読んで、ツールを使うかどうかと、どんな言葉を渡すかを決めます。データに何が入っているかを、1〜2文で書きます。
# MAGIC
# MAGIC ツールはもう1つ、今日の日付と曜日を返す `get_today` を持たせてあります。

# COMMAND ----------

TOOL_DESCRIPTION = "みどり大学の学内イベントの一覧から、指定した言葉を含むイベントを探します。日付、開始時刻、イベント名、場所が分かります。"

# COMMAND ----------

# MAGIC %md
# MAGIC 下のセルで、2つのツールを用意します。中身は短いので、読んでおくとトレースが読みやすくなります。
# MAGIC
# MAGIC このノートブックでは、仕組みに集中するため、ツールをノートブックの中の Python の関数にしています。本番で使うエージェントでは、ツールを Unity Catalog に登録し、誰が使えるかを権限で管理します。

# COMMAND ----------

from datetime import datetime, timedelta, timezone


def get_today():
    """今日の日付と曜日を返す"""
    now = datetime.now(timezone(timedelta(hours=9)))  # 日本時間
    return f"{now:%Y-%m-%d}（{'月火水木金土日'[now.weekday()]}）"


def search_data(keyword):
    """データの中から、keyword を含む行を返す。どの列に書かれた言葉でも見つかる"""
    hits = [line for line in LINES if keyword in line]
    return "\n".join(hits) if hits else "該当するデータはありません"


TOOLS = {"get_today": get_today, "search_data": search_data}

print(get_today())
print(search_data("図書館"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. システムプロンプトを書く【書き換える】
# MAGIC
# MAGIC エージェントの役割を、LLM に伝える文章です。下のセルの `" "` の中の文章を書き換えます。最初は1〜2文でかまいません。

# COMMAND ----------

SYSTEM_PROMPT = "あなたは、みどり大学の学内イベントの案内係です。必要に応じてツールを使って答えてください。"

# COMMAND ----------

# MAGIC %md
# MAGIC 下のセルで、エージェントのループ（LLM に聞く → 依頼されたツールを実行する → 結果を渡す、を答えが出るまで繰り返す）を用意します。読み飛ばしてかまいません。

# COMMAND ----------

import logging
import mlflow

logging.getLogger("mlflow").setLevel(logging.ERROR)  # 学習に関係しない MLflow の警告を表示しない
mlflow.openai.autolog()  # LLM の呼び出しを自動で記録する


def tool_specs():
    """LLM に渡すツールの説明（JSON）。search_data の説明には、2. の TOOL_DESCRIPTION をそのまま使う"""
    return [
        {"type": "function", "function": {
            "name": "get_today",
            "description": "今日の日付と曜日を返します（日本時間）。例：2026-12-14（月）",
            "parameters": {"type": "object", "properties": {}, "required": []}}},
        {"type": "function", "function": {
            "name": "search_data",
            "description": TOOL_DESCRIPTION,
            "parameters": {"type": "object",
                           "properties": {"keyword": {"type": "string", "description": "探す言葉"}},
                           "required": ["keyword"]}}},
    ]


@mlflow.trace(name="エージェントの実行")
def run_agent(question, max_steps=8, verbose=True):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": question}]
    for _ in range(max_steps):
        # LLM が考える（ツールの説明は、実行のたびに TOOL_DESCRIPTION から作り直す）
        reply = client.chat.completions.create(model=MODEL, messages=messages, tools=tool_specs()).choices[0].message
        if not reply.tool_calls:  # 依頼がなければ、それが最終回答
            return reply.content
        # 依頼されたツールを実行して、結果を会話の記録に足す
        messages.append(reply.to_dict())
        for call in reply.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            with mlflow.start_span(name=f"ツール：{call.function.name}", span_type="TOOL") as span:
                span.set_inputs(args)
                result = TOOLS[call.function.name](**args)
                span.set_outputs(result)
            if verbose:  # 結果の1行目だけを表示する
                print(f"  [ツール] {call.function.name}({args}) → {result.splitlines()[0]} …")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    return "（繰り返しの上限に達しました）"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. 質問して、トレースで確かめる【書き換える】
# MAGIC
# MAGIC 自分の題材で、エージェントに聞いてみたい質問を、下のセルに1行に1つずつ書きます。ツールを2回以上使う質問を、1つは入れてください。
# MAGIC
# MAGIC 実行すると、質問ごとにトレースが表示されます。トレースは、エージェントの中で起きたことを順番に記録したものです。左の「Trace breakdown」で `ツール：search_data` を選ぶと、右の「Inputs / Outputs」に、入力（LLM が渡した言葉）と出力（ツールが返した結果）が出ます。
# MAGIC
# MAGIC 答えがおかしかったら、トレースを次の順に見ます（第2回の 7. でも同じ順で見ます）。
# MAGIC
# MAGIC 1. ツールは呼ばれたか
# MAGIC 2. ツールに渡した言葉は、データの書き方と合っているか
# MAGIC 3. LLM は、ツールの結果どおりに答えたか
# MAGIC
# MAGIC 正しく答えられない質問があってもかまいません。第2回で、原因を調べて直します。
# MAGIC
# MAGIC **宿題はここまでです。** 第2回までに、1〜4 を自分の題材に書き換えて、ここまで実行しておいてください。
# MAGIC
# MAGIC 「すべてを実行」すると、5. のセルで「評価データを自分の題材に書き換えてから…」というエラーが出て止まります。第2部の前で止めるためのもので、正常です。

# COMMAND ----------

# 1行に1つ、質問を書く
QUESTIONS = """
今日はどんなイベントがある？
明日、図書館で何かある？
古本市はいつ？
"""

for q in [line.strip() for line in QUESTIONS.strip().splitlines() if line.strip()]:
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
# MAGIC 質問と、期待する答え（正解）を5〜10組書きます。1. のデータと同じく、1行に1組をカンマで区切って書きます。
# MAGIC
# MAGIC - 正解は、データを見て自分で書きます
# MAGIC - 4. で試した質問のほかに、書き方を変えた質問も入れます（例：「12/4」と「12月4日」）
# MAGIC - 「今日」「明日」を含む質問は、実行する日によって正解が変わるので、入れません
# MAGIC
# MAGIC 書き終えたら、セルの1行目の `READY = False` を `READY = True` に書き換えてから実行します。

# COMMAND ----------

READY = False

# 1行目は見出し。2行目から、質問と正解をカンマで区切って書く（1. のデータと同じ書き方）
EVAL_DATA = """
質問,正解
12月4日はどんなイベントがある？,写真部 作品展（14:00、図書館 1F ギャラリー）
12月17日の昼休みには何がある？,昼休みミニコンサート（12:30、学生会館ホール）
図書館で開かれるイベントは？,古本市（11月30日と12月18日、図書館前広場）と、写真部 作品展（12月4日、図書館 1F ギャラリー）
プログラミング勉強会はどこで開かれる？,情報棟 301
12月25日にイベントはある？,ない
"""

if not READY:
    raise ValueError("評価データを自分の題材に書き換えてから、READY = True にして実行してください")

# 書いた評価データを読み込み、MLflow の評価で使う形にする
pairs = [[v.strip() for v in r] for r in csv.reader(io.StringIO(EVAL_DATA.strip())) if any(v.strip() for v in r)][1:]
for i, r in enumerate(pairs, start=2):
    if len(r) != 2:
        raise ValueError(f"{i}行目は、質問と正解の2つをカンマで区切って書いてください（正解の中では、半角のカンマを使わない）：{r}")
data = [{"inputs": {"question": q}, "expectations": {"expected_response": a}} for q, a in pairs]
for q, a in pairs:
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


# 8. で比べるために、直す前（v1）のツールの説明とシステムプロンプトを控えておく
TOOL_DESCRIPTION_V1 = TOOL_DESCRIPTION
SYSTEM_PROMPT_V1 = SYSTEM_PROMPT

with mlflow.start_run(run_name="v1：直す前"):
    result_v1 = mlflow.genai.evaluate(data=data, predict_fn=predict_fn, scorers=scorers)

result_v1.metrics

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. 原因を調べて、1か所だけ直す【書き換える】
# MAGIC
# MAGIC 上のセルの出力にある「View evaluation results in MLflow」を押して評価結果を開き、`Correctness` が「Fail」の質問のトレースを開きます。
# MAGIC トレースを次の表の上から順に見て、**最初に当てはまったところ** を直します。直すのは1か所だけです。2か所を同時に変えると、どちらが効いたのか分からなくなります。
# MAGIC
# MAGIC | 順番 | トレースで見ること | こうなっていたら | 直すもの |
# MAGIC |---|---|---|---|
# MAGIC | ① | ツールは呼ばれたか | ツールを呼ばずに答えている | システムプロンプトに「必ずツールで調べてから答える」と書き足す |
# MAGIC | ② | ツールに渡した言葉は、データの書き方と合っているか | 合っていない（例：データは「12/04」なのに「12月4日」が渡されている） | ツールの説明に、どんな形で言葉を渡せばよいかを書き足す |
# MAGIC | ③ | LLM は、ツールの結果どおりに答えたか | 結果にないことを答えている | システムプロンプトに「ツールの結果だけを使って答える」と書き足す |
# MAGIC
# MAGIC 下のセルの、当てはまったほうの `""` の中に、書き足す文章を書いて実行します。もう一方は `""` のままにします。
# MAGIC
# MAGIC 例の題材では ② に当てはまるので、ツールの説明のほうに「日付で探すときは、12/04 のように、月と日を2桁の数字にして / でつないだ形で渡してください。」と書きます。

# COMMAND ----------

# ② に当てはまったら：ツールの説明に書き足す文章を、"" の中に書く
ADD_TO_TOOL_DESCRIPTION = ""

# ① か ③ に当てはまったら：システムプロンプトに書き足す文章を、"" の中に書く
ADD_TO_SYSTEM_PROMPT = ""

# 直す前（v1）の文章の後ろに書き足す
TOOL_DESCRIPTION = TOOL_DESCRIPTION_V1 + ADD_TO_TOOL_DESCRIPTION
SYSTEM_PROMPT = SYSTEM_PROMPT_V1 + ADD_TO_SYSTEM_PROMPT

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. もう一度評価して比べる
# MAGIC
# MAGIC 評価データと採点の観点は、6. と同じです。違うのは、7. で直した1か所だけです。
# MAGIC
# MAGIC 実行したら「View evaluation results in MLflow」を押し、上の「Compare」で「v1：直す前」と「v2：直した後」を選ぶと、質問ごとに v1 と v2 の結果が並びます。直したかった質問が、Fail から Pass になったかを確かめてください。

# COMMAND ----------

import pandas as pd

# 直したのが1か所だけかを確かめる（直し忘れや、両方を直した場合はここで止まる）
changed_tool = TOOL_DESCRIPTION != TOOL_DESCRIPTION_V1
changed_prompt = SYSTEM_PROMPT != SYSTEM_PROMPT_V1
if changed_tool and changed_prompt:
    raise ValueError("7. のセルで、2つの \"\" の両方に書いています。どちらか1つだけにしてください")
if not (changed_tool or changed_prompt):
    raise ValueError("まだ何も直していません。7. のセルの \"\" の中に、書き足す文章を書いて実行してください")
print("直したもの：", "ツールの説明" if changed_tool else "システムプロンプト")

# 直したツールの説明かシステムプロンプトで、6. と同じ評価をする
with mlflow.start_run(run_name="v2：直した後"):
    result_v2 = mlflow.genai.evaluate(data=data, predict_fn=predict_fn, scorers=scorers)

pd.DataFrame({"v1：直す前": result_v1.metrics, "v2：直した後": result_v2.metrics})

# COMMAND ----------

# MAGIC %md
# MAGIC ## ふりかえり（発表で聞かれること）
# MAGIC
# MAGIC - どんな題材のエージェントを作ったか
# MAGIC - どの質問で、なぜ正しく答えられなかったか（トレースで分かったこと）
# MAGIC - 何を、なぜ直したか（7. の表のどれに当てはまったか）
# MAGIC - 点数はどう変わったか。直したかった質問が、トレースの上で直ったか
# MAGIC
# MAGIC 同じ設定でも、評価のたびに点数は少し変わります。点数だけで判断せず、直したかった質問がトレースの上で直っているかも確かめてください。
