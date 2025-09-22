import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv('GEMINI_SECRET_KEY')
if not api_key:
    print('No GEMINI_SECRET_KEY found in environment')
else:
    genai.configure(api_key=api_key)
    try:
        # Intentar llamar al método de listados de modelos. La API puede exponer "list_models"
        models = None
        if hasattr(genai, 'list_models'):
            models = genai.list_models()
        elif hasattr(genai, 'Models'):
            models = genai.Models.list()
        else:
            print('No direct list_models method found on genai; attempting fallback...')
            try:
                models = genai.get_models()
            except Exception:
                models = None

        if models is None:
            print('No models list obtained. The SDK may not support listing in this version.')
        else:
            print('Models:')
            try:
                # models may be a generator or an iterable from the SDK
                for m in models:
                    print(m)
            except TypeError:
                print(models)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print('Exception while listing models:', e)
