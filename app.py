"""
AZURE AI STORE
Flask + Bootstrap + Azure App Configuration + Azure AI
Demo local para YouTube.
"""

from pathlib import Path

from flask import Flask, jsonify, render_template
from azure.appconfiguration.provider import load
from openai import OpenAI


app = Flask(__name__)


# ================================================================
# DEMO LOCAL - COPIAR Y PEGAR DESDE AZURE
# ================================================================
# App Configuration:
# Azure Portal -> App Configuration -> Access keys
# Copia el Connection string y pégalo abajo.
#
# Azure AI Foundry:
# Proyecto -> modelo/deployment -> Use your model in code
# Copia Endpoint y Key y pégalos abajo.
#
# Este formato es deliberadamente sencillo para la demo de YouTube.
# Para producción, no guardes secretos directamente en el código.
# ================================================================

APP_CONFIG_CONNECTION_STRING = ""

AZURE_AI_ENDPOINT = ""
0
AZURE_OPENAI_API_KEY = ""


app_config = None

PRODUCTS_FILE = (
    Path(__file__).resolve().parent / "products.txt"
)


def load_products():
    loaded_products = []

    try:
        with PRODUCTS_FILE.open("r", encoding="utf-8") as file:

            for line_number, line in enumerate(file, start=1):

                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                if line == "name|price|icon":
                    continue

                parts = line.split("|", 2)

                if len(parts) != 3:
                    print(
                        f"Advertencia: línea {line_number} inválida."
                    )
                    continue

                name = parts[0].strip()
                price_text = parts[1].strip()
                icon = parts[2].strip()

                try:
                    price = float(price_text)
                except ValueError:
                    print(
                        f"Advertencia: precio inválido "
                        f"en línea {line_number}."
                    )
                    continue

                loaded_products.append(
                    {
                        "name": name,
                        "price": price,
                        "icon": icon,
                    }
                )

        print(
            f"{len(loaded_products)} productos "
            f"cargados desde products.txt."
        )

        return loaded_products

    except FileNotFoundError:

        print(
            f"ERROR: No se encontró {PRODUCTS_FILE}"
        )

        return []

    except Exception as error:

        print(
            f"ERROR leyendo products.txt: {error}"
        )

        return []


products = load_products()


def initialize_app_configuration():

    global app_config

    try:

        print(
            "Conectando con Azure App Configuration..."
        )

        app_config = load(

            connection_string=(
                APP_CONFIG_CONNECTION_STRING.strip()
            ),

            refresh_enabled=True,

            # Esto es el refresh del provider,
            # NO el intervalo de la recomendación AI.
            refresh_interval=5,

        )

        print(
            "Azure App Configuration "
            "conectado correctamente."
        )

    except Exception as error:

        print(
            "ERROR conectando con "
            f"Azure App Configuration: {error}"
        )


def refresh_configuration():

    if app_config is None:
        return

    try:

        app_config.refresh()

    except Exception as error:

        print(
            "Error actualizando "
            f"App Configuration: {error}"
        )


def get_config(
    key,
    default=None
):

    if app_config is None:
        return default

    return app_config.get(
        key,
        default
    )


def get_boolean(
    key,
    default=False
):

    value = get_config(
        key,
        str(default)
    )

    return (
        str(value).lower() == "true"
    )


def get_integer(
    key,
    default=0
):

    value = get_config(
        key,
        str(default)
    )

    try:

        return int(value)

    except (
        TypeError,
        ValueError
    ):

        return default


def get_runtime_configuration():

    refresh_configuration()

    refresh_seconds = get_integer(
        "AI_Refresh_seconds",
        15
    )

    # Protección mínima.
    refresh_seconds = max(
        refresh_seconds,
        5
    )

    return {

        "store_name": get_config(
            "Store_name",
            "Azure Store"
        ),

        "discount_enabled": get_boolean(
            "Discount",
            False
        ),

        "products_amount": max(
            get_integer(
                "Display_products_amount",
                5
            ),
            0
        ),

        "ai_enabled": get_boolean(
            "AI_enabled",
            False
        ),

        "ai_model": get_config(
            "AI_Model",
            "gpt-4.1-mini"
        ),

        "ai_prompt": get_config(
            "AI_Welcome_Prompt",
            (
                "Genera un mensaje corto y atractivo "
                "de bienvenida para los clientes he invitalos a ver las ofertas INCREÍBLES "
                "de nuestra tienda tecnológica, agrega emojis y no uses más de 50 palabras."
            )
        ),

        "recommendation_enabled": get_boolean(
            "AI_Recommendation_Enabled",
            True
        ),

        # Fuente de verdad para el intervalo
        # de recomendación.
        "refresh_seconds": refresh_seconds,
    }


