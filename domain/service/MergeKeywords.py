import json
import pprint
from typing import List

from googleapiclient.model import Model
from openai import OpenAI
from pydantic import BaseModel

from domain.DTO.DTO import KeywordDTO


class MergeKeywordsDTO(BaseModel):
    prompt: str
    keywords: List[str]


class MargeKeywords:
    client = OpenAI()

    @staticmethod
    def print_total_tokens(msg=None, response=None):
        users = response.model_dump().get("usage")
        print(f"{msg} -> total_token : {users.get('total_tokens')}")

    @staticmethod
    def build_shopping_prompt() -> str:
        return """
Objective:
- Group related keywords and assign a representative keyword.

Instructions:
1. Group semantically similar or hierarchical keywords.
2. Use broad terms as representatives, specific ones as subkeywords.
3. For example:
   - "kitchen utensil set", "paring knife" → "kitchenware"
   - "camping table", "lantern" → "camping"
   - "pillow/blanket" → "bedding"
4. Avoid duplicates.

Output Format:
[
  {
    "keyword": "대표 키워드",
    "options": ["하위 키워드1", "하위 키워드2"]
  }
]

Requirements:
- Output should be in Korean.
"""

    @staticmethod
    def build_place_prompt() -> str:
        return """
We will classify the keywords into two types: locations and categories.

Objective:
- Separate location-related keywords as top-level 'location' keywords.
- Classify related types (e.g. business types like cafes, bakeries, etc.) as sub-level 'category' keywords.

Instructions:
1. Identify location keywords such as neighborhood or district names (e.g. '성수동', '강남역') and place them in the 'location' list.
2. Identify keywords related to business types or categories (e.g. '카페', '디저트', '베이커리') and place them in the 'category' list.
3. Remove any duplicates.
4. Output must be in Korean.

Output Format:
{
    "location": ["location1", "location2", ...],
    "category": ["category1", "category2", ...]
}
"""

    @staticmethod
    def convert_place_keywords_to_result(data: dict) -> list:
        location_list = data.get("location", [])
        category_list = data.get("category", [])
        return [{"keyword": location, "options": category_list} for location in location_list]

    async def _send_to_gpt(self, dto: MergeKeywordsDTO):
        # DTO 리스트를 JSON 문자열로 변환
        text = dto.keywords.__str__()
        response = self.client.responses.create(
            model="gpt-4.1",
            input=[
                {
                    "role": "system",
                    "content": dto.prompt,
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
        self.print_total_tokens("키워드 점수", response)
        pprint.pprint(response)
        keyword = json.loads(response.model_dump()["output"][0]["content"][0]["text"])

        return keyword

    @classmethod
    async def get_shopping_keywords(cls, keywords: List[str]):
        print(keywords)

        prompt = cls.build_shopping_prompt()
        dto = MergeKeywordsDTO(prompt=prompt, keywords=keywords)
        return await cls()._send_to_gpt(dto)

    @classmethod
    async def get_place_keywords(cls, keywords: List[str]):
        print(keywords)
        prompt = cls.build_place_prompt()
        dto = MergeKeywordsDTO(prompt=prompt, keywords=keywords)
        data = await cls()._send_to_gpt(dto)
        return cls.convert_place_keywords_to_result(data)
