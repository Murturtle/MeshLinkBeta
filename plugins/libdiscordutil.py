import asyncio
import collections
import plugins.libmesh as LibMesh
import plugins.liblogger as logger

_MAX_TRACKED_MESSAGES = 1000
_packet_message_ids = collections.OrderedDict()

def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def _track_message_id(channel_id, packet_id, message_id):
    channel_id = _safe_int(channel_id)
    packet_id = _safe_int(packet_id)
    message_id = _safe_int(message_id)
    if channel_id is None or packet_id is None or message_id is None:
        return
    key = (channel_id, packet_id)
    _packet_message_ids[key] = message_id
    _packet_message_ids.move_to_end(key)
    while len(_packet_message_ids) > _MAX_TRACKED_MESSAGES:
        _packet_message_ids.popitem(last=False)

def _lookup_message_id(channel_id, reply_id):
    channel_id = _safe_int(channel_id)
    reply_id = _safe_int(reply_id)
    if channel_id is None or reply_id is None:
        return None
    return _packet_message_ids.get((channel_id, reply_id))

def genUserName(interface, packet, details=True):

    short = LibMesh.getUserShort(interface, packet)
    long = LibMesh.getUserLong(interface, packet) or ""
    nodeinfo_url = LibMesh.getNodeInfoUrl(interface, packet)
    lat, lon, hasPos = LibMesh.getPosition(interface, packet)

    parts = []
    
    # Build name parts (without backticks yet)
    if details and packet.get("fromId") is not None:
        parts.append(packet['fromId'])
    
    if short:
        parts.append(short)
    
    if long:
        parts.append(long)
    
    # Start with opening backtick and join parts
    result = "`" + " ".join(parts)
    
    # Add hop count (inside code block)
    if "hopLimit" in packet:
        if "hopStart" in packet:
            result += f" {packet['hopStart'] - packet['hopLimit']}/{packet['hopStart']}"
        else:
            result += f" {packet['hopLimit']}"
    
    # Add MQTT indicator
    if "viaMqtt" in packet and str(packet["viaMqtt"]) == "True":
        result += "[MQTT]"
    
    # Close code block
    result += "`"

    # Add URL link
    if nodeinfo_url:
        result += f" [url](<{nodeinfo_url}>)"
    
    # Add map link
    if details and hasPos:
        result += f" [map](<https://www.google.com/maps/search/?api=1&query={lat}%2C{lon}>)"
    
    return result

def send_msg(message,client,config,channel_id=0,packet_id=None,reply_id=None):
    if config["use_discord"]:
        if (client.is_ready()):
            if config.get("secondary_channel_message_ids") and channel_id and channel_id > 0:
                channels = [config["secondary_channel_message_ids"][channel_id-1]]
            else:
                channels = list(config["message_channel_ids"])

            for chan_id in channels:
                channel = client.get_channel(chan_id)
                if channel is None:
                    continue

                async def _send_to_channel(ch, ch_id):
                    target_id = _lookup_message_id(ch_id, reply_id)
                    if target_id is not None:
                        try:
                            target = await ch.fetch_message(target_id)
                            sent = await target.reply(message, mention_author=False)
                        except Exception:
                            sent = await ch.send(message)
                    else:
                        sent = await ch.send(message)

                    _track_message_id(ch_id, packet_id, sent.id)

                asyncio.run_coroutine_threadsafe(_send_to_channel(channel, chan_id), client.loop)
        else:
            logger.warn("Tried to send but Discord client not ready yet")

def send_info(message,client,config):
    if config["use_discord"]:
        if (client.is_ready()):
            for i in config["info_channel_ids"]:
                asyncio.run_coroutine_threadsafe(client.get_channel(i).send(message),client.loop)

        else:
            logger.warn("Tried to send info but Discord client not ready yet")

# ============================================================================
# Discord Message Formatting Functions
# ============================================================================

def format_text_message(interface, packet, config):

    username = genUserName(interface, packet, details=False)
    text = packet["decoded"]["text"]
    message = f"{username} >> {text}"
    
    if config["ping_on_messages"]:
        message += f" ||{config['message_role']}||"
    
    return message

def format_encrypted_message(interface, packet):

    username = genUserName(interface, packet)
    return f"{username} >> encrypted/failed"

def format_packet_info(interface, packet, portnum):

    username = genUserName(interface, packet)
    return f"{username} >> {portnum}"

def format_system_message(message, is_header=False):

    if is_header:
        return f"# {message}"
    return message

def format_command_response(response):

    return f"`MeshLink` >> {response}"