import mysql.connector
from mysql.connector import Error
from typing import Dict
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def create_connection():
    """데이터베이스 연결을 생성합니다."""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            database=os.getenv('MYSQL_DATABASE'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD')
        )
        if connection.is_connected():
            print("MySQL 데이터베이스에 연결되었습니다.")
            return connection
    except Error as e:
        print(f"Error: {e}")
        return None

def save_article(article: Dict[str, str]):
    """기사를 news_article_info 테이블에 저장합니다."""
    connection = create_connection()
    if connection is None:
        return

    try:
        cursor = connection.cursor()
        query = """INSERT INTO news_article_info 
                   (divisionyear, sitecodename, subsitecodename, usernick, subject, 
                    outsubject, summary, postdate, livedate, deskdate, contentrating, 
                    postip, state, deskstate, livestate)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        values = (
            datetime.now().year,  # divisionyear
            'AI_AGENT',  # sitecodename
            'NEWS',  # subsitecodename
            'AI_WRITER',  # usernick
            article['title'][:255],  # subject
            article['title'][:255],  # outsubject
            article['content'][:1000],  # summary (첫 1000자만 저장)
            current_time,  # postdate
            current_time,  # livedate
            current_time,  # deskdate
            0,  # contentrating
            '127.0.0.1',  # postip
            1,  # state (게시 상태)
            1,  # deskstate
            1   # livestate
        )
        
        cursor.execute(query, values)
        connection.commit()
        print(f"기사가 성공적으로 저장되었습니다. ID: {cursor.lastrowid}")
    except Error as e:
        print(f"기사 저장 중 오류 발생: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL 연결이 종료되었습니다.")

def get_article(article_id: int) -> Dict[str, str]:
    """ID로 기사를 조회합니다."""
    connection = create_connection()
    if connection is None:
        return {}

    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT * FROM news_article_info WHERE idx = %s"
        cursor.execute(query, (article_id,))
        article = cursor.fetchone()
        return article if article else {}
    except Error as e:
        print(f"기사 조회 중 오류 발생: {e}")
        return {}
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL 연결이 종료되었습니다.")

# 필요한 경우 추가 함수를 구현할 수 있습니다 (예: 기사 업데이트, 삭제 등)