import unittest
import mysql.connector
from db_operations import save_article, get_article
from dotenv import load_dotenv
import os

load_dotenv()

class TestSaveArticle(unittest.TestCase):
    def setUp(self):
        # 테스트 데이터베이스 연결 설정
        self.connection = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            database=os.getenv('MYSQL_DATABASE'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD')
        )
        self.cursor = self.connection.cursor(dictionary=True)

    def tearDown(self):
        # 테스트 후 정리
        if self.connection.is_connected():
            self.cursor.close()
            self.connection.close()

    def test_save_and_get_article(self):
        # 테스트할 기사 데이터
        test_article = {
            'title': 'Test Article Title',
            'content': 'This is the content of the test article.'
        }

        # 기사 저장
        save_article(test_article)

        # 가장 최근에 삽입된 기사의 ID 가져오기
        self.cursor.execute("SELECT MAX(idx) as last_id FROM news_article_info")
        last_id = self.cursor.fetchone()['last_id']

        # 저장된 기사 조회
        saved_article = get_article(last_id)

        # 저장된 데이터 확인
        self.assertEqual(saved_article['subject'], test_article['title'])
        self.assertEqual(saved_article['summary'], test_article['content'])
        self.assertEqual(saved_article['sitecodename'], 'AI_AGENT')
        self.assertEqual(saved_article['subsitecodename'], 'NEWS')
        self.assertEqual(saved_article['usernick'], 'AI_WRITER')

        self.connection.commit()

if __name__ == '__main__':
    unittest.main()