from typing import List

import Constants
from  openai import OpenAI
import os
import numpy as np
import pandas as pd
import time

import os
from io import StringIO
from datetime import datetime

from main.gsheets import load_dict, save_df_to_gsheet, format_gsheet

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

def get_prompt_convo_eval(conv_df):
    return f'''
    Given the following conversation:
    {conv_df}

    Please evaluate a Mandarin Chinese conversation and provide a table with the following columns.  
    There's only need to be a evaluation row for the line provided by the users.  The score is ONLY based on the user's own line.  
    The preceding line is AI generated and hence does not need to be evaluated but will only be used for contextual accuracy of the user's line.

    The output table should have the following columns.  No new columns can be needed and no columns can be removed:
    1) Conversation ID:  ID of the conversation based on the input table
    2) Preceding Line- The AI-generated line preceding the line to be evaluated.  This is used to evaluate the user's line for contextual accuracy
    3) Preceding LinePinyin - Pinyin for the preceding line .
    4) Line- The exact line from the conversation (user’s input).
    5) LinePinyin - Pinyin for the line .
    6) Correctness - A score from 1 to 10 based on grammatical accuracy and vocabulary usage for the Sentence column.
    7) Naturalness - A score from 1 to 10 based on how colloquial and fluent the sentence sounds in casual conversation.
    8) Contextual Appropriateness - A score from 1 to 10 based on whether the sentence fits the context of the conversation.
    9) Comment on Correction - Feedback on what could be improved, with pinyin included for any Chinese words mentioned in the comment.
    '''