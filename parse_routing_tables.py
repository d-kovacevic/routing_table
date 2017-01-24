#!/usr/bin/python
__author__ = 'd-kovacevic'
import re
import datetime
import time
import argparse
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
    match_ipv6_old = "(2|::|ff|fe).*/\d{1,3}"
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
                match_route = "@"

            current_table = RoutingTable(row)
            tables.append(current_table)
        #:TODO Add validation for IPv4 and IPv6 routes
        elif re.match(match_route, row):
            current_table.add_route(re.match(match_route, row).group(0))

    remove_black_lst_tbls(tables)

    return tables


def compare_table(src_table, dst_table, reverse=False):
    if reverse:
        message = "[ ROUTE + ] "
    else:
        message = "[ ROUTE - ] "
    for route in src_table.get_parsed_rts():
        if route not in dst_table.get_parsed_rts():
            logger.info(message + src_table.get_tbl_name() + " => " + route)
    return


def compare_routing_tables_direction(src_routing_table, dst_routing_table, reverse=False):
    if reverse:
        message = "[ TABLE + ] "
    else:
        message = "[ TABLE - ] "
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


def compare(src_file, dst_file, chk_parsed_routes):
    src_routing_table = parse_routing_table(src_file)
    dst_routing_table = parse_routing_table(dst_file)

    if chk_parsed_routes:
        check_parsed_routes(src_routing_table)
        check_parsed_routes(dst_routing_table)

    compare_routing_tables(src_routing_table, dst_routing_table)


def copy_file(src_file, dst_file):
        with open(src_file) as f:
            with open(dst_file, "w") as f1:
                for line in f:
                    f1.write(line)


def monitor_routes(device, command_src, command_dst, chk_parsed_routes, sleep=10, loop=False):
    try:
        now = datetime.datetime.now()

        src_file = connect_device(device, command_src, device + "_src_" + now.strftime("%Y%m%d_%H%M%S"))
        dst_file = connect_device(device, command_dst, device + "_dst_" + now.strftime("%Y%m%d_%H%M%S"))

        while loop:

            compare(src_file, dst_file, chk_parsed_routes)

            copy_file(dst_file, src_file)

            dst_file = connect_device(device, command_dst, dst_file)

            logger.debug("Sleeping for " + str(sleep) + "s")
            time.sleep(sleep)

    except Exception as e:
        logger.error(str(e.message) + "\n" + e.printStackTrace())
        exit(1)
    except KeyboardInterrupt:
        print "\nBye, bye..."
        exit(0)


def compare_routes(device_a, device_b, command_a, command_b, chk_parsed_routes=False):
    try:
        now = datetime.datetime.now()

        src_file = connect_device(device_a, command_a, device_a + "_a_" + now.strftime("%Y%m%d_%H%M%S"))
        dst_file = connect_device(device_b, command_b, device_b + "_b_" + now.strftime("%Y%m%d_%H%M%S"))

        compare(src_file, dst_file, chk_parsed_routes)

    except Exception as e:
        logger.error(str(e.message) + "\n" + e.printStackTrace())
        exit(1)
    except KeyboardInterrupt:
        print "\nBye, bye..."
        exit(0)


def file_compare_routes(file_a, file_b, chk_parsed_routes=False):
    try:

        compare(file_a, file_b, chk_parsed_routes)

    except Exception as e:
        logger.error(str(e.message) + "\n" + e.printStackTrace())
        exit(1)
    except KeyboardInterrupt:
        print "\nBye, bye..."
        exit(0)


def parse_arguments():

    parser = argparse.ArgumentParser(description='Route Parser')

    subparsers = parser.add_subparsers(help='Routing table subparsers')

    parser_monitor = subparsers.add_parser('monitor', help='Set route parser in monitor mode')
    parser_monitor.add_argument('-d', '--device', help='Device', required=True)
    parser_monitor.add_argument('-c', '--command', help='Command used to pull routes', required=True)
    parser_monitor.add_argument('-s', '--sleep', help='Sleep between pooling (seconds)', type=int, required=False)
    parser_monitor.set_defaults(which='monitor')

    parser_compare = subparsers.add_parser('compare', help='Set route parser in compare mode')
    parser_compare.add_argument('-da', '--device-a', help='Device "a"', required=True)
    parser_compare.add_argument('-ca', '--command-a', help='Command used to pull routes', required=True)
    parser_compare.add_argument('-db', '--device-b', help='Device "b"', required=True)
    parser_compare.add_argument('-cb', '--command-b', help='Command used to pull routes', required=True)
    parser_compare.add_argument('-v', '--verify', help='Check if all routes are parsed correctly', action='store_true', required=False)
    parser_compare.set_defaults(which='compare')

    parser_static = subparsers.add_parser('file', help='Set route parser in file compare mode')
    parser_static.add_argument('-fa', '--file-a', help='File "a" that contains routes', required=True)
    parser_static.add_argument('-fb', '--file-b', help='File "b" that contains routes', required=True)
    parser_static.add_argument('-v', '--verify', help='Check if all routes are parsed correctly', action='store_true', required=False)
    parser_static.set_defaults(which='file')

    return vars(parser.parse_args())


def main():

    args = parse_arguments()

    if args["which"] == "monitor":
        if args["sleep"] is None:
            sleep = 10
        else:
            sleep = args["sleep"]

        monitor_routes(args["device"], args["command"], args["command"], chk_parsed_routes=True, sleep=sleep, loop=True)
    elif args["which"] == "compare":

        compare_routes(args["device_a"], args["device_b"], args["command_a"], args["command_b"], args["verify"])
    elif args["which"] == "file":

        file_compare_routes(args["file_a"], args["file_b"], args["verify"])


#:TODO add checking for commands that are allowed to enter
#:TODO restrict pool interval
#:TODO display error when connecting device
#: TODO allow to save files to local folder, and change naming for log file
#: TODO add inet.4 table to blacklist; solve input for blacklist; dodati da se moze iskljuciti tip tabele
if __name__ == "__main__":
    main()
