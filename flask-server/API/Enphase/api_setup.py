import requests
from base64 import b64encode
from requests.auth import HTTPBasicAuth
import json
import pathlib


def get_params(api=1):
    json_file = f'run_params_{api}.json'
    json_path = pathlib.Path(__file__).parents[0] / pathlib.Path(json_file)
    with open(json_path, 'r') as json_file:
        params = json.load(json_file)

    if params['API_Count'] > 960 or params['Operational'] is False or params['Consecutive_Failures'] > 9:
        params, json_path, json_file = get_params(api=api + 1)

    return params, json_path, json_file


def reset_api_count():
    apis = [1, 2, 3, 4]
    for api in apis:
        json_file = f'run_params_{api}.json'
        json_path = pathlib.Path(__file__).parents[0] / pathlib.Path(json_file)
        with open(json_path, 'r') as json_file:
            params = json.load(json_file)

        params['API_Count'] = 0
        params['Operational'] = True
        params['Consecutive_Failures'] = 0

        with open(json_path, 'w') as json_file:
            json.dump(params, json_file, indent=4)


def Website_For_Authentication_Code():
    """Run this to get the authorization website which you need t send to system owner aka.Kashif to get
    authorization code"""
    params, json_path, json_file = get_params()
    print(json_file)

    client_id = params['client_id']
    authorization_url = f"https://api.enphaseenergy.com/oauth/authorize?response_type=code&client_id={client_id}&redirect_uri=https://api.enphaseenergy.com/oauth/redirect_uri"

    # todo: Add a input functionality that wll show on react
    print(f"Please authorize the application by visiting the following URL:\n{authorization_url}")

    params['authorization_url'] = authorization_url
    with open(json_path, 'w') as json_file:
        json.dump(params, json_file, indent=4)


def get_Access_Refresh_Token_From_Authorization_Code():
    """After filling out the info below you should be able to see the access and refresh token in
    the command output. Keep these safe as they are used in later api calls """
    params, json_path, json_file = get_params()

    client_id = params['client_id']
    client_secret = params['client_secret']
    redirect_uri = params['redirect_uri']
    authorization_code = params['authorization_code']
    token_endpoint = params['token_endpoint']

    # Set up headers with basic authorization
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    # Set up data for the token request
    data = {
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri,
        'code': authorization_code,
    }

    # Make the POST request to generate the token
    response = requests.post(
        token_endpoint,
        headers=headers,
        auth=HTTPBasicAuth(client_id, client_secret),
        data=data
    )

    params['API_Count'] += 1

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the JSON response
        token_data = response.json()

        print('Updated Access and Refresh Tokens')

        params['Operational'] = True
        params['access_token'] = token_data.get("access_token")
        params['refresh_token'] = token_data.get("refresh_token")
        params['Consecutive_Failures'] = 0
    else:
        # Print an error message if the request was not successful
        print(response)
        print(f"Error Auth Token: {response.text}")
        if response.status_code != 401 and response.status_code != 429: # 401: not authorized, 429: too many requests
            params['Operational'] = False
        params['Consecutive_Failures'] = params['Consecutive_Failures'] + 1

    with open(json_path, 'w') as json_file:
        json.dump(params, json_file, indent=4)


def Generate_New_Access_Token_From_Refresh_Token():
    params, json_path, json_file = get_params()

    client_id = params['client_id']
    client_secret = params['client_secret']
    refresh_token = params['refresh_token']

    auth_header = b64encode(f"{client_id}:{client_secret}".encode()).decode()

    token_endpoint = "https://api.enphaseenergy.com/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    response = requests.post(token_endpoint, data=payload, headers=headers)

    params['API_Count'] += 1

    if response.status_code == 200:
        token_data = response.json()
        params['access_token'] = token_data.get("access_token")
        params['refresh_token'] = token_data.get("refresh_token")

        print("Updated New Access and Refresh Tokens")

        params['Operational'] = True
        # not putting consecutive failures since this works even when api limit has been reached

    else:
        print(f"Error Refresh and Access: {response.status_code} - {response.text}")
        if response.status_code != 401 and response.status_code != 429: # 401: not authorized, 429: too many requests
            params['Operational'] = False

    with open(json_path, 'w') as json_file:
        json.dump(params, json_file, indent=4)


if __name__ == "__main__":
    # Website_For_Authentication_Code()
    # get_Access_Refresh_Token_From_Authorization_Code()
    # Generate_New_Access_Token_From_Refresh_Token()
    # params, json_path, json_file = get_params()
    # print(json_file)
    get_Access_Refresh_Token_From_Authorization_Code()

