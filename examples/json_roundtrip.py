import json
product = {"name": "Notebook", "active": True}
text = json.dumps(product)
restored = json.loads(text)
print(text)
print(restored["active"])
