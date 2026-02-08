from typing import List

from  openai import OpenAI
import os
import numpy as np
import pandas as pd
import time

import os
from io import StringIO
from datetime import datetime

from main.gsheets import load_gsheet_dict, save_df_to_gsheet, format_gsheet
from main.sql import load_dict
from main.utils import get_completion, parse_response_table
from main.sql import sql_update_worddict

# Incorporate data
df = load_dict()

cat = df['Word Category'].drop_duplicates().values 
#cat = ['General', 'Grammar', 'Direction', 'Opinion', 'Time',
#       'Description', 'Organization', 'Travel', 'Social', 'Technology',
#       'Health', 'Object', 'Work', 'Intent', 'Geography', 'Agriculture',
#       'Weather', 'Action', 'Problem Solving', 'Necessity', 'Support',
#       'Business', 'Information', 'Emotion', 'Assurance', 'Economics',
#       'Degree', 'Frequency', 'Question', 'Location', 'Sequence',
#       'Contrast', 'Thought', 'Relationship', 'Food', 'Weather']


def get_prompt_for_word_comparison(word1, word2):
    chinese_prompt =  f"""
    For the following word pair, please output the following as a one row in a table.  There should be the following columns in table related to the word.  
    1) Word1: The first word provided.
    2) Word1 Pinyin: The pinyin for the first word.
    3) Word2: The second word provided.
    4) Word2 Pinyin: The pinyin for the second word.
    5) Meaning: The shared meaning or general definition of the two words.
    6) Part of Speech 1: The part of speech for the first word (e.g., noun, verb, adjective).
    7) Part of Speech 2: The part of speech for the second word (e.g., noun, verb, adjective).
    8) Word 1 Nuance: A description of nuances or usage contexts specific to the first word.
    9) Word 2 Nuance: A description of nuances or usage contexts specific to the second word.
    10) Word 1 Tone: Indicates the tone or register (e.g., casual, formal) typically associated with the first word.
    11) Word 2 Tone: Indicates the tone or register (e.g., casual, formal) typically associated with the second word.
    12) Word 1 Example: An example sentence using the first word.
    13) Word 1 Example Pinyin: The pinyin for the example sentence using the first word.
    14) Word 1 Example Meaning: The English translation of the example sentence using the first word.
    15) Word 2 Example: An example sentence using the second word.
    16) Word 2 Example Pinyin: The pinyin for the example sentence using the second word.
    17) Word 2 Example Meaning: The English translation of the example sentence using the second word.

    No textual output if is allowed.  The table should be the only output.
    """

    return chinese_prompt



