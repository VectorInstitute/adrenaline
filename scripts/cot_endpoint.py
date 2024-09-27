import os
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Set up FastAPI
app = FastAPI()

# Set up OpenAI client with custom endpoint
BASE_URL = "http://gpu053:8080/v1"
os.environ["OPENAI_API_KEY"] = "EMPTY"

# Initialize LLM
llm = OpenAI(
    base_url=BASE_URL, model="Llama3-OpenBioLLM-70B", temperature=0.7, max_tokens=1000
)

# Define prompt template for chain of thought
cot_template = """You are a helpful and knowledgeable medical assistant. Provide accurate and concise information about medical conditions and symptoms.

Problem: {query}

Please break down this problem into steps and solve it:

1. Identify the key components of the question.
2. List any relevant medical terms or concepts that need to be explained.
3. Break down the problem into smaller, manageable sub-questions.
4. Answer each sub-question step by step.
5. Synthesize the information to provide a comprehensive answer to the original question.

Let's approach this step-by-step:

"""

cot_prompt = PromptTemplate(input_variables=["query"], template=cot_template)

# Create RunnableSequence
chain = cot_prompt | llm | StrOutputParser()


# Define request model
class Query(BaseModel):
    text: str


# Define endpoint
@app.post("/cot")
async def chain_of_thought(query: Query):
    try:
        result = chain.invoke({"query": query.text})

        return {
            "result": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8015)
