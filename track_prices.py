import requests, json, os
from datetime import datetime, timedelta

# Usunięto dotenv – używamy zmiennych środowiskowych z GitHub Secrets

STORE = os.getenv("SHOPIFY_STORE")
VERSION = os.getenv("SHOPIFY_API_VERSION")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

HEADERS = {
    "X-Shopify-Access-Token": TOKEN,
    "Content-Type": "application/json"
}

# Pobierz listę produktów (maks 250 na raz)
def get_products():
    url = f"https://{STORE}/admin/api/{VERSION}/products.json?limit=250"
    r = requests.get(url, headers=HEADERS)
    return r.json().get('products', [])

# Pobierz Metafieldy produktu
def get_metafields(product_id):
    url = f"https://{STORE}/admin/api/{VERSION}/products/{product_id}/metafields.json"
    r = requests.get(url, headers=HEADERS)
    return r.json().get('metafields', [])

# Zaktualizuj historię cen i zapisz najniższą z 30 dni
def update_price_history(product_id, price):
    metafields = get_metafields(product_id)
    history_field = next((f for f in metafields if f['namespace'] == 'custom' and f['key'] == 'price_history'), None)

    today = datetime.today().strftime('%Y-%m-%d')
    history = []

    # Wczytaj dotychczasową historię
    if history_field:
        try:
            history = json.loads(history_field['value'])
        except:
            pass
        # Ogranicz do 30 dni
        history = [entry for entry in history if entry['date'] > (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')]

    # Dodaj dzisiejszą cenę
    history.append({"date": today, "price": price})

    # Znajdź najniższą cenę
    lowest_price = min(float(p["price"]) for p in history)

    # Dane do zapisania
    payload_history = {
        "metafield": {
            "namespace": "custom",
            "key": "price_history",
            "type": "json",
            "value": json.dumps(history)
        }
    }

    payload_lowest = {
        "metafield": {
            "namespace": "custom",
            "key": "lowest_price_30_days",
            "type": "single_line_text_field",
            "value": f"{lowest_price:.2f}"
        }
    }

    # Zapisz historię cen (update lub create)
    if history_field:
        metafield_id = history_field["id"]
        requests.put(f"https://{STORE}/admin/api/{VERSION}/metafields/{metafield_id}.json", json=payload_history, headers=HEADERS)
    else:
        requests.post(f"https://{STORE}/admin/api/{VERSION}/products/{product_id}/metafields.json", json=payload_history, headers=HEADERS)

    # Zapisz najniższą cenę
    requests.post(f"https://{STORE}/admin/api/{VERSION}/products/{product_id}/metafields.json", json=payload_lowest, headers=HEADERS)

# Główna funkcja – przechodzi przez produkty
def main():
    products = get_products()
    for product in products:
        try:
            price = product["variants"][0]["price"]
            update_price_history(product["id"], price)
            print(f"✅ {product['title']} – cena: {price}")
        except Exception as e:
            print(f"❌ Błąd dla {product['title']}: {e}")

if __name__ == "__main__":
    main()