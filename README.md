Keywords: Python, Multithreading, Web server implementation

📝 Task Objective
Create a web server for the automatic control of remote robots. The robots will autonomously register with the server, which will then guide them towards the center of a coordinate system. For testing purposes, each robot starts at random coordinates and attempts to reach the coordinate [0,0]. Upon reaching the target coordinate, the robot must retrieve a secret. On the way to the goal, robots may encounter obstacles that they must navigate around. The server is capable of guiding multiple robots simultaneously and implements a flawless communication protocol.

🤖 Robot Navigation:
Robot Registration:

Robots autonomously connect to the server to receive navigation instructions.
Starting Position:

Each robot begins at a random coordinate within the coordinate system.
Target Coordinate:

The objective for each robot is to reach the [0,0] coordinate.
Secret Retrieval:

Once at [0,0], the robot must retrieve a secret.
Obstacle Avoidance:

Robots may encounter obstacles that they need to navigate around while moving towards the target.
⚙️ Server Requirements:
Multi-Robot Navigation:

The server must be capable of navigating multiple robots simultaneously.
Communication Protocol:

The server must implement and handle the communication protocol flawlessly, ensuring that all navigation commands and status updates are correctly transmitted between the server and the robots.
