"""Ulauncher extension main  class"""

import logging
import requests
import re
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction

LOGGER = logging.getLogger(__name__)

ipdata_api_url = 'https://api.ipdata.co/'
ip_regex = r"((^\s*((([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))\s*$)|(^\s*((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))(%.+)?\s*$))"


class IPLookupExtension(Extension):
    """ Main extension class """

    def __init__(self):
        """ init method """
        super(IPLookupExtension, self).__init__()
        LOGGER.info("Initialsing IP Lookup extension")
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
    
    def lookup(self, ip = None):
        params = {
            "api-key": self.preferences['ipl_api_key'],
        }

        url = ipdata_api_url

        if ip != "?":
            url = "%s%s" % (ipdata_api_url, ip)
        
        r = requests.get(url, params = params, timeout = 3)
        
        if r.status_code == 200:
            response = r.json()

            out_arr = {}

            out_arr["IP"] = response["ip"]
            location = [response["city"], response["country_name"]]

            location = ", ".join(filter(None, location))
            location = location + " (%s)" % response["country_code"] if response["country_code"] != None else ""
            out_arr["Location"] = location
            out_arr["Coordiates"] = "%s, %s" % (response["latitude"], response["longitude"])
            out_arr["Calling code"] = response["calling_code"]
            out_arr["Languages"] = ", ".join(obj["name"] for obj in response["languages"])
            out_arr["ISP"] = response["organisation"]
            out_arr["Currency"] = "%s (%s)" % (response["currency"]["name"], response["currency"]["code"])

            return out_arr
        else:
            return {}


class KeywordQueryEventListener(EventListener):
    """ Handles Keyboard input """

    def on_event(self, event, extension):
        """ Handles the event """
        items = []

        query = event.get_argument() or ""


        matches = re.findall(ip_regex, query, re.IGNORECASE)

        if query != "?" and not matches:
            items.append(ExtensionResultItem(icon='images/icon.png',
                                             name='Keep typing your IP...',
                                             description='Type "?" for see your own IP or any IP v4/v6 to see details',
                                             highlightable=False,
                                             on_enter=HideWindowAction()))

            return RenderResultListAction(items)

        try:
            response_list = extension.lookup(query)

            if len(response_list) > 0:
                for key in response_list:
                    items.append(ExtensionResultItem(icon='images/icon.png',
                                                    name=response_list[key],
                                                    description=key,
                                                    highlightable=False,
                                                    on_enter=CopyToClipboardAction(response_list[key])))
            return RenderResultListAction(items)

        except LookupException as e:
            items.append(ExtensionResultItem(icon='images/icon.png',
                                             name='An error ocurred during the lookup process',
                                             description=e.message,
                                             highlightable=False,
                                             on_enter=HideWindowAction()))

            return RenderResultListAction(items)


class LookupException(Exception):
    """ Exception thrown when there was an error calling the lookup API """
    pass


if __name__ == '__main__':
    IPLookupExtension().run()