def get_prompt_for_chinese_translation(chinese_words, existing_categories=cat):
    chinese_prompt =  f"""
    For each of the input Chinese words, please output the following as a one row in a table.  There should be the following columns in table related to the word.  

    Generate output similar to the following example: 
    1. Word:  农场 (If the word provided is in traditional Chinese, then replace it with the simplified version)
    2. Pinyin:  nóng chǎng  (This is a column of proper pinyin.  All the tones should be shown explicitly, no number representation for tone allowed in this column) 
    3. Pinyin Simplified:  nong2 chang3  (Instead of showing tones explicitly use number to represent tones instead and use v to represent the special character ǜ)    
    4. Type:   Noun (This should be adjusted whether the meaning of the word is noun/adjective/verb based on the meaning and example sentence)
    5. Word Category: Agriculture (This should be a general category that the word belongs to)
    5. Meaning:  Farm (This is could be a longer description of the meaning of the word if no exact translation exists in English.  If this is a common word in English, then only one word translation is sufficient)
        For words with nuanced meanings, the meaning column should capture the nuance in the meaning of the word. For words that can have be mapped to single English word, but has nuanced meaning in Chinese, the meaning column should capture the nuance of the word.
        For example 说, 讲, 聊, 谈, 吵, all can be translated to "talk" or "speak" in English, but each word has its own nuance in Chinese.  The meaning column should capture the nuance of each word.
    6. Sentence:  我暑假打算去爷爷的农场帮忙  
    7. Sentence Pinyin:  Wǒ shǔjià dǎsuàn qù yéye de nóngchǎng bāngmáng. 
    8. Sentence Meaning:  I plan to go to my grandfather's farm to help during the summer vacation.

    For each word with multiple meanings, add more rows to the the table with alternate meaning and example sentence.  Each row should have a unique meaning.
    If there is only one meaning, then keep only one row for each word.  Do not add rows for alternate meanings if there is only one meaning.  If the two meanings are sufficiently similar then they can be included in the same row.
    If the meanings are different, then the second meaning should be in a new row with the same word, pinyin, word type, and sentence.  Don't omit any values in any row even if they are the same as the row above.

    Translation Instructions:
    When provided with words that have nuances such that the English translation is not sufficient to capture the full meaning of the word, please provide a more nuanced translation.  
    Do NOT provide incomplete one word translations for words that have nuanced meanings.  
    Example words with nuanced translations:

    Word: 说 
    Incomplete Literal Translation: To speak --> (Incorrect)
    Nuanced Translation: To convey information or express thoughts through spoken language, often in a more formal or structured manner. --> (Correct)
    
    Word: 讲
    Incomplete Literal Translation: To speak --> (Incorrect)
    Nuanced Translation: To tell or narrate something, often with an emphasis on the content or story being shared. --> (Correct)
    
    Word: 包容
    Incomplete Literal Translation: Tolerance --> (Incorrect)
    Nuanced Translation: To accept differences with understanding, not just putting up with them. --> (Correct)

    Word: 敬畏 (jìngwèi)
    Incomplete Literal Translation: Respect --> (Incorrect)
    Nuanced Translation: A deep awe mixed with fear toward something greater. --> (Correct)

    Word: 缘分 (yuánfèn)
    Incomplete Literal Translation: Fate --> (Incorrect)
    Correct Nuanced Translation: A destined connection or bond between people. --> (Correct)

    Word: 顾忌 (gùjì)
    Incomplete Literal Translation: Concern --> (Incorrect)
    Correct Nuanced Translation: Hesitation or reservation caused by fear, worry, or consideration of other people's feelings or social norms. --> (Correct)

    Word: 缘分 (yuánfèn)
    Incomplete Literal Translation: Fate --> (Incorrect)
    Correct Nuanced Translation: A destined connection or bond between people. --> (Correct)

    Word: 时光 (shíguāng)
    Incomplete Literal Translation: Time --> (Incorrect)
    Correct Nuanced Translation: A period or moment in time; often used poetically to refer to the passage of time. --> (Correct)

    Conversely, if a word has a simple translation that is sufficient to capture the meaning, then only provide the simple translation.  
    Do not provide a nuanced translation if the simple translation is sufficient and do not provide explanation for simple concepts if there is no nuance to the word.
    In this case, do not nuance along the simple translation.  Only provide the simple translation.
    Example words with simple translations:
    Word: 爱 (ài)
    Literal Translation: Love --> (Correct)
    Explained Translation:  Love; An intense feeling of deep affection.--> (Incorrect)

    Word: 陌生人 (mòshēngrén)
    Literal Translation: Stranger --> (Correct)
    Explained Translation: A person whom one does not know --> (Incorrect)
    
    Word: 水 (shuǐ)
    Literal Translation: Water  --> (Correct)
    Explained Translation: A colorless, transparent, odorless liquid that forms the seas, lakes, rivers, and rain --> (Incorrect)

    Word: 狗 (gǒu)
    Literal Translation: Dog  --> (Correct)
    Explained Translation: A domesticated carnivorous mammal that typically has a long snout, an acute sense of smell, nonretractable claws, and a barking, howling, or whining voice --> (Incorrect)

    Word: 吹 (chuī)
    Literal Translation: To blow  --> (Correct)
    Explained Translation: To emit air through pursed lips --> (Incorrect)

    Word: 时间 (shíjiān)
    Literal Translation: Time  --> (Correct)
    Explained Translation: The indefinite continued progress of existence --> (Incorrect)

    Word: 客户 (kèhù)
    Literal Translation: Client  --> (Correct)
    Explained Translation: Client; a person or organization using the services of a professional or business.  --> (Incorrect)

    Input Chinese Word = {chinese_words}
    Do not include any word that is not in the list {chinese_words} in the Word column of the ouput table
    
    All input words should be included in one table.  Only return the table with no other text.
    """

    if existing_categories is not None:
        chinese_prompt = f"""
            {chinese_prompt}

            Existing Categories: {','.join(existing_categories)}"
            The categories above already exist in the database.  Only add new category if the word does not fit into any of the existing categories.
            """

    return chinese_prompt

