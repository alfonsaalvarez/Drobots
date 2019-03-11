import sys

import Ice

Ice.loadSlice('factory.ice --all -I .')
Ice.loadSlice('container.ice --all -I .')
import drobots
import Services
import socket
import math

class RobotControllerI(drobots.RobotFactory):
	def make(self, robot, key, current = None):
		if (robot.ice_isA("::drobots::Attacker")):
			servant = RobotControllerAttacker(robot, key)
		else (robot.ice_isA("::drobots::Defender")):
			servant = RobotControllerDefender(robot, key)

		robotProxy = current.adapter.addWithUUkey(servant)
		prx_key = robotProxy.ice_getkeyentity()
		direct_prx = current.adapter.createDirectProxy(prx_key)
		robotProxy = drobots.RobotControllerPrx.uncheckedCast(robotProxy)

		print("Robot proxy: {} \n".format(robotProxy))

		return robotProxy

	def makeDetector(self, key, current = None):
		servant = DetectorController(key)
		detectorProxy = current.adapter.addWithUUkey(servant)
		prx_key = detectorProxy.ice_getkeyentity()
		direct_prx = current.adapter.createDirectProxy(prx_key)
		detectorProxy = drobots.DetectorControllerPrx.uncheckedCast(detectorProxy)

		print("Detector proxy: {} \n".format(detectorProxy))

		return detectorProxy

class Strategy(Ice.Application):

	# We want to move the defender robot to the nearest corner so we calculate where to move
	def moveRobotToCorner(self, position, current = None):
		distanceToLD = self.distanceToPoint(position, 0, 0)
		distanceToRD = self.distanceToPoint(position, 399, 0)
		distanceToLT = self.distanceToPoint(position, 0, 399)
		distanceToRT = self.distanceToPoint(position, 399, 399)

		minDistance = min(distanceToLD, distanceToLT, distanceToRD, distanceToRT)

		if(minDistance == distanceToLD):
			corner = (0, 0)
		elif (minDistance == distanceToLT):
			corner = (0, 399)
		elif (minDistance == distanceToRD):
			corner = (399, 0)
		else:
			corner = (399, 399)

		return corner

	# We want to move the complete robots to the mkeydle point of each battlefield skeye, starting by the nearest
	def getNearestPoint(self, position, current = None):
		# We want to move the robot to the nearest corner
		distanceToDown = self.distanceToPoint(position, 200, 0)
		distanceToRight = self.distanceToPoint(position, 399, 200)
		distanceToUp = self.distanceToPoint(position, 200, 399)
		distanceToLeft = self.distanceToPoint(position, 0, 200)

		minDistance = min(distanceToDown, distanceToRight, distanceToUp, distanceToLeft)

		if(minDistance == distanceToDown):
			point = (200, 0)
		elif (minDistance == distanceToRight):
			point = (399, 200)
		elif (minDistance == distanceToUp):
			point = (200, 399)
		else:
			point = (0, 200)

		return point

	def distanceToPoint(self, position, coordenateX, coordenateY, current = None):
		relativeDistanceX = coordenateX - position.x
		relativeDistanceY = coordenateY - position.y
		distanceDestination = math.hypot(relativeDistanceX, relativeDistanceY)

		return distanceDestination

	def angleToPoint(self, position, coordenateX, coordenateY, current = None):
		relativeDistanceX = coordenateX - position.x
		relativeDistanceY = coordenateY - position.y
		angle = (int(math.degrees(math.atan2(relativeDistanceY, relativeDistanceX)) % 360.0))

		return angle

class RobotControllerDefenderI(drobots.RobotControllerDefender):
	def __init__(self, bot, container, key):
		self.robot = bot
		self.key = key
		self.enemies = 0
		self.robotsContainer = container
		self.companions = {}
		self.detectors = {}
		self.arrivalToCorner = False
		self.selectedCorner = False
		self.corner = (0,0)
		self.rangeToScan = (0,0)
		self.angleToScan = 0

		print("I'm the defender robot {}. \n".format(self.key))

	def turn(self, current = None):
		print("Defender robot{} turn. \n".format(self.key))

		# Get the robot's data
		pos = self.robot.location()
		energy = self.robot.energy()
		damage = self.robot.damage()
		speed = self.robot.speed()

		if not self.arrivalToCorner:
			if not self.selectedCorner:
				# We move the robot to the nearest corner
				self.corner = Strategy().moveRobotToCorner(pos)
				self.selectedCorner = True

				#We set the range to scan, because otherwise it would scan out of the battlefield
				if(self.corner[0] == 0 and self.corner[1] == 0):
					self.rangeToScan = (0, 90)
				elif(self.corner[0] == 399 and self.corner[1] == 0):
					self.rangeToScan = (90, 180)
				elif(self.corner[0] == 0 and self.corner[1] == 399):
					self.rangeToScan = (180, 270)
				else:
					self.rangeToScan = (270, 359)

				self.angleToScan = self.rangeToScan[0]

			print ("I'm moving to corner {}.".format(self.corner))
			print("From the current position {} {}.".format(pos.x, pos.y))

			distanceDestination = Strategy().distanceToPoint(pos, self.corner[0], self.corner[1])
			angle = Strategy().angleToPoint(pos, self.corner[0], self.corner[1])
			print("With the angle {} to reach destination.\n".format(angle))
			speed = 100

			if distanceDestination < 10:
				speed = max(min(100, self.robot.speed() / (10 - distanceDestination)), 1)

			if distanceDestination > 10 && self.robot.energy() > 60:
				self.robot.drive(angle, speed)
				self.robot.energy -= 60

			if distanceDestination == 0:
				self.robot.drive(angle, 0)
				self.robot.energy -= 1
				self.arrivalToCorner = True
		else:

			wkeye = 20
			detectedRobots = self.robot.scan(self.angleToScan, wkeye)
			self.robot.energy -= 10
			print("I'm scanning with the angle {}\n".format(self.angleToScan))
			print("The number of detected robots is = {}.\n".format(detectedRobots))
			self.angleToScan = self.angleToScan + 20

			if self.angleToScan >= self.rangeToScan[1]:
				self.angleToScan = self.rangeToScan[0]

		# Get the updated robot's location
		pos = self.robot.location()
		self.robot.energy -= 1

		# Send my updated position to my companions
		self.counter = 1
		while self.counter <= 4:
			if self.counter != self.key:
				robotProxy = self.robotsContainer.getProxy("robot" + str(self.counter))
				companion = drobots.RobotControllerCompletePrx.uncheckedCast(robotProxy)
				companion.position(pos, self.key)
			self.counter += 1

	def robotDestroyed(self, current = None):
		print("Defender robot {} has been destroyed".format(self.key))

	def position(self, pointTransmitter, keyTransmitter, current = None):
		self.companions[keyTransmitter] = pointTransmitter

	def detectorEnemies(self, keyDetector, pointTransmitter, enemies, current = None):
		# The tuple detectorInfo contains the point and the enemies found by a detector
		self.detectorInfo = (pointTransmitter, enemies)

		# The detectors contains all detector's info
		self.detectors[keyDetector] = self.detectorInfo

