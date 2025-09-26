# GPT4LanguageLearning

A Mandarin Chinese language learning platform powered by GPT-4, designed to generate quizzes, evaluate answers, and track learning progress. This project leverages OpenAI's GPT models, Google Sheets, and SQL for a flexible, data-driven language learning experience.

## Features

- **Quiz Generation:** Automatically generate Mandarin vocabulary and sentence quizzes with randomized content.
- **Automated Evaluation:** Use GPT-4 to evaluate user answers for meaning and pinyin accuracy.
- **Progress Tracking:** Log quiz results and update user progress in Google Sheets or a local database.
- **Customizable Filters:** Select quiz content by date, category, or rarity.
- **Data Management:** Import/export word dictionaries and quiz logs from Google Sheets or local files.

## Project Structure

```
.
├── main/
│   ├── quiz.py              # Core quiz logic and evaluation
│   ├── phrase_generator.py  # Phrase generation utilities
│   ├── translation.py       # Translation helpers
│   └── ...                  # Other utilities and constants
├── models/                  # Data models for words, quizzes, logs
├── pages/                   # Dash/Streamlit app pages
├── config.py                # Configuration settings
├── database.py              # Database connection and helpers
├── dashapp.py               # Dash app entry point
├── environment.yml          # Conda environment specification
├── gpt4language.yaml        # Project configuration
├── mydata.db                # Local SQLite database
└── ...
```

## Setup

### 1. Clone the Repository

```cmd
git clone https://github.com/tuawong/GPT4LanguageLearning.git
cd GPT4LanguageLearning
```

### 2. Environment Setup

Create the environment using Conda:

```cmd
conda env create -f environment.yml
conda activate gpt4languagelearning
```

Or install dependencies manually:

### 3. Configuration

- Set your OpenAI API key in `main/Constants.py` as `API_KEY_OPENAI`.

### 4. Running the App

To launch the Dash app:

```cmd
python dashapp.py
```

Or run Jupyter notebooks for interactive exploration.

## Usage
- Translate new Chinese words and add to personal database using the `TranslationPipeline` class in `main/translation.py`.
- Generate quizzes using the `QuizGenerator` class in `main/quiz.py`.
- Evaluate answers and update progress logs.

## Contributing

Pull requests and suggestions are welcome! Please open an issue to discuss your ideas.
