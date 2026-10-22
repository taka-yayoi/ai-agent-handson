# Databricks notebook source
# MAGIC %md
# MAGIC # 00_config：共通の設定
# MAGIC
# MAGIC 各ノートブックの先頭で `%run ./00_config` として読み込みます。直接開いて実行する必要はありません。
# MAGIC
# MAGIC - 使う LLM、カタログとスキーマの名前を決めます
# MAGIC - 演習で使う架空の学食「ひかり食堂」のメニュー表を作ります（すでにあれば作り直しません）

# COMMAND ----------

import json
from datetime import datetime, timedelta, timezone

from databricks.sdk import WorkspaceClient
from databricks_openai import DatabricksOpenAI

# 使う LLM（Databricks が提供している基盤モデル）
MODEL = "databricks-qwen3-next-80b-a3b-instruct"

# データと関数を置く場所（カタログ.スキーマ）
CATALOG = "workspace"
SCHEMA = "agent_handson"
MENU_TABLE = f"{CATALOG}.{SCHEMA}.menu"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

# LLM を呼び出すためのクライアント（OpenAI と同じ書き方で呼べる）
client = DatabricksOpenAI()

# COMMAND ----------

# 架空の学食「ひかり食堂」のメニュー。土日は休業
MENU = [
    ("月", "日替わり定食", "鶏の唐揚げ定食", 520),
    ("月", "麺", "醤油ラーメン", 450),
    ("月", "カレー", "ビーフカレー", 480),
    ("月", "デザート", "プリン", 150),
    ("火", "日替わり定食", "サバの味噌煮定食", 540),
    ("火", "麺", "きつねうどん", 380),
    ("火", "丼", "親子丼", 460),
    ("火", "デザート", "杏仁豆腐", 160),
    ("水", "日替わり定食", "ハンバーグ定食", 560),
    ("水", "麺", "冷やし中華", 470),
    ("水", "カレー", "カツカレー", 590),
    ("水", "デザート", "プリン", 150),
    ("木", "日替わり定食", "豚の生姜焼き定食", 530),
    ("木", "麺", "天ぷらそば", 490),
    ("木", "丼", "牛丼", 420),
    ("木", "デザート", "コーヒーゼリー", 150),
    ("金", "日替わり定食", "白身魚フライ定食", 510),
    ("金", "麺", "味噌ラーメン", 480),
    ("金", "カレー", "シーフードカレー", 520),
    ("金", "デザート", "わらび餅", 170),
]

if not spark.catalog.tableExists(MENU_TABLE):
    (spark.createDataFrame(MENU, "weekday STRING, category STRING, item STRING, price INT")
        .write.saveAsTable(MENU_TABLE))

print(f"LLM: {MODEL}")
print(f"メニュー表: {MENU_TABLE}")
