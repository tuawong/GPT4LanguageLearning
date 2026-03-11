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

# Pricing: (input_per_token_usd, output_per_token_usd)
# Update these when official pricing changes.
_MODEL_PRICING = {
    'gpt-4o-mini': (0.150e-6, 0.600e-6),
    'gpt-4o':      (2.500e-6, 10.00e-6),
    'gpt-5-mini':  (0.150e-6, 0.600e-6),  # placeholder — update when official pricing is available
}


def _log_api_call(category, model, latency_ms, response, error_message, num_items):
    """Write one row to APILatencyLog. Never raises — failures are caught by the caller."""
    from database import engine
    from models import APILatencyLog
    from sqlalchemy.orm import Session

    usage = getattr(response, 'usage', None) if response is not None else None
    input_tokens     = getattr(usage, 'input_tokens', None)
    output_tokens    = getattr(usage, 'output_tokens', None)
    reasoning_tokens = getattr(
        getattr(usage, 'output_tokens_details', None), 'reasoning_tokens', None
    )
    finish_reason = getattr(response, 'status', None)
    status = 'error' if error_message else 'success'

    in_price, out_price = _MODEL_PRICING.get(model, (0.0, 0.0))
    estimated_cost = None
    if input_tokens is not None and output_tokens is not None:
        estimated_cost = round((input_tokens * in_price) + (output_tokens * out_price), 8)

    record = APILatencyLog(
        category=category,
        model=model,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
        num_items=num_items,
        finish_reason=finish_reason,
        status=status,
        error_message=error_message,
        estimated_cost_usd=estimated_cost,
    )
    with Session(engine) as session:
        session.add(record)
        session.commit()


def get_completion(prompt, model="gpt-5-mini", temperature=1, category='unknown', num_items=None):
    if "gpt-5" in model:
        reasoning={"effort": "medium"}
        temperature = None
    else:
        reasoning=None

    print(f"Model: {model}, Temperature: {temperature}, Reasoning: {reasoning}")
    start_ms = time.time()
    response = None
    error_msg = None
    try:
        response = client.responses.create(
            model=model,
            input=prompt,
            temperature=temperature,
            reasoning=reasoning
        )
        usage = response.usage
        cached = getattr(getattr(usage, 'input_tokens_details', None), 'cached_tokens', 0) or 0
        print(f"Tokens — input: {usage.input_tokens}, output: {usage.output_tokens}, cached: {cached}")
        print(f"Usage details: {usage}")
        return response
    except Exception as e:
        error_msg = str(e)
        raise
    finally:
        latency_ms = int((time.time() - start_ms) * 1000)
        try:
            _log_api_call(
                category=category,
                model=model,
                latency_ms=latency_ms,
                response=response,
                error_message=error_msg,
                num_items=num_items,
            )
        except Exception as log_exc:
            print(f"[latency logging failed] {log_exc}")


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