
class port_id_mapper(object):
    id_map = {}
    
    def __init__(self):
        pass

    def update(self, port_id):
        if port_id not in id_map:
            pass

    def load_from_file(self, file = None):
        if not file:
            pass


    def save_to_file(self):
        pass

    def get_user_id(self, port_id):
        if port_id not in id_map:
            update()
        return id_map[port_id]
