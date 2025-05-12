from channels.layers import get_channel_layer

def send_sensor_data_to_ws(data):
    channel_layer = get_channel_layer()
    channel_layer.group_send(
        'sensor_data_group',
        {
            'type': 'send_sensor_data',
            'data': data,
        }
    )

def send_alert_to_ws(alert_data):
    channel_layer = get_channel_layer()
    channel_layer.group_send(
        'alert_group',
        {
            'type': 'send_alert',
            'data': alert_data,
        }
    )

def send_recent_route_to_ws(route_data):
    channel_layer = get_channel_layer()
    channel_layer.group_send(
        'recent_route_group',
        {
            'type': 'send_recent_route',
            'data': route_data,
        }
    )
