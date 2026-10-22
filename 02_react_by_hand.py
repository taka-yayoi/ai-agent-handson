# Databricks notebook source
# MAGIC %md
# MAGIC # 02：あなたがループになる（問い②）
# MAGIC
# MAGIC 01 では、人が「何を調べるか」を決め、調べて、プロンプトに貼りました。ここでは役割を分けます。
# MAGIC
# MAGIC | 役割 | 担当 |
# MAGIC |---|---|
# MAGIC | 何を調べるかを決める | LLM |
# MAGIC | 実際に調べる（ツールを実行する） | あなた（このあと、プログラムに置き換える） |
# MAGIC
# MAGIC **「すべてを実行」は使わず、上から1セルずつ実行してください。**

# COMMAND ----------

# MAGIC %pip install -qU databricks-openai
# MAGIC %restart_python

# COMMAND ----------

# MAGIC %run ./00_config

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. ツールを用意する
# MAGIC
# MAGIC ツールは、ふつうの Python の関数です。

# COMMAND ----------

def get_today():
    """今日の日付と曜日を返す（日本時間）"""
    now = datetime.now(timezone(timedelta(hours=9)))
    return f"{now:%Y-%m-%d}（{'月火水木金土日'[now.weekday()]}）"


def get_menu(weekday):
    """指定した曜日のメニューを返す"""
    rows = spark.sql(
        f"SELECT category, item, price FROM {MENU_TABLE} WHERE weekday = :w", args={"w": weekday}
    ).collect()
    if not rows:
        return "該当するメニューはありません"
    return "\n".join(f"{r.category}：{r.item} {r.price}円" for r in rows)


TOOLS = {"get_today": get_today, "get_menu": get_menu}

print(get_today())
print(get_menu("月"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. ツールの説明を書く
# MAGIC
# MAGIC LLM は関数の中身を読めません。読むのは、名前・説明・引数（関数に渡す値）の説明だけです。
# MAGIC これを JSON（プログラム同士がデータをやり取りするときの書式）で書いて LLM に渡します。

# COMMAND ----------

tool_specs = [
    {
        "type": "function",
        "function": {
            "name": "get_today",
            "description": "今日の日付と曜日を返します。",
            "parameters": {"type": "object", "properties": {}},
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
                    "weekday": {"type": "string", "description": "曜日を1文字で。月, 火, 水, 木, 金, 土, 日 のいずれか"}
                },
                "required": ["weekday"],
            },
        },
    },
]

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. 会話を始める
# MAGIC
# MAGIC `messages` は、LLM に渡す会話の記録です。`role` は発言者を表します。
# MAGIC
# MAGIC - `system`：LLM への役割やルールの指示（システムプロンプト）
# MAGIC - `user`：利用者の質問
# MAGIC - `assistant`：LLM の返事
# MAGIC - `tool`：ツールの実行結果

# COMMAND ----------

messages = [
    {"role": "system", "content": "あなたはひかり食堂の案内係です。必要に応じてツールを使って答えてください。"},
    {"role": "user", "content": "今日の日替わり定食は何？"},
]

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. ループを手で回す
# MAGIC
# MAGIC 次の2つのセルを、**A → B → A → B …** の順に、A が「最終回答」を出すまで繰り返し実行してください。
# MAGIC
# MAGIC - **セル A（LLM が考える）**：LLM に会話の記録を渡し、次に何をするかを決めさせます
# MAGIC - **セル B（あなたが行動する）**：LLM が依頼したツールを実行し、結果を会話の記録に足します

# COMMAND ----------

# セル A：LLM が考える
resp = client.chat.completions.create(model=MODEL, messages=messages, tools=tool_specs)
reply = resp.choices[0].message

print("【LLM の返事（そのまま）】")
print(json.dumps(reply.to_dict(), ensure_ascii=False, indent=2))
print("=" * 60)
if reply.tool_calls:
    for call in reply.tool_calls:
        print(f"LLM の依頼：{call.function.name} を 引数 {call.function.arguments} で実行してほしい")
    print("→ セル B を実行してください")
else:
    print("【最終回答】")
    print(reply.content)

# COMMAND ----------

# セル B：あなたが行動する（LLM の依頼どおりにツールを実行する）
if not reply.tool_calls:
    print("依頼はありません。セル A で最終回答が出ています。次の「確かめること」に進んでください")
else:
    messages.append(reply.to_dict())  # LLM の返事を会話の記録に足す
    for call in reply.tool_calls:
        args = json.loads(call.function.arguments or "{}")
        result = TOOLS[call.function.name](**args)  # ← ツールを実行しているのは、LLM ではなくこの行
        print(f"{call.function.name}({args}) の結果：\n{result}\n")
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

# MAGIC %md
# MAGIC ## 5. ループをプログラムに任せる
# MAGIC
# MAGIC あなたが手でやった「A → B → A → B」を、`while` の繰り返しにします。これがエージェントの本体です。

# COMMAND ----------

def run_agent(question, max_steps=6):
    messages = [
        {"role": "system", "content": "あなたはひかり食堂の案内係です。必要に応じてツールを使って答えてください。"},
        {"role": "user", "content": question},
    ]
    for step in range(max_steps):
        reply = client.chat.completions.create(model=MODEL, messages=messages, tools=tool_specs).choices[0].message
        if not reply.tool_calls:  # 依頼がなければ、それが最終回答
            return reply.content
        messages.append(reply.to_dict())
        for call in reply.tool_calls:  # 依頼されたツールを実行して、結果を返す
            args = json.loads(call.function.arguments or "{}")
            result = TOOLS[call.function.name](**args)
            print(f"  [ステップ{step + 1}] {call.function.name}({args})")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    return "（繰り返しの上限に達しました）"


print(run_agent("今日の日替わり定食は何？"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. 質問を変えてみる
# MAGIC
# MAGIC 下の質問を書き換えて実行し、LLM がどのツールを何回呼ぶかを見てください。
# MAGIC
# MAGIC - 「こんにちは」
# MAGIC - 「明日のデザートは何？」
# MAGIC - 「カレーがあるのは何曜日？」

# COMMAND ----------

print(run_agent("カレーがあるのは何曜日？"))
