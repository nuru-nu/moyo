
import { Kinect } from './kinect.js'

const network = function () {
  const data = {
    signals: {
      people: [],
    },
  }

  const listeners = { signals: new Set() }

  function tick() {
    Array.from(listeners.signals).forEach(listener => listener(data.signals))
    setTimeout(tick, 20)
  }
  tick()

  return {
    listenJson: function (which, listener) {
      listeners[which].add(listener)
    },
    sender: function ({ people_override }) {
      if (people_override) data.signals.people = people_override
    },
  }
}()

Kinect('#kinect', { network })
