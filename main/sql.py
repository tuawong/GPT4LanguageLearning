import hashlib

from sqlalchemy.orm import Session
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from database import engine
from models import WordDict, QuizAgg, PhraseDict, QuizLog, ResponseLog, TranslationLog, WordComparison
import pandas as pd
from typing import List


def _compute_pair_id(word1: str, word2: str) -> str:
    """Return a stable 14-char identifier for a (word1, word2) pair."""
    raw = f"{(word1 or '').strip()}|{(word2 or '').strip()}"
    return "WP" + hashlib.sha256(raw.encode()).hexdigest()[:12]

def load_dict():
    """
    Load the dictionary data from the database, joining with quiz statistics.
    """
    rename_dict = {'word_id': 'Word Id',
    'word': 'Word',
    'pinyin': 'Pinyin',
    'pinyin_simplified': 'Pinyin Simplified',
    'type': 'Type',
    'word_category': 'Word Category',
    'word_rarity': 'Word Rarity',
    'meaning': 'Meaning',
    'sentence': 'Sentence',
    'sentence_pinyin': 'Sentence Pinyin',
    'sentence_meaning': 'Sentence Meaning',
    'added_date': 'Added Date',
    'num_quiz_attempt': 'Quiz Attempts',
    'pinyin_correct_cnt': 'Num Pinyin Correct',
    'pinyin_wrong_cnt': 'Num Pinyin Wrong',
    'meaning_correct_cnt': 'Num Meaning Correct',
    'meaning_wrong_cnt': 'Num Meaning Wrong',
    'last_quiz': 'Last Quiz'}

    cols = ['Word Id', 'Word', 'Pinyin', 'Pinyin Simplified', 'Meaning', 'Added Date', 'Word Category', 'Word Rarity', 'Type', 'Sentence', 'Sentence Pinyin', 'Sentence Meaning', 'Quiz Attempts', 'Num Pinyin Correct', 'Num Pinyin Wrong', 'Num Meaning Correct', 'Num Meaning Wrong', 'Last Quiz']
    orig_df = pd.read_sql("""
                    SELECT 
                        WordDict.*, 
                        IIF(num_quiz_attempt IS NULL, 0, num_quiz_attempt) AS num_quiz_attempt,
                        IIF(pinyin_correct_cnt IS NULL, 0, pinyin_correct_cnt) AS pinyin_correct_cnt,
                        IIF(pinyin_wrong_cnt IS NULL, 0, pinyin_wrong_cnt) AS pinyin_wrong_cnt,
                        IIF(meaning_correct_cnt IS NULL, 0, meaning_correct_cnt) AS meaning_correct_cnt,
                        IIF(meaning_wrong_cnt IS NULL, 0, meaning_wrong_cnt) AS meaning_wrong_cnt,
                        last_quiz
                    FROM WordDict
                    LEFT JOIN QuizScore ON (WordDict.word_id = QuizScore.word_id) AND (WordDict.word = QuizScore.word)
                    """, engine)

    orig_df = orig_df.rename(columns=rename_dict)
    orig_df = orig_df[cols]
    return orig_df


def load_phrase_dict():
    """
    Load the phrase dictionary data from the database.
    """
    rename_dict = {col:col.replace('_', ' ').title() for col in PhraseDict.__table__.columns.keys()}
    phrase_df = pd.read_sql("""
                    SELECT *
                    FROM PhraseDict
                    """, engine)
    phrase_df = phrase_df.rename(columns=rename_dict)
    return phrase_df

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
        overlap_count, add_count = count_overlap_word(df['word'].tolist())
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

        message = f"Overwrite mode enabled.  Replacing {overlap_count} words and {add_count} new words added."
        return message
    
    except SQLAlchemyError as e:
        message = f"Replace-by-word transaction failed: {e}"
        return message 