def get_prompt_for_rarity_classification(chinese_words, debug=False):
    chinese_prompt =  f"""
    For each of the input Chinese please generate a classification of how rare they word is.

    Rarity Classification:  
    Common:  Used in everyday conversations or in formal situations.
    Rare:  Used only in a more poetic/literary sense.  Will typically only seen in songs or poem or literature.  Very rarely used in conversation. 
    If a word is both often used in both common conversation and in literature, it MUST be classified as common.  
    Only classify words as rare if they are not used in everyday conversation.  

    Each word should be outputted as a single row in a table. 
    No other written response should be outputted except for the table.  No text or symbols should be outputted except for the table.
    The columns in the table should be as follows:
    1) Word:  农场 (If the word provided is in traditional Chinese, then the simplified version should be provided in parentheses)
    2) Word Rarity:  Common (This should be adjusted based on the rarity of the word)
    Do not change the column names or the order of the columns.  Only include the columns above in the table.

    Input Chinese Word = {chinese_words}
    Do not include any word that is not in the list {chinese_words} in the Word column of the ouput table
    If there is duplicate in the word list, then only include the word once in the table.  
    Do not include the same word multiple times in the table.
    """

    
    if debug:
        chinese_prompt = f"""
            {chinese_prompt}

            In addition to the first two columns, also include the following columns in the table.
            3) Pinyin:  nóng chǎng  (This is a column of proper pinyin.  All the tones should be shown explicitly, no number representation for tone allowed in this column)
            4) Meaning:  Farm (This is could be a longer description of the meaning of the word if no exact translation exists in English.  If this is a common word in English, then only one word translation is sufficient)
            5) Justification:  Provide a brief explanation of why the word is classified as common, uncommon, or rare.  This should be a brief explanation of why the word is classified as such.  
            """
        
    return chinese_prompt

# Multiclass rarity classification into common, uncommon, and rare is still difficult 
# Model mixes up the classification of the words.  Need to provide more examples and more detailed instructions
def get_prompt_for_multiclass_rarity_classification(chinese_words, debug=False):
    chinese_prompt =  f"""
    For each of the input Chinese please generate a classification of how rare they word is.

    Rarity Classification:  
    Common:  Used in everyday conversations.  
    Uncommon:  Used in conversation but during formal situation such as in when you're in a meeting or talking to someone to be respected.  
    Rare:  Used only in a more poetic/literary sense.  Will typically only seen in songs or poem or literature.  Very rarely used in conversation. 
    If a word is both often used in both common conversation and in literature, it MUST be classified as common.  
    Only classify words as uncommon or rare if they are not used in everyday conversation.  

    Each word should be outputted as a single row in a table. 
    No other written response should be outputted except for the table.  
    The columns in the table should be as follows:
    1) Word:  农场 (If the word provided is in traditional Chinese, then replace it with the simplified version.  Do not put both words in parentheses. Do not add anything else in the Word column except for the simplified version of the word.)
    2) Word Rarity:  Common (This should be adjusted based on the rarity of the word with the two options Common or Rare)
    Do not change the column names or the order of the columns.  Only include the columns above in the table.

    Example Words Common: 太太, 主意, 酒店, 超市, 带, 多久
    Example Words Rare: 奢求, 空虚, 时光, 仰望, 侧脸

    Input Chinese Word = {chinese_words}
    Do not include any word that is not in the list {chinese_words} in the Word column of the ouput table
    If there is duplicate in the word list, then only include the word once in the table.  
    Do not include the same word multiple times in the table.
    """

    
    if debug:
        chinese_prompt = f"""
            {chinese_prompt}

            In addition to the first two columns, also include the following columns in the table.
            3) Pinyin:  nóng chǎng  (This is a column of proper pinyin.  All the tones should be shown explicitly, no number representation for tone allowed in this column)
            4) Meaning:  Farm (This is could be a longer description of the meaning of the word if no exact translation exists in English.  If this is a common word in English, then only one word translation is sufficient)
            5) Justification:  Provide a brief explanation of why the word is classified as common, uncommon, or rare.  This should be a brief explanation of why the word is classified as such.  
            """
        
    return chinese_prompt


