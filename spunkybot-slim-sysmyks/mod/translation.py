import openai
import sys
from unidecode import unidecode

def translate_text(text, target_lang):
    # Initialisation de l'API OpenAI avec votre clé d'API
    client = openai.Client(api_key="")

    # Appel à l'API OpenAI pour la traduction
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Translate to {target_lang}: {text}"}
        ]
    )

    # Récupérer la traduction depuis la réponse de l'API
    translation = response.choices[0].message.content
    
    return translation

# Récupérer les arguments de ligne de commande
target_lang = sys.argv[1]
text_to_translate = ' '.join(sys.argv[2:])

# Appeler la fonction de traduction
translated_text = translate_text(text_to_translate, target_lang)
translated_text = unidecode(translated_text) 
# Afficher le résultat de traduction
print("^8Translation ^7:", translated_text)
