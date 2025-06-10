def get_client_ip(request):
    """Get IP address from request headers."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_location_from_ip(ip):
    """Get approximate location from IP using ipapi.co"""
    try:
        response = requests.get(f'https://ipapi.co/{ip}/json/')
        data = response.json()
        return f"{data.get('city')}, {data.get('region')}, {data.get('country_name')}"
    except:
        return "Unknown"

def get_geo_data(ip):
    """Fetch geo data for the IP (example using ipapi.co)"""
    try:
        response = requests.get(f"https://ipapi.co/{ip}/json/")
        if response.status_code == 200:
            data = response.json()
            return {
                'city': data.get('city'),
                'region': data.get('region'),
                'country': data.get('country_name'),
                'org': data.get('org'),
            }
    except:
        pass
    return {}

import httpagentparser

def get_device_info(request):
    agent = request.META.get('HTTP_USER_AGENT', '')
    parsed = httpagentparser.detect(agent)
    
    os = parsed.get('os', {}).get('name', 'Unknown')
    os_version = parsed.get('os', {}).get('version', '')
    browser = parsed.get('browser', {}).get('name', 'Unknown')
    browser_version = parsed.get('browser', {}).get('version', '')

    return f"{os} {os_version} — {browser} {browser_version}"
