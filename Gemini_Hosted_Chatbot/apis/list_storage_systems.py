import requests
import urllib3
urllib3.disable_warnings()

def get_list_storage_systems(x_api_key):

    url = <ENTER_URL_HERE>
    headers = {
        "x-api-token":x_api_key,
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200 or response.status_code == 201:
        return response.text

    else:
        return f"Unable to get the list of all your storage systems: Returned {response.status_code}"


if __name__ == "__main__":
    pass