class RobotControllerAttackerI(drobots.RobotControllerAttacker):
	def __init__(self, bot, container, key):
		self.robot = bot
		self.key = key
		self.enemies = 0
		self.robotsContainer = container
		self.companions = {}
		self.detectors = {}
		self.arrivalToCentre = False
		self.rangeToShoot = (0,360)
		self.angleToShoot = 0

		print("I'm the attacker robot {}. \n".format(self.key))

	def turn(self, current = None):
		print("Attacker robot {} turn. \n".format(self.key))

		# Get the robot's data
		pos = self.robot.location()
		energy = self.robot.energy()
		damage = self.robot.damage()
		speed = self.robot.speed()

		if not self.arrivalToCentre:
			#We set the centre coordenates as we want the attacker to move to the centre
			coordenateX = 200
			coordenateY = 200
			distanceDestination = Strategy().distanceToPoint(pos, coordenateX, coordenateY)
			print("I'm moving to the center of the battlefield.")
			angle = Strategy().angleToPoint(pos, coordenateX, coordenateY)
			print("With the angle {} to reach destination\n".format(angle))
			speed = 100

			if distanceDestination < 10:
				speed = max(min(100, self.robot.speed() / (10 - distanceDestination)), 1)

			if distanceDestination > 10 && self.robot.energy() > 60:
				self.robot.drive(angle, speed)
				self.robot.energy -= 60

			if distanceDestination == 0:
				self.robot.drive(angle, 0)
				self.robot.energy -= 1
				self.arrivalToCentre = True
				print("Now, I'm in the centre. Let's start shooting!\n")
		else:

			self.angleToShoot = self.angleToShoot + 45

			if self.angleToShoot >= self.rangeToShoot[1]:
				self.angleToShoot = self.rangeToShoot[0]

			distanceToShoot = 100

			valkeyShoot = self.robot.cannon(self.angleToShoot, distanceToShoot)

			if valkeyshoot:
				print("Fine! The shoot has hurt at least one enemy!")
			else:
				print("Sorry, there were no enemies near...")

		# Get the updated robot's location
		pos = self.robot.location()

		# Send my updated position to my companions
		self.counter = 1
		while self.counter <= 4:
			if self.counter != self.key:
				robotProxy = self.robotsContainer.getProxy("robot" + str(self.counter))
				companion = drobots.RobotControllerCompletePrx.uncheckedCast(robotProxy)
				companion.position(pos, self.key)
			self.counter += 1

	def robotDestroyed(self, current = None):
		print("Attacker robot {} has been destroyed".format(self.key))

	def position(self, pointTransmitter, keyTransmitter, current = None):
		self.companions[keyTransmitter] = pointTransmitter

	def detectorEnemies(self, keyDetector, pointTransmitter, enemies, current = None):
		# The tuple detectorInfo contain the point and the enemies found by a detector
		self.detectorInfo = (pointTransmitter, enemies)

		# The detectors contains all detector's info
		self.detectors[keyDetector] = self.detectorInfo

class DetectorControllerI(drobots.DetectorController):
	def __init__(self, key):
		self.robotsContainer = container
		self.key = key

	def alert(self, pos, enemies, current = None):
		print("Eureka! The detector {} has found {} enemies in the point {}. \n".format(self.key, enemies, pos))

		# Send the number of the enemies to the companion robots
		self.counter = 1
		while self.counter <= 4:
			robotProxy = self.robotsContainer.getProxy("robot" + str(self.counter))
			companion = drobots.RobotControllerCompletePrx.uncheckedCast(robotProxy)
			companion.detectorEnemies(self.key, pos, enemies)
			self.counter += 1

class Server(Ice.Application):
	def run(self, argv):
		broker = self.communicator()
		adapter = broker.createObjectAdapter("RobotFactoryAdapter")

		servant = RobotControllerI()
		proxyFactory = adapter.add(servant, broker.stringTokeyentity("robotFactory"))
		print("I'm the factory: {} \n".format(proxyFactory))

		factory = drobots.RobotFactoryPrx.uncheckedCast(proxyFactory)

		factoriesContainer = Functions().getContainer(0)

		key = len(factoriesContainer.list()) + 1
		factoriesContainer.link("factory"+str(key), factory)

		sys.stdout.flush()

		adapter.activate()
		self.shutdownOnInterrupt()
		broker.waitForShutdown()

		return 0

sys.exit(Server().main(sys.argv))
