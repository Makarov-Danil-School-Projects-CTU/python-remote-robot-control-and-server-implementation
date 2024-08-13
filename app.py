#gitlab repository https://gitlab.fit.cvut.cz/makardan/psi-semestral-work
import socket
import threading


SIZE = 1024
UTF_8 = 'utf-8'
HOST = 'localhost'
PORT = 5555
# server variables
SERVER_MOVE = '102 MOVE\a\b'.encode(UTF_8)
SERVER_TURN_LEFT = '103 TURN LEFT\a\b'.encode(UTF_8)
SERVER_TURN_RIGHT = '104 TURN RIGHT\a\b'.encode(UTF_8)
SERVER_PICK_UP = '105 GET MESSAGE\a\b'.encode(UTF_8)
SERVER_LOGOUT = '106 LOGOUT\a\b'.encode(UTF_8)
SERVER_KEY_REQUEST = '107 KEY REQUEST\a\b'.encode(UTF_8)
SERVER_OK = '200 OK\a\b'.encode(UTF_8)
SERVER_LOGIN_FAILED = '300 LOGIN FAILED\a\b'.encode(UTF_8)
SERVER_SYNTAX_ERROR = '301 SYNTAX ERROR\a\b'.encode(UTF_8)
SERVER_LOGIC_ERROR = '302 LOGIC ERROR\a\b'.encode(UTF_8)
SERVER_KEY_OUT_OF_RANGE_ERROR = '303 KEY OUT OF RANGE\a\b'.encode(UTF_8)
server_keys = {
    0: 23019,
    1: 32037,
    2: 18789,
    3: 16443,
    4: 18189
}
client_keys = {
    0: 32037,
    1: 29295,
    2: 13603,
    3: 29533,
    4: 21952
}
DIRECTION_UP = 0
DIRECTION_RIGHT = 1
DIRECTION_DOWN = 2
DIRECTION_LEFT = 3
TIMEOUT = 1
TIMEOUT_RECHARGING = 5
CLIENT_RECHARGING = 'RECHARGING'
CLIENT_FULL_POWER = 'FULL POWER'
#Errors
class ServerKeyOutOfRangeError(Exception):
    pass
class ServerSyntaxError(Exception):
    pass
class ServerLoginFailedError(Exception):
    pass
class ServerLogicError(Exception):
    pass
class ServerSocketTimeout(Exception):
    pass
class Robot:
    def __init__(self, name):
        self.name = name
        self.x = None
        self.y = None
        self.prev_x = None
        self.prev_y = None
        self.direction = None


    def parse_coordinates(self, coordInput):
        # splitting 'OK 2323 -231\a\b' for example
        coords_array = coordInput.split(' ')
        if len(coords_array) > 3:
            raise ServerSyntaxError
        # testing the string numbers
        if not self.test_num(coords_array[1]) or not self.test_num(coords_array[2]):
            raise ServerSyntaxError

        self.prev_x = self.x
        self.prev_y = self.y
        self.x = coords_array[1]
        self.y = coords_array[2]
        self.calculate_direction()

    def has_moved(self):
        return self.prev_x != self.x or self.prev_y != self.y

    def calculate_direction(self):
        # calculation of a direction, based on actual and previous coordinates
        if self.prev_x and int(self.x) > int(self.prev_x):
            self.direction = DIRECTION_RIGHT
        elif self.prev_x and int(self.x) < int(self.prev_x):
            self.direction = DIRECTION_LEFT
        elif self.prev_y and int(self.y) > int(self.prev_y):
            self.direction = DIRECTION_UP
        elif self.prev_y and int(self.y) < int(self.prev_y):
            self.direction = DIRECTION_DOWN

    def recalculate_direction(self):
        # always turning to right
        if self.direction == 3:
            self.direction = 0
        else:
            self.direction += 1


    def recalculate_path(self):
        # the main movement logic of a robot
        if int(self.x) > 0:
            if self.direction != DIRECTION_LEFT:
                self.recalculate_direction()
                return SERVER_TURN_RIGHT
            return SERVER_MOVE
        elif int(self.x) < 0:
            if self.direction != DIRECTION_RIGHT:
                self.recalculate_direction()
                return SERVER_TURN_RIGHT
            return SERVER_MOVE
        elif int(self.y) > 0:
            if self.direction != DIRECTION_DOWN:
                self.recalculate_direction()
                return SERVER_TURN_RIGHT
            return SERVER_MOVE
        elif int(self.y) < 0:
            if self.direction != DIRECTION_UP:
                self.recalculate_direction()
                return SERVER_TURN_RIGHT
            return SERVER_MOVE

        return SERVER_PICK_UP

    # testing input coordinates
    def test_num(self, num_str):
        for char in num_str:
            # if there are in our coordinates . or another symbols except '-' => we have an incorrect number
            if not char.isdigit() and char != '-':
                return False
        return True


