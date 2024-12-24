import os
from openai import OpenAI

def get_openai_client():
    """Get an authenticated OpenAI client instance"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)

def generate_response(prompt, max_tokens=150):
    """Generate a response using GPT-4o-mini
    
    Args:
        prompt (str): The input prompt to send to GPT
        max_tokens (int): Maximum length of the response
        
    Returns:
        str: The generated response text
    """
    client = get_openai_client()
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "developer", "content": """Ta tâche est d'agir en tant que modérateur de contenu. Analyse le message suivant d'un utilisateur de messagerie et classe le selon les critères suivants :
1 - Inapproprié: insultes, propos discriminatoires, haineux, racistes, sexistes, incitation à des comportements illégaux ou tout autre contenu inapproprié. 
0 - Approprié: Conversation légitime ou cas incertain.
Retourne seulement le numéro correspondant (1 or 0). Toute information supplémentaire entrainerai des pénalités. Assure-toi que ton jugement est constant et sans biais et constant. Raisonne étape par étape pour produire une classification précise.
"""},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")
