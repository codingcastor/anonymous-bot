import os
from openai import OpenAI

def get_openai_client():
    """Get an authenticated OpenAI client instance"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)

async def generate_response(prompt, max_tokens=150):
    """Generate a response using GPT-4-mini
    
    Args:
        prompt (str): The input prompt to send to GPT
        max_tokens (int): Maximum length of the response
        
    Returns:
        str: The generated response text
    """
    client = get_openai_client()
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")
