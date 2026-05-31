import os
from google import genai

# This automatically checks for the GEMINI_API_KEY environment variable
client = genai.Client()

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Respond with the word "Connected" if you can read this.',
)

print(response.text)