import json
import pprint
from typing import List

from openai import OpenAI

from domain.DTO.DTO import KeywordDTO


class MargeKeywords:
    client = OpenAI()

    @staticmethod
    def print_total_tokens(msg=None, response=None):
        users = response.model_dump().get("usage")
        print(f"{msg} -> total_token : {users.get('total_tokens')}")

    @classmethod
    async def get_keywords(cls, keywords: List[KeywordDTO]):
        print(keywords)

        prompt = """
Objective:  
- Receive a list of keywords of interest in JSON format.  

Instructions:  
1. Group similar keywords (both English and Korean).  
2. Choose the most frequent keyword as the representative.  
3. Remove duplicates.  

Output Format:  
- The result should be a list of JSON objects, where each object follows this structure:  
{
    "keyword": "Representative keyword",
    "options": ["subkeyword1", "subkeyword2", "subkeyword3"]
}

Requirements:  
- If no subkeywords are available, the "options" array should be empty.  
- Always output in Korean.
                """
        # DTO 리스트를 JSON 문자열로 변환
        text = json.dumps([keyword.__dict__ for keyword in keywords], ensure_ascii=False)
        response = cls.client.responses.create(
            model="gpt-4.1",
            input=[
                {
                    "role": "system",
                    "content": prompt,
                },
                {
                    "role": "user",
                    "content": text,
                }
            ],
            temperature=1,
            top_p=1,
            store=True
        )
        cls.print_total_tokens("키워드 점수", response)
        pprint.pprint(response)
        keyword = json.loads(response.model_dump()["output"][0]["content"][0]["text"])

        return keyword
