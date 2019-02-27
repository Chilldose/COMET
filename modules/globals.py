# Defining the Queue Objects for data sharing need to be here, than the main knows them to!!!
# TODO: This is very bad implemented and causes confusions find a better way to implement queues!!!!
import Queue
global message_to_main
global message_from_main
global queue_to_GUI


message_to_main = Queue.Queue()
message_from_main = Queue.Queue()
queue_to_GUI = Queue.Queue()


