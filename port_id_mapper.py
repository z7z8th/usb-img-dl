import os
import threading
import cPickle as pickle

class port_id_mapper(object):
    lock = threading.Lock()
    id_map = {}
    default_file = "id_map.dict"

    @staticmethod
    def init():
        if os.path.exists(port_id_mapper.default_file):
            port_id_mapper.load()

    @staticmethod
    def map_new(port_id):
        assert(port_id not in port_id_mapper.id_map)
        user_id = len(port_id_mapper.id_map) + 1
        port_id_mapper.id_map[port_id] = user_id
        port_id_mapper.dump()

        
    @staticmethod
    def load(file = None):
        print "(II) load port_id_mapper"
        if not file:
            file = port_id_mapper.default_file
        with open(file, 'rb') as f:
            port_id_mapper.id_map = pickle.load(f)

            
    @staticmethod
    def dump(file = None):
        if not file:
            file = port_id_mapper.default_file
        with open(file, 'wb') as f:
            pickle.dump(port_id_mapper.id_map, f)

            
    @staticmethod
    def get_user_id(port_id):
        with port_id_mapper.lock:
            if port_id not in port_id_mapper.id_map:
                port_id_mapper.map_new(port_id)
            return port_id_mapper.id_map[port_id]

    @staticmethod
    def dump_to_stdout():
        print port_id_mapper.id_map

port_id_mapper.init()


if __name__ == '__main__':
    port_id_mapper.dump()
    port_id_mapper.get_user_id('\x89\x11\x02\x90')
    port_id_mapper.get_user_id('\x01\x03\x07')
    port_id_mapper.dump_to_stdout()
    port_id_mapper.dump()
