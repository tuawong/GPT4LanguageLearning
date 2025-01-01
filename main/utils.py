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


def parse_response_table(
        content: str, 
        ffill_cols: List[str] = None,
        date_col: List[str] = None
        ) -> pd.DataFrame:
    '''
    Parse the table response from OpenAI into a pandas DataFrame
    '''
    # Using StringIO to treat the text as a file-like object for pandas
    data = StringIO(content)

    # Read the table into a pandas DataFrame
    df = pd.read_csv(data, delimiter='|',  engine='python')

    # Cleaning the DataFrame by stripping leading/trailing whitespaces from column names and data
    df.columns = df.columns.str.strip()
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

    df = df[[col for col in df if 'Unnamed' not in col]]

    # Remove rows with dashes
    col_name = df.select_dtypes(include=['object']).columns[0]
    df = df.loc[~df[col_name].fillna('').str.contains('--')]

    col_to_keep = [col for col in df if 'Unnamed' not in col]
    df = df[col_to_keep]

    if ffill_cols:
        for col in ffill_cols:
            df[col] = df[col].replace('', pd.NA).ffill()

    if date_col:
        for col in date_col:
            df[col] = datetime.now().strftime("%Y-%m-%d")

    return df