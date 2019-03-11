#!/usr/bin/env python3

import sys

import Ice

Ice.loadSlice('factory.ice --all -I .')
Ice.loadSlice('container.ice --all -I .')
import drobots
import Services
import random

class PlayerI(drobots.Player):
    """
    Player interface implementation.

    It responds correctly to makeController, win, lose or gameAbort.
    """
    def __init__(self, container):
        self.detector_controller = None
        self.mine_index = 0
        self.mines = [
            drobots.Point(x=100, y=100),
            drobots.Point(x=100, y=300),
            drobots.Point(x=300, y=100),
            drobots.Point(x=300, y=300),
        ]
        self.robotsContainer = container

    def makeController(self, bot, current = None):
        if self.robots == 0:
            print("Building the container of robots...")
            robot_container_prx = self.broker.stringToProxy('robots_container'+
            ' -t -e 1.1:tcp -h localhost -p 9004 -t 60000')
            containerRobot = \
            Services.ContainerPrx.checkedCast(robot_container_prx)
            containerRobot.setType("RobotContainer")
            self.robots_container = containerRobot
            container_prx = self.broker.stringToProxy('factory_container -t'+
            ' -e 1.1:tcp -h localhost -p 9004 -t 60000')
            containerFactory = Services.ContainerPrx.checkedCast(container_prx)
            containerFactory.setType("FactoryContainer")
            print("Building factories...")
            for i in range(0,4):
                string_prx = \
                'factory -t -e 1.1:tcp -h localhost -p 900'+str(i)+' -t 60000'
                factory_prx = self.broker.stringToProxy(string_prx)
                print(factory_prx)
                factory = Services.FactoryPrx.checkedCast(factory_prx)
                containerFactory.link(i, factory_prx)
                self.factory_container = containerFactory
                print("Make controller received bot {}".format(bot))

            i = self.robots % 4
            print('Building robot controller in factory nº' + str(i))
            factory_prx2 = self.factory_container.getElement(i)
            print(factory_prx2)
            factory = Services.FactoryPrx.checkedCast(factory_prx2)
            robot = factory.make(bot, self.robots_container, self.robots)
            self.robots += 1

            return robot

    def makeDetectorController(self, current = None):
        if self.detector_controller is not None:
                return self.detector_controller

        print("Make detector controller.")

        # Calculate the id of the detector, minus 3 due to id of robots
        id = len(self.robotsContainer.list()) - 3
        controller = Factory().makeDetector(id)
        object_prx = current.adapter.addWithUUID(controller)
        self.detector_controller = \
            drobots.DetectorControllerPrx.checkedCast(object_prx)

        return self.detector_controller

    def getMinePosition(self, current = None):
        x = random.randint(0, 399)
        y = random.randint(0, 399)
        pos = drobots.Point(x,y)

        while pos in self.mines:
            x = random.randint(0, 399)
            y = random.randint(0, 399)
            pos = drobots.Point(x,y)

        self.mines.append(pos)
        self.mine_index += 1

        return pos

    def win(self, current = None):
        """
        Received when we win the match
        """
        print("You win")
        current.adapter.getCommunicator().shutdown()

    def lose(self, current = None):
        """
        Received when we lose the match
        """
        print("You lose :-(")
        current.adapter.getCommunicator().shutdown()

    def gameAbort(self, current = None):
        """
        Received when the match is aborted (when there are not enough players
        to start a game, for example)
        """
        print("The game was aborted")
        current.adapter.getCommunicator().shutdown()


class ClientApp(Ice.Application):
    """
    Ice.Application specialization
    """
    def run(self, argv):
        """
        Entry-point method for every Ice.Application object.
        """

        broker = self.communicator()

        # Using PlayerAdapter object adapter forces to define a config file
        # where, at least, the property "PlayerAdapter.Endpoints" is defined
        adapter = broker.createObjectAdapter("PlayerAdapter")

        # Using "propertyToProxy" forces to define the property "GameProxy"
        game_prx = broker.propertyToProxy("GameProxy")
        game_prx = drobots.GamePrx.checkedCast(game_prx)

        # Using "getProperty" forces to define the property "PlayerName"
        name = broker.getProperties().getProperty("PlayerName")

        servant = PlayerI()
        player_prx = adapter.addWithUUID(servant)
        player_prx = drobots.PlayerPrx.uncheckedCast(player_prx)
        adapter.activate()

        print("Connecting to game {} with nickname {}".format(game_prx, name))

        try:
            game_prx.login(player_prx, name)

            self.shutdownOnInterrupt()
            self.communicator().waitForShutdown()

        except Exception as ex:
            print("An error has occurred: {}".format(ex))
            return 1

        return 0


if __name__ == '__main__':
    client = ClientApp()
    retval = client.main(sys.argv)
    sys.exit(retval)
