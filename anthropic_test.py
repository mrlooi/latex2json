# mine 
API_KEY = "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"
# SZ
# API_KEY = "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"

import json
import anthropic
# Create an instance of the Anthropics API client
client = anthropic.Anthropic(api_key=API_KEY)

# Add json import
import json

# Read the paper data
with open('data/res.json', 'r') as f:
    paper_data = json.load(f)

system_prompt = """
You are a research assistant helping advanced users read scientific papers much faster.  
Use the provided paper content to answer questions accurately. But also keep concise.
Do not repeat verbatim the outputs of the paper, use your insights. 
Always ground your answers in the paper's content.
That said, you can provide suggestions and ideas from other papers you know of to make useful connections.
"""

user_question = "which papers is biblio is top 3 for rec reading"

user_prompt = """
<paper_content>
{paper_content}
</paper_content>

<user_question>
{user_question}
</user_question>
""".format(paper_content=paper_data, user_question=user_question)

# assistant_prompt = """
# I'll help you understand this research paper by breaking it down into key components.

# Let's start with analyzing the main aspects of:
# - Research objective
# - Methodology
# - Key findings
# - Implications

# Please feel free to ask specific questions about any part of the paper.
# """

# MODEL = "claude-3-sonnet-20240229"
# MODEL = "claude-3-5-sonnet-20241022"
MODEL = "claude-3-5-sonnet-20240620"

message = client.messages.create(
    model=MODEL,
    max_tokens=4000,
    temperature=0,
    system=system_prompt,
    messages=[
        {
            "role": "user",
            "content": user_prompt
        }
    ]
)

a = message.content 
print(a)