def save_new_words_to_dict(
        newwords_df : pd.DataFrame, 
        gsheet_mode = False, 
        gsheet_name = None, 
        worksheet_name = None,
        dict_path: str = None, 
        overwrite_mode: bool =False
        ) -> None:
    '''
    Add new words to the Chinese dictionary and save to disk. 
    If overwrite_mode is enabled, then the new words will replace any existing words in the dictionary.  
    Otherwise, only new words will be added to the dictionary.
    '''
    new_words = newwords_df['Word'].drop_duplicates().values

    if gsheet_mode:
        chinese_dict = load_dict(gsheet_mode=gsheet_mode, gsheet_name=gsheet_name, worksheet_name=worksheet_name)
    else:
        chinese_dict = pd.read_csv(dict_path) 
    
    max_id = pd.to_numeric(chinese_dict['Word Id'].apply(lambda x: x.replace('D','')), errors='coerce').max()
    newwords_df['Word Id'] = ['D'+str(num + max_id).zfill(6) for num in range(1, len(newwords_df) + 1)]
    newwords_df['Num_Quiz_Attempt'] = 0
    newwords_df['Num_Correct'] = 0
    newwords_df['Num_Wrong'] = 0
    newwords_df['Last_Quiz'] = ''

    missing_cols = [col for col in chinese_dict.columns if col not in newwords_df.columns]
    if len(missing_cols) > 0:
        raise Exception(f"Missing columns in df to add: {missing_cols}")

    newwords_df = newwords_df[chinese_dict.columns]
    existing_words = chinese_dict['Word'].drop_duplicates().values

    starting_words_len = len(existing_words)
    new_words_len = len(new_words)

    if overwrite_mode:
        #print(f'Word Before: {chinese_dict.loc[chinese_dict.Word.isin(new_words)][['Word Id', 'Word']]}')
        chinese_dict = chinese_dict.loc[~chinese_dict.Word.isin(new_words)]
        #print(f'Word After: {chinese_dict.loc[chinese_dict.Word.isin(new_words)][['Word Id', 'Word']]}')
        if len(chinese_dict.loc[chinese_dict.Word.isin(new_words)]) == 0:

            dedup_words_len = len(chinese_dict['Word'].drop_duplicates().values)
            chinese_dict = pd.concat([chinese_dict, newwords_df])
        
        else:
            raise Exception("Some words in the new words list already exist in the dictionary.  Please disable overwrite mode to add new words.")
            
        message = f"Overwrite mode enabled.  Replacing {starting_words_len - dedup_words_len} words and {new_words_len - (starting_words_len - dedup_words_len)} new words added."

    else: 
        newwords_df = newwords_df.loc[~newwords_df.Word.isin(existing_words)]
        dedup_words_len = len(newwords_df['Word'].drop_duplicates().values)
        chinese_dict = pd.concat([chinese_dict, newwords_df])
        
        message = f"Overwrite mode disabled.  {new_words_len - dedup_words_len} exists in current dictionary, adding {dedup_words_len} words."

    chinese_dict = chinese_dict.loc[(chinese_dict['Word Id'].notnull()) & (chinese_dict['Word Id'] != '')]
    chinese_dict['Word'] = chinese_dict['Word'].str.strip()

    if gsheet_mode:
        #Save empty df first to clear the worksheet
        save_df_to_gsheet(gsheet_name, worksheet_name, pd.DataFrame(), overwrite_mode=overwrite_mode)
        save_df_to_gsheet(gsheet_name, worksheet_name, chinese_dict, overwrite_mode=overwrite_mode)
    else:
        chinese_dict.to_csv(dict_path, index=False)
    
    return message


