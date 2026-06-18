from typing import List, Dict, Any, Tuple, Union

from  openai import OpenAI
import os
import numpy as np
import pandas as pd
import time

import os
from io import StringIO
from datetime import datetime

from main.sql import sql_update_quizlog, load_dict
from main.gsheets import load_gsheet_dict, save_df_to_gsheet
from main.utils import get_completion
from database import engine

def calculate_adaptive_weights(
    df: pd.DataFrame,
    seed: float = 0.01,
    spread_power: float = 1.0
) -> np.ndarray:
    """
    Calculate adaptive sampling weights based on quiz performance.

    Words with more combined wrong answers (pinyin + meaning) are sampled
    more frequently. Words with more combined correct answers are down-weighted.

    Formula:
        num_wrong   = Num Pinyin Wrong  + Num Meaning Wrong
        num_correct = Num Pinyin Correct + Num Meaning Correct
        base_weight = (num_wrong + max(0, max_wrong - num_correct))
                      / (max_wrong + max_correct)  +  seed
        final_weight = base_weight ^ spread_power   (then normalized)

    Args:
        df:           filtered word DataFrame (must contain Num Pinyin Wrong,
                      Num Meaning Wrong, Num Pinyin Correct, Num Meaning Correct)
        seed:         minimum floor weight to prevent zero probability (default 0.01)
        spread_power: exponent applied after computing base weights.
                      >1 widens gap toward problem words,
                      <1 flattens toward uniform,
                      1.0 is the baseline (default)
    Returns:
        normalized probability array aligned to df index
    """
    num_wrong   = df['Num Pinyin Wrong']   + df['Num Meaning Wrong']
    num_correct = df['Num Pinyin Correct'] + df['Num Meaning Correct']

    max_wrong   = num_wrong.max()
    max_correct = num_correct.max()
    denominator = max_wrong + max_correct

    if denominator == 0:  # all new words with no history yet
        return np.ones(len(df)) / len(df)

    base    = (num_wrong + (max_wrong - num_correct).clip(lower=0)) / denominator + seed
    powered = base ** spread_power
    return (powered / powered.sum()).values


def get_top_error_word_ids(df: pd.DataFrame, n: int = 20, error_type: str = 'pinyin') -> list:
    """
    Returns up to n word_ids for the worst-performing words.

    Uses the same aggregation as the statistics chart (prepare_df-equivalent).
    For words with multiple word_ids (multiple meanings), selects the word_id
    that has the most errors so the most-problem variant is quizzed.

    Args:
        df:         DataFrame returned by load_dict().
        n:          Maximum number of words to return (default 20).
        error_type: 'pinyin' to rank by pinyin error rate,
                    'meaning' to rank by meaning error rate.

    Returns:
        List of word_id strings (length <= n).
    """
    work = df.copy()
    # Mirror prepare_df: recalculate wrong counts the same way the chart does
    work['Num Pinyin Wrong'] = work['Quiz Attempts'] - work['Num Pinyin Correct']
    work['Num Meaning Wrong'] = work['Quiz Attempts'] - work['Num Meaning Correct']

    wrong_col = 'Num Meaning Wrong' if error_type == 'meaning' else 'Num Pinyin Wrong'

    agg = (
        work.groupby('Word')
        .agg(num_wrong=(wrong_col, 'sum'),
             quiz_attempts=('Quiz Attempts', 'sum'))
        .reset_index()
    )
    agg = agg[agg['quiz_attempts'] > 1]
    agg['pct'] = agg['num_wrong'] / agg['quiz_attempts']
    top_words_series = (
        agg[agg['num_wrong'] >= 1]
        .sort_values(by=['pct', 'num_wrong'], ascending=[False, False])
        .head(n)['Word']
    )

    # For each word, prefer the word_id with the most errors (most problem variant).
    # Fall back to random choice if all word_ids have 0 attempts.
    word_ids = []
    for word in top_words_series:
        word_rows = work[work['Word'] == word]
        rows_with_history = word_rows[word_rows['Quiz Attempts'] > 0]
        if not rows_with_history.empty:
            # Pick the word_id with the highest wrong count for this error type
            best_row = rows_with_history.loc[rows_with_history[wrong_col].idxmax()]
            word_ids.append(str(best_row['Word Id']))
        elif not word_rows.empty:
            word_ids.append(str(np.random.choice(word_rows['Word Id'].tolist())))

    return word_ids


