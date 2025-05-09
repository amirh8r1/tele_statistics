from typing import Union
from pathlib import Path
import json

import arabic_reshaper
from bidi.algorithm import get_display
from hazm import Normalizer, word_tokenize, sent_tokenize
from src.data import DATA_DIR
from wordcloud import WordCloud
from loguru import logger
from collections import Counter, defaultdict


class ChatStatistics:
    """Generates chat statistics from a telegram chat json file
    """
    def __init__(self, chat_json: Union[str, Path]):
        """
        :param chat_json: path to telegram export json file
        """
        # load chat data
        logger.info(f"Loading chat data from {chat_json}")
        with open(chat_json) as f:
            self.chat_data = json.load(f)

        self.normalizer = Normalizer()

        # load stopwords
        logger.info(f"Loading stopwords from {DATA_DIR / 'stopwords.txt'}")
        stop_words = open(DATA_DIR / 'stopwords.txt').readlines()
        stop_words = map(str.strip, stop_words)
        self.stop_words = set(map(self.normalizer.normalize, stop_words))

    @staticmethod
    def rebuild_msg(sub_messages):
        msg_text = ''
        for sub_msg in sub_messages:
            if isinstance(sub_msg, str):
                msg_text += sub_msg
            elif 'text' in sub_msg:
                msg_text += sub_msg['text']

        return msg_text
    
    def msg_has_question(self, msg):
        """check if a massage has a question
        
        :param msg: message to check
        """
        if not isinstance(msg['text'], str):
            msg['text'] = self.rebuild_msg(msg['text'])

        sentences = sent_tokenize(msg['text'])
        for sentence in sentences:
            if ('?' not in sentence) and ('؟' not in sentence):
                continue

            return True

    def get_top_users(self, top_n: int = 10) -> dict:
        """Get the top n users from the chat.

        :param top_n: number of users to get, default is 10
        :return: dict of top users
        """
        # check messages for questions
        is_question = defaultdict(bool)
        for msg in self.chat_data['messages']:
            if self.msg_has_question(msg):
                is_question[msg['id']] = True

        # get top users based on replying to questions from others
        logger.info("Getting top users...")
        users = []
        for msg in self.chat_data['messages']:
            if not msg.get('reply_to_message_id'):
                continue
            if is_question[msg['reply_to_message_id']] is False:
                continue

            users.append(msg['from'])

        return dict(Counter(users).most_common(top_n))

    def generate_word_cloud(self, output_dir: Union[str, Path]):
        """Generate a word cloud from the data

        :param output_dir: path to output directory for word cloud image
        """
        logger.info("Loading text content...")
        text_content = ''

        for msg in self.chat_data['messages']:
            if type(msg['text']) is str:
                tokens = word_tokenize(msg['text'])
                tokens = list(filter(lambda item: item not in self.stop_words, tokens))
                text_content += f" {' '.join(tokens)}"

        # normalize, reshape for final word cloud
        text_content = self.normalizer.normalize(text_content)
        text_content = arabic_reshaper.reshape(text_content)
        # text_content = get_display(text_content)

        # generate word cloud
        logger.info("Generating word cloud...")
        wordcloud = WordCloud(
            width=1200, height=1200,
            font_path=str(DATA_DIR / 'BHoma.ttf'),
            background_color='white'
        ).generate(text_content)

        logger.info(f"Saving word cloud to {output_dir}")
        wordcloud.to_file(Path(output_dir) / 'wordcloud.png')


if __name__ == "__main__":
    chat_stats = ChatStatistics(chat_json=DATA_DIR / 'result.json')
    chat_stats.generate_word_cloud(output_dir=DATA_DIR)

    top_users = chat_stats.get_top_users()
    print(top_users)

    print('Done!')
