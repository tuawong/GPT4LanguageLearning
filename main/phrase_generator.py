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

from main.gsheets import load_dict, save_df_to_gsheet, format_gsheet

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


def get_prompt_to_gen_phrases(
    situation: str = "",
    num_phrases: int = 5,
    complexity: str = "Low",
    existing_phrases: List[str] = []
    ):
    prompt = f'''
    Can you generate some useful phrases in Mandarin base on the following situation.  
    If the situation provided is blank.  Then generate some phrases that could be useful for someone building more proficiency in Mandarin.  

    Parameters
    Situation: {situation}
    Number of phrase to generate: {num_phrases}
    Complexity: {complexity}

    The output should be a table with the following columns. 
    1) Line:  In simplified Chinese.  The phrase generated should be relevant to the situation.
    2) Pinyin: Pinyin associated with the phrase
    3) Meaning:  Meaning of the phrase
    4) Response:  A line that can be said in response to the phrase
    5) Response Pinyin:  Pinyin associated with response
    6) Response Meaning:  Meaning of the response
    7) Complexity:  Complexity of the phrase to generate based on the input parameters.  Can be...
    -  Low (Used everyday.  Easily learnt by first time Mandarin speaker)
    -  Medium (More contextual conversations with more details that are more common between natural Mandarin speakers)
    -  High (More formal/detailed/rare conversation that might not be used everyday)
    8) Category:  Category of the phrase such as Daily Life, Cooking, Movies and Entertainment, Date night, Classroom conversation, and so on  
    '''

    if len(existing_phrases) > 0:
        prompt += f'''
            Here are the sentences I already have, please don't output something too similar
            {existing_phrases}
            '''
    
    return prompt

def get_prompt_to_respond(
    input_phrases: str,
    ): 
    return f'''
    Can you generate some useful responses to the input phrase in Mandarin base on the following situation.  
    If the situation provided is blank.  Then generate some phrases that could be useful for someone building more proficiency in Mandarin.  

    Parameters
    Input Phrases: {input_phrases}

    The output should be a table with the following columns. 
    1) Line: The line provided in Input Phrases. 
    2) Pinyin: Pinyin associated with the phrase
    3) Meaning:  Meaning of the input phrases
    4) Response:  A line that can be said in response to the phrase
    5) Response Pinyin:  Pinyin associated with response
    6) Response Meaning:  Meaning of the response
    7) Complexity:  Complexity of the phrase to generate based on the input parameters.  Can be...
    -  Low (Used everyday.  Easily learnt by first time Mandarin speaker)
    -  Medium (More contextual conversations with more details that are more common between natural Mandarin speakers)
    -  High (More formal/detailed/rare conversation that might not be used everyday)
    8) Category:  Category of the phrase such as Daily Life, Cooking, Movies and Entertainment, Date night, Classroom conversation, and so on  
    '''
    
