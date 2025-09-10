SELECT
    word_id,
    word,
    COUNT(*) AS num_quiz_attempt,
    SUM(CASE WHEN lower(pinyin_correct)='yes' THEN 1 ELSE 0 END) AS pinyin_correct_cnt,
    SUM(CASE WHEN lower(pinyin_correct)='no'  THEN 1 ELSE 0 END) AS pinyin_wrong_cnt,
    SUM(CASE WHEN lower(meaning_correct)='yes' THEN 1 ELSE 0 END) AS meaning_correct_cnt,
    SUM(CASE WHEN lower(meaning_correct)='no'  THEN 1 ELSE 0 END) AS meaning_wrong_cnt,
    MAX(last_quiz) AS last_quiz
FROM quizlog
GROUP BY word_id, word;
