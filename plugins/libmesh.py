import base64
import cfg
from meshtastic.protobuf import mesh_pb2

def getUserLong(interface,packet):
    ret=None
    node = getNode(interface,packet)
    if(node and "user" in node):
        ret = str(node["user"]["longName"])
        return ret

    ret = decimal_to_hex(packet["from"])
    return f"{ret}"

def getUserShort(interface,packet):
    ret=None
    node = getNode(interface,packet)
    if(node and "user" in node):
        ret = str(node["user"]["shortName"])
    return ret

def getNode(interface,packet):
    ret = None
    if(packet["fromId"] in interface.nodes):
        ret = interface.nodes[packet["fromId"]]
    return ret

def decimal_to_hex(decimal_number):
    return f"!{decimal_number:08x}"

def _base64url_encode(data):
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def _set_proto_field(message, field_name, value):
    if field_name in message.DESCRIPTOR.fields_by_name:
        setattr(message, field_name, value)

def _set_proto_enum(message, field_name, value):
    if field_name not in message.DESCRIPTOR.fields_by_name:
        return
    field = message.DESCRIPTOR.fields_by_name[field_name]
    if not field.enum_type:
        return
    if isinstance(value, str):
        enum_value = field.enum_type.values_by_name.get(value)
        if enum_value is None:
            return
        setattr(message, field_name, enum_value.number)
        return
    try:
        setattr(message, field_name, int(value))
    except (TypeError, ValueError):
        return

def _coerce_bytes(value):
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        try:
            return base64.b64decode(value)
        except (ValueError, TypeError):
            return None
    return None

def _coerce_macaddr(value):
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        cleaned = value.replace(":", "").replace("-", "")
        try:
            return bytes.fromhex(cleaned)
        except ValueError:
            return None
    if isinstance(value, (list, tuple)):
        try:
            return bytes(int(b) & 0xFF for b in value)
        except (TypeError, ValueError):
            return None
    return None

def getNodeInfoUrl(interface, packet):
    node = getNode(interface, packet)
    if not isinstance(node, dict):
        return None

    node_data = {}
    if "num" in node and node["num"] is not None:
        node_num = node["num"]
        if isinstance(node_num, str):
            try:
                node_num = int(node_num, 0)
            except ValueError:
                node_num = None
        if node_num is not None:
            node_data["num"] = int(node_num)

    user_data = {}
    user = node.get("user")
    if isinstance(user, dict):
        if user.get("id"):
            user_data["id"] = str(user["id"])
        if user.get("longName"):
            user_data["long_name"] = str(user["longName"])
        if user.get("shortName"):
            user_data["short_name"] = str(user["shortName"])
        if user.get("hwModel") is not None:
            user_data["hw_model"] = user["hwModel"]
        if user.get("macaddr"):
            user_data["macaddr"] = user["macaddr"]
        if user.get("macAddr"):
            user_data["macaddr"] = user["macAddr"]
        if user.get("isLicensed") is not None:
            user_data["is_licensed"] = user["isLicensed"]
        if user.get("role") is not None:
            user_data["role"] = user["role"]
        if user.get("publicKey"):
            user_data["public_key"] = user["publicKey"]
        if user.get("isUnmessagable") is not None:
            user_data["is_unmessagable"] = user["isUnmessagable"]
    if user_data:
        node_data["user"] = user_data

    if not node_data:
        return None

    node_info = mesh_pb2.NodeInfo()
    has_data = False

    if "num" in node_data:
        _set_proto_field(node_info, "num", node_data["num"])
        has_data = True

    if "user" in node_data:
        user = mesh_pb2.User()
        user_fields = node_data["user"]
        if "id" in user_fields:
            _set_proto_field(user, "id", user_fields["id"])
        if "long_name" in user_fields:
            _set_proto_field(user, "long_name", user_fields["long_name"])
        if "short_name" in user_fields:
            _set_proto_field(user, "short_name", user_fields["short_name"])
        if "hw_model" in user_fields:
            _set_proto_enum(user, "hw_model", user_fields["hw_model"])
        if "macaddr" in user_fields:
            macaddr_value = _coerce_macaddr(user_fields["macaddr"])
            if macaddr_value:
                _set_proto_field(user, "macaddr", macaddr_value)
        if "is_licensed" in user_fields:
            _set_proto_field(user, "is_licensed", user_fields["is_licensed"])
        if "role" in user_fields:
            _set_proto_enum(user, "role", user_fields["role"])
        if "public_key" in user_fields:
            public_key_value = _coerce_bytes(user_fields["public_key"])
            if public_key_value:
                _set_proto_field(user, "public_key", public_key_value)
        if "is_unmessagable" in user_fields:
            _set_proto_field(user, "is_unmessagable", user_fields["is_unmessagable"])
        if user.ListFields():
            node_info.user.CopyFrom(user)
            has_data = True

    if not has_data:
        return None

    encoded_data = _base64url_encode(node_info.SerializeToString())
    return f"https://meshtastic.org/v/#{encoded_data}"

def getPosition(interface,packet):
    lat = None
    long = None
    hasPos = False
    
    node = getNode(interface,packet)
    if(packet["fromId"] in interface.nodes):
        if("position" in node):
                if("latitude" in node["position"] and "longitude" in node["position"]):
                    lat = node["position"]["latitude"]
                    long = node["position"]["longitude"]
                    hasPos = True
                     
    return lat, long, hasPos


def sendReply(text, interface, packet, channelIndex = -1):
    ret = packet

    if(channelIndex == -1):
        channelIndex = cfg.config["send_channel_index"]
        
    to = 4294967295 # ^all

    if(packet["to"] == interface.localNode.nodeNum):
         to = packet["from"]
    interface.sendText(text=text,destinationId=to,channelIndex=channelIndex)

    return ret