def sql_patch_worddict_rows(records: list) -> str:
    """
    Update editable fields on existing WordDict rows in-place, identified by word_id.

    Only the following columns are updated (others like word_id, added_date are ignored):
        word_category, word_rarity, type, meaning,
        pinyin, sentence, sentence_pinyin, sentence_meaning

    Args:
        records: List of dicts from the DataTable (display-name keys, e.g. 'Word Category').

    Returns:
        A status message string.
    """
    col_map = {
        'Word Id': 'word_id',
        'Word Category': 'word_category',
        'Word Rarity': 'word_rarity',
        'Type': 'type',
        'Meaning': 'meaning',
        'Pinyin': 'pinyin',
        'Sentence': 'sentence',
        'Sentence Pinyin': 'sentence_pinyin',
        'Sentence Meaning': 'sentence_meaning',
    }
    EDITABLE = {'word_category', 'word_rarity', 'type', 'meaning', 'pinyin',
                'sentence', 'sentence_pinyin', 'sentence_meaning'}

    if not records:
        return "No records to update."

    try:
        with Session(engine) as session:
            updated = 0
            for rec in records:
                normalised = {col_map.get(k, k): v for k, v in rec.items()}
                word_id = normalised.get('word_id')
                if not word_id:
                    continue
                patch = {k: v for k, v in normalised.items() if k in EDITABLE}
                if not patch:
                    continue
                session.query(WordDict)\
                       .filter(WordDict.word_id == word_id)\
                       .update(patch, synchronize_session=False)
                updated += 1
            session.commit()
        return f"Updated {updated} row(s) successfully."
    except SQLAlchemyError as e:
        return f"Update failed: {e}"


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
    max_quiz_id_val = df_id.values[0][0]
    if max_quiz_id_val is None:
        max_phrase_id = 0
    else:
        max_phrase_id = pd.to_numeric(max_quiz_id_val.replace("QW", ""))
    new_phrase_ids = ['QW'+str(num + max_phrase_id).zfill(6) for num in range(1, df.shape[0] + 1)]
    df['quiz_id'] = new_phrase_ids
    
    required = ['quiz_id', 'word_id', 'word', 'sentence', 'sentence_pinyin',
       'pinyin_answer', 'pinyin_correct', 'pinyin_correction', 'meaning',
       'meaning_correct', 'meaning_correction', 'last_quiz', 'adaptive_sample_scale',
       'is_top_pinyin_error', 'is_top_meaning_error']
        
    for col in required:
        if col not in df.columns:
            df[col] = None

    # Fill optional string correction columns with empty string to satisfy NOT NULL constraints
    for col in ['pinyin_answer', 'pinyin_correction', 'meaning', 'meaning_correction']:
        if col in df.columns:
            df[col] = df[col].fillna('')

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
 


def sql_update_responselog(df: pd.DataFrame, mode="conversation"):
    """
    For every distinct `word` in df:
      - delete all existing WordDict rows with that word
      - insert the provided rows for that word
    All in one transaction (atomic).
    """
    df = df.copy()
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]

    # Ensure required columns exist

    # Generate word_id
    if mode == "conversation":
        df_id = pd.read_sql("SELECT MAX(quiz_id) FROM ResponseLog", engine).fillna(0)
        max_phrase_id = pd.to_numeric(df_id.values[0][0].replace("QR", ""))
        new_phrase_ids = ['QR'+str(num + max_phrase_id).zfill(6) for num in range(1, df.shape[0] + 1)]
        df['quiz_id'] = new_phrase_ids
        
        required = ['quiz_id', 'prompt', 'prompt_pinyin', 'prompt_meaning', 'response',
        'response_pinyin', 'response_meaning', 'correctness', 'naturalness',
        'contextual_appropriateness', 'comment', 'complexity', 'tone']
    elif mode == "translation":
        df_id = pd.read_sql("SELECT MAX(quiz_id) FROM TranslationLog", engine)
        if df_id.values[0][0] is None:
            df_id.values[0][0] = "QT000000"
        max_phrase_id = pd.to_numeric(df_id.values[0][0].replace("QT", ""))
        new_phrase_ids = ['QT'+str(num + max_phrase_id).zfill(6) for num in range(1, df.shape[0] + 1)]
        df['quiz_id'] = new_phrase_ids
        
        required = ['quiz_id', 'prompt', 'prompt_pinyin', 'user_translation', 'correct_translation', 'correctness',
        'tone_correctness', 'comment', 'complexity', 'tone']
    else:
        return "Invalid mode for sql_update_responselog"
            
    for col in required:
        if col not in df.columns:
            df[col] = None

    # SQLite wants None, not NaN
    df = df.where(pd.notnull(df), None)
    records = df[required].to_dict(orient="records")

    try:
        with Session(engine) as session:
            if mode == "conversation":
                session.bulk_insert_mappings(ResponseLog, records)
            elif mode == "translation":
                print('Inserting into TranslationLog')
                session.bulk_insert_mappings(TranslationLog, records)
            session.commit()
        
        message = "Saved quiz result."
        return message
    
    except SQLAlchemyError as e:
        message = f"Quiz Update transaction failed: {e}"
        return message 
 

