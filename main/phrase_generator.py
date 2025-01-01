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
from main.utils import get_completion, parse_response_table

gsheet_name = Constants.SHEET_NAME
phrasesheet_name = Constants.PHRASE_SHEET_NAME

phrase_dict = load_dict(gsheet_mode=True, gsheet_name=gsheet_name, worksheet_name=phrasesheet_name)
existing_cat = phrase_dict['Category'].drop_duplicates().values

client = OpenAI(
    api_key = Constants.API_KEY_OPENAI,
)



def get_prompt_to_gen_phrases(
    situation: str = "",
    num_phrases: int = 5,
    complexity: str = "Low",
    existing_phrases: List[str] = None
    ):
    prompt = f'''
    Can you generate some useful phrases in Mandarin base on the following situation.  
    If the situation provided is blank.  Then generate some phrases that could be useful for someone building more proficiency in Mandarin.  
    Do NOT output anything response except for the table. There should not be any space, letter, symbol, or new line before or after the table. 

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
    8) Category:  Category of the phrase such as Daily Life, Cooking, Movies and Entertainment, Date night, Classroom conversation

    Here are the existing categories.  Please map the new phrases to one of these categories.  
    If none of these categories fit, please create a new category.
    {existing_cat}
    '''

    if len(existing_phrases) > 0:
        prompt += f'''
            Here are the sentences I already have, please don't output something too similar
            {existing_phrases}
            '''
    
    return prompt

def get_prompt_to_respond(
    input_phrases: str,
    complexity: str = "Low"
    ): 
    return f'''
    Can you generate some useful responses to the input phrase in Mandarin base on the following situation.  
    Only one output is needed for each input phrase.
    Do NOT output anything response except for the table. There should not be any space, letter, symbol, or new line before or after the table. 

    Parameters
    Input Phrases: {input_phrases}
    Complexity: {complexity}


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

    Here are the existing categories.  Please map the new phrases to one of these categories.  
    If none of these categories fit, please create a new category.
    {existing_cat}
    '''
    

def save_new_phrase_to_dict(
    new_phrase_df: pd.DataFrame,
    gsheet_name: str,
    worksheet_name: str,
):
    phrase_dict = load_dict(gsheet_mode=True, gsheet_name=gsheet_name, worksheet_name=worksheet_name)
    max_id = pd.to_numeric(phrase_dict['Phrase Id'], errors='coerce').max()
    new_phrase_df['Phrase Id'] = [num + max_id for num in range(1, len(new_phrase_df) + 1)]

    phrase_df_to_save = pd.concat([phrase_dict, new_phrase_df], ignore_index=True)
    save_df_to_gsheet(gsheet_name, worksheet_name, pd.DataFrame(), overwrite_mode=True)
    save_df_to_gsheet(gsheet_name, worksheet_name, phrase_df_to_save, overwrite_mode=True)

    return "Saved new phrases to the dictionary."


class PhraseGenerationPipeline:
    '''
    Translation pipeline to generate translations for Chinese words and update the dictionary with the new words.
    '''
    def __init__(self, gsheet_name, worksheet_name):
        self.gsheet_name = gsheet_name
        self.worksheet_name = worksheet_name
        self.new_phrase_df = pd.DataFrame()
    
    def phrase_generation_module(
            self, 
            situation, 
            num_phrases, 
            complexity, 
            existing_phrases=[], 
            translation_model="gpt-4o",
            temp=0.7
            ):
        phrase_gen_response =  get_completion(
            prompt = get_prompt_to_gen_phrases(
                situation = situation,
                num_phrases = num_phrases,
                complexity = complexity,
                existing_phrases=existing_phrases
                ),
            model=translation_model, 
            temperature=temp)
        self.phrase_gen_response = phrase_gen_response

        new_phrase_df = parse_response_table(phrase_gen_response.choices[0].message.content, date_col=['Added Date'])
        self.new_phrase_df = new_phrase_df

    def phrase_response_module(
            self, 
            input_phrases,
            complexity, 
            translation_model="gpt-4o", 
            temp=0.7
            ):
        phrase_gen_response =  get_completion(
            prompt = get_prompt_to_respond(input_phrases, complexity=complexity),
            model=translation_model, 
            temperature=temp)
        self.phrase_gen_response = phrase_gen_response

        new_phrase_df = parse_response_table(phrase_gen_response.choices[0].message.content, date_col=['Added Date'])
        self.new_phrase_df = new_phrase_df

    def clear_new_phrases(self):
        self.new_phrase_df = pd.DataFrame() 
    
    def update_module(self, df=None):
        if (df is None):
            upload_df = self.new_phrase_df
        elif (df is not None):
            upload_df = df
        else:
            raise Exception("Run the phrase generation module first or provide external dataset before running the update module.")
        
        message = save_new_phrase_to_dict(
                new_phrase_df = upload_df,
                gsheet_name = self.gsheet_name,
                worksheet_name = self.worksheet_name
            )
        
        return message

    def run_phrase_generation_pipeline(
            self, 
            situation,
            num_phrases, 
            complexity, 
            existing_phrases=[], 
            translation_model="gpt-4o", 
            temp=0.7
        ):
        self.phrase_generation_module(situation, num_phrases, complexity, existing_phrases, translation_model, temp)
        message = self.update_module()
        return message
    
    def run_phrase_response_pipeline(
            self, 
            input_phrases, 
            complexity, 
            translation_model="gpt-4o", 
            temp=0.7
        ):
        self.phrase_response_module(input_phrases, complexity, translation_model, temp)
        message = self.update_module()
        return message