def get_prompt_generate_word_quiz(
    word_dict: pd.DataFrame,
    startfrom_date_filter: str = None,
    category_filter: str = None
    ) -> str:
        
    if startfrom_date_filter:
        word_dict = word_dict.loc[word_dict['Added Date'] >= startfrom_date_filter]

    if category_filter:
            word_dict = word_dict.loc[word_dict['Word Category'] == category_filter]

    word_list = word_dict['Word'].drop_duplicates().sample(10).values
    prompt = f''' 
    Given this word list:
    {word_list}

    Can you create an Mandarin exercise where you choose 10 non-duplicated words and an example sentence using them.   
    Leaving 2 blank columns where user can input the pinyin and the meaning in English.

    The output should only be a 10x4 table with no other written text.  The table should have the following columns:
    1) Word
    2) Sentence
    3) Pinyin (Leave blank)
    4) Meaning (Leave blank)
    '''

    return prompt

# 4O Maybe Necessary to Evaluate Quiz.  Mini seems to be halluciating quite a bit. 
def get_prompt_evaluate_quiz_meaning_only(
        word_list, 
        sentence_list, 
        meaning
    ) -> str:
    quiz_input_df = pd.DataFrame()
    quiz_input_df['Word'] = word_list
    quiz_input_df['Sentence'] = sentence_list
    quiz_input_df['Meaning'] = meaning

    prompt = f'''
    Please act as Chinese teacher and evaluate the following quiz.  The student was asked to provide the meaning for the following words.
    The context for the word is provided in the sentence.  Please check whether the meaning provided is correct.  If not, please provide the correct meaning.
    Each word should be evaluated separately.
    
    The quiz is as follows.  There are 3 columns
    Word List:  The word list provided
    Sentence:  The sentence provided
    Meaning:  The meaning provided by the students.  If the meaning provided is blank then the student did not provide an answer, then leave blank and mark as incorrect.
    Quiz Input:{quiz_input_df}

    Please generate the following table with the following columns: 
    Word List (Column #1):  The word list provided.  This is 1 to 1 mapping with the Word List column
    Meaning (Column #2):  The meaning provided by the students.  This is 1 to 1 mapping with the Meaning column
    Meaning Correct (Column #6):  Check whether the Provided Meaning is correct relative to the Word List.  Give just yes/no response.  Minor typos/grammatical error can be ignored but the overall meaning should be correct 
        (eg. cigarette vs cigarrete can be considered correct, but cigarette vs dog would be incorrect).  Similarly synonyms can be considered correct (cigarette vs smokes vs tobacco can be considered correct).
    Meaning Correction (Column #4):  If column #3 is "no" provide the correct answer.  If the meaning provided is missing, the correct meaning of the word must be provided. If the correct meaning is provided, then this column must be blank.  The meaning must be in English..

    The table columns must be (1) Word List, (2) Meaning, (3) Meaning Correct, (4) Meaning Correction
    The table is always separated by | and the first row is the column name.  Do not use any other separator such as comma or tab.
    No changes to the column name is allowed.
    No other response should be given except the table
    '''

    return prompt

# 4O Maybe Necessary to Evaluate Quiz.  Mini seems to be halluciating quite a bit. 
def get_prompt_evaluate_quiz(
        word_list, 
        sentence_list, 
        pinyin, 
        meaning
    ) -> str:
    prompt = f'''
    Here's the answer provided.  Please check them for correctness and mark any incorrect answer and provide the correct one. 

    Word List: {word_list}
    Provided Sentence: {sentence_list}
    
    Please generate the following table with the following columns: 
    Word List (Column #1):  The word list provided
    Pinyin (Column #2): Should be a value from this list {pinyin}
    Meaning (Column #3):  Should be a value from this list {meaning}
    Pinyin Correct (Column #4):  Check whether the Provided Pinyin is correct relative to the Word List.  Give just yes/no response.
    Correct Pinyin (Column #5):  Should contain the correct pinyin if the answer is incorrect.  Blank otherwise. When pinyin is incorrect only the correct pinyin should be provided, no other text is allowed
    Meaning Correct (Column #6):  Check whether the Provided Meaning is correct relative to the Word List.  Give just yes/no response.  Minor typos/grammatical error can be ignored but the overall meaning should be correct 
        (eg. cigarette vs cigarrete can be considered correct, but cigarette vs dog would be incorrect).  Similarly synonyms can be considered correct (cigarette vs smokes vs tobacco can be considered correct).
    Correct Meaning (Column #7):  If column #6 is "no" provide short explanation of why the meaning is incorrect and provide correct answer.  If column #6 is "yes" then must be blank. 

    The tone for the pinyin will be provided with number 1, 2, 3, 4, 5
    The special character ü⁠ can be replaced by v in the answer

    No other response should be given except the table
    '''
    return prompt


def parse_meaning_table(content: str) -> pd.DataFrame:
    '''
    Parse the table response from OpenAI into a pandas DataFrame
    '''
    data = StringIO(content)

    # Read the table into a pandas DataFrame
    df = pd.read_csv(data, delimiter='|',  engine='python')
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    col_to_keep = [col for col in df if 'Unnamed' not in col]
    df = df[col_to_keep]
    df.columns = df.columns.str.strip()

    col = df.columns[0]
    df = df.loc[~df[col].str.contains('--')]
    return df


