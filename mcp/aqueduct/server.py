from fastmcp import FastMCP, Context
import requests
import json
import os
import typing as t
from urllib.parse import urlencode
mcp = FastMCP("Demo 🚀")

ACCESS_TOKEN = None
# ID_TOKEN = None
# REFRESH_TOKEN = None


def _get_token():
    global ACCESS_TOKEN
    
    if ACCESS_TOKEN:
        return ACCESS_TOKEN
    
    # Get configuration from environment variables
    region = os.environ.get('COGNITO_REGION', 'us-east-1')
    client_id = os.environ.get('COGNITO_CLIENT_ID','1rb6ljn7mvb64hc0a7n8p11s' )
    username = os.environ.get('USERNAME')
    password = os.environ.get('PASSWORD')
    
    # Validate required environment variables
    if not client_id:
        raise ValueError("COGNITO_CLIENT_ID environment variable is required")
    if not username:
        raise ValueError("USERNAME environment variable is required")
    if not password:
        raise ValueError("PASSWORD environment variable is required")

    url = f'https://cognito-idp.{region}.amazonaws.com/'
    headers = {
        'Content-Type': 'application/x-amz-json-1.1',
        'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth'
    }

    payload = {
        'AuthFlow': 'USER_PASSWORD_AUTH',
        'AuthParameters': {
            'USERNAME': username,
            'PASSWORD': password
        },
        'ClientId': client_id
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    auth_result = response.json().get('AuthenticationResult', {})

    id_token = auth_result.get('IdToken')
    #access_token = auth_result.get('AccessToken')
    # REFRESH_TOKEN = auth_result.get('RefreshToken')
    
    # Update the global variable
    ACCESS_TOKEN = id_token
    
    return ACCESS_TOKEN

EVENTS_API_BASE = "https://n55z1gf28h.execute-api.us-east-1.amazonaws.com/prod"
ENTITIES_API_BASE = "https://rodw7i01t3.execute-api.us-east-1.amazonaws.com/prod"
def _call_events_api(path: str, params: dict, fetch_all: bool,ctx: Context) -> dict:
    """
    Low-level helper: calls the Events API once or keeps following next_token when fetch_all=True.
    Returns a dict with 'items' (list) and 'next_token' (str|None).
    """
    token = _get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    all_items: t.List[dict] = []
    next_token = params.get("next_token")

    while True:
        q = {k: v for k, v in params.items() if v is not None}
        if next_token:
            q["next_token"] = next_token

        url = f"{EVENTS_API_BASE}{path}"
        if q:
            url += f"?{urlencode(q)}"
            

        resp = requests.get(url, headers=headers, timeout=30)
 
        resp.raise_for_status()
        data = resp.json()

        # Adjust these keys to whatever your API actually returns
        items = data.get("data") or data.get("Events") or data.get("results") or []
        all_items.extend(items)

        next_token = data.get("next_token")
        if not (fetch_all and next_token):
            return {"items": all_items, "next_token": next_token}
        
def _call_entities_api(path: str, params: dict, fetch_all: bool,ctx: Context) -> dict:
    """
    Low-level helper: calls the Events API once or keeps following next_token when fetch_all=True.
    Returns a dict with 'items' (list) and 'next_token' (str|None).
    """
    token = _get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    all_items: t.List[dict] = []
    next_token = params.get("next_token")

    while True:
        q = {k: v for k, v in params.items() if v is not None}
        if next_token:
            q["next_token"] = next_token

        url = f"{ENTITIES_API_BASE}{path}"
        if q:
            url += f"?{urlencode(q)}"
            

        resp = requests.get(url, headers=headers, timeout=30)
 
        resp.raise_for_status()
        data = resp.json()

        # Adjust these keys to whatever your API actually returns
        items = data.get("data") or data.get("Events") or data.get("results") or []
        all_items.extend(items)

        next_token = data.get("next_token")
        if not (fetch_all and next_token):
            return {"items": all_items, "next_token": next_token}
        
@mcp.tool
def get_token() -> str:
    """Get token"""
    return _get_token()




@mcp.tool(
    name="get_sensor_events",
    description="Get Triggered Events for a specific sensor. If no query paramaters are provided it returns the last event only", # Custom description
)
def get_sensor_events(
    sensor_id: str,
    ctx: Context,
    start_time: str = "",
    end_time: str = "",
    event_severity: t.Optional[t.Literal["info", "warning", "alert"]] = None,
    event_state: t.Optional[t.Literal["active", "inactive"]] = None,
    sort_key: t.Optional[t.Literal["event_severity"]] = None,
    sort_order: t.Literal["asc", "desc"] = "desc",
    page_size: int = 20,
    next_token: str = "",
    fetch_all: bool = False,
) -> dict:
    """
    Retrieve triggered events for a specific sensor with optional filtering and pagination.
    
    This function fetches sensor events from the Events API with support for various filters
    and pagination. When no filters are provided, it automatically returns only the most
    recent event for optimal performance.
    
    Args:
        sensor_id (str): The unique identifier of the sensor to retrieve events for.
        ctx (Context): The MCP context object for the current request.
        start_time (str, optional): ISO 8601 timestamp to filter events from this time onwards.
            Defaults to empty string (no start time filter).
        end_time (str, optional): ISO 8601 timestamp to filter events up to this time. If start time is given, end time must be given
            Defaults to empty string (no end time filter).
        event_severity (Optional[Literal["info", "warning", "alert"]], optional): 
            Filter events by severity level. Defaults to None (no severity filter).
        event_state (Optional[Literal["active", "inactive"]], optional):
            Filter events by their current state. Defaults to None (no state filter).
        sort_key (Optional[Literal["event_severity"]], optional):
            Secondary field to sort results by. Results are always sorted by Timestamp first, then by this field.
        sort_order (Literal["asc", "desc"], optional):
            Sort order for results. Defaults to "desc" (most recent first).
        page_size (int, optional): Maximum number of events to return per page.
            Defaults to 20. Automatically set to 1 when no filters are applied.
        next_token (str, optional): Pagination token for retrieving subsequent pages.
            Defaults to empty string (start from first page).
        fetch_all (bool, optional): Whether to fetch all available results across pages.
            Defaults to False. Currently not implemented in this function.
    
    Returns:
        dict: When no filters are applied, returns a single event dict (or empty dict if none exist).
              When filters are applied, returns a dict containing:
              - 'items': List of event dictionaries
              - 'next_token': String token for pagination (or None if no more pages)
    
    Note:
        The function automatically detects when no filtering parameters are provided
        and optimizes the request to return only the single most recent event.
        This "no filters" mode is triggered when start_time, end_time, event_severity,
        event_state, and next_token are all empty/None.
    """
    # detect "no filters" → only want the latest event
    # Check if all filter parameters are empty/default (using proper AND logic)
    no_filters = (
        (start_time == "" or start_time is None) and
        (end_time == "" or end_time is None) and
        (event_severity is None) and
        (event_state is None) and
        (next_token == "" or next_token is None)
    )

    # Build params dict only with user-provided values (not defaults)
    params = {}
    
    # Only add parameters if they have non-default values
    if start_time and start_time != "":
        params["start_time"] = start_time
    if end_time and end_time != "":
        params["end_time"] = end_time
    if event_severity is not None:
        params["event_severity"] = event_severity
    if event_state is not None:
        params["event_state"] = event_state
    if sort_key is not None:
        params["sort_key"] = sort_key
    if next_token and next_token != "":
        params["next_token"] = next_token
    
    # Handle sort_order - only add if it's not the default "desc"
    if sort_order != "desc":
        params["sort_order"] = sort_order
    
    # Handle page_size
    if no_filters:
        # For no filters, request only 1 result (most recent)
        params["page_size"] = "1"
    else:
        # Only add page_size if it's different from default
        if page_size != 20:
            params["page_size"] = str(page_size)

    result = _call_events_api(f"/sensors/{sensor_id}", params=params, fetch_all=False, ctx=ctx)
    items = result.get("items", [])

    if no_filters:
        # return just the single most-recent event (or {} if none exist)
        return items[0] if items else {}
    else:
        # return the full payload (with items, next_token, etc)
        return result

@mcp.tool(
    name="get_sensors",
    description="Retrieve a list of all sensors with their complete configuration and status information.", 
)
def get_sensors(
ctx: Context
) -> dict:
    """
    Retrieve a list of all sensors with their complete configuration and status information.
    
    This function fetches all sensors from the Entities API, returning comprehensive data
    about each sensor including device health, threshold evaluations, analytics state,
    and configuration details.
    
    Returns:
        dict: A dictionary containing:
            - 'items': List of sensor dictionaries, each containing:
                - Basic Info:
                    - 'id': Unique sensor identifier
                    - 'Name': Human-readable sensor name
                    - 'Model': Sensor model (e.g., "ERS-CO2")
                    - 'Vendor': Manufacturer name (e.g., "Elsys")
                    - 'DevEui': Device EUI identifier
                    - 'AppEui': Application EUI identifier
                    - 'AppKey': Application key for authentication
                    - 'ModelId': Model identifier UUID
                    - 'CustomerId': Customer identifier
                    - 'OwnerId': Owner identifier
                    - 'AwsRegion': AWS region where sensor is registered
                    - 'RfRegion': RF region configuration (e.g., "US915")
                    - 'Active': Boolean indicating if sensor is active
                    - 'StateVersion': Version number of sensor state
                
                - Status Information:
                    - 'Status': Overall sensor status (e.g., "normal")
                    - 'StatusPriority': Numeric priority of current status
                    - 'StatusDetail': Detailed status description
                    - 'DeviceHealthStatus': Device health status (e.g., "normal")
                    - 'DeviceHealthStatusPriority': Numeric priority of health status
                    - 'DeviceHealthStatusDetail': Detailed health status description
                
                - Threshold Evaluations:
                    - 'ThresholdEvaluations': Dict of threshold evaluation objects keyed by threshold ID:
                        - 'ThresholdId': Unique threshold identifier
                        - 'Name': Human-readable threshold name
                        - 'Metric': Metric being evaluated (e.g., "temperature", "humidity")
                        - 'Condition': Evaluation condition (e.g., "greater_than", "less_than")
                        - 'Status': Current evaluation status
                        - 'TriggeredStatus': Status when threshold is triggered
                        - 'Priority': Numeric priority of threshold
                        - 'EvaluationTime': ISO timestamp of last evaluation
                
                - Device Health Evaluations:
                    - 'DeviceHealthEvaluations': Dict of health evaluation objects keyed by evaluation ID:
                        - Similar structure to ThresholdEvaluations but for device health metrics
                        - Includes metrics like "rssi", "battery_voltage"
                
                - Analytics State:
                    - 'AnalyticsState': Dict of analytics objects keyed by analytics ID:
                        - 'metric_state': Dict of metric values with timestamps:
                            - Each metric contains 'LastValue' and 'LastTimestamp'
                            - Common metrics: "pir_count", "light", "temperature", "humidity"
                        - 'CurrentEventState': Current state ("active" or "inactive")
            
            - 'next_token': Pagination token (null if no more pages)
    
    Example:
        The function returns data in this format:
        {
            "items": [
                {
                    "id": "6c0bae30-ed2a-4c7d-9657-c261de0a982e",
                    "Name": "Sensor1",
                    "Model": "ERS-CO2",
                    "Vendor": "Elsys",
                    "Status": "normal",
                    "ThresholdEvaluations": {
                        "threshold-id": {
                            "Name": "High Temperature",
                            "Metric": "temperature",
                            "Condition": "greater_than",
                            "Priority": 3
                        }
                    },
                    "AnalyticsState": {
                        "analytics-id": {
                            "metric_state": {
                                "temperature": {
                                    "LastValue": 22.5,
                                    "LastTimestamp": "2025-07-29T19:26:35"
                                }
                            },
                            "CurrentEventState": "inactive"
                        }
                    }
                }
            ],
            "next_token": null
        }
    """

    result = _call_entities_api(f"/sensors", params={}, fetch_all=False, ctx=ctx)
    #items = result.get("items", [])

    return result
    
if __name__ == "__main__":
    mcp.run()
