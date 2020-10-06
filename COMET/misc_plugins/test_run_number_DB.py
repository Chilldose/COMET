# This is a test return for the DB return
import argparse
parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--number', type=int,
                    help='an integer for the accumulator')
args = parser.parse_args()
print("RUN NUMBER \n{}".format(args.number))