def load_word_comparisons() -> pd.DataFrame:
    """
    Load all saved word comparison rows from the database.
    Returns a DataFrame with display-friendly column names.
    """
    rename_dict = {
        'id': 'Id',
        'pair_id': 'Pair ID',
        'word1': 'Word 1',
        'word1_pinyin': 'Word 1 Pinyin',
        'word2': 'Word 2',
        'word2_pinyin': 'Word 2 Pinyin',
        'meaning': 'Meaning',
        'part_of_speech_1': 'Part of Speech 1',
        'part_of_speech_2': 'Part of Speech 2',
        'word1_nuance': 'Word 1 Nuance',
        'word2_nuance': 'Word 2 Nuance',
        'word1_tone': 'Word 1 Tone',
        'word2_tone': 'Word 2 Tone',
        'word1_example': 'Word 1 Example',
        'word1_example_pinyin': 'Word 1 Example Pinyin',
        'word1_example_meaning': 'Word 1 Example Meaning',
        'word2_example': 'Word 2 Example',
        'word2_example_pinyin': 'Word 2 Example Pinyin',
        'word2_example_meaning': 'Word 2 Example Meaning',
        'added_date': 'Added Date',
    }
    df = pd.read_sql("SELECT * FROM WordComparison ORDER BY id DESC", engine)
    df = df.rename(columns=rename_dict)
    return df


def sql_insert_word_comparison(df: pd.DataFrame) -> str:
    """
    Insert one or more word comparison rows into the WordComparison table.

    Args:
        df: DataFrame whose columns match the display names returned by
            load_word_comparisons() (i.e. 'Word 1', 'Word 1 Pinyin', etc.)
            OR the raw snake_case column names.

    Returns:
        A status message string.
    """
    col_map = {
        'Word 1': 'word1',
        'Word 1 Pinyin': 'word1_pinyin',
        'Word1 Pinyin': 'word1_pinyin',
        'Word1': 'word1',
        'Word 2': 'word2',
        'Word 2 Pinyin': 'word2_pinyin',
        'Word2 Pinyin': 'word2_pinyin',
        'Word2': 'word2',
        'Meaning': 'meaning',
        'Part of Speech 1': 'part_of_speech_1',
        'Part of Speech 2': 'part_of_speech_2',
        'Word 1 Nuance': 'word1_nuance',
        'Word 2 Nuance': 'word2_nuance',
        'Word 1 Tone': 'word1_tone',
        'Word 2 Tone': 'word2_tone',
        'Word 1 Example': 'word1_example',
        'Word 1 Example Pinyin': 'word1_example_pinyin',
        'Word 1 Example Meaning': 'word1_example_meaning',
        'Word 2 Example': 'word2_example',
        'Word 2 Example Pinyin': 'word2_example_pinyin',
        'Word 2 Example Meaning': 'word2_example_meaning',
    }
    df = df.copy()
    df = df.rename(columns=col_map)

    required = [
        'pair_id', 'word1', 'word1_pinyin', 'word2', 'word2_pinyin', 'meaning',
        'part_of_speech_1', 'part_of_speech_2',
        'word1_nuance', 'word2_nuance',
        'word1_tone', 'word2_tone',
        'word1_example', 'word1_example_pinyin', 'word1_example_meaning',
        'word2_example', 'word2_example_pinyin', 'word2_example_meaning',
    ]
    for col in required:
        if col not in df.columns:
            df[col] = None

    # Compute pair_id for every row
    df['pair_id'] = df.apply(
        lambda r: _compute_pair_id(r.get('word1') or '', r.get('word2') or ''),
        axis=1,
    )

    df = df.where(pd.notnull(df), None)
    records = df[required].to_dict(orient='records')
    pair_ids = [r['pair_id'] for r in records if r.get('pair_id')]

    try:
        with Session(engine) as session:
            # Remove any existing rows for these word pairs before inserting
            if pair_ids:
                session.query(WordComparison)\
                       .filter(WordComparison.pair_id.in_(pair_ids))\
                       .delete(synchronize_session=False)
            session.bulk_insert_mappings(WordComparison, records)
            session.commit()
        return "Word comparison saved successfully."
    except SQLAlchemyError as e:
        return f"Word comparison insert failed: {e}"


def sql_delete_word_comparisons(pair_ids: List[str]) -> str:
    """
    Delete word comparison rows by their pair_id values.

    Args:
        pair_ids: List of pair_id strings to delete.

    Returns:
        A status message string.
    """
    if not pair_ids:
        return "No rows selected for deletion."
    try:
        with Session(engine) as session:
            deleted = session.query(WordComparison)\
                             .filter(WordComparison.pair_id.in_(pair_ids))\
                             .delete(synchronize_session=False)
            session.commit()
        return f"Deleted {deleted} comparison(s) successfully."
    except SQLAlchemyError as e:
        return f"Delete failed: {e}"


def sql_delete_word_dict(word_ids: List[str]) -> str:
    """
    Delete WordDict rows by their word_id values.

    Args:
        word_ids: List of word_id strings to delete.

    Returns:
        A status message string.
    """
    if not word_ids:
        return "No rows selected for deletion."
    try:
        with Session(engine) as session:
            deleted = session.query(WordDict)\
                             .filter(WordDict.word_id.in_(word_ids))\
                             .delete(synchronize_session=False)
            session.commit()
        return f"Deleted {deleted} word(s) successfully."
    except SQLAlchemyError as e:
        return f"Delete failed: {e}"
