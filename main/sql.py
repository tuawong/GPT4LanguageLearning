from sqlalchemy.orm import Session
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from database import engine
from models import WordDict, QuizAgg, PhraseDict, QuizLog
import pandas as pd
from typing import List

def count_overlap_word(new_word_list: List) -> tuple[int,int]:
    """
    Count the number of overlapping words between the new words and the existing words in the database.
    To generate message for the user.
    """ 
    overlap_word = 0
    chunk_size = 500
    new_word_list = list(set(new_word_list))
    with engine.begin() as conn:
        for i in range(0, len(new_word_list), chunk_size):
            chunk = new_word_list[i:i+chunk_size]
            placeholders = ",".join([f":w{j}" for j in range(len(chunk))])
            params = {f"w{j}": v for j, v in enumerate(chunk)}
            sql = text(f"""
                SELECT COUNT(DISTINCT word)
                FROM WordDict
                WHERE word IN ({placeholders})
            """)
            overlap_word += conn.execute(sql, params).scalar() or 0

    dedup = len(new_word_list)
    add_word = dedup - overlap_word
    return overlap_word, add_word


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
        
        overlap_count, add_count = count_overlap_word(df['word'].tolist())
        message = f"Overwrite mode enabled.  Replacing {overlap_count} words and {add_count} new words added."
        return message
    
    except SQLAlchemyError as e:
        message = f"Replace-by-word transaction failed: {e}"
        return message 
 

 
def sql_update_phrasedict(df: pd.DataFrame):
    """
    For every distinct `word` in df:
      - delete all existing WordDict rows with that word
      - insert the provided rows for that word
    All in one transaction (atomic).
    """
    df = df.copy()
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    df['added_date'] = pd.to_datetime('today').normalize()

    # Ensure required columns exist
    required = ['phrase_id', 'line', 'pinyin', 'meaning', 'response', 'response_pinyin',
        'response_meaning', 'complexity', 'category', 'tone', 'added_date']
        
    for col in required:
        if col not in df.columns:
            df[col] = None

    # Generate word_id
    df_id = pd.read_sql("SELECT MAX(phrase_id) FROM PhraseDict", engine)
    max_phrase_id = pd.to_numeric(df_id.values[0][0].replace("P", ""))
    new_phrase_ids = ['P'+str(num + max_phrase_id).zfill(6) for num in range(1, df.shape[0] + 1)]
    df['phrase_id'] = new_phrase_ids

    # SQLite wants None, not NaN
    df = df.where(pd.notnull(df), None)

    records = df[required].to_dict(orient="records")

    try:
        with Session(engine) as session:
            session.bulk_insert_mappings(PhraseDict, records)
            session.commit()
        
        message = "Saved new phrases to the dictionary."
        return message
    
    except SQLAlchemyError as e:
        message = f"Replace-by-word transaction failed: {e}"
        return message 
 


def sql_update_quizlog(df: pd.DataFrame):
    """
    For every distinct `word` in df:
      - delete all existing WordDict rows with that word
      - insert the provided rows for that word
    All in one transaction (atomic).
    """
    df = df.copy()
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    df['last_quiz'] = pd.to_datetime('today').normalize()

    # Ensure required columns exist

    # Generate word_id
    df_id = pd.read_sql("SELECT MAX(quiz_id) FROM QuizLog", engine)
    max_phrase_id = pd.to_numeric(df_id.values[0][0].replace("QW", ""))
    new_phrase_ids = ['QW'+str(num + max_phrase_id).zfill(6) for num in range(1, df.shape[0] + 1)]
    df['quiz_id'] = new_phrase_ids
    
    required = ['quiz_id', 'word_id', 'word', 'sentence', 'sentence_pinyin',
       'pinyin_answer', 'pinyin_correct', 'pinyin_correction', 'meaning',
       'meaning_correct', 'meaning_correction', 'last_quiz']
        
    for col in required:
        if col not in df.columns:
            df[col] = None

    # SQLite wants None, not NaN
    df = df.where(pd.notnull(df), None)

    records = df[required].to_dict(orient="records")

    try:
        with Session(engine) as session:
            session.bulk_insert_mappings(QuizLog, records)
            session.commit()
        
        message = "Saved quiz result."
        return message
    
    except SQLAlchemyError as e:
        message = f"QuizLog Update transaction failed: {e}"
        return message 
 