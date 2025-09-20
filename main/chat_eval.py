from typing import List

import main.Constants as Constants
from  openai import OpenAI
import os
import numpy as np
import pandas as pd
import time

import os
from io import StringIO
from datetime import datetime

from main.gsheets import load_gsheet_dict, save_df_to_gsheet, format_gsheet
from main.utils import get_completion, parse_response_table
from main.sql import sql_update_responselog


client = OpenAI(
    api_key = Constants.API_KEY_OPENAI,
)

def get_prompt_for_structure_convo():
    return '''
    Given the above conversation, please structure it in a table with the following columns:
    1) Conversation ID:  Randomly generated ID for each conversation
    2) Speaker:  The speaker of each line.  Can either be "User" or the version of GPT used to generate the reply
    3) Line:  The text of the line
    4) Pinyin: The pinyin of the line
    5) Meaning: The meaning of the line
    6) Line Number: The order of the line in the conversation

    '''


def get_prompt_to_gen_phrases_for_quiz(
    situation: str = "",
    num_phrases: int = 5,
    complexity: str = "Low",
    tone: str = "Polite",
    ):
    prompt = f'''
    Can you generate some useful phrases in Mandarin base on the following situation.  
    If the situation provided is blank.  Then generate some phrases that could be useful for someone building more proficiency in Mandarin.  
    Do NOT output anything response except for the table. There should not be any space, letter, symbol, or new line before or after the table. 

    Parameters
    Situation: {situation}
    Number of phrase to generate: {num_phrases}
    Complexity: {complexity}
    Tone: {tone}
    
    The output should be a table with the following columns. 
    1) Prompt:  In simplified Chinese.  The phrase generated should be relevant to the situation.  The phrases should be unique and not repeated.
    2) Prompt Pinyin: Pinyin associated with the phrase
    3) Response:  (Leave Blank)
    4) Complexity:  Complexity of content of the phrase to generate based on the input parameters.  Can be...
    -  Low (Short basic conversation, easily learnt by first time Mandarin speaker.  Keep the line less than 10 characters)
    -  Medium (More detailed conversation that might be used in everyday life)
    -  High (More formal/rare conversation that might not be used everyday.  Should be longer than 10 characters)
    5) Tone:  Tone of the phrase.  Can be Polite or Casual.  Polite used for work or formal situations for speaking with strangers and older people.  
    Casual is typically for everyday use with close friends, make it more conversational. 
    '''
    return prompt


def get_prompt_convo_eval(conv_df):
    return f'''
    Given the following conversation:
    {conv_df}

    The input definition is as follows:
    1) Prompt - The line preceding the response to be evaluated.  This is used to evaluate the user's line for contextual accuracy
    2) Prompt Pinyin - Pinyin for the line.
    3) Response - The response provided by the user.
    4) Complexity - The complexity of the response.  Can be Low, Medium, or High.
    5) Tone - The tone of the response.  Can be Polite or Casual.

    Please take the role of a Mandarin teacher and evaluate a Mandarin Chinese conversation and provide a table with the following columns.  
    There's only need to be a evaluation row for the line provided by the users.  The score is ONLY based on the user's own line.  
    The line in Columnn#1 is AI generated and hence does not need to be evaluated but will only be used for contextual accuracy of the user's line.

    The output table should have the following columns.  No new columns can be needed and no columns can be removed:
    1) Prompt- Prompt provided in the input table.  Do not change this column from the input table.
    2) Prompt Pinyin - Pinyin provided in the input table. Do not change this column from the input table.
    3) Prompt Meaning - Meaning of the prompt
    4) Response- The response provided in the response table. Do not change this column from the input table.
    5) Response Pinyin - Pinyin for the response.
    6) Response Meaning - Meaning of the response.
    6) Correctness - A score from 1 to 10 based on grammatical accuracy and vocabulary usage in the Response column.
    7) Naturalness - A score from 1 to 10 based on how colloquial and fluent the sentence in the Response column sounds in casual conversation.
    8) Contextual Appropriateness - A score from 1 to 10 based on whether the sentence in the Response column fits the context of the conversation. 
    9) Comment - Feedback on what could be improved, with pinyin included for any Chinese words mentioned in the comment.  The comment MUST be in written in English.
        certain Chinese words can be provided as example but pinyin will also have to be provided.
    10) Complexity - The complexity of the response.  Provided in input table
    11) Tone - The tone of the response.  Provided in input table

    No other textual output should be provided.  The only output should be a table with the above columns.
    The same number of rows should be provided as the number of rows in the input table.
    '''


class ResponseQuizGenerator:
    def __init__(
            self, 
            gsheet_mode: bool = False,
            gsheet_name: str = None,
            wks_name: str = None,
            table_name: str = None 
            ):
        self.gsheet_mode = gsheet_mode
        self.gsheet_name = gsheet_name
        self.wks_name = wks_name
        self.table_name = table_name

    def generate_response_quiz(
            self, 
            situation: str = "",
            num_phrases: int = 5,
            complexity: str = "Low",
            tone: str = "Polite",
            temp = 0.7,
            model = "gpt-4o-mini"
        ) -> pd.DataFrame:

            prompt = get_prompt_to_gen_phrases_for_quiz(
                    situation=situation,
                    num_phrases=num_phrases, 
                    complexity=complexity,
                    tone=tone,
                )

            sample_response_translation = (
                get_completion(
                    prompt=prompt, 
                    model=model , 
                    temperature=temp
                    )
                )
            content = sample_response_translation.choices[0].message.content
            phrase_df = parse_response_table(content)
            self.phrase_df = phrase_df

            return phrase_df

    def provide_response(
            self, 
            response
        ):
        self.phrase_df['Response'] = response
    
    def evaluate_response(
            self, 
            eval_df = None,
            temp = 0.7,
            model = "gpt-4o-mini"
        ) -> pd.DataFrame:
        if eval_df is None:
            eval_df = self.phrase_df
        sample_response_translation = (
            get_completion(
                prompt=get_prompt_convo_eval(eval_df), 
                model=model , 
                temperature=temp
                )
            )
        content = sample_response_translation.choices[0].message.content
        eval_df = parse_response_table(content)
        self.eval_df = eval_df
        return eval_df
    
    def output_quiz_log(self):
        if not hasattr(self, 'eval_df'):
            raise Exception("Quiz Result not available.  Please run evaluate the quiz first.")
        if self.gsheet_mode:
            quiz_export = self.eval_df
            quiz_log = load_gsheet_dict(gsheet_mode=True, gsheet_name=self.gsheet_name, worksheet_name=self.wks_name)
            max_id = pd.to_numeric(quiz_log['Quiz Id'].apply(lambda x: x.replace('QR','')), errors='coerce').max()
            quiz_export['Quiz Id'] = ['QR'+str(num + max_id).zfill(6) for num in range(1, len(quiz_export) + 1)]
            quiz_export = quiz_export[quiz_log.columns]

            quiz_log = pd.concat([quiz_log, quiz_export], axis=0)
            save_df_to_gsheet(overwrite_mode=True, df_to_save=quiz_log, gsheet_name=self.gsheet_name, wks_name=self.wks_name)
        else:
            sql_update_responselog(self.eval_df)
