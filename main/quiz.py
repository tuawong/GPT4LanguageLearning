from typing import List, Dict, Any, Tuple, Union

import main.Constants as Constants
from  openai import OpenAI
import os
import numpy as np
import pandas as pd
import time

import os
from io import StringIO
from datetime import datetime

from main.gsheets import load_dict, save_df_to_gsheet
from main.translation import save_new_words_to_dict

client = OpenAI(
    api_key = Constants.API_KEY_OPENAI,
)

def get_completion(prompt, model="gpt-4o-mini", temperature=0):
    messages = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response


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
    Meaning Correct (Column #3):  Check whether the Provided Meaning is correct given the context sentence.  The meaning of the word has to evaluated in the context of the sentence provided. Give just yes/no response.  
    Meaning Correction (Column #4):  If column #3 is "no" provide the correct answer.  If the meaning provided is missing, the correct meaning of the word must be provided. If the correct meaning is provided, then this column must be blank.

    The table columns must be (1) Word List, (2) Meaning, (3) Meaning Correct, (4) Meaning Correction
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
    Meaning Correct (Column #6):  Check whether the Provided Meaning is correct relative to the Word List.  Give just yes/no response.  
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
            gsheet_name: str,
            wks_name: str
            ):
        self.gsheet_name = gsheet_name
        self.wks_name = wks_name
        self.dict_df = load_dict(gsheet_mode=True, gsheet_name=gsheet_name, worksheet_name=wks_name)

    def generate_pinyin_and_meaning_quiz(
            self, 
            id_column: str = 'Word Id',
            num_words: int = 10,
            date_filter: Union[List[str], str] = None,
            category_filter: Union[List[str], str] = None, 
            rarity_filter: Union[List[str], str] = None
        ) -> pd.DataFrame:
        dict_df = self.dict_df.copy()

        if date_filter is not None:
            dict_df = dict_df[dict_df['Added Date'] >= date_filter]

        if category_filter is not None:
            if type(category_filter) == str:
                category_filter = [category_filter]
                dict_df = dict_df[dict_df['Word Category'].isin(category_filter)]

        if rarity_filter is not None:
            if type(rarity_filter) == str:
                rarity_filter = [rarity_filter]
                dict_df = dict_df[dict_df['Word Rarity'].isin(rarity_filter)]

        unique_ids = dict_df[id_column].unique()
        num_to_select = min(num_words, len(unique_ids))
        quiz_id = pd.Series(unique_ids).sample(n=num_to_select)  

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
        pinyin_eval_df['Pinyin Correction'] = np.where(pinyin_eval_df['Pinyin Correct'], '', pinyin_eval_df['Pinyin'])
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

        sample_response_translation = get_completion(prompt=quiz_prompt, temperature=0.7)
        meaning_eval_df = parse_meaning_table(sample_response_translation.choices[0].message.content)
        meaning_eval_df = meaning_eval_df.reset_index(drop=True)

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
            self.quiz[['Word', 'Sentence']], 
            pinyin_eval_df[['Sentence Pinyin', 'Pinyin Answer', 'Pinyin Correct', 'Pinyin Correction']], 
            meaning_eval_df[['Meaning', 'Meaning Correct', 'Meaning Correction']]
            ], axis=1).set_index(pinyin_eval_df['Word Id'])
        
        self.quiz_result = outdf
        return outdf

    def update_quiz_score(
            self,
            gsheet_name: str,
            wks_name: str
        ) -> None:
        '''
        This function updates the quiz score for the word dictionary.
        '''
        if not hasattr(self, 'quiz_result'):
            raise Exception("Quiz Result not available.  Please run evaluate the quiz first.")
        
        quiz_result_df = self.quiz_result
        word_dict = load_dict(gsheet_mode=True, gsheet_name=gsheet_name, worksheet_name=wks_name)

        quiz_result_df['Right Score'] = np.where((quiz_result_df['Meaning Correct']=="yes")&(quiz_result_df['Pinyin Correct']=="yes"), 1, 0)
        quiz_result_df['Wrong Score'] = np.where(quiz_result_df['Right Score']==0, 1, 0)
        quiz_result_df['Last Quiz'] = datetime.now().strftime('%Y-%m-%d')

        word_dict_quiz_export = word_dict.merge(quiz_result_df[['Right Score', 'Wrong Score', 'Last Quiz']].reset_index(), on='Word Id', how='left')

        num_attempts = word_dict_quiz_export['Num_Quiz_Attempt'].fillna(0).astype(int).sum()
        word_dict_quiz_export['Num_Quiz_Attempt'] = word_dict_quiz_export['Num_Quiz_Attempt'].astype(int) + word_dict_quiz_export['Right Score'].notna()
        word_dict_quiz_export['Num_Correct'] = word_dict_quiz_export['Num_Correct'].astype(int) + word_dict_quiz_export['Right Score'].fillna(0)
        word_dict_quiz_export['Num_Wrong'] = word_dict_quiz_export['Num_Wrong'].astype(int) + word_dict_quiz_export['Wrong Score'].fillna(0)
        word_dict_quiz_export['Last_Quiz'] = word_dict_quiz_export['Last_Quiz'].fillna('2001-01-01')
        word_dict_quiz_export['Last_Quiz'] = np.where(word_dict_quiz_export['Last_Quiz'] < word_dict_quiz_export['Last Quiz'], word_dict_quiz_export['Last Quiz'], word_dict_quiz_export['Last_Quiz'])

        num_attempts_post_update = word_dict_quiz_export['Num_Quiz_Attempt'].fillna(0).astype(int).sum()
        num_correct_post_update = word_dict_quiz_export['Num_Correct'].fillna(0).astype(int).sum()
        num_wrong_post_update = word_dict_quiz_export['Num_Wrong'].fillna(0).astype(int).sum()

        attempt_count_condition = (num_attempts + len(quiz_result_df) != num_attempts_post_update)
        correct_wrong_total_condition = (num_correct_post_update + num_wrong_post_update != num_attempts_post_update)

        if (attempt_count_condition) or (correct_wrong_total_condition):
            raise Exception("Error in updating the quiz results.  Please check the code.")

        word_dict_quiz_export = word_dict_quiz_export.drop(columns=['Right Score', 'Wrong Score', 'Last Quiz'])

        save_df_to_gsheet(overwrite_mode=True, df_to_save=word_dict_quiz_export, gsheet_name=gsheet_name, wks_name=wks_name)

        return "Quiz Result Updated"
    
    def output_quiz_log(
            self, 
            gsheet_name: str,
            wks_name: str
        ) -> None:
        if not hasattr(self, 'quiz_result'):
            raise Exception("Quiz Result not available.  Please run evaluate the quiz first.")
        
        quiz_log = load_dict(gsheet_mode=True, gsheet_name=gsheet_name, worksheet_name=wks_name)
        quiz_export = self.quiz_result.drop(['Sentence', 'Sentence Pinyin'], axis=1).copy()

        if len(quiz_log) == 0:
            quiz_log = pd.DataFrame()
            quiz_export['Quiz Id'] = 1
        else:
            quiz_export['Quiz Id'] = int(quiz_log['Quiz Id'].max()) + 1
        
        quiz_log = pd.concat([quiz_log, quiz_export], axis=0)
        save_df_to_gsheet(overwrite_mode=True, df_to_save=quiz_log, gsheet_name=gsheet_name, wks_name=wks_name)

        return "Quiz Log Updated"