class TranslationPipeline:
    '''
    Translation pipeline to generate translations for Chinese words and update the dictionary with the new words.
    '''
    def __init__(self, 
                 gsheet_mode=False,
                 gsheet_name=None, 
                 worksheet_name=None
                 ):
        self.gsheet_mode = gsheet_mode
        self.gsheet_name = gsheet_name
        self.worksheet_name = worksheet_name
        self.new_words_df = pd.DataFrame()
    
    def translation_module(self, word_list, translation_model="gpt-4o", rarity_model="gpt-4o-mini", temp=0.7, replace_new_words=True):
        ## Generate words translation
        translation_response = (
            get_completion(
                prompt=get_prompt_for_chinese_translation(word_list), model=translation_model , temperature=temp))

        newwords_df = (
            parse_response_table(
                translation_response.choices[0].message.content,
                ffill_cols = ['Word', 'Pinyin', 'Pinyin Simplified', 'Type'],
                date_col = ['Added Date']
                )
            )
        
        ## Generate words rarity classification
        rarity_response = (
            get_completion(
                prompt=get_prompt_for_rarity_classification(word_list), model=rarity_model, temperature=temp))
        word_rarity_df = parse_response_table(rarity_response.choices[0].message.content)
        #print(word_rarity_df)

        max_retries = 3
        for retry in range(max_retries):
            if word_rarity_df['Word Rarity'].notna().min() > 0: 
                break
            else:
                print(f"Retrying rarity classification for {word_list} due to empty Rarity column. Attempt {retry + 1}/{max_retries}")
                time.sleep(1) 
                rarity_response = (
                    get_completion(
                        prompt=get_prompt_for_rarity_classification(word_list), model=rarity_model, temperature=temp))
                word_rarity_df = parse_response_table(rarity_response.choices[0].message.content)

        newwords_df = pd.merge(newwords_df, word_rarity_df, on='Word', how='left')

        if not (replace_new_words) and len(self.new_words_df) > 0:
            orig_new_words_df = self.new_words_df.copy()

            if len(orig_new_words_df) > 0:
                orig_new_words_df = orig_new_words_df.loc[~orig_new_words_df.Word.isin(newwords_df.Word)]
            self.new_words_df = pd.concat([orig_new_words_df, newwords_df])

        else:
            self.new_words_df = newwords_df
            
    def clear_new_words(self):
        self.new_words_df = pd.DataFrame()

    def update_module(self, df=None, overwrite_mode=False):
        if (df is None):
            upload_df = self.new_words_df
        elif (df is not None):
            upload_df = df
        else:
            raise Exception("Run the translation module first or provide external dataset before running the update module.")
        
        if self.gsheet_mode:
            message = save_new_words_to_dict(
                newwords_df = upload_df,
                gsheet_mode= True,
                overwrite_mode = overwrite_mode,
                gsheet_name = self.gsheet_name,
                worksheet_name = self.worksheet_name
            )
        else:
            message = sql_update_worddict(upload_df)
        
        return message
    
    def run_translation_pipeline(self, word_list, translation_model="gpt-4.1-mini", rarity_model="gpt-4.1-mini", temp=0.7, gsheet_mode=False):
        self.translation_module(word_list, translation_model=translation_model, rarity_model=rarity_model, temp=temp)   
        message = self.update_module(gsheet_mode=gsheet_mode)
        return message
