import requests
import urllib3
import json
urllib3.disable_warnings()

def get_system_name_to_uuid_mapping(x_api_key):

    url = <ENTER_URL_HERE>
    headers = {
        "x-api-token":x_api_key,
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200 or response.status_code == 201:
        response_json = json.loads(response.text)

        extracted_data = [{"storage_system_name": item["type"], "storage_system_id": item["storage_system_id"]} for item in response_json["data"]]

        result_json = json.dumps(extracted_data, indent=2)

        return result_json

    else:
        return f"Unable to get the mappings of system names to system uuids: Returned {response.status_code}"


if __name__ == "__main__":
    pass