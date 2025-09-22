from time import sleep
from flask import Flask, jsonify, render_template, request,Response
from dotenv import load_dotenv
import google.generativeai as genai
import os
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)

api_key = os.getenv("GEMINI_SECRET_KEY")
# Use a fully-qualified model name from the available models list.
# Updated to a supported model discovered via `list_models.py`.
model = "models/gemini-1.5-flash"
genai.configure(api_key=api_key)


app = Flask(__name__)
app.secret_key = "Pachyderm_Secret_Key"

def bot(prompt):
    max_intentos=1
    repeticion=0
    while True:
        try:
            prompt_sistema=f"""Eres un chatbot llamado Pachyderm, No debes
            responder preguntas que no sean referentes a los datos del ecommerce 
            informado. que ayuda a los usuarios a encontrar información relevante y precisa."""
            configuracion_modelo = {
                "temperature": 0.2,
                "max_output_tokens": 8192,

            }
            llm = genai.GenerativeModel(
                model_name=model,
                system_instruction=prompt_sistema,
                generation_config=configuracion_modelo
            )
            respuesta = llm.generate_content(prompt)
            # `generate_content` puede devolver distintos shapes según versión.
            # Intentamos extraer texto de manera robusta.
            # 1) Atributo `text` directo
            if hasattr(respuesta, 'text') and respuesta.text:
                return respuesta.text

            # 2) `candidates` iterable con posibles contenidos
            if hasattr(respuesta, 'candidates'):
                parts = []
                try:
                    for c in respuesta.candidates:
                        # varios nombres posibles en candidatos
                        if hasattr(c, 'text') and c.text:
                            parts.append(c.text)
                        elif hasattr(c, 'content') and c.content:
                            parts.append(str(c.content))
                        elif hasattr(c, 'output') and c.output:
                            parts.append(str(c.output))
                        else:
                            parts.append(str(c))
                except Exception:
                    logging.exception('Error parsing candidates')
                if parts:
                    return "\n\n".join(parts)

            # 3) Intento general: convertir a string
            try:
                return str(respuesta)
            except Exception:
                logging.exception('Fallo al convertir respuesta a str')
                return ""
        
        except Exception as e:
            # Loggear la excepción completa para depuración
            import traceback
            logging.exception("Error al generar contenido con la API de Gemini: %s", e)
            # Si es un error de cuota (ResourceExhausted) o similar, propagar la excepción
            try:
                from google.api_core.exceptions import ResourceExhausted, NotFound, PermissionDenied, InvalidArgument
                if isinstance(e, ResourceExhausted):
                    # Quota agotada: devolver información para manejo en caller
                    raise
                if isinstance(e, NotFound):
                    raise
                if isinstance(e, PermissionDenied):
                    raise
            except Exception:
                # Si google.api_core no está disponible por alguna razón, continuar con fallback
                logging.debug('google.api_core.exceptions no disponible o excepción no categorizable')

            repeticion += 1
            if repeticion >= max_intentos:
                # Devolver None para indicar al caller que hubo fallo crítico
                return None
            # Espera breve antes de reintentar
            sleep(1)
            

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True)
    if not data or 'msg' not in data:
        return Response("Missing 'msg' in request", status=400)

    prompt = data['msg']
    try:
        respuesta = bot(prompt)
    except Exception as e:
        # Manejar errores específicos de la librería google.api_core
        try:
            from google.api_core.exceptions import ResourceExhausted, NotFound, PermissionDenied
            if isinstance(e, ResourceExhausted):
                logging.warning('Quota exhausted when calling model: %s', e)
                # Fallback simulado para desarrollo: devolver respuesta local y 200
                fallback = f"[SIMULATED RESPONSE - quota exceeded] Puedo ayudarte con: {prompt}"
                return Response(fallback, mimetype='text/plain', status=200)
            if isinstance(e, NotFound):
                return Response('Modelo no encontrado. Revisa la configuración del model.', status=404)
            if isinstance(e, PermissionDenied):
                return Response('Permisos denegados. Revisa tu API key/billing.', status=401)
        except Exception:
            logging.exception('No se pudieron evaluar excepciones específicas de google.api_core')
        logging.exception('Error inesperado al llamar a bot()')
        return Response('Error interno al procesar la solicitud', status=500)

    # Asegurar que siempre devolvemos texto (no None)
    if respuesta is None or respuesta == "":
        # Fallback: devolver respuesta simulada para no romper la UI en desarrollo
        fallback = f"[SIMULATED RESPONSE] Puedo ayudarte con: {prompt}"
        return Response(fallback, mimetype='text/plain', status=200)

    return Response(str(respuesta), mimetype='text/plain')



if __name__ == "__main__":
    app.run(debug=True)