class Server:
    def __init__(self):
        self.server_hash = None
        self.client_hash = None
        self.client = None
        self.robot = None
        self.ascii_sum = None
        self.buffer = ''


    def handle_connection(self):
        try:
            # our main handle function. we are doing 2 main steps: 1) doing auth 2) making the robot moves
            self.auth()
            self.move()
        except ServerKeyOutOfRangeError:
            self.client.send(SERVER_KEY_OUT_OF_RANGE_ERROR)
        except ServerLoginFailedError:
            self.client.send(SERVER_LOGIN_FAILED)
        except ServerSyntaxError:
            self.client.send(SERVER_SYNTAX_ERROR)
        except ServerLogicError:
            self.client.send(SERVER_LOGIC_ERROR)
        except ServerSocketTimeout:
                pass
        finally:
            self.client.close()

    def auth(self):
        # checking the name
        robot_name = self.parse_client_message(18)
        if not self.validate_robot_name(robot_name):
            raise ServerSyntaxError

        # creating robot instance
        self.robot = Robot(robot_name)
        self.client.send(SERVER_KEY_REQUEST)

        # getting the client key
        keyId = self.parse_client_message(3)
        if not keyId.isdigit():
            raise ServerSyntaxError
        elif not (0 <= int(keyId) <= 4):
            raise ServerKeyOutOfRangeError

        # calculating the hash
        server_hash = self.calculate_server_hash(robot_name, int(keyId))
        self.client.send(server_hash.encode(UTF_8))

        # comparing the hash
        client_hash = self.parse_client_message(7)
        if not client_hash.isdigit() or not (0 <= int(client_hash) < 65536):
            raise ServerSyntaxError
        if not self.compare_hash(int(client_hash), robot_name, int(keyId)):
            raise ServerLoginFailedError

        self.client.send(SERVER_OK)


    def move(self):
        # robot is without the coordinates. getting first steps...
        self.get_first_coordinates()
        self.move_robot()
        secret = self.parse_client_message(98)
        if secret:
            self.client.send(SERVER_LOGOUT)
            self.client.close()

    def get_first_coordinates(self):
        directions = [SERVER_TURN_RIGHT, SERVER_TURN_LEFT]
        # when robot spawns, it doesn't have any coordinates. we are doing 2 turns, to get actual and previous coordinates
        for direction in directions:
            self.client.send(direction)
            coords = self.parse_client_message(10)
            self.robot.parse_coordinates(coords)

        self.robot.calculate_direction()

        # intelligence...
        if not self.robot.has_moved():
            self.getAround()

    def getAround(self):
        # if we have a wall forward to us, then we must turn to right, do one step, turn to left and do one step
        directions = [SERVER_TURN_RIGHT, SERVER_MOVE, SERVER_TURN_LEFT, SERVER_MOVE]

        for direction in directions:
            self.client.send(direction)
            coords = self.parse_client_message(10)
            self.robot.parse_coordinates(coords)

    def move_robot(self):
        while True:
            # if robot was spawned at [0, 0] => we will take the secret
            if self.robot.x == 0 and self.robot.y == 0:
                self.client.send(SERVER_PICK_UP)
                break
            # if not => we are calculating the direction. we are going to move forward or turn right
            future_direction = self.robot.recalculate_path()

            # if we are at [0, 0] => picking up
            if future_direction == SERVER_PICK_UP:
                self.client.send(SERVER_PICK_UP)
                break

            self.client.send(future_direction)

            self.robot.parse_coordinates(self.parse_client_message(10))

            # if we have same coordinates 2 times => we have a wall forward to us => must turn around
            if future_direction == SERVER_MOVE and not self.robot.has_moved():
                self.getAround()

    # calculate a server hash
    def calculate_server_hash(self, robot_name, key_id):
        ascii_sum = sum(ord(c) for c in robot_name)
        server_hash = (ascii_sum * 1000 + server_keys[key_id]) % 65536
        self.ascii_sum = ascii_sum
        return str(server_hash) + '\a\b'

    # calculate a client hash
    def calculate_client_hash(self, robot_name, key_id):
        self.ascii_sum = sum(ord(c) for c in robot_name)
        return (self.ascii_sum * 1000 + client_keys[key_id]) % 65536

    # just a comparing hashes
    def compare_hash(self, client_hash, robot_name, key_id):
        calculated_hash = self.calculate_client_hash(robot_name, key_id)
        return client_hash == calculated_hash

    # parsing client input
    def parse_client_message(self, max_buffer_len):
        while True:
            # it will be split every iteration
            message, separator, remainder = self.buffer.partition('\a\b')
            # if we have a full command which ends like \a\b, then we go here
            if separator:
                # we cut the first correct commands ends with \a\b and update our buffer
                self.buffer = remainder

                if message == CLIENT_RECHARGING:
                    self.recharging()
                else:
                    return message
            # some kind of optimization. we can raise the error if partition buffer is longer than our limit
            elif len(self.buffer) > max_buffer_len:
                self.buffer = ''
                raise ServerSyntaxError
            else:
                # if we don't have full command, we are starting an infinity cycle
                while True:
                    try:
                        self.client.settimeout(TIMEOUT)
                        client_input = self.client.recv(SIZE).decode(UTF_8)
                        # updating the buffer +=
                        if client_input:
                            self.buffer += client_input
                            break
                    except socket.timeout:
                        self.buffer = ''
                        raise ServerSocketTimeout


    # recharging function
    def recharging(self):
        while True:
            try:
                self.client.settimeout(TIMEOUT_RECHARGING)
                client_input = self.client.recv(SIZE).decode(UTF_8)
                if not client_input:
                    continue
                #adding client input to buffer
                self.buffer += client_input
                message, _, self.buffer = self.buffer.partition('\a\b')
                if message == CLIENT_FULL_POWER:
                    break
                else:
                    raise ServerLogicError
            except socket.timeout:
                raise ServerSocketTimeout

    # validating robot name
    def validate_robot_name(self, robot_name):
        if len(robot_name) >= 19:
            raise ServerSyntaxError
        return True


def main():
    # create socket connection
    new_socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    new_socket_connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    new_socket_connection.bind((HOST, PORT))
    new_socket_connection.listen()
    while True:
        try:
            # accepting a new client
            client, address = new_socket_connection.accept()
            new_server = Server()
            new_server.client = client
            # creating a thread
            threading.Thread(target=new_server.handle_connection).start()
        except KeyboardInterrupt:
            try:
                if client:
                    client.close()
            except:
                pass
            break


if __name__ == '__main__':
    main()
