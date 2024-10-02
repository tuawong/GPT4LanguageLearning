import Constants
from  openai import OpenAI
import os
import pandas as pd
import time

import gspread
import gspread_dataframe as gd
import gspread_formatting as gf
from gspread_formatting import cellFormat, color, textFormat

from io import StringIO
from datetime import datetime

cat = ['General', 'Grammar', 'Direction', 'Opinion', 'Time',
       'Description', 'Organization', 'Travel', 'Social', 'Technology',
       'Health', 'Object', 'Work', 'Intent', 'Geography', 'Agriculture',
       'Weather', 'Action', 'Problem Solving', 'Necessity', 'Support',
       'Business', 'Information', 'Emotion', 'Assurance', 'Economics',
       'Degree', 'Frequency', 'Question', 'Location', 'Sequence',
       'Contrast', 'Thought', 'Relationship']

def load_dict(
        dict_path: str = None, 
        gsheet_mode=False, 
        gsheet_name = None, 
        worksheet_name = None
        ):
    if gsheet_mode:
        sa = gspread.service_account()
        sh = sa.open(gsheet_name)
        wks = sh.worksheet(worksheet_name)
        current_data = pd.DataFrame(wks.get_all_values())
        current_data.columns = current_data.iloc[0]
        current_data = current_data.iloc[1:]
        return current_data
    
    else:
        if os.path.exists(dict_path):
            return pd.read_csv(dict_path)
        else:
            return pd.DataFrame(columns=["Chinese", "English", "Pinyin"])

     
def save_df_to_gsheet(
        gsheet_name, 
        wks_name,
        df_to_save,
        overwrite_mode = False
    ):
    sa = gspread.service_account()
    sh = sa.open(gsheet_name)
    wks = sh.worksheet(wks_name)

    if not overwrite_mode:
        existing = gd.get_as_dataframe(wks)
        df_to_save = pd.concat([existing, df_to_save])
    
    gd.set_with_dataframe(wks, df_to_save)


def format_gsheet(
        gsheet_name, 
        wks_name
    ):
    sa = gspread.service_account()
    sh = sa.open(gsheet_name)
    wks = sh.wks(wks_name)

    fmt = cellFormat(
        backgroundColor=color(0.6, 0.8, 0.9),
        textFormat=textFormat(bold=True, fontSize=15, foregroundColor=color(0, 0, 0.6)),
        horizontalAlignment='CENTER'
        )

    gf.format_cell_range(wks, 'A1:H1', fmt)

    fmt = cellFormat(
        textFormat=textFormat(fontSize=15),
        )

    gf.format_cell_range(wks, 'A2:A500', fmt)
    gf.format_cell_range(wks, 'E2:E500', fmt)


def get_prompt_for_chinese_translation(chinese_words, existing_categories=cat):
    chinese_prompt =  f"""
    For each of the input Chinese words, please output the following as a one row in a table.  There should be the following columns in table related to the word.  

    Generate output similar to the following example: 
    1. Word:  农场
    2. Pinyin:  nóng chǎng  (This is a column of proper pinyin.  All the tones should be shown explicitly, no number representation for tone allowed in this column) 
    3. Pinyin Simplified:  nong2 chang3  (Instead of showing tones explicitly use number to represent tones instead and use v to represent the special character ǜ)    
    4. Type:   Noun (This should be adjusted whether the meaning of the word is noun/adjective/verb based on the meaning and example sentence)
    5. Meaning:  Farm (This is could be a longer description of the meaning of the word if no exact translation exists in English.  If this is a common word in English, then only one word translation is sufficient)
    6. Sentence:  我暑假打算去爷爷的农场帮忙  
    7. Sentence Pinyin:  Wǒ shǔjià dǎsuàn qù yéye de nóngchǎng bāngmáng. 
    8. Sentence Meaning:  I plan to go to my grandfather's farm to help during the summer vacation.
    9. Word Category: Agriculture (This should be a general category that the word belongs to)

    For each word with multiple meanings, add more rows to the the table with alternate meaning and example sentence.  Each row should have a unique meaning.
    If there is only one meaning, then keep only one row for each word.  Do not add rows for alternate meanings if there is only one meaning.  If the two meanings are sufficiently similar then they can be included in the same row.
    If the meanings are different, then the second meaning should be in a new row with the same word, pinyin, word type, and sentence.  Don't omit any values in any row even if they are the same as the row above.
    
    All input words should be included in one table.  Only return the table with no other text.

    Input Chinese Word = {chinese_words}
    Do not include any word that is not in the list {chinese_words} in the Word column of the ouput table
    """


    if existing_categories:
        chinese_prompt = f"""
            {chinese_prompt}

            Existing Categories: {','.join(existing_categories)}"
            The categories above already exist in the database.  Only add new category if the word does not fit into any of the existing categories.
            """

    return chinese_prompt



def parse_translation_response(content: str) -> pd.DataFrame:
    '''
    Parse the table response from OpenAI into a pandas DataFrame
    '''
    # Using StringIO to treat the text as a file-like object for pandas
    data = StringIO(content)

    # Read the table into a pandas DataFrame
    df = pd.read_csv(data, delimiter='|',  engine='python')

    # Cleaning the DataFrame by stripping leading/trailing whitespaces from column names and data
    df.columns = df.columns.str.strip()
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.loc[~df.Word.str.contains('--')]

    col_to_keep = [col for col in df if 'Unnamed' not in col]
    df = df[col_to_keep]
    df['Word'] = df.Word.replace('', pd.NA).ffill()
    df['Pinyin'] = df.Pinyin.replace('', pd.NA).ffill()
    df['Pinyin Simplified'] = df['Pinyin Simplified'].replace('', pd.NA).ffill()
    df['Type'] = df.Type.replace('', pd.NA).ffill()
    df['Added Date'] = datetime.now().strftime("%Y-%m-%d")

    return df


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
        
    existing_words = chinese_dict['Word'].drop_duplicates().values

    starting_words_len = len(existing_words)
    new_words_len = len(new_words)

    if overwrite_mode:
        chinese_dict = chinese_dict.loc[~chinese_dict.Word.isin(new_words)]
        dedup_words_len = len(chinese_dict['Word'].drop_duplicates().values)
        chinese_dict = pd.concat([chinese_dict, newwords_df])
        
        print(f"Overwrite mode enabled.  Replacing {starting_words_len - dedup_words_len} words and {new_words_len - (starting_words_len - dedup_words_len)} new words added.")

    else: 
        newwords_df = newwords_df.loc[~newwords_df.Word.isin(existing_words)]
        dedup_words_len = len(newwords_df['Word'].drop_duplicates().values)
        chinese_dict = pd.concat([chinese_dict, newwords_df])
        
        print(f"Overwrite mode disabled.  {new_words_len - dedup_words_len} exists in current dictionary, adding {dedup_words_len} words.")

    if gsheet_mode:
        save_df_to_gsheet(gsheet_name, worksheet_name, chinese_dict, overwrite_mode=True)
    else:
        chinese_dict.to_csv(dict_path, index=False)