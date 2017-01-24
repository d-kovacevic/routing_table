__author__ = 'd-kovacevic'
import subprocess
import re

from my_logger import logger


class RoutingTable:
    match_tbl_hdr1 = "(\w+.*): (\d+) destinations, (\d+) routes \((\d+) active, (\d+) holddown, (\d+) hidden\)"

    def __init__(self, row):

        parse_table_data = re.search(self.match_tbl_hdr1, row)

        self.table_name = parse_table_data.group(1)
        self.table_destinations = parse_table_data.group(2)
        self.table_routes = parse_table_data.group(3)
        self.table_active = parse_table_data.group(4)
        self.table_holddown = parse_table_data.group(5)
        self.table_hidden = parse_table_data.group(6)

        if self.table_name == "bgp.l3vpn.0" or self.table_name == "bgp.l3vpn-inet6.0":
            self.table_type = self.table_name
        else:
            self.table_type = ".".join(self.table_name.split(".")[-2:])

        self.routes = []

    def add_route(self, route):

        self.routes.append(route)

    def __str__(self):

        return self.table_name

    def get_str_parsed_rts(self):

        str = ""
        for rt in self.routes:
            str += rt + "\n"
        return str

    def get_parsed_rts(self):
        return self.routes

    def get_nbr_parsed_rts(self):
        return len(self.routes)

    def get_nbr_act_rts(self):
        return int(self.table_active)

    def get_tbl_name(self):
        return self.table_name

    def get_tbl_type(self):
        return self.table_type


def connect_device(device, command, output_file, overwrite=True, method="ssk_askpass"):
    return_file = output_file
    cmd_line = "ssh_askpass.sh -q " + device + " '" + command + "' > " + output_file
    if subprocess.call([cmd_line], shell=True) != 0:
        raise Exception("Error while connecting device")
    return return_file