def create_ai_client():

    if not AZURE_OPENAI_API_KEY:
        return None

    return OpenAI(

        api_key=(
            AZURE_OPENAI_API_KEY.strip()
        ),

        base_url=(
            AZURE_AI_ENDPOINT.strip()
        ),

        timeout=20.0,

        max_retries=2,

    )


def generate_ai_welcome(
    store_name,
    model,
    prompt
):

    client = create_ai_client()

    if client is None:
        return None

    final_prompt = f"""
{prompt}

Nombre de la tienda:

{store_name}

Genera solamente el mensaje de bienvenida.

Máximo 30 palabras.

No utilices emojis.
"""

    try:

        response = client.responses.create(

            model=model,

            input=final_prompt,

            max_output_tokens=80,

        )

        return response.output_text.strip()

    except Exception as error:

        print(
            "ERROR generando mensaje "
            f"de bienvenida: {error}"
        )

        return None


def generate_product_recommendation(
    store_name,
    model,
    current_products,
    discount_enabled
):

    client = create_ai_client()

    if client is None:
        return None

    product_information = []

    for product in current_products:

        if discount_enabled:

            discount_price = round(
                product["price"] * 0.80,
                2
            )

            product_information.append(

                f"- {product['name']} | "
                f"Precio original: "
                f"${product['price']:.2f} | "
                f"Precio con descuento: "
                f"${discount_price:.2f}"

            )

        else:

            product_information.append(

                f"- {product['name']} | "
                f"Precio: "
                f"${product['price']:.2f}"

            )

    inventory = "\n".join(
        product_information
    )

    prompt = f"""
Eres el asistente inteligente de una tienda tecnológica
llamada "{store_name}".

Estos son los productos disponibles actualmente:

{inventory}

Analiza el inventario y recomienda DOS o TRES productos.

La recomendación debe basarse únicamente en los productos
proporcionados.

Si existen descuentos, puedes utilizarlos como criterio.

Explica brevemente por qué cada producto puede ser una buena opción.

No inventes características técnicas que no aparecen
en la información proporcionada.

NO USES ASTERISCOS.
INCLUYE EMOJIS.

Máximo 120 palabras.
"""

    try:

        response = client.responses.create(

            model=model,

            input=prompt,

            max_output_tokens=180,

        )

        return response.output_text.strip()

    except Exception as error:

        print(
            f"ERROR generando recomendación: {error}"
        )

        return None


@app.route("/")
def home():

    config = get_runtime_configuration()

    display_products = [

        product.copy()

        for product in products[
            :config["products_amount"]
        ]

    ]

    for product in display_products:

        product["discount_price"] = None

        if config["discount_enabled"]:

            product["discount_price"] = round(

                product["price"] * 0.80,

                2

            )

    ai_message = None

    if config["ai_enabled"]:

        ai_message = generate_ai_welcome(

            config["store_name"],

            config["ai_model"],

            config["ai_prompt"]

        )

    return render_template(

        "index.html",

        store_name=config["store_name"],

        products=display_products,

        discount=config["discount_enabled"],

        ai_enabled=config["ai_enabled"],

        ai_message=ai_message,

        recommendation_enabled=(
            config["recommendation_enabled"]
        ),

        refresh_seconds=config["refresh_seconds"],

    )


@app.route("/api/recommendation")
def recommendation():

    config = get_runtime_configuration()

    if (
        not config["ai_enabled"]
        or not config["recommendation_enabled"]
    ):

        return jsonify({

            "enabled": False,

            "message": None,

            "refresh_seconds": (
                config["refresh_seconds"]
            ),

        })

    current_products = [

        product.copy()

        for product in products[
            :config["products_amount"]
        ]

    ]

    message = generate_product_recommendation(

        config["store_name"],

        config["ai_model"],

        current_products,

        config["discount_enabled"],

    )

    return jsonify({

        "enabled": True,

        "message": message,

        # Este valor viene de Azure App Configuration.
        "refresh_seconds": (
            config["refresh_seconds"]
        ),

    })


initialize_app_configuration()


if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=True,

    )
