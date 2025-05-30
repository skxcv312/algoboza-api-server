import json
from openai import OpenAI


class YoutubeSummary:
    client = OpenAI()

    @staticmethod
    def print_total_tokens(msg=None, response=None):
        users = response.model_dump().get("usage")
        print(f"{msg} -> total_token : {users.get('total_tokens')}")

    # 관심사 추출
    @classmethod
    async def create_interest_keyword(cls, interest_scores, max_search_keyword: int = 5):
        prompt = f"""
                    You will receive a JSON object of user interest keywords and their scores.
                    Produce search terms that reflect the high interest of your users.
                    Create search terms by grouping similar keywords together.
                    Don't make your search terms into sentences.
                    Do not output more than 5 items. Return only a list of search queries.
                """
        text = interest_scores

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
            text={
                "format": {
                    "type": "json_schema",
                    "name": "user_interest_algorithm",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "keywords": {
                                "type": "array",
                                "description": f"Korean 5-word sentences of search keywords.",
                                "items": {
                                    "type": "string"
                                },
                            },
                        },
                        "required": [
                            "keywords"
                        ],
                        "additionalProperties": False
                    }
                }
            },
            temperature=1.2,
            tools=[],
            max_output_tokens=100,
            top_p=1,
            store=True
        )
        cls.print_total_tokens("유튜브 검색 키워드", response)
        keyword = json.loads(response.model_dump()["output"][0]["content"][0]["text"])
        # print(keyword)
        return keyword.get("keywords")[:max_search_keyword]

    # 영상 내용 요약
    @classmethod
    async def create_summary(cls, description: str):
        if description is None or len(description) < 30:
            return "설명과 자막이 모두 제공되지 않았습니다."
        try:
            prompt_1 = f"""
                        The text received is the text to be summarized. 
                        In your response, only pass the summarized text. 
                        No other format is needed, just return text.
                        and Do not wrap.
                        """

            prompt_2 = """
                        No more than four sentences.
                        If the text is not in Korean, translate it to Korean anyway.
                        """

            response = cls.client.responses.create(
                model="gpt-4.1-mini-2025-04-14",
                input=[
                    {
                        "role": "system",
                        "content": prompt_1,
                    },
                    {
                        "role": "system",
                        "content": prompt_2,
                    },
                    {
                        "role": "user",
                        "content": description,
                    }
                ],
                temperature=1,
                max_output_tokens=400,
                top_p=1,
                store=True
            )

            cls.print_total_tokens("요약", response)
            # pprint(response.model_dump())
            text = response.model_dump()["output"][0]["content"][0]["text"]
            return text.strip()
        except Exception as e:
            print(e)
            return "자막 생성 에러"