class QuizGenerator:
    def __init__(
            self, 
            gsheet_mode: bool = False,
            gsheet_name: str = None,
            wks_name: str = None,
            table_name: str = None, 
            df: pd.DataFrame = None
            ):
        self.gsheet_name = gsheet_name
        self.wks_name = wks_name
        if df is not None:
            self.dict_df = df
        else:
            if gsheet_mode:
                self.dict_df = load_gsheet_dict(gsheet_mode=True, gsheet_name=gsheet_name, worksheet_name=wks_name)
                self.dict_df.columns = [col.lower().replace(' ', '_') for col in self.dict_df.columns]
            else:
                self.dict_df = load_dict()

    def generate_pinyin_and_meaning_quiz(
            self, 
            id_column: str = 'Word Id',
            date_column: str = 'Added Date',
            category_column: str = 'Word Category',
            rarity_column: str = 'Word Rarity',
            num_words: int = 10,
            date_filter: Union[List[str], str] = None,
            category_filter: Union[List[str], str] = None, 
            rarity_filter: Union[List[str], str] = None,
            new_words_only: bool = False,
            adaptive_sampling: bool = True,
            spread_power: float = 1.0,
            seed: float = 0.01,
            word_ids: List[str] = None,
            top_error_type: str = None,
        ) -> pd.DataFrame:
        self.new_words_only = new_words_only
        self.spread_power = spread_power if adaptive_sampling else 1.0
        self.top_error_type = top_error_type
        dict_df = self.dict_df.copy()

        # When explicit word_ids are provided, skip all filters and sampling
        if word_ids is not None:
            dict_df = dict_df[dict_df[id_column].isin(word_ids)]
            quiz_answer_key = dict_df[
                ['Word Id', 'Word', 'Word Category', 'Sentence', 'Sentence Pinyin', 'Pinyin', 'Pinyin Simplified']
            ].sample(frac=1).reset_index(drop=True)
            quiz_df = quiz_answer_key.drop(columns=['Pinyin', 'Pinyin Simplified', 'Sentence Pinyin'])
            quiz_df['Pinyin'] = ''
            quiz_df['Meaning'] = ''
            self.answer_key = quiz_answer_key
            self.quiz = quiz_df
            return quiz_df


        if date_filter is not None:
            dict_df = dict_df[dict_df[date_column] >= date_filter]

        if category_filter is not None:
            if type(category_filter) == str:
                category_filter = [category_filter]
                dict_df = dict_df[dict_df[category_column].isin(category_filter)]

        # rarity_filter is now a checklist.  Will have to handle the data type correctly 
        if rarity_filter is not None:
            dict_df = dict_df[dict_df[rarity_column].isin(rarity_filter)]

        if new_words_only:
            dict_df = dict_df[dict_df['Quiz Attempts'].isna() | (dict_df['Quiz Attempts'] == 0)]
            
        unique_ids = dict_df[id_column].unique()
        num_to_select = min(num_words, len(unique_ids))

        if adaptive_sampling and all(c in dict_df.columns for c in
                ['Num Pinyin Wrong', 'Num Meaning Wrong', 'Num Pinyin Correct', 'Num Meaning Correct']):
            weights = calculate_adaptive_weights(dict_df, seed=seed, spread_power=spread_power)
            quiz_id = dict_df[id_column].sample(n=num_to_select, replace=False, weights=weights)
        else:
            quiz_id = pd.Series(unique_ids).sample(n=num_to_select, replace=False)

        quiz_df = dict_df.loc[dict_df[id_column].isin(quiz_id)]
        quiz_answer_key = quiz_df[['Word Id', 'Word', 'Word Category', 'Sentence', 'Sentence Pinyin', 'Pinyin', 'Pinyin Simplified']].sample(frac=1, random_state=1).reset_index(drop=True)
        quiz_df = quiz_answer_key.drop(columns=['Pinyin', 'Pinyin Simplified', 'Sentence Pinyin'])
        quiz_df['Pinyin'] = ''
        quiz_df['Meaning'] = '' 

        self.answer_key = quiz_answer_key
        self.quiz = quiz_df
        return quiz_df

    def check_pinyin(
            self,   
            pinyin_answer
        ):
        '''
        This function checks the pinyin for the quiz provided.
        '''
        answer_key_df = self.answer_key
        quiz_df = self.quiz

        pinyin_eval_df = answer_key_df.loc[answer_key_df['Word Id'].isin(quiz_df['Word Id'])][['Word Id', 'Word', 'Pinyin', 'Pinyin Simplified', 'Sentence Pinyin']].reset_index (drop=True)
        pinyin_eval_df['Pinyin Answer'] = pinyin_answer
        pinyin_eval_df['Pinyin Simplified'] = pinyin_eval_df['Pinyin Simplified'].fillna('').apply(lambda x: x.replace(' ', '').lower().replace('5', ''))
        pinyin_eval_df['Pinyin Answer'] = pinyin_eval_df['Pinyin Answer'].fillna('').apply(lambda x: x.replace(' ', '').lower().replace('5', ''))
        pinyin_eval_df['Pinyin Correct'] = (pinyin_eval_df['Pinyin Simplified'] == pinyin_eval_df['Pinyin Answer'])
        pinyin_eval_df['Pinyin Correction'] = np.where(pinyin_eval_df['Pinyin Correct'], '', pinyin_eval_df['Pinyin Simplified'])
        pinyin_eval_df['Pinyin Correct'] = pinyin_eval_df['Pinyin Correct'].map({True: 'yes', False: 'no'})

        self.pinyin_eval_df = pinyin_eval_df
        return pinyin_eval_df

    def check_meaning(
            self,
            meaning_answer
        ):
        '''
        This function checks the meaning for the quiz provided.
        '''
        quiz_df = self.quiz
        quiz_prompt = get_prompt_evaluate_quiz_meaning_only(
            word_list = quiz_df['Word'].values,
            sentence_list = quiz_df['Sentence'].values,
            meaning = meaning_answer
            )

        if isinstance(meaning_answer, (list, tuple)):
            num_items = len(meaning_answer)
        elif isinstance(meaning_answer, str):
            num_items = len(quiz_df)
        else:
            num_items = len(quiz_df)

        sample_response_translation = get_completion(prompt=quiz_prompt, temperature=1, category='quiz_eval', num_items=num_items)
        meaning_eval_df = parse_meaning_table(sample_response_translation.output_text)
        meaning_eval_df = meaning_eval_df.reset_index(drop=True)
        #meaning_eval_df.columns = [col.lower().replace(' ', '_') for col in meaning_eval_df.columns]
        
        self.meaning_eval_df = meaning_eval_df
        return meaning_eval_df


    def evaluate_pinyin_and_meaning_quiz(
            self,
            pinyin_answer,
            meaning_answer
        ):
        pinyin_eval_df = self.check_pinyin(
            pinyin_answer = pinyin_answer
            )
        meaning_eval_df = self.check_meaning(
            meaning_answer = meaning_answer
            )
        
        outdf = pd.concat([
            self.answer_key[['Word Id']],
            self.quiz[['Word', 'Sentence']], 
            pinyin_eval_df[['Sentence Pinyin', 'Pinyin Answer', 'Pinyin Correct', 'Pinyin Correction']], 
            meaning_eval_df[['Meaning', 'Meaning Correct', 'Meaning Correction']]
            ], axis=1)

        outdf['last_quiz'] = datetime.now().strftime('%Y-%m-%d')
        # Log null for adaptive sample scale when new words only mode is used
        if getattr(self, 'new_words_only', False):
            outdf['Adaptive Sample Scale'] = None
        else:
            outdf['Adaptive Sample Scale'] = getattr(self, 'spread_power', 1.0)
        top_error_type = getattr(self, 'top_error_type', None)
        outdf['Is Top Pinyin Error'] = 1 if top_error_type == 'pinyin' else 0
        outdf['Is Top Meaning Error'] = 1 if top_error_type == 'meaning' else 0
        self.quiz_result = outdf
        return outdf
    
    def output_quiz_log(
            self, 
            gsheet_name: str = None,
            wks_name: str = None,
            gsheet_mode: bool = False,
        ) -> None:

        if not hasattr(self, 'quiz_result'):
            raise Exception("Quiz Result not available.  Please run evaluate the quiz first.")
        
        if gsheet_mode:
            quiz_log = load_dict()
            quiz_export = self.quiz_result.drop(['Sentence', 'Sentence Pinyin'], axis=1).copy()

            max_id = pd.to_numeric(quiz_log['Quiz Id'].apply(lambda x: x.replace('QW','')), errors='coerce').max()
            quiz_export['Quiz Id'] = ['QW'+str(1 + max_id).zfill(6) for _ in range(1, len(quiz_export) + 1)]
            
            quiz_log = pd.concat([quiz_log, quiz_export], axis=0).reset_index(drop=True)
            save_df_to_gsheet(overwrite_mode=True, df_to_save=quiz_log, gsheet_name=gsheet_name, wks_name=wks_name)
        else:


            result = sql_update_quizlog(self.quiz_result)

            if result != "Saved quiz result.":
                raise RuntimeError(f"Failed to save quiz log: {result}")
        return "Quiz Log Updated"