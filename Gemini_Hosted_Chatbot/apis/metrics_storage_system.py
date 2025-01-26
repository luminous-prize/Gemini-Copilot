import requests
import urllib3
urllib3.disable_warnings()

def get_storage_system_metrics(x_api_key,storage_system_uuid):

    url = <ENTER_URL_HERE>
    headers = {
        "x-api-token":x_api_key,
        "Content-Type": "application/json",
    }
    params = {
        "types": "volume_overall_total_io_rate"
    }
    response = requests.get(url, headers=headers,params=params)
    if response.status_code == 200 or response.status_code == 201:
        return response.text

    else:
        return f"Unable to get metrics details for your storage system: Returned {response.status_code}"


if __name__ == "__main__":
    pass