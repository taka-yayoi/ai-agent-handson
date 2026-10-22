# Databricks notebook source
# MAGIC %md
# MAGIC # 01：LLM だけで答えられるか（問い①）
# MAGIC
# MAGIC 架空の学食「ひかり食堂」について、LLM に質問してみます。
# MAGIC
# MAGIC 1. LLM だけに聞く
# MAGIC 2. 必要な情報を、人がプロンプトに貼り付けてから聞く
# MAGIC 3. 質問を変えると、貼り付ける情報も変わることを確かめる

# COMMAND ----------

# MAGIC %pip install -qU databricks-openai
# MAGIC %restart_python

# COMMAND ----------

# MAGIC %run ./00_config

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. LLM だけに聞く

# COMMAND ----------

def ask(prompt):
    """LLM に1回だけ質問して、答えの文章を返す"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content


print(ask("ひかり食堂の、今日の日替わり定食は何ですか？"))

# COMMAND ----------

# MAGIC %md
# MAGIC LLM は「今日が何日か」も「ひかり食堂のメニュー」も知りません。分からないと答えるか、それらしい答えを作ってしまいます。

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. 必要な情報を、人がプロンプトに貼り付けてから聞く
# MAGIC
# MAGIC 今日の日付と、今日のメニューを調べて、プロンプトに書き足します。

# COMMAND ----------

now = datetime.now(timezone(timedelta(hours=9)))  # 日本時間
weekday = "月火水木金土日"[now.weekday()]
today = f"{now:%Y-%m-%d}（{weekday}）"

rows = spark.sql(f"SELECT category, item, price FROM {MENU_TABLE} WHERE weekday = '{weekday}'").collect()
menu_today = "\n".join(f"{r.category}：{r.item} {r.price}円" for r in rows) or "休業日"

prompt = f"""次の情報だけを使って答えてください。

# 今日の日付
{today}

# ひかり食堂の今日のメニュー（土日は休業）
{menu_today}

# 質問
ひかり食堂の、今日の日替わり定食は何ですか？"""

print(prompt)
print("=" * 60)
print(ask(prompt))

# COMMAND ----------

# MAGIC %md
# MAGIC 情報を渡せば、正しく答えられます。

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. 質問を変えると、貼り付ける情報も変わる
# MAGIC
# MAGIC 「明日のデザートは何？」と聞くなら、明日の日付と明日のメニューが要ります。
# MAGIC 「カレーがあるのは何曜日？」なら、1週間分のメニューが要ります。
# MAGIC
# MAGIC 質問のたびに、人が「何を調べて貼るか」を考えて、調べて、貼る必要があります。

# COMMAND ----------

# MAGIC %md
# MAGIC ### 考えてみよう
# MAGIC
# MAGIC 「何を調べるか」を決める作業と、「実際に調べる」作業を、それぞれ誰に任せられるでしょうか。
# MAGIC 次のノートブック `02_react_by_hand` で確かめます。
