#include <drobots.ice>

module drobots {
  interface Factory {
    RobotController* make(Robot* bot, int id);
    DetectorController* makeDetector (int id);
  };
};
