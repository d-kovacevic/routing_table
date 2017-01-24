#!/usr/bin/python
__author__ = 'd-kovacevic'
import re
import datetime
import time
from helper_classes import RoutingTable
from helper_classes import connect_device
from my_logger import logger


def check_parsed_routes(tables):
    for table in tables:
        if table.get_nbr_parsed_rts() != table.get_nbr_act_rts():
            logger.error("Parse route miss match [ " + table.get_tbl_name() + " Active routes = " + str(table.get_nbr_act_rts()) + " Parsed routes = " + str(table.get_nbr_parsed_rts()) + " ]")


def remove_black_lst_tbls(tables):

    black_list_tbls = ["iso.0", "mpls.0", "l2circuit.0", "inet.1", "inet6.1", "VULA-LWAP.inet.1"]
    tbls_to_rmv = []
    for table in tables:
        if table.get_tbl_name() in black_list_tbls:
            tbls_to_rmv.append(table)

    for table in tbls_to_rmv:
        tables.remove(table)


def parse_routing_table(file_name):

    input_file = open(file_name, 'r')

    match_tbl_hdr1 = "(\w+.*): (\d+) destinations, (\d+) routes \((\d+) active, (\d+) holddown, (\d+) hidden\)"
    match_ipv4 = "\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}"
    match_ipv4_nosub = "\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    match_ipv6 = "[\.:abcdefABCDEF\d]+/\d{1,3}"
    match_bgpl3vpn = "(" + match_ipv4_nosub + "):(\d+):(" + match_ipv4 + ")|(\d+):(\d+):(" + match_ipv4 + ")"
    match_bgpl3vpn_inet6 = "(" + match_ipv4_nosub + "):(\d+):(" + match_ipv6 + ")|(\d+):(\d+):(" + match_ipv6 + ")"
    match_route = "@"

    tables = []
    current_table = None

    for row in iter(input_file):

        if re.match(match_tbl_hdr1, row):

            parse_table_data = re.search(match_tbl_hdr1, row)
            table_name = parse_table_data.group(1)

            if table_name == "bgp.l3vpn.0" or table_name == "bgp.l3vpn-inet6.0":
                table_type = table_name
            else:
                table_type = ".".join(table_name.split(".")[-2:])

            if table_type == "inet.0" or table_type == "inet.2" or table_type == "inet.3":
                match_route = match_ipv4
            elif table_type == "inet6.0" or table_type == "inet6.3":
                match_route = match_ipv6
            elif table_type == "bgp.l3vpn.0":
                match_route = match_bgpl3vpn
            elif table_type == "bgp.l3vpn-inet6.0":
                match_route = match_bgpl3vpn_inet6
            else:
                #TODO is this ok?
                match_route = "@"

            current_table = RoutingTable(row)
            tables.append(current_table)
        elif re.match("  |\* ", row):
            # remove 2 char spacing in from of every route
            row = row[2:]

            #:TODO Add validation for IPv4 and IPv6 routes
            if re.match(match_route, row):
                current_table.add_route(re.match(match_route, row).group(0))

    remove_black_lst_tbls(tables)

    # Cannot perform this check with bgp received routes
    #check_parsed_routes(tables)

    return tables


def compare_table(src_table, dst_table, reverse=False):
    if reverse:
        message = "Route added: "
    else:
        message = "Route removed: "
    for route in src_table.get_parsed_rts():
        if route not in dst_table.get_parsed_rts():
            logger.info(message + src_table.get_tbl_name() + " => " + route)
    return


def compare_routing_tables_direction(src_routing_table, dst_routing_table, reverse=False):
    if reverse:
        message = "Table added: "
    else:
        message = "Table removed: "
    for src_table in src_routing_table:
        found_table = False
        for dst_table in dst_routing_table:
            if src_table.get_tbl_name() == dst_table.get_tbl_name():
                compare_table(src_table, dst_table, reverse)
                found_table = True
        if not found_table:
            logger.info(message + src_table.get_tbl_name())


def compare_routing_tables(src_rt_tbl, dst_rt_tbl):
    compare_routing_tables_direction(src_rt_tbl, dst_rt_tbl, reverse=False)
    compare_routing_tables_direction(dst_rt_tbl, src_rt_tbl, reverse=True)
    return


def compare(src_file, dst_file):
    src_routing_table = parse_routing_table(src_file)
    dst_routing_table = parse_routing_table(dst_file)
    compare_routing_tables(src_routing_table, dst_routing_table)


def copy_file(src_file, dst_file):
        with open(src_file) as f:
            with open(dst_file, "w") as f1:
                for line in f:
                    f1.write(line)


def monitor_routes(device):
    try:
        now = datetime.datetime.now()

        src_file = connect_device(device, "show route", device + "_src_" + now.strftime("%Y%m%d_%H%M%S"))
        if src_file == "":
            raise Exception("Error while executing connect_device: " + device)

        dst_file = connect_device(device, "show route", device + "_dst_" + now.strftime("%Y%m%d_%H%M%S"))
        if dst_file == "":
            raise Exception("Error while executing connect_device: " + device)

        while True:

            compare(src_file, dst_file)

            copy_file(dst_file, src_file)

            dst_file = connect_device(device, "show route", dst_file)
            if dst_file == "":
                raise Exception("Error while executing connect_device: " + device)

            logger.debug("Sleeping for 10s")
            time.sleep(10)

    except Exception as e:
        logger.error(str(e.message))
        exit(1)
    except KeyboardInterrupt:
        print "\nBye, bye..."
        exit(0)


def main():
    #compare("reference_data/sar10asd2_route_receive-protocol_bgp_217.16.41.244", "reference_data/sar10asd2_route_receive-protocol_bgp_217.16.40.225")
    compare("reference_data/sar10asd2_route_receive-protocol_bgp_217.16.40.225", "reference_data/sar10asd2_route_receive-protocol_bgp_217.16.41.244")
    #monitor_routes("bras05campus")

if __name__ == "__main__":
    main()
