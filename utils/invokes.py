import requests
import logging

SUPPORTED_HTTP_METHODS = set([
    "GET", "OPTIONS", "HEAD", "POST", "PUT", "PATCH", "DELETE"
])

def invoke_http(url, method='GET', json=None, **kwargs):
    code = 200
    result = {}

    logging.debug(f"Invoking URL: {url} with method: {method} and data: {json}")

    try:
        if method.upper() in SUPPORTED_HTTP_METHODS:
            r = requests.request(method, url, json=json, **kwargs)
        else:
            raise Exception(f"HTTP method {method} unsupported.")
    except Exception as e:
        code = 500
        result = {"code": code, "message": "invocation of service fails: " + url + ". " + str(e)}
    
    if code not in range(200, 300):
        return result

    if r.status_code != requests.codes.ok:
        code = r.status_code
    
    try:
        result = r.json() if len(r.content) > 0 else ""
    except Exception as e:
        code = 500
        result = {"code": code, "message": "Invalid JSON output from service: " + url + ". " + str(e)}

    return result