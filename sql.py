from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from database import engine
from models import WordDict, QuizAgg
import pandas as pd


def sql_update_worddict(df: pd.DataFrame):
    """
    For every distinct `word` in df:
      - delete all existing WordDict rows with that word
      - insert the provided rows for that word
    All in one transaction (atomic).
    """
    # Defensive copy & normalize
    df = df.copy()
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    df['added_date'] = pd.to_datetime('today').normalize()

    # Ensure required columns exist
    required = {
        "word", "pinyin", "pinyin_simplified", "type", "word_category",
        "word_rarity", "meaning", "sentence", "sentence_pinyin",
        "sentence_meaning"
    }
    for col in required:
        if col not in df.columns:
            df[col] = None

    # Generate word_id
    df_id = pd.read_sql("SELECT MAX(word_id) FROM WordDict", engine)
    max_word_id = pd.to_numeric(df_id.values[0][0].replace("D", ""))
    new_word_ids = ['D'+str(num + max_word_id).zfill(6) for num in range(1, len(df) + 1)]
    df["word_id"] = new_word_ids
    
    # SQLite wants None, not NaN
    df = df.where(pd.notnull(df), None)

    words_to_replace = sorted(set(df["word"]))
    if not words_to_replace:
        return  # nothing to do

    records = df[[
        "word_id","word","pinyin","pinyin_simplified","type","word_category",
        "word_rarity","meaning","sentence","sentence_pinyin","sentence_meaning",
        "added_date"
    ]].to_dict(orient="records")

    try:
        with Session(engine) as session:
            # 1) Delete existing rows for these words
            session.query(WordDict)\
                   .filter(WordDict.word.in_(words_to_replace))\
                   .delete(synchronize_session=False)

            # 2) Insert the new rows
            session.bulk_insert_mappings(WordDict, records)

            # 3) Initialize QuizAgg rows for any new word_ids
            if records:
                quizagg_init = [
                    {"word_id": r["word_id"],
                     "num_quiz_attempt": 0, "num_correct": 0, "num_wrong": 0,
                     "last_quiz": None}
                    for r in records
                ]
                session.bulk_insert_mappings(QuizAgg, quizagg_init)
            
            session.commit()

    except SQLAlchemyError as e:
        print("Replace-by-word transaction failed:", e)
        raise 
 