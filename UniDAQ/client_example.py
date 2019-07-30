if __name__ == "__main__":
    from socket_connections import Client_
    client = Client_("127.0.0.2", "65432")
    client.send_message("It works!!!")
    client.send_message("It works!!!")
    client.send_message("It works!!!")

