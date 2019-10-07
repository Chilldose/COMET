if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.debug('This is a log message.')
    from socket_connections import Client_
    client = Client_("127.0.0.2", "65432")
    response = client.send_request("plot_data", {"Plot":"IV"})
    print(response)

