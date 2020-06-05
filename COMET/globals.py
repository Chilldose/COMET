# Defining the Queue Objects for data sharing need to be here, than the main knows them to!!!
# TODO: This is very bad implemented and causes confusions find a better way to implement queues!!!!
import queue

global message_to_main
global message_from_main
global queue_to_GUI


message_to_main = queue.Queue()
message_from_main = queue.Queue()
queue_to_GUI = queue.Queue()
