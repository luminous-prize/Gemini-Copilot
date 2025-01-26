import requests
import urllib3
import json
urllib3.disable_warnings()

def get_x_api_token():

    url = <ENTER_URL_HERE>
    headers = {
        "x-api-key":<ENTER_APIKEY_HERE>,
        "Accept": "application/json",
    }

    response = requests.post(url, headers=headers)

    if response.status_code == 200 or response.status_code == 201:
        print(f"X api token generation: Returned {response.status_code}".center(50,"."))
        response_list = json.loads(response.text)
        x_api_key = response_list["result"]["token"]
        return x_api_key

    else:
        print(f"Here is the outcome : Returned {response.status_code}")
    
    


if __name__ == "__main__":
    x_api_key = get_x